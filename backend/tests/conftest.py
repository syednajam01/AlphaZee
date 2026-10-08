"""
conftest.py — Shared pytest fixtures for AlphaZee backend tests.

Test database strategy:
- Uses a separate database named `alphazee_test` on the same local PostgreSQL
  instance as development.
- Each test session applies migrations fresh and tears down after.
- Each test runs in a transaction that is rolled back — this gives isolation
  without repeated migration runs.

Requirements:
- PostgreSQL running (docker compose up -d db).
- TEST_DATABASE_URL environment variable or the default alphazee_test DB.
- Run from backend/ directory: pytest tests/
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# ── Test database URL ─────────────────────────────────────────────────────────
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://alphazee:changeme@localhost:5433/alphazee_test",
)


@pytest.fixture(scope="session")
def test_engine():
    """Create the test database schema once per test session."""
    engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
    # Apply schema — this is the only place create_all is permitted (test-only)
    Base.metadata.create_all(engine)
    yield engine
    # Tear down after all tests in the session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    """
    Provide a per-test transactional session that is rolled back after each test.

    No data persists between tests.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """FastAPI test client with the test session injected via dependency override."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
