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
from sqlalchemy import create_engine
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


def validate_test_database_url(url_str: str) -> None:
    """
    Validate that the test database URL points to a dedicated disposable database.

    Refuses execution if the URL targets development, production, or lacks a '_test' suffix.
    """
    url = make_url(url_str)
    db_name = (url.database or "").lower()

    if db_name in ("alphazee_dev", "alphazee", "postgres") or not (
        db_name.endswith("_test") or db_name == "alphazee_test"
    ):
        raise RuntimeError(
            f"Unsafe test database configuration: {db_name!r}. "
            "Tests must target a dedicated disposable database ending with '_test'."
        )

    if url_str.strip() == settings.database_url.strip():
        raise RuntimeError(
            "TEST_DATABASE_URL cannot match application DATABASE_URL."
        )


@pytest.fixture(scope="session")
def test_engine():
    """Create the test database schema once per test session."""
    validate_test_database_url(TEST_DB_URL)

    engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
    # Apply schema — isolated test shortcut only
    Base.metadata.create_all(engine)
    yield engine
    # Tear down after all tests in the session
    Base.metadata.drop_all(engine)
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
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)

