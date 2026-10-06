"""
Health and readiness endpoints — GET /api/v1/health and GET /api/v1/ready.

Design rules:
- /health always returns 200 while the process is running. No database call.
- /ready performs a live SELECT 1 and returns 503 if the database is
  unreachable. The 503 body never includes credentials or internal details.
- Neither endpoint exposes environment variables or internal configuration.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import check_db_connection, get_db

router = APIRouter(tags=["diagnostics"])


# ── Response schemas ──────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness check",
    description=(
        "Returns 200 as long as the application process is running. "
        "Does not contact the database."
    ),
)
def health() -> HealthResponse:
    """Liveness probe — always 200 while the process is alive."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadyResponse,
    summary="Readiness check",
    responses={
        200: {"description": "Application and database are ready."},
        503: {"description": "Database is unavailable. No credentials exposed."},
    },
)
def ready(db: Session = Depends(get_db)) -> ReadyResponse:
    """
    Readiness probe — confirms the application can reach PostgreSQL.

    Returns 200 + {"status": "ready", "database": "connected"} on success.
    Returns 503 + {"detail": "Database unavailable"} on failure.
    Never surfaces the database URL, credentials, or internal error text.
    """
    if check_db_connection(db):
        return ReadyResponse(status="ready", database="connected")

    raise HTTPException(
        status_code=503,
        detail="Database unavailable",
    )
