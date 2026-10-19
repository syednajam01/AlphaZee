"""Additive migration: stock_ownership_and_expenses.

Revision ID: 9c2b4d8e1f5a
Revises: 7a3e9b1c5d2f
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '9c2b4d8e1f5a'
down_revision = '7a3e9b1c5d2f'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add supplier_type to suppliers
    op.add_column(
        'suppliers',
        sa.Column('supplier_type', sa.String(32), nullable=False, server_default=sa.text("'external_vendor'")),
    )
    op.create_check_constraint(
        'ck_suppliers_supplier_type',
        'suppliers',
        "supplier_type IN ('external_vendor', 'alphazee_internal')",
    )

    # Seed the internal AlphaZee inventory source supplier if it doesn't exist
    op.execute("""
        INSERT INTO suppliers (id, name, slug, status, supplier_type, notes, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'AlphaZee In-House',
            'alphazee-internal',
            'active',
            'alphazee_internal',
            'Internal inventory source for AlphaZee-managed catalog stock',
            NOW(),
            NOW()
        )
        ON CONFLICT (slug) DO NOTHING;
    """)

    # 2. Add stock_management_source and vendor_id to products
    op.add_column(
        'products',
        sa.Column('stock_management_source', sa.String(32), nullable=False, server_default=sa.text("'alphazee_managed'")),
    )
    op.add_column(
        'products',
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=True),
    )
    op.create_check_constraint(
        'ck_product_stock_management_source',
        'products',
        "stock_management_source IN ('alphazee_managed', 'vendor_managed')",
    )
    op.create_check_constraint(
        'ck_product_vendor_managed_requires_vendor',
        'products',
        "stock_management_source != 'vendor_managed' OR vendor_id IS NOT NULL",
    )
    op.create_index('ix_products_vendor_id', 'products', ['vendor_id'])

    # 3. Add ownership_source to order_lines
    op.add_column(
        'order_lines',
        sa.Column('ownership_source', sa.String(32), nullable=False, server_default=sa.text("'vendor_consignment'")),
    )
    op.create_check_constraint(
        'ck_order_lines_ownership_source',
        'order_lines',
        "ownership_source IN ('vendor_consignment', 'alphazee_owned')",
    )

    # 4. Create business_expenses table
    op.create_table(
        'business_expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('incurred_date', sa.Date(), nullable=False),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('payee', sa.String(160), nullable=False),
        sa.Column('reference', sa.String(120), nullable=True),
        sa.Column('payment_method', sa.String(32), nullable=False, server_default=sa.text("'bank_transfer'")),
        sa.Column('linked_shipment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shipments.id', ondelete='SET NULL'), nullable=True),
        sa.Column('linked_return_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('order_returns.id', ondelete='SET NULL'), nullable=True),
        sa.Column('linked_courier_settlement_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('courier_settlement_entries.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('amount_minor > 0', name='ck_business_expenses_amount_positive'),
        sa.CheckConstraint(
            "category IN ('packaging', 'advertising', 'outbound_delivery', 'rto_transport', 'customer_return_transport', 'platform_hosting', 'office_supplies', 'salaries', 'other_overhead')",
            name='ck_business_expenses_category',
        ),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'bank_transfer', 'courier_deduction', 'credit_card', 'other')",
            name='ck_business_expenses_payment_method',
        ),
    )
    op.create_index('ix_business_expenses_category', 'business_expenses', ['category'])
    op.create_index('ix_business_expenses_incurred_date', 'business_expenses', ['incurred_date'])
    op.create_index('ix_business_expenses_shipment', 'business_expenses', ['linked_shipment_id'])
    op.create_index('ix_business_expenses_return', 'business_expenses', ['linked_return_id'])
    op.create_index('ix_business_expenses_settlement', 'business_expenses', ['linked_courier_settlement_id'])


def downgrade():
    # 4. Drop business_expenses
    op.drop_index('ix_business_expenses_settlement', table_name='business_expenses')
    op.drop_index('ix_business_expenses_return', table_name='business_expenses')
    op.drop_index('ix_business_expenses_shipment', table_name='business_expenses')
    op.drop_index('ix_business_expenses_incurred_date', table_name='business_expenses')
    op.drop_index('ix_business_expenses_category', table_name='business_expenses')
    op.drop_table('business_expenses')

    # 3. Drop order_lines ownership_source
    op.drop_constraint('ck_order_lines_ownership_source', 'order_lines', type_='check')
    op.drop_column('order_lines', 'ownership_source')

    # 2. Drop products columns & constraints
    op.drop_index('ix_products_vendor_id', table_name='products')
    op.drop_constraint('ck_product_vendor_managed_requires_vendor', 'products', type_='check')
    op.drop_constraint('ck_product_stock_management_source', 'products', type_='check')
    op.drop_column('products', 'vendor_id')
    op.drop_column('products', 'stock_management_source')

    # 1. Drop suppliers supplier_type
    op.drop_constraint('ck_suppliers_supplier_type', 'suppliers', type_='check')
    op.drop_column('suppliers', 'supplier_type')
