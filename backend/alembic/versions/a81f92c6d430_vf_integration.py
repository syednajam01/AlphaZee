"""Connect acquisition ownership and authoritative shipping without rewriting history."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a81f92c6d430'
down_revision = '6e4a2b8d0c1f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shipments', sa.Column('rto_cost_recorded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('order_returns', sa.Column('restocked_cost_minor', sa.Integer(), nullable=True))
    op.add_column('inventory_balances', sa.Column('ownership_review_required', sa.Boolean(), nullable=False, server_default=sa.false()))
    # Legacy products had no explicit vendor responsibility. Backfill only an unambiguous source.
    op.execute("""UPDATE products p SET stock_management_source='vendor_managed', vendor_id=source.supplier_id
        FROM (SELECT v.product_id, (array_agg(DISTINCT sv.supplier_id))[1] supplier_id
              FROM variants v JOIN supplier_variants sv ON sv.variant_id=v.id AND sv.active=true
              JOIN suppliers s ON s.id=sv.supplier_id GROUP BY v.product_id
              HAVING count(DISTINCT sv.supplier_id)=1 AND bool_and(s.supplier_type='external_vendor')) source
        WHERE p.id=source.product_id AND p.stock_management_source='alphazee_managed' AND p.vendor_id IS NULL""")
    op.execute("""UPDATE inventory_balances b SET ownership_review_required=true
        FROM supplier_variants sv JOIN variants v ON v.id=sv.variant_id
        JOIN products p ON p.id=v.product_id JOIN suppliers s ON s.id=sv.supplier_id
        WHERE b.supplier_variant_id=sv.id AND sv.active=true AND NOT (
            (p.stock_management_source='vendor_managed' AND p.vendor_id=sv.supplier_id) OR
            (p.stock_management_source='alphazee_managed' AND s.supplier_type='alphazee_internal'))""")
    # Old returned stock may have been resold already: never invent remaining lots.
    op.execute("UPDATE inventory_balances SET ownership_review_required=true WHERE on_hand > 0 AND supplier_variant_id IN (SELECT supplier_variant_id FROM stock_events WHERE reason IN ('customer_return','rto_return'))")
    op.add_column('order_lines', sa.Column('acquisition_snapshot', sa.JSON(), nullable=True))
    op.add_column('order_lines', sa.Column('acquisition_cost_minor', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('shipping_rule_snapshot', sa.JSON(), nullable=True))
    op.add_column('orders', sa.Column('supplier_picked_up_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('store_settings', sa.Column('shipping_rules_configured', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table('owned_stock_lots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('supplier_variant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('supplier_variants.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('source_ref', sa.String(160), nullable=False, unique=True),
        sa.Column('remaining_quantity', sa.Integer(), nullable=False),
        sa.Column('unit_cost_minor', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('remaining_quantity >= 0 AND unit_cost_minor >= 0', name='ck_owned_lot_counts'))
    op.create_index('ix_owned_stock_lots_supplier_variant_id', 'owned_stock_lots', ['supplier_variant_id'])
    op.create_table('owned_stock_allocations',
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stock_reservations.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('lot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('owned_stock_lots.id', ondelete='RESTRICT'), primary_key=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.CheckConstraint('quantity > 0', name='ck_owned_allocation_quantity'))


def downgrade():
    op.drop_column('shipments', 'rto_cost_recorded_at')
    op.drop_column('order_returns', 'restocked_cost_minor')
    op.drop_column('inventory_balances', 'ownership_review_required')
    op.drop_table('owned_stock_allocations')
    op.drop_index('ix_owned_stock_lots_supplier_variant_id', table_name='owned_stock_lots')
    op.drop_table('owned_stock_lots')
    op.drop_column('store_settings', 'shipping_rules_configured')
    op.drop_column('orders', 'supplier_picked_up_at')
    op.drop_column('orders', 'shipping_rule_snapshot')
    op.drop_column('order_lines', 'acquisition_cost_minor')
    op.drop_column('order_lines', 'acquisition_snapshot')
