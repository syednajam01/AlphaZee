"""PostgreSQL-backed owner sessions and atomic, multi-process login limits."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from sqlalchemy import case, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.auth import OwnerCredential, OwnerLoginBucket, OwnerSession


def utcnow():
    return datetime.now(timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return hmac.new(token.encode(), b'alphazee-owner-csrf-v1', hashlib.sha256).hexdigest()


def consume_login_attempt(db: Session, username: str, client_address: str) -> bool:
    now = utcnow()
    cutoff = now - timedelta(minutes=15)
    db.execute(delete(OwnerLoginBucket).where(OwnerLoginBucket.window_started_at < now - timedelta(days=1)))
    limited = False
    # Fixed lock order avoids deadlocks. Both counters include successes so
    # a successful login cannot reset an attacker's per-IP allowance.
    for scope, limit in [(f'ip:{client_address}', 20), (f'account:{username}', 5)]:
        expired = OwnerLoginBucket.window_started_at <= cutoff
        statement = insert(OwnerLoginBucket).values(key_hash=token_hash(scope), window_started_at=now, attempts=1)
        statement = statement.on_conflict_do_update(index_elements=['key_hash'], set_={
            'attempts': case((expired, 1), else_=OwnerLoginBucket.attempts + 1),
            'window_started_at': case((expired, now), else_=OwnerLoginBucket.window_started_at),
        }).returning(OwnerLoginBucket.attempts)
        limited = int(db.scalar(statement)) > limit
        if limited:
            break  # Exhausted IPs cannot create unbounded username buckets.
    db.commit()  # Failed logins must retain their rate-limit counters.
    return limited


def issue_session(db: Session, owner: OwnerCredential, previous_token: str | None = None):
    now = utcnow()
    db.execute(delete(OwnerSession).where(OwnerSession.expires_at < now - timedelta(days=1)))
    if previous_token:
        db.execute(update(OwnerSession).where(OwnerSession.token_hash == token_hash(previous_token))
                   .values(revoked_at=now))
    token = secrets.token_urlsafe(32)
    session = OwnerSession(token_hash=token_hash(token), user_id=owner.user_id,
                           created_at=now, expires_at=now + timedelta(seconds=settings.session_max_age_seconds))
    db.add(session)
    db.flush()
    return token, session
