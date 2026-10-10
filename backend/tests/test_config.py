"""
Tests for application configuration and environment variable loading.

Covers:
- ALLOWED_ORIGINS comma-separated parsing
- ALLOWED_ORIGINS JSON-array format parsing
- ALLOWED_ORIGINS whitespace handling and empty token stripping
- Default settings behavior
"""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings


def test_default_allowed_origins():
    """Verify default allowed origins include development localhost servers."""
    settings = Settings(_env_file=None)
    assert "http://localhost:5173" in settings.allowed_origins
    assert "http://localhost:3000" in settings.allowed_origins


def test_allowed_origins_comma_separated(monkeypatch):
    """Verify comma-separated ALLOWED_ORIGINS strings are correctly parsed into a list."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,https://alphazee.pk")
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.allowed_origins == [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://alphazee.pk",
        ]
    finally:
        get_settings.cache_clear()


def test_allowed_origins_whitespace_and_empty_tokens(monkeypatch):
    """Verify whitespace is trimmed and empty entries are ignored."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "  https://example.com , ,  https://app.example.com  ")
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.allowed_origins == [
            "https://example.com",
            "https://app.example.com",
        ]
    finally:
        get_settings.cache_clear()


def test_allowed_origins_json_format(monkeypatch):
    """Verify JSON array formatted ALLOWED_ORIGINS string is parsed correctly."""
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://alphazee.pk", "https://admin.alphazee.pk"]')
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.allowed_origins == [
            "https://alphazee.pk",
            "https://admin.alphazee.pk",
        ]
    finally:
        get_settings.cache_clear()


def test_environment_helpers():
    """Verify is_production and is_development helper properties."""
    dev_settings = Settings(app_env="development", _env_file=None)
    assert dev_settings.is_development is True
    assert dev_settings.is_production is False

    prod_settings = Settings(app_env="production", _env_file=None)
    assert prod_settings.is_development is False
    assert prod_settings.is_production is True


def test_validate_test_database_url_allowed():
    """Verify valid disposable test database URL passes validation."""
    from tests.conftest import validate_test_database_url

    app_url = "postgresql://alphazee:secret@localhost:5433/alphazee_dev"
    test_url = "postgresql://alphazee:secret@localhost:5433/alphazee_test"
    # Should not raise
    validate_test_database_url(test_url, app_url_str=app_url)


def test_validate_test_database_url_rejects_non_test_database():
    """Verify non-disposable and non-_test databases are rejected."""
    from tests.conftest import validate_test_database_url

    app_url = "postgresql://alphazee:secret@localhost:5433/alphazee_dev"

    for unsafe_db in ("alphazee_dev", "alphazee", "postgres", "production_db", "my_store"):
        with pytest.raises(RuntimeError, match="Unsafe test database configuration"):
            validate_test_database_url(f"postgresql://alphazee:secret@localhost:5433/{unsafe_db}", app_url_str=app_url)


def test_validate_test_database_url_rejects_credential_independent_match():
    """Verify test URL is rejected when targeting the same host/port/db even with different credentials."""
    from tests.conftest import validate_test_database_url

    app_url = "postgresql://admin_user:production_pass@localhost:5433/disposable_test"
    test_url = "postgresql://different_user:different_pass@localhost:5433/disposable_test"

    with pytest.raises(RuntimeError, match="matches application database name"):
        validate_test_database_url(test_url, app_url_str=app_url)


def test_validate_test_database_url_normalizes_localhost_and_ip():
    """Verify localhost and 127.0.0.1 are normalized and detected as matching targets."""
    from tests.conftest import validate_test_database_url

    app_url = "postgresql://u1:p1@127.0.0.1:5433/custom_test"
    test_url = "postgresql://u2:p2@localhost:5433/custom_test"

    with pytest.raises(RuntimeError, match="matches application database name"):
        validate_test_database_url(test_url, app_url_str=app_url)

