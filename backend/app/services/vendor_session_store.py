"""PostgreSQL-backed vendor sessions, throttling and token hashing."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import uuid

from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.vendor_portal import VendorLoginBucket, VendorSession, VendorUser


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return hmac.new(token.encode(), b"alphazee-vendor-csrf-v1", hashlib.sha256).hexdigest()


def consume_vendor_login_attempt(db: Session, username: str, client_address: str) -> bool:
    """Multi-process rate-limiting for vendor login attempts."""
    now = utcnow()
    cutoff = now - timedelta(minutes=15)
    db.execute(delete(VendorLoginBucket).where(VendorLoginBucket.window_started_at < now - timedelta(days=1)))
    limited = False
    for scope, limit in [(f"vendor_ip:{client_address}", 20), (f"vendor_account:{username.lower().strip()}", 5)]:
        expired = VendorLoginBucket.window_started_at <= cutoff
        statement = insert(VendorLoginBucket).values(
            key_hash=token_hash(scope), window_started_at=now, attempts=1
        )
        statement = statement.on_conflict_do_update(
            index_elements=["key_hash"],
            set_={
                "attempts": case((expired, 1), else_=VendorLoginBucket.attempts + 1),
                "window_started_at": case((expired, now), else_=VendorLoginBucket.window_started_at),
            },
        ).returning(VendorLoginBucket.attempts)
        count = int(db.scalar(statement) or 1)
        if count > limit:
            limited = True
            break
    db.commit()
    return limited


def issue_vendor_session(db: Session, vendor_user: VendorUser, previous_token: str | None = None) -> tuple[str, VendorSession]:
    """Issue a new vendor session token and revoke previous if provided."""
    now = utcnow()
    db.execute(delete(VendorSession).where(VendorSession.expires_at < now - timedelta(days=1)))
    if previous_token:
        db.execute(
            update(VendorSession)
            .where(VendorSession.token_hash == token_hash(previous_token))
            .values(revoked_at=now)
        )
    token = secrets.token_urlsafe(32)
    session = VendorSession(
        token_hash=token_hash(token),
        vendor_user_id=vendor_user.id,
        created_at=now,
        expires_at=now + timedelta(seconds=settings.session_max_age_seconds),
    )
    db.add(session)
    vendor_user.last_login_at = now
    db.flush()
    return token, session


def revoke_vendor_user_sessions(db: Session, vendor_user_id: uuid.UUID) -> int:
    """Revoke all active sessions for a vendor user (e.g. on password reset or account disable)."""
    now = utcnow()
    res = db.execute(
        update(VendorSession)
        .where(VendorSession.vendor_user_id == vendor_user_id, VendorSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.flush()
    return res.rowcount
