"""Add onboarding and business profile fields to suppliers.

Revision ID: e5a7b9c1d3f2
Revises: d3f8a1c9e2b4
Create Date: 2026-11-13 05:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'e5a7b9c1d3f2'
down_revision = 'd3f8a1c9e2b4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('suppliers', sa.Column('whatsapp_number', sa.String(length=32), nullable=True))
    op.add_column('suppliers', sa.Column('contact_person', sa.String(length=128), nullable=True))
    op.add_column('suppliers', sa.Column('business_type', sa.String(length=64), nullable=True))
    op.add_column('suppliers', sa.Column('cnic', sa.String(length=32), nullable=True))
    op.add_column('suppliers', sa.Column('ntn', sa.String(length=32), nullable=True))
    op.add_column('suppliers', sa.Column('email', sa.String(length=128), nullable=True))
    op.add_column('suppliers', sa.Column('warehouse_address', sa.Text(), nullable=True))
    op.add_column('suppliers', sa.Column('city', sa.String(length=64), nullable=True))
    op.add_column('suppliers', sa.Column('bank_name', sa.String(length=64), nullable=True))
    op.add_column('suppliers', sa.Column('bank_account_title', sa.String(length=128), nullable=True))
    op.add_column('suppliers', sa.Column('bank_iban', sa.String(length=34), nullable=True))
    op.add_column('suppliers', sa.Column('lead_time_days', sa.Integer(), nullable=False, server_default='2'))
    op.add_column('suppliers', sa.Column('onboarding_status', sa.String(length=32), nullable=False, server_default='pending_profile'))

    op.create_index('idx_suppliers_whatsapp', 'suppliers', ['whatsapp_number'])
    op.create_index('idx_suppliers_onboarding_status', 'suppliers', ['onboarding_status'])
    op.create_check_constraint(
        'ck_suppliers_onboarding_status',
        'suppliers',
        "onboarding_status IN ('pending_profile', 'active', 'suspended')"
    )

    # Set existing active suppliers to active onboarding status
    op.execute("UPDATE suppliers SET onboarding_status = 'active' WHERE status = 'active'")


def downgrade():
    op.drop_constraint('ck_suppliers_onboarding_status', 'suppliers', type_='check')
    op.drop_index('idx_suppliers_onboarding_status', table_name='suppliers')
    op.drop_index('idx_suppliers_whatsapp', table_name='suppliers')
    op.drop_column('suppliers', 'onboarding_status')
    op.drop_column('suppliers', 'lead_time_days')
    op.drop_column('suppliers', 'bank_iban')
    op.drop_column('suppliers', 'bank_account_title')
    op.drop_column('suppliers', 'bank_name')
    op.drop_column('suppliers', 'city')
    op.drop_column('suppliers', 'warehouse_address')
    op.drop_column('suppliers', 'email')
    op.drop_column('suppliers', 'ntn')
    op.drop_column('suppliers', 'cnic')
    op.drop_column('suppliers', 'business_type')
    op.drop_column('suppliers', 'contact_person')
    op.drop_column('suppliers', 'whatsapp_number')
