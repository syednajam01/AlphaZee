"""Acquired units remain separately traceable within a supplier's physical balance."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OwnedStockLot(Base):
    __tablename__ = 'owned_stock_lots'
    __table_args__ = (CheckConstraint('remaining_quantity >= 0 AND unit_cost_minor >= 0', name='ck_owned_lot_counts'),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_variant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('supplier_variants.id', ondelete='RESTRICT'), index=True)
    source_ref: Mapped[str] = mapped_column(String(160), unique=True)
    remaining_quantity: Mapped[int] = mapped_column(Integer)
    unit_cost_minor: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class OwnedStockAllocation(Base):
    __tablename__ = 'owned_stock_allocations'
    __table_args__ = (CheckConstraint('quantity > 0', name='ck_owned_allocation_quantity'),)
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('stock_reservations.id', ondelete='CASCADE'), primary_key=True)
    lot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('owned_stock_lots.id', ondelete='RESTRICT'), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
