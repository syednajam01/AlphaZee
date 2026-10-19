"""
suppliers.py — SQLAlchemy ORM models for supplier identities and administrative management.

Schema:
- UserAccount: Administrative user identity (owner/operator).
- Supplier: Approved vendor/supplier supplying catalog products.
- SupplierMembership: Association mapping user accounts to suppliers with permissions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_SUPPLIER_STATUSES = {"active", "inactive", "suspended"}
ALLOWED_SUPPLIER_TYPES = {"external_vendor", "alphazee_internal"}
INTERNAL_SUPPLIER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class UserAccount(Base):
    """
    Administrative user account (owner / admin operator).
    """

    __tablename__ = "user_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    auth_subject: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
    )
    """External identity claim (e.g. JWT sub)."""

    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Human-readable operator name for audit display."""

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

    # Relationships
    memberships: Mapped[list[SupplierMembership]] = relationship(
        "SupplierMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<UserAccount id={self.id} auth_subject={self.auth_subject!r}>"


class Supplier(Base):
    """
    An approved local supplier for AlphaZee products.
    """

    __tablename__ = "suppliers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended')",
            name="ck_suppliers_status",
        ),
        CheckConstraint(
            "supplier_type IN ('external_vendor', 'alphazee_internal')",
            name="ck_suppliers_supplier_type",
        ),
        Index("idx_suppliers_status", "status"),
        Index("idx_suppliers_type", "supplier_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    """Trade name of the supplier."""

    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    """URL-safe identifier for admin portal routing."""

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )

    supplier_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="external_vendor",
        server_default=text("'external_vendor'"),
    )
    """'external_vendor' for third-party shops; 'alphazee_internal' for internal inventory source."""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Private owner notes (payment arrangements, contact info, WhatsApp number)."""

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

    # Relationships
    memberships: Mapped[list[SupplierMembership]] = relationship(
        "SupplierMembership",
        back_populates="supplier",
        cascade="all, delete-orphan",
    )
    variants: Mapped[list[SupplierVariant]] = relationship(
        "SupplierVariant",
        back_populates="supplier",
    )

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in ALLOWED_SUPPLIER_STATUSES:
            raise ValueError(
                f"Invalid supplier status {value!r}. Must be one of {sorted(ALLOWED_SUPPLIER_STATUSES)}."
            )
        return value

    @validates("supplier_type")
    def validate_supplier_type(self, key: str, value: str) -> str:
        if value not in ALLOWED_SUPPLIER_TYPES:
            raise ValueError(
                f"Invalid supplier type {value!r}. Must be one of {sorted(ALLOWED_SUPPLIER_TYPES)}."
            )
        return value

    def __repr__(self) -> str:
        return f"<Supplier id={self.id} slug={self.slug!r} status={self.status!r} type={self.supplier_type!r}>"


def get_or_create_internal_supplier(db) -> Supplier:
    """Return the designated internal inventory supplier for AlphaZee-managed stock."""
    from sqlalchemy import select
    sup = db.scalar(select(Supplier).where(Supplier.supplier_type == "alphazee_internal"))
    if sup is not None:
        return sup
    sup = db.scalar(select(Supplier).where(Supplier.slug == "alphazee-internal"))
    if sup is not None:
        sup.supplier_type = "alphazee_internal"
        db.flush()
        return sup
    sup = Supplier(
        id=INTERNAL_SUPPLIER_ID,
        name="AlphaZee In-House",
        slug="alphazee-internal",
        status="active",
        supplier_type="alphazee_internal",
        notes="Internal inventory source for AlphaZee-managed catalog stock",
    )
    db.add(sup)
    db.flush()
    return sup



class SupplierMembership(Base):
    """
    Mapping between administrative user accounts and suppliers with read/write access.
    """

    __tablename__ = "supplier_memberships"
    __table_args__ = (
        Index("idx_sm_supplier_id", "supplier_id"),
        Index("idx_sm_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        primary_key=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=text("now()"),
    )

    # Relationships
    user: Mapped[UserAccount] = relationship("UserAccount", back_populates="memberships")
    supplier: Mapped[Supplier] = relationship("Supplier", back_populates="memberships")

    def __repr__(self) -> str:
        return f"<SupplierMembership user_id={self.user_id} supplier_id={self.supplier_id} active={self.active}>"
