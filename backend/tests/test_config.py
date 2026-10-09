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
