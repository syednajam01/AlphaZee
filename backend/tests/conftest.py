"""
conftest.py — Shared pytest fixtures for AlphaZee backend tests.

Test database strategy:
- Uses a dedicated disposable database (default `alphazee_test`) strictly separated
  from development and production.
- Validates the database URL before any operations to prevent accidental destruction
  of development or production databases.
- Applies schema via Base.metadata.create_all() as an isolated test-schema shortcut;
  this is NOT migration verification (migration verification requires the explicit
  Alembic upgrade/downgrade cycle).
- Each test runs in a transaction with savepoints (nested transactions) that is rolled
  back after the test — ensuring test isolation even after intentional IntegrityError tests.

Requirements:
- PostgreSQL running (docker compose up -d db).
- TEST_DATABASE_URL environment variable targeting an isolated test database.
- Run from backend/ directory: pytest tests/
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app

# ── Test database URL ─────────────────────────────────────────────────────────
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://alphazee:changeme@localhost:5433/alphazee_test",
)


def validate_test_database_url(url_str: str, app_url_str: str | None = None) -> None:
    """
    Validate that the test database URL points to a dedicated disposable database.

    Refuses execution if:
    1. The database name is an application/system database ('alphazee_dev', 'alphazee', 'postgres').
    2. The database name does not end with '_test'.
    3. The database name matches the application database name.
    4. The normalized (host, port, database) matches the application target,
       independently of credentials or username/password differences.
    """
    url = make_url(url_str)
    if (url.get_backend_name() != "postgresql"
            or url.host not in {"localhost", "127.0.0.1", "::1"}
            or url.query):
        raise RuntimeError(
            "Unsafe test database configuration: use loopback PostgreSQL "
            "without connection query overrides."
        )
    db_name = (url.database or "").lower()

    if db_name in ("alphazee_dev", "alphazee", "postgres") or not (
        db_name.endswith("_test") or db_name == "alphazee_test"
    ):
        raise RuntimeError(
            f"Unsafe test database configuration: {db_name!r}. "
            "Tests must target a dedicated disposable database ending with '_test'."
        )

    app_target_str = app_url_str if app_url_str is not None else settings.database_url
    app_url = make_url(app_target_str)
    app_db_name = (app_url.database or "").lower()

    if db_name == app_db_name:
        raise RuntimeError(
            f"Unsafe test database target: {db_name!r} matches application database name {app_db_name!r}."
        )

    def canonical_host(h: str | None) -> str:
        h_norm = (h or "localhost").lower()
        return "127.0.0.1" if h_norm in ("localhost", "127.0.0.1", "::1") else h_norm

    test_target = (canonical_host(url.host), url.port or 5432, db_name)
    app_target = (canonical_host(app_url.host), app_url.port or 5432, app_db_name)

    if test_target == app_target:
        raise RuntimeError(
            f"TEST_DATABASE_URL targets the same host/port/database ({test_target[0]}:{test_target[1]}/{test_target[2]}) "
            "as application DATABASE_URL independently of credentials."
        )



@pytest.fixture(scope="session")
def test_engine():
    """Create the test database schema once per test session."""
    validate_test_database_url(TEST_DB_URL)

    engine = create_engine(TEST_DB_URL, pool_pre_ping=True, hide_parameters=True)
    # A second pytest process must not drop the first process's test tables.
    try:
        with engine.connect() as guard:
            acquired = guard.scalar(text('SELECT pg_try_advisory_lock(71856292352852)'))
            guard.commit()
            if not acquired:
                raise RuntimeError('Another test suite is using this disposable database. Run sequentially or choose another TEST_DATABASE_URL.')
            try:
                Base.metadata.create_all(engine)
                try:
                    yield engine
                finally:
                    Base.metadata.drop_all(engine)
            finally:
                guard.execute(text('SELECT pg_advisory_unlock(71856292352852)'))
                guard.commit()
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    """
    Provide a per-test transactional session that is rolled back after each test.

    Uses savepoint isolation so intentional constraint violations do not
    break the outer transaction cleanup.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI test client with the test session injected via dependency override."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # This fixture already depends on a guarded disposable DB session.
    # Exercise order behavior independently of the production containment gate.
    from app.dependencies.checkout import require_checkout_enabled
    app.dependency_overrides[require_checkout_enabled] = lambda: None
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_checkout_enabled, None)


@pytest.fixture(scope="session")
def sample_password_hash():
    from app.services.passwords import hash_password
    return hash_password("SAMPLE-test-password-2026")


@pytest.fixture()
def sample_owner(db_session, sample_password_hash):
    from app.models.suppliers import UserAccount
    from app.models.auth import OwnerCredential
    user = UserAccount(auth_subject="local-owner:sample_owner", display_name="SAMPLE Owner", is_active=True)
    db_session.add(user)
    db_session.flush()
    owner = OwnerCredential(user_id=user.id, username="sample_owner", password_hash=sample_password_hash, enabled=True)
    db_session.add(owner)
    db_session.flush()
    return owner


@pytest.fixture()
def admin_headers(db_session, sample_owner):
    from app.dependencies.auth import cookie_name
    from app.services.session_store import issue_session, csrf_token
    token, _ = issue_session(db_session, sample_owner)
    return {"Cookie": f"{cookie_name()}={token}", "X-CSRF-Token": csrf_token(token), "Origin": "http://localhost:3000"}


@pytest.fixture()
def admin_client(db_session, admin_headers):
    """FastAPI test client pre-authenticated with valid owner admin key."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    from app.dependencies.checkout import require_checkout_enabled
    app.dependency_overrides[require_checkout_enabled] = lambda: None
    try:
        with TestClient(app, headers=admin_headers) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(require_checkout_enabled, None)


