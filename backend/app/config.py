from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_url: str = "postgresql://alphazee:changeme@localhost:5432/alphazee_dev"

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    debug: bool = False
    app_title: str = "AlphaZee API"
    app_version: str = "0.1.0"

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In development: localhost Vite dev servers.
    # In production: set to the actual domain serving the frontend.
    allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

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
