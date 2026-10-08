"""
Alembic environment configuration for AlphaZee.

Key behaviours:
- DATABASE_URL is loaded from app.config.settings — never from alembic.ini.
- Base.metadata is imported so autogenerate can diff the ORM models.
- Only online migration mode is supported (offline mode is not used).
- Tables are never created or dropped automatically on startup; all schema
  changes must go through an explicit migration file.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make sure `app` package is importable from the backend/ directory ─────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.models import Base  # imports all model modules, registering with Base

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override the URL from settings rather than from alembic.ini
# This ensures credentials never live in a version-controlled file.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # disposable — not reused after migration
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,        # detect column type changes
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Only online mode — offline is not needed for this project
run_migrations_online()
