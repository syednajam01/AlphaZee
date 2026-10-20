"""Additive migration: store_settings_and_preferences.

Revision ID: 6e4a2b8d0c1f
Revises: 5d3f8a1c9e2b
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '6e4a2b8d0c1f'
down_revision = '5d3f8a1c9e2b'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create store_settings table
    op.create_table(
        'store_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('brand_name', sa.String(100), nullable=False, server_default='AlphaZee'),
        sa.Column('tagline', sa.String(255), nullable=False, server_default='Modern Apparel & Curated Essentials'),
        sa.Column('announcement_banner_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('announcement_banner_text', sa.String(255), nullable=False, server_default='AlphaZee Concept Preview • Public ordering is not open yet'),
        sa.Column('announcement_banner_link', sa.String(255), nullable=True),
        sa.Column('logo_media_id', sa.String(32), sa.ForeignKey('media_assets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('accent_color', sa.String(32), nullable=False, server_default='#111827'),
        sa.Column('font_family', sa.String(64), nullable=False, server_default='Inter, sans-serif'),
        sa.Column('border_radius', sa.String(32), nullable=False, server_default='md'),
        sa.Column('spacing_density', sa.String(32), nullable=False, server_default='comfortable'),
        sa.Column('section_order', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text('\'["hero", "collections", "featured", "reassurance", "faq"]\'::jsonb')),
        sa.Column('support_email', sa.String(120), nullable=True),
        sa.Column('support_phone', sa.String(50), nullable=True),
        sa.Column('support_hours', sa.String(120), nullable=True),
        sa.Column('delivery_policy_content', sa.Text(), nullable=True),
        sa.Column('delivery_policy_status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('delivery_policy_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('return_policy_content', sa.Text(), nullable=True),
        sa.Column('return_policy_status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('return_policy_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terms_policy_content', sa.Text(), nullable=True),
        sa.Column('terms_policy_status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('terms_policy_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('privacy_policy_content', sa.Text(), nullable=True),
        sa.Column('privacy_policy_status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('privacy_policy_published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shipping_coverage_area', sa.String(100), nullable=False, server_default='All Pakistan'),
        sa.Column('standard_shipping_fee_minor', sa.Integer(), nullable=False, server_default=sa.text('20000')),
        sa.Column('free_shipping_threshold_minor', sa.Integer(), nullable=True),
        sa.Column('low_stock_threshold', sa.Integer(), nullable=False, server_default=sa.text('3')),
        sa.Column('stock_staleness_threshold_days', sa.Integer(), nullable=False, server_default=sa.text('7')),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_check_constraint(
        'ck_store_settings_delivery_status',
        'store_settings',
        "delivery_policy_status IN ('draft', 'published')",
    )
    op.create_check_constraint(
        'ck_store_settings_return_status',
        'store_settings',
        "return_policy_status IN ('draft', 'published')",
    )
    op.create_check_constraint(
        'ck_store_settings_terms_status',
        'store_settings',
        "terms_policy_status IN ('draft', 'published')",
    )
    op.create_check_constraint(
        'ck_store_settings_privacy_status',
        'store_settings',
        "privacy_policy_status IN ('draft', 'published')",
    )
    op.create_check_constraint(
        'ck_store_settings_standard_shipping_non_neg',
        'store_settings',
        'standard_shipping_fee_minor >= 0',
    )
    op.create_check_constraint(
        'ck_store_settings_low_stock_pos',
        'store_settings',
        'low_stock_threshold >= 0',
    )
    op.create_check_constraint(
        'ck_store_settings_staleness_pos',
        'store_settings',
        'stock_staleness_threshold_days >= 1',
    )

    # Seed initial store_settings row if not exists
    op.execute("""
        INSERT INTO store_settings (
            brand_name, tagline, announcement_banner_enabled, announcement_banner_text,
            accent_color, font_family, border_radius, spacing_density, section_order,
            shipping_coverage_area, standard_shipping_fee_minor, low_stock_threshold,
            stock_staleness_threshold_days, version
        ) VALUES (
            'AlphaZee', 'Modern Apparel & Curated Essentials', true,
            'AlphaZee Concept Preview • Public ordering is not open yet',
            '#111827', 'Inter, sans-serif', 'md', 'comfortable',
            '["hero", "collections", "featured", "reassurance", "faq"]'::jsonb,
            'All Pakistan', 20000, 3, 7, 1
        )
    """)

    # 2. Create store_settings_audit_logs table
    op.create_table(
        'store_settings_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('changed_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('full_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('change_reason', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_ssal_version', 'store_settings_audit_logs', ['version'])
    op.create_index('idx_ssal_created_at', 'store_settings_audit_logs', ['created_at'])

    # 3. Create owner_preferences table
    op.create_table(
        'owner_preferences',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('theme', sa.String(20), nullable=False, server_default='system'),
        sa.Column('table_density', sa.String(20), nullable=False, server_default='comfortable'),
        sa.Column('default_date_range', sa.String(32), nullable=False, server_default='this_month'),
        sa.Column('nav_order', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text('\'["products", "collections", "hero", "media", "inventory", "suppliers", "orders", "returns", "coupons", "expenses", "analytics", "settings"]\'::jsonb')),
        sa.Column('dashboard_layout', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text('\'{"cards": [{"id": "sales", "visible": true}, {"id": "inventory", "visible": true}, {"id": "liabilities", "visible": true}, {"id": "expenses", "visible": true}]}\'::jsonb')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_check_constraint(
        'ck_owner_preferences_theme',
        'owner_preferences',
        "theme IN ('system', 'light', 'dark')",
    )
    op.create_check_constraint(
        'ck_owner_preferences_density',
        'owner_preferences',
        "table_density IN ('comfortable', 'compact')",
    )


def downgrade():
    op.drop_table('owner_preferences')
    op.drop_table('store_settings_audit_logs')
    op.drop_table('store_settings')
