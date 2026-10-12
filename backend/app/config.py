from __future__ import annotations

from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables or .env file.

    All secrets (database credentials) stay server-side — never returned in
    API responses and never logged.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql://alphazee:changeme@localhost:5433/alphazee_dev"

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False
    app_title: str = "AlphaZee API"
    app_version: str = "0.1.0"
    test_checkout_enabled: bool = False

    @property
    def checkout_enabled(self) -> bool:
        """Public checkout remains closed until the later release decision."""
        url = make_url(self.database_url)
        return bool(
            self.test_checkout_enabled
            and self.app_env.lower() == "test"
            and url.get_backend_name() == "postgresql"
            and url.host in {"localhost", "127.0.0.1", "::1"}
            and (url.database or "").endswith("_test")
            and not url.query
        )

    @model_validator(mode="after")
    def validate_test_checkout(self):
        if self.test_checkout_enabled and not self.checkout_enabled:
            raise ValueError(
                "Test checkout requires APP_ENV=test and a loopback PostgreSQL "
                "DATABASE_URL ending in _test, without connection query overrides."
            )
        return self

    # ── Security & Authentication ─────────────────────────────────────────────
    # Deprecated compatibility input only. Never accepted as authentication.
    admin_api_key: str = Field(default="", exclude=True, repr=False)
    session_max_age_seconds: int = Field(default=28800, ge=300, le=28800)

    # ── Bank Transfer Configuration ───────────────────────────────────────────
    bank_name: str = "Meezan Bank Ltd."
    bank_account_title: str = "AlphaZee Private Limited"
    bank_account_number: str = "PENDING_CONFIGURATION"
    bank_iban: str = "PENDING_IBAN_CONFIGURATION"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In development: localhost Vite dev servers.
    # In production: set to the actual domain serving the frontend.
    allowed_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return []

    @model_validator(mode="after")
    def validate_owner_origins(self):
        from urllib.parse import urlsplit
        if not self.allowed_origins:
            raise ValueError("Configure at least one exact allowed origin.")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.path
                    or parsed.query or parsed.fragment or "*" in origin):
                raise ValueError("ALLOWED_ORIGINS must contain exact HTTP(S) origins without paths or wildcards.")
            if self.is_production and (parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
                raise ValueError("Production owner sessions require HTTPS deployment origins.")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance. Only reads the environment once."""
    return Settings()


# Module-level singleton — import this in other modules
settings = get_settings()
