"""Order-scoped credentials and HttpOnly sessions; phone numbers confer no access."""
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import re
import secrets
import uuid

from fastapi import HTTPException, Request, Response
from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models.order_access import OrderAccessAttempt, OrderAccessGrant, OrderAccessSession
from app.models.orders import Order


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def cookie_name() -> str:
    return '__Host-alphazee_order' if settings.is_production else 'alphazee_order_session'


def _cookie(response: Response, token: str) -> None:
    response.set_cookie(cookie_name(), token, max_age=30 * 86400, httponly=True,
                        secure=settings.is_production, samesite='strict', path='/')
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'


def issue_access(db: Session, order: Order, *, issued_by_user_id: uuid.UUID | None = None,
                 note: str | None = None) -> tuple[str, str]:
    """Return a one-time visible code and opaque session token, never the stored hashes."""
    now = _now()
    code, token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    grant = OrderAccessGrant(order_id=order.id, code_hash=_hash(code), created_at=now,
        expires_at=now + timedelta(days=180), issued_by_user_id=issued_by_user_id,
        issue_note=note)
    db.add(grant)
    db.flush()
    db.add(OrderAccessSession(token_hash=_hash(token), grant_id=grant.id,
                              created_at=now, expires_at=now + timedelta(days=30)))
    db.flush()
    return code, token


def set_order_session_cookie(response: Response, token: str) -> None:
    _cookie(response, token)


def _client_address(request: Request) -> str:
    address = request.client.host if request.client else 'unknown'
    try:
        private_proxy = ipaddress.ip_address(address).is_private
    except ValueError:
        private_proxy = False
    if private_proxy:
        forwarded = request.headers.get('x-forwarded-for', '').split(',')[0].strip()
        try:
            return str(ipaddress.ip_address(forwarded)) if forwarded else address
        except ValueError:
            pass
    return address


def consume_access_attempt(db: Session, request: Request, order_number: str) -> None:
    """Persist failures independently of authentication, including unknown orders."""
    now = _now()
    cutoff = now - timedelta(minutes=15)
    for scope, limit in ((f'ip:{_client_address(request)}', 30),
                         (f'order:{order_number.strip().upper()}', 10)):
        expired = OrderAccessAttempt.window_started_at <= cutoff
        stmt = insert(OrderAccessAttempt).values(key_hash=_hash(scope), window_started_at=now, attempts=1)
        count = db.scalar(stmt.on_conflict_do_update(index_elements=['key_hash'], set_={
            'attempts': case((expired, 1), else_=OrderAccessAttempt.attempts + 1),
            'window_started_at': case((expired, now), else_=OrderAccessAttempt.window_started_at),
        }).returning(OrderAccessAttempt.attempts))
        if int(count) > limit:
            db.commit()
            raise HTTPException(429, 'Too many access attempts. Try again later.')
    db.commit()


def exchange_access_code(db: Session, *, order_number: str, code: str,
                         request: Request, response: Response) -> Order:
    consume_access_attempt(db, request, order_number)
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', code):
        raise HTTPException(404, 'Order access unavailable')
    row = db.execute(select(Order, OrderAccessGrant).join(
        OrderAccessGrant, OrderAccessGrant.order_id == Order.id).where(
        Order.order_number == order_number.strip(), OrderAccessGrant.code_hash == _hash(code),
        OrderAccessGrant.revoked_at.is_(None), OrderAccessGrant.expires_at > _now())).first()
    if row is None:
        raise HTTPException(404, 'Order access unavailable')
    order, grant = row
    token = secrets.token_urlsafe(32)
    now = _now()
    db.add(OrderAccessSession(token_hash=_hash(token), grant_id=grant.id,
        created_at=now, expires_at=min(grant.expires_at, now + timedelta(days=30))))
    db.commit()
    _cookie(response, token)
    return order


def require_order_access(db: Session, request: Request, order_id: uuid.UUID | None = None,
                         order_number: str | None = None) -> Order:
    token = request.cookies.get(cookie_name(), '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise HTTPException(404, 'Order access unavailable')
    stmt = select(Order).join(OrderAccessGrant, OrderAccessGrant.order_id == Order.id).join(
        OrderAccessSession, OrderAccessSession.grant_id == OrderAccessGrant.id).where(
        OrderAccessSession.token_hash == _hash(token), OrderAccessSession.revoked_at.is_(None),
        OrderAccessSession.expires_at > _now(), OrderAccessGrant.revoked_at.is_(None),
        OrderAccessGrant.expires_at > _now())
    if order_id is not None:
        stmt = stmt.where(Order.id == order_id)
    if order_number is not None:
        stmt = stmt.where(Order.order_number == order_number.strip())
    order = db.scalar(stmt)
    if order is None:
        raise HTTPException(404, 'Order access unavailable')
    return order


def revoke_order_access(db: Session, order_id: uuid.UUID) -> int:
    now = _now()
    grants = db.scalars(select(OrderAccessGrant.id).where(
        OrderAccessGrant.order_id == order_id, OrderAccessGrant.revoked_at.is_(None))).all()
    if grants:
        db.execute(update(OrderAccessGrant).where(OrderAccessGrant.id.in_(grants)).values(revoked_at=now))
        db.execute(update(OrderAccessSession).where(OrderAccessSession.grant_id.in_(grants)).values(revoked_at=now))
    return len(grants)
