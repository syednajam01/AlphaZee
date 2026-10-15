from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies.auth import OwnerPrincipal, cookie_name, require_owner_session, require_trusted_origin
from app.models.auth import OwnerCredential
from app.models.suppliers import UserAccount
from app.services.passwords import DUMMY_HASH, verify_password
from app.services.session_store import consume_login_attempt, csrf_token, issue_session, utcnow

router = APIRouter(prefix='/auth', tags=['Owner Sessions'])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r'^[A-Za-z0-9_.@-]+$')
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator('username', mode='before')
    @classmethod
    def normalize(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


def session_response(principal: OwnerPrincipal):
    return {'username': principal.owner.username, 'csrf_token': csrf_token(principal.token),
            'expires_at': principal.session.expires_at}


@router.post('/login', dependencies=[Depends(require_trusted_origin)])
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    if consume_login_attempt(db, payload.username, request.client.host if request.client else 'unknown'):
        raise HTTPException(429, 'Too many login attempts. Try again later.', headers={'Retry-After': '900'})
    owner = db.scalar(select(OwnerCredential).join(UserAccount, UserAccount.id == OwnerCredential.user_id)
        .where(OwnerCredential.username == payload.username, OwnerCredential.enabled.is_(True), UserAccount.is_active.is_(True))
        .with_for_update(of=OwnerCredential))
    valid = verify_password(payload.password.get_secret_value(), owner.password_hash if owner else DUMMY_HASH)
    if owner and settings.is_production:
        user = db.get(UserAccount, owner.user_id)
        if user.auth_subject.startswith('local-development-owner:'):
            valid = False
    if not valid or owner is None:
        db.rollback()
        raise HTTPException(401, 'Invalid username or password')
    token, session = issue_session(db, owner, request.cookies.get(cookie_name()))
    result = session_response(OwnerPrincipal(session, owner, token))
    db.commit()
    response.set_cookie(cookie_name(), token, max_age=settings.session_max_age_seconds,
                        httponly=True, secure=settings.is_production, samesite='strict', path='/')
    return result


@router.get('/session')
def current_session(principal: OwnerPrincipal = Depends(require_owner_session)):
    return session_response(principal)


@router.post('/logout')
def logout(response: Response, principal: OwnerPrincipal = Depends(require_owner_session), db: Session = Depends(get_db)):
    principal.session.revoked_at = utcnow()
    db.commit()
    response.delete_cookie(cookie_name(), path='/', secure=settings.is_production, httponly=True, samesite='strict')
    return {'logged_out': True}
