"""
SQLAlchemy ORM models for AlphaZee.

Models are defined in submodules and imported here so that:
  - Alembic's env.py can import Base.metadata via `from app.models import Base`
  - All model classes are registered with Base before any migration runs.

Phase 1: placeholder only. Models are added in Phase 2.
"""

from app.database import Base  # re-export so Alembic can find it

__all__ = ["Base"]
