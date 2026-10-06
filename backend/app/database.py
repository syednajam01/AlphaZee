from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# pool_pre_ping=True revalidates connections before use, avoiding stale
# connection errors after a database restart or idle timeout.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,       # logs SQL in development; silent in production
)

# ── Session factory ───────────────────────────────────────────────────────────
# autocommit=False — explicit transaction control.
# autoflush=False  — prevents implicit flushes before every query.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Declarative base ──────────────────────────────────────────────────────────
# All SQLAlchemy models inherit from this.
# Alembic reads Base.metadata for autogenerate — do NOT call
# Base.metadata.create_all() anywhere; migrations own schema creation.
class Base(DeclarativeBase):
    pass


# ── Request-scoped session dependency ────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session for a single request.

    The session is always closed in the finally block, even if the handler
    raises an exception. Use `db: Session = Depends(get_db)` in route functions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection(db: Session) -> bool:
    """
    Execute a trivial query to confirm the database is reachable.

    Returns True if the database responds, False on any error.
    Never raises — callers translate the result to HTTP status codes.
    """
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
