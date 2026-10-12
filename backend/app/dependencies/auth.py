"""
Authentication dependencies for AlphaZee API.

Guards privileged owner administrative endpoints (/api/v1/admin/*).
"""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings


def require_admin_key(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Enforce admin authentication for privileged endpoints.

    Accepts credentials via:
    1. Custom header: `X-Admin-Key: <token>`
    2. Standard authorization header: `Authorization: Bearer <token>`

    Uses constant-time comparison (secrets.compare_digest) to prevent timing attacks.
    Raises 401 Unauthorized if missing, empty, or mismatched.
    """
    provided_token: Optional[str] = None

    if x_admin_key and x_admin_key.strip():
        provided_token = x_admin_key.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            provided_token = parts[1]
        elif len(parts) == 1:
            provided_token = parts[0]

    expected_token = settings.admin_api_key

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return provided_token
