"""
shipments.py — SQLAlchemy ORM model for courier shipments, delivery tracking, COD remittance, and RTO lifecycle.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


ALLOWED_COURIER_CODES = {
    "trax",
    "leopards",
    "call_courier",
    "postex",
    "tcs",
    "mnp",
    "manual",
}

ALLOWED_SHIPMENT_STATUSES = {
    "booked",
    "dispatched",
    "in_transit",
    "out_for_delivery",
    "delivered",
    "rto_initiated",
    "rto_delivered",
    "cancelled",
}

ALLOWED_REMITTANCE_STATUSES = {
    "pending_remittance",
    "remitted",
    "not_applicable",
    "disputed",
}


class Shipment(Base):
    """
    Courier dispatch record tracking parcel status, delivery tracking numbers,
    COD cash collection, courier expense, and Return-to-Origin (RTO) lifecycle.
    """

    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint("shipping_cost_minor >= 0", name="ck_shipments_shipping_cost_nonnegative"),
        CheckConstraint("cod_amount_minor >= 0", name="ck_shipments_cod_amount_nonnegative"),
        CheckConstraint(
            "cod_remitted_amount_minor >= 0",
            name="ck_shipments_cod_remitted_amount_nonnegative",
        ),
        CheckConstraint(
            "rto_courier_cost_minor >= 0",
            name="ck_shipments_rto_courier_cost_nonnegative",
        ),
        CheckConstraint(
            f"courier_code IN ({', '.join(repr(c) for c in sorted(ALLOWED_COURIER_CODES))})",
            name="ck_shipments_courier_code",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in sorted(ALLOWED_SHIPMENT_STATUSES))})",
            name="ck_shipments_status",
        ),
        CheckConstraint(
            f"cod_remittance_status IN ({', '.join(repr(r) for r in sorted(ALLOWED_REMITTANCE_STATUSES))})",
            name="ck_shipments_cod_remittance_status",
        ),
        Index("idx_shipments_order_id", "order_id"),
        Index("idx_shipments_tracking", "courier_code", "tracking_number"),
        Index("idx_shipments_status", "status"),
        Index("idx_shipments_remittance_status", "cod_remittance_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    courier_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="manual",
        server_default=text("'manual'"),
    )

    tracking_number: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    tracking_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    shipping_cost_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="booked",
        server_default=text("'booked'"),
    )

    # Cash On Delivery & Remittance Tracking
    cod_amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    cod_remitted_amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    cod_remittance_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_remittance",
        server_default=text("'pending_remittance'"),
    )

    cod_remittance_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    cod_remitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # RTO Tracking
    rto_reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    rto_restocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rto_courier_cost_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # Operational Timestamps
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    # Relationship to parent Order
    order: Mapped[Order] = relationship(
        "Order",
        back_populates="shipments",
    )

    @property
    def remittance_amount_minor(self) -> int:
        return self.cod_remitted_amount_minor

    @property
    def is_partial_remittance(self) -> bool:
        return bool(
            self.cod_remittance_status == "remitted"
            and self.cod_amount_minor > 0
            and self.cod_remitted_amount_minor < self.cod_amount_minor
        )

    @validates("courier_code")
    def validate_courier(self, key: str, value: str) -> str:
        if value not in ALLOWED_COURIER_CODES:
            raise ValueError(
                f"Invalid courier code {value!r}. Must be one of {sorted(ALLOWED_COURIER_CODES)}."
            )
        return value

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in ALLOWED_SHIPMENT_STATUSES:
            raise ValueError(
                f"Invalid shipment status {value!r}. Must be one of {sorted(ALLOWED_SHIPMENT_STATUSES)}."
            )
        return value

    @validates("cod_remittance_status")
    def validate_remittance_status(self, key: str, value: str) -> str:
        if value not in ALLOWED_REMITTANCE_STATUSES:
            raise ValueError(
                f"Invalid remittance status {value!r}. Must be one of {sorted(ALLOWED_REMITTANCE_STATUSES)}."
            )
        return value
