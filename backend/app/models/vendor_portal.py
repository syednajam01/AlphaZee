"""Vendor stock portal models: vendor users, authenticated sessions, throttling, and shortages."""
from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class VendorUser(Base):
    """Stock management user account for an external shop/vendor."""

    __tablename__ = "vendor_users"
    __table_args__ = (
        Index("idx_vu_vendor_id", "vendor_id"),
        Index("idx_vu_username", "username"),
        CheckConstraint("length(trim(username)) >= 3", name="ck_vendor_users_username_min_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("now()"),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    vendor = relationship("Supplier", foreign_keys=[vendor_id])
    user_account = relationship("UserAccount", foreign_keys=[user_id])
    sessions = relationship("VendorSession", back_populates="vendor_user", cascade="all, delete-orphan")


class VendorSession(Base):
    """Active or historical session token for an authenticated vendor user."""

    __tablename__ = "vendor_sessions"
    __table_args__ = (
        Index("idx_vs_vendor_user_id", "vendor_user_id"),
        Index("idx_vs_expires_at", "expires_at"),
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    vendor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    vendor_user: Mapped[VendorUser] = relationship("VendorUser", back_populates="sessions")


class VendorLoginBucket(Base):
    """Brute-force login attempt throttling for vendor endpoints."""

    __tablename__ = "vendor_login_buckets"
    __table_args__ = (
        Index("idx_vlb_window_started_at", "window_started_at"),
        CheckConstraint("attempts > 0", name="ck_vendor_login_attempts_positive"),
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    window_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )


class VendorStockShortage(Base):
    """Reported stock shortage when vendor physical count is lower than committed holds."""

    __tablename__ = "vendor_stock_shortages"
    __table_args__ = (
        Index("idx_vss_variant_id", "variant_id"),
        Index("idx_vss_vendor_id", "vendor_id"),
        Index("idx_vss_status", "status"),
        CheckConstraint("status IN ('open', 'resolved', 'cancelled')", name="ck_vss_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    variant_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("variants.id", ondelete="CASCADE"),
        nullable=False,
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )

    vendor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reported_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    held_reservations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    physical_on_hand_snapshot: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="open",
        server_default=text("'open'"),
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    resolution_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    variant = relationship("Variant", foreign_keys=[variant_id])
    vendor = relationship("Supplier", foreign_keys=[vendor_id])
    vendor_user = relationship("VendorUser", foreign_keys=[vendor_user_id])
