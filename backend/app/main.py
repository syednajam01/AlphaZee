"""
AlphaZee FastAPI application factory.

Architecture rules enforced here:
- CORS allows configured origins and explicit methods/headers for the storefront.
- The /docs and /redoc UIs are available only in development (debug=True).
- No database tables are created on startup — Alembic owns schema creation.
- The app is import-safe: all side effects (DB connection, etc.) happen at
  request time via FastAPI dependencies.
"""

from __future__ import annotations

from fastapi import FastAPI, Response, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin as admin_router
from app.api.v1 import auth as auth_router
from app.api.v1 import catalog as catalog_router
from app.api.v1 import coupons as coupons_router
from app.api.v1 import health as health_router
from app.api.v1 import orders as orders_router
from app.api.v1 import returns as returns_router
from app.config import settings

# ── Application instance ──────────────────────────────────────────────────────
# Swagger UI (/docs) and ReDoc (/redoc) are disabled in production to avoid
# exposing schema details. Set DEBUG=true in .env to enable them locally.
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "AlphaZee Commerce API.\n\n"
        "Endpoints for product catalog, storefront orders, payment verification, "
        "and owner inventory administration."
    ),
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allowed origins are configured via ALLOWED_ORIGINS in .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-CSRF-Token", "Idempotency-Key"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# All public endpoints are versioned under /api/v1.
app.include_router(health_router.router, prefix="/api/v1")
app.include_router(catalog_router.router, prefix="/api/v1")
app.include_router(orders_router.router, prefix="/api/v1")
app.include_router(coupons_router.router, prefix="/api/v1")
app.include_router(returns_router.router, prefix="/api/v1")
app.include_router(admin_router.router, prefix="/api/v1")
app.include_router(auth_router.router, prefix="/api/v1")


@app.middleware('http')
async def private_owner_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(('/api/v1/auth/', '/api/v1/admin/')):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    if request.url.path.startswith('/api/v1/auth/'):
        # Do not reflect passwords from invalid request bodies in errors.
        return JSONResponse({'detail': 'Invalid login request'}, status_code=422)
    return await request_validation_exception_handler(request, error)


@app.get("/api/v1/storefront/capabilities")
def storefront_capabilities(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {"checkout_enabled": settings.checkout_enabled,
            "test_mode": settings.checkout_enabled,
            "payment_methods": settings.permitted_payment_methods}



# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root() -> dict:
    """Minimal root response — confirms the API is reachable."""
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs": "/docs" if settings.debug else "disabled",
    }
