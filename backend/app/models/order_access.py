"""Hashed customer order credentials, scoped sessions and lookup throttles."""
from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrderAccessGrant(Base):
    __tablename__ = 'order_access_grants'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('user_accounts.id', ondelete='SET NULL'))
    issue_note: Mapped[str | None] = mapped_column(Text)


class OrderAccessSession(Base):
    __tablename__ = 'order_access_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    grant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('order_access_grants.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrderAccessAttempt(Base):
    __tablename__ = 'order_access_attempts'
    __table_args__ = (CheckConstraint('attempts > 0', name='ck_order_access_attempts_positive'),)
    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
