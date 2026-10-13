"""Allocate shipments and move physical stock at dispatch with safe legacy quarantine.

Revision ID: d61f4b8c2a90
Revises: c4d8a71e29f0
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'd61f4b8c2a90'
down_revision = 'c4d8a71e29f0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('stock_reservations', sa.Column('legacy_stock_hold', sa.Boolean(),
        nullable=False, server_default=sa.text('false')))
    op.execute("UPDATE stock_reservations SET legacy_stock_hold=true WHERE stage='dispatched'")
    op.drop_index('idx_sr_open_stage', table_name='stock_reservations')
    op.create_index('idx_sr_open_stage', 'stock_reservations', ['supplier_variant_id', 'quantity'],
        postgresql_where=sa.text("stage IN ('held', 'confirmed') OR legacy_stock_hold = true"))

    op.add_column('stock_events', sa.Column('source_ref', sa.String(160)))
    op.create_index('uq_stock_events_source_ref', 'stock_events', ['source_ref'], unique=True,
        postgresql_where=sa.text('source_ref IS NOT NULL'))
    op.drop_constraint('ck_stock_events_reason', 'stock_events', type_='check')
    op.create_check_constraint('ck_stock_events_reason', 'stock_events',
        "reason IN ('manual_count', 'supplier_receipt', 'reservation_fulfilled', "
        "'reservation_cancelled', 'rto_return', 'adjustment_correction', 'dispatch', 'customer_return')")

    op.add_column('shipments', sa.Column('stock_reconciliation_status', sa.String(24),
        nullable=False, server_default='ready'))
    op.create_check_constraint('ck_shipments_stock_reconciliation_status', 'shipments',
        "stock_reconciliation_status IN ('ready', 'legacy_review', 'resolved')")
    op.execute("UPDATE shipments SET stock_reconciliation_status='legacy_review'")
    op.create_table('shipment_allocations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('shipment_id', UUID(as_uuid=True), sa.ForeignKey('shipments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reservation_id', UUID(as_uuid=True), sa.ForeignKey('stock_reservations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('received_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sellable_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('damaged_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('inspection_notes', sa.Text()),
        sa.Column('inspected_by_user_id', UUID(as_uuid=True)),
        sa.Column('inspected_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint('quantity > 0', name='ck_shipment_allocations_quantity_positive'),
        sa.CheckConstraint('received_quantity >= 0 AND received_quantity <= quantity',
                           name='ck_shipment_allocations_received_bounds'),
        sa.CheckConstraint('sellable_quantity >= 0 AND damaged_quantity >= 0 AND '
                           'sellable_quantity + damaged_quantity <= received_quantity',
                           name='ck_shipment_allocations_inspection_bounds'),
    )
    op.create_index('uq_shipment_allocations_reservation', 'shipment_allocations', ['reservation_id'], unique=True)
    op.create_index('idx_shipment_allocations_shipment', 'shipment_allocations', ['shipment_id'])

    op.add_column('order_returns', sa.Column('quantity', sa.Integer()))
    for name in ('received_quantity', 'sellable_quantity', 'damaged_quantity'):
        op.add_column('order_returns', sa.Column(name, sa.Integer(), nullable=False, server_default='0'))
    op.add_column('order_returns', sa.Column('inspection_state', sa.String(24),
        nullable=False, server_default='pending'))
    op.add_column('order_returns', sa.Column('inspection_notes', sa.Text()))
    op.add_column('order_returns', sa.Column('inspected_by_user_id', UUID(as_uuid=True)))
    op.add_column('order_returns', sa.Column('inspected_at', sa.DateTime(timezone=True)))
    op.execute("UPDATE order_returns SET inspection_state='legacy_review'")
    op.create_check_constraint('ck_order_returns_quantity_positive', 'order_returns', 'quantity IS NULL OR quantity > 0')
    op.create_check_constraint('ck_order_returns_received_bounds', 'order_returns',
        'received_quantity >= 0 AND (quantity IS NULL OR received_quantity <= quantity)')
    op.create_check_constraint('ck_order_returns_inspection_bounds', 'order_returns',
        'sellable_quantity >= 0 AND damaged_quantity >= 0 AND sellable_quantity + damaged_quantity <= received_quantity')
    op.create_check_constraint('ck_order_returns_inspection_state', 'order_returns',
        "inspection_state IN ('pending', 'legacy_review')")


def downgrade():
    op.drop_constraint('ck_order_returns_inspection_state', 'order_returns', type_='check')
    op.drop_constraint('ck_order_returns_inspection_bounds', 'order_returns', type_='check')
    op.drop_constraint('ck_order_returns_received_bounds', 'order_returns', type_='check')
    op.drop_constraint('ck_order_returns_quantity_positive', 'order_returns', type_='check')
    for name in ('inspected_at', 'inspected_by_user_id', 'inspection_notes',
                 'inspection_state', 'damaged_quantity', 'sellable_quantity', 'received_quantity', 'quantity'):
        op.drop_column('order_returns', name)
    op.drop_index('idx_shipment_allocations_shipment', table_name='shipment_allocations')
    op.drop_index('uq_shipment_allocations_reservation', table_name='shipment_allocations')
    op.drop_table('shipment_allocations')
    op.drop_constraint('ck_shipments_stock_reconciliation_status', 'shipments', type_='check')
    op.drop_column('shipments', 'stock_reconciliation_status')
    op.drop_constraint('ck_stock_events_reason', 'stock_events', type_='check')
    op.create_check_constraint('ck_stock_events_reason', 'stock_events',
        "reason IN ('manual_count', 'supplier_receipt', 'reservation_fulfilled', "
        "'reservation_cancelled', 'rto_return', 'adjustment_correction')")
    op.drop_index('uq_stock_events_source_ref', table_name='stock_events')
    op.drop_column('stock_events', 'source_ref')
    op.drop_index('idx_sr_open_stage', table_name='stock_reservations')
    op.create_index('idx_sr_open_stage', 'stock_reservations', ['supplier_variant_id', 'quantity'],
        postgresql_where=sa.text("stage NOT IN ('fulfilled', 'cancelled', 'returned')"))
    op.drop_column('stock_reservations', 'legacy_stock_hold')
