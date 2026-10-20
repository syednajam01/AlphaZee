"""Vendor authorization dependency, cookie management, and scoped principal."""
from dataclasses import dataclass
import re
import secrets
import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.suppliers import Supplier, UserAccount
from app.models.vendor_portal import VendorSession, VendorUser
from app.services.vendor_session_store import csrf_token, token_hash, utcnow


def vendor_cookie_name() -> str:
    if settings.checkout_lab:
        return "alphazee_lab_vendor_session"
    return "__Host-alphazee_vendor" if settings.is_production else "alphazee_vendor_session"


def require_vendor_trusted_origin(request: Request):
    if request.headers.get("origin") not in settings.allowed_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Untrusted or missing request origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-site vendor requests are not permitted")


def require_vendor_session_token(request: Request) -> str:
    token = request.cookies.get(vendor_cookie_name(), "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing vendor session")
    return token


@dataclass
class VendorPrincipal:
    session: VendorSession
    vendor_user: VendorUser
    vendor: Supplier
    token: str

    @property
    def vendor_id(self) -> uuid.UUID:
        return self.vendor_user.vendor_id

    @property
    def username(self) -> str:
        return self.vendor_user.username

    @property
    def user_id(self) -> uuid.UUID:
        return self.vendor_user.user_id


def require_vendor_session(
    request: Request,
    token: str = Depends(require_vendor_session_token),
    db: Session = Depends(get_db),
) -> VendorPrincipal:
    statement = (
        select(VendorSession, VendorUser, Supplier)
        .join(VendorUser, VendorUser.id == VendorSession.vendor_user_id)
        .join(Supplier, Supplier.id == VendorUser.vendor_id)
        .where(
            VendorSession.token_hash == token_hash(token),
            VendorSession.revoked_at.is_(None),
            VendorSession.expires_at > utcnow(),
            VendorUser.is_active.is_(True),
        )
    )

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_vendor_trusted_origin(request)
        supplied = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(supplied, csrf_token(token)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or missing CSRF token")
        statement = statement.with_for_update(of=VendorSession)

    row = db.execute(statement).first()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid, expired, or inactive vendor session")

    session_obj, user_obj, supplier_obj = row
    return VendorPrincipal(
        session=session_obj,
        vendor_user=user_obj,
        vendor=supplier_obj,
        token=token,
    )
