import re
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.auth import OwnerCredential, OwnerSession
from app.models.suppliers import UserAccount
from app.services.passwords import hash_password
from app.services.session_store import utcnow


def provision_owner(db: Session, username: str, password: str, *, reset_password: bool = False):
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9_.@-]{3,100}', username):
        raise ValueError('Username must contain 3 to 100 letters, digits, _, ., @ or -.')
    password_hash = hash_password(password)
    owner = db.scalar(select(OwnerCredential).where(OwnerCredential.username == username).with_for_update())
    if owner:
        if not reset_password:
            raise ValueError('Owner already exists. Use --reset-password explicitly.')
        owner.password_hash = password_hash
        db.execute(update(OwnerSession).where(OwnerSession.user_id == owner.user_id).values(revoked_at=utcnow()))
    else:
        user = UserAccount(auth_subject=f'local-owner:{username}', display_name=username, is_active=True)
        db.add(user)
        db.flush()
        owner = OwnerCredential(user_id=user.id, username=username, password_hash=password_hash, enabled=True)
        db.add(owner)
    db.flush()
    return owner
