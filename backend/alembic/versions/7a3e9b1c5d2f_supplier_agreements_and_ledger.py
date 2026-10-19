"""Additive migration: supplier_agreements, supplier_ledger_entries, and supplier_payment_allocations.

Revision ID: 7a3e9b1c5d2f
Revises: 2c8a1b3e5f70
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '7a3e9b1c5d2f'
down_revision = '2c8a1b3e5f70'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create supplier_agreements table
    op.create_table(
        'supplier_agreements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payable_trigger', sa.String(32), nullable=False, server_default=sa.text("'manual'")),
        sa.Column('payment_terms_days', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("payable_trigger IN ('manual', 'confirmed_pickup', 'dispatch', 'delivery')", name='ck_supplier_agreements_trigger'),
        sa.CheckConstraint('payment_terms_days >= 0', name='ck_supplier_agreements_terms_nonnegative'),
    )
    op.create_index('idx_supplier_agreements_supplier_id', 'supplier_agreements', ['supplier_id'])

    # 2. Create supplier_ledger_entries table
    op.create_table(
        'supplier_ledger_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('entry_type', sa.String(32), nullable=False),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(16), nullable=False),
        sa.Column('source_event_key', sa.String(160), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('order_line_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('order_lines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('shipment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shipments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reference', sa.String(120), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'posted'")),
        sa.Column('reversal_entry_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('supplier_ledger_entries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('amount_minor > 0', name='ck_supplier_ledger_amount_positive'),
        sa.CheckConstraint("entry_type IN ('charge', 'credit_note', 'payment', 'advance', 'refund_received', 'opening_balance', 'adjustment')", name='ck_supplier_ledger_entry_type'),
        sa.CheckConstraint("direction IN ('credit', 'debit')", name='ck_supplier_ledger_direction'),
        sa.CheckConstraint("status IN ('posted', 'reversed')", name='ck_supplier_ledger_status'),
    )
    op.create_index('idx_supplier_ledger_supplier_id', 'supplier_ledger_entries', ['supplier_id'])
    op.create_index('idx_supplier_ledger_effective_date', 'supplier_ledger_entries', ['effective_date'])
    op.create_index('idx_supplier_ledger_order_id', 'supplier_ledger_entries', ['order_id'])
    op.create_index(
        'uq_supplier_ledger_source_key',
        'supplier_ledger_entries',
        ['source_event_key'],
        unique=True,
        postgresql_where=sa.text('source_event_key IS NOT NULL')
    )

    # 3. Create supplier_payment_allocations table
    op.create_table(
        'supplier_payment_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('payment_entry_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('supplier_ledger_entries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('charge_entry_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('supplier_ledger_entries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('allocated_amount_minor', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('allocated_amount_minor > 0', name='ck_payment_alloc_amount_positive'),
    )
    op.create_index('idx_payment_alloc_payment_id', 'supplier_payment_allocations', ['payment_entry_id'])
    op.create_index('idx_payment_alloc_charge_id', 'supplier_payment_allocations', ['charge_entry_id'])


def downgrade():
    op.drop_table('supplier_payment_allocations')
    op.drop_table('supplier_ledger_entries')
    op.drop_table('supplier_agreements')
