"""Immutable cash evidence for courier settlements and customer refunds."""
from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CourierSettlementEntry(Base):
    __tablename__ = 'courier_settlement_entries'
    __table_args__ = (
        CheckConstraint('amount_minor > 0', name='ck_courier_settlement_amount_positive'),
        CheckConstraint("entry_type IN ('receipt', 'outbound_shipping', 'rto_shipping', 'other_deduction')",
                        name='ck_courier_settlement_entry_type'),
        Index('uq_courier_settlement_reference', 'reference', unique=True),
        Index('ix_courier_settlement_shipment', 'shipment_id'),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4, server_default=text('gen_random_uuid()'))
    shipment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
        ForeignKey('shipments.id', ondelete='RESTRICT'), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    final_statement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                                   server_default=text('false'))
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True),
        ForeignKey('user_accounts.id', ondelete='SET NULL'))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
        default=_utcnow, server_default=text('now()'))


class RefundExecution(Base):
    __tablename__ = 'refund_executions'
    __table_args__ = (
        CheckConstraint('amount_minor > 0', name='ck_refund_execution_amount_positive'),
        Index('uq_refund_execution_reference', 'reference', unique=True),
        Index('ix_refund_execution_return', 'return_id'),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4, server_default=text('gen_random_uuid()'))
    return_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
        ForeignKey('order_returns.id', ondelete='RESTRICT'), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True),
        ForeignKey('user_accounts.id', ondelete='SET NULL'))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
        default=_utcnow, server_default=text('now()'))
