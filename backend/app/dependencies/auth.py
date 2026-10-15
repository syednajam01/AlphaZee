"""Cookie-only owner authorization. Shared API keys never grant access."""
from dataclasses import dataclass
import re
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.auth import OwnerCredential, OwnerSession
from app.models.suppliers import UserAccount
from app.services.session_store import csrf_token, token_hash, utcnow


def cookie_name() -> str:
    if settings.checkout_lab:
        return 'alphazee_lab_owner_session'
    return '__Host-alphazee_owner' if settings.is_production else 'alphazee_owner_session'


def require_trusted_origin(request: Request):
    if request.headers.get('origin') not in settings.allowed_origins:
        raise HTTPException(403, 'Untrusted or missing request origin')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Cross-site owner requests are not permitted')


def require_session_token(request: Request) -> str:
    token = request.cookies.get(cookie_name(), '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise HTTPException(401, 'Invalid or missing owner session')
    return token


@dataclass
class OwnerPrincipal:
    session: OwnerSession
    owner: OwnerCredential
    token: str


def require_owner_session(request: Request, token: str = Depends(require_session_token),
                          db: Session = Depends(get_db)) -> OwnerPrincipal:
    statement = (select(OwnerSession, OwnerCredential)
        .join(OwnerCredential, OwnerCredential.user_id == OwnerSession.user_id)
        .join(UserAccount, UserAccount.id == OwnerCredential.user_id)
        .where(OwnerSession.token_hash == token_hash(token), OwnerSession.revoked_at.is_(None),
               OwnerSession.expires_at > utcnow(), OwnerCredential.enabled.is_(True), UserAccount.is_active.is_(True)))
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        require_trusted_origin(request)
        supplied = request.headers.get('x-csrf-token', '')
        if not secrets.compare_digest(supplied, csrf_token(token)):
            raise HTTPException(403, 'Invalid or missing CSRF token')
        statement = statement.with_for_update(of=OwnerSession)
    row = db.execute(statement).first()
    if row is not None and settings.is_production:
        user = db.get(UserAccount, row[1].user_id)
        if user.auth_subject.startswith('local-development-owner:'):
            raise HTTPException(401, 'Local development credentials cannot access production')
    if row is None:
        raise HTTPException(401, 'Invalid or missing owner session')
    return OwnerPrincipal(session=row[0], owner=row[1], token=token)
