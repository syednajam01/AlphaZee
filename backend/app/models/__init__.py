"""
SQLAlchemy ORM models for AlphaZee.

Models are defined in submodules and imported here so that:
  - Alembic's env.py can import Base.metadata via `from app.models import Base`
  - All model classes are registered with Base before any migration runs.
"""

from app.database import Base  # re-export so Alembic can find it
from app.models.catalog import AvailabilityStatus, Collection, Product, Variant  # noqa: F401

__all__ = ["Base", "Collection", "Product", "Variant", "AvailabilityStatus"]

