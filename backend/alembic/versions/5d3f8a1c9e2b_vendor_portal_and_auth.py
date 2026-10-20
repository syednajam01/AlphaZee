"""Additive migration: vendor_portal_and_auth.

Revision ID: 5d3f8a1c9e2b
Revises: 9c2b4d8e1f5a
Create Date: 2026-10-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '5d3f8a1c9e2b'
down_revision = '9c2b4d8e1f5a'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create vendor_users table
    op.create_table(
        'vendor_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_vu_vendor_id', 'vendor_users', ['vendor_id'])
    op.create_index('idx_vu_username', 'vendor_users', ['username'])
    op.create_check_constraint(
        'ck_vendor_users_username_min_length',
        'vendor_users',
        'length(trim(username)) >= 3',
    )

    # 2. Create vendor_sessions table
    op.create_table(
        'vendor_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('vendor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendor_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_vs_vendor_user_id', 'vendor_sessions', ['vendor_user_id'])
    op.create_index('idx_vs_expires_at', 'vendor_sessions', ['expires_at'])

    # 3. Create vendor_login_buckets table
    op.create_table(
        'vendor_login_buckets',
        sa.Column('key_hash', sa.String(64), primary_key=True),
        sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default=sa.text('1')),
    )
    op.create_index('idx_vlb_window_started_at', 'vendor_login_buckets', ['window_started_at'])
    op.create_check_constraint(
        'ck_vendor_login_attempts_positive',
        'vendor_login_buckets',
        'attempts > 0',
    )

    # 4. Create vendor_stock_shortages table
    op.create_table(
        'vendor_stock_shortages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('variant_id', sa.Integer(), sa.ForeignKey('variants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vendor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vendor_users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reported_count', sa.Integer(), nullable=False),
        sa.Column('held_reservations', sa.Integer(), nullable=False),
        sa.Column('physical_on_hand_snapshot', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default=sa.text("'open'")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
    )
    op.create_index('idx_vss_variant_id', 'vendor_stock_shortages', ['variant_id'])
    op.create_index('idx_vss_vendor_id', 'vendor_stock_shortages', ['vendor_id'])
    op.create_index('idx_vss_status', 'vendor_stock_shortages', ['status'])
    op.create_check_constraint(
        'ck_vss_status',
        'vendor_stock_shortages',
        "status IN ('open', 'resolved', 'cancelled')",
    )


def downgrade():
    op.drop_table('vendor_stock_shortages')
    op.drop_table('vendor_login_buckets')
    op.drop_table('vendor_sessions')
    op.drop_table('vendor_users')
