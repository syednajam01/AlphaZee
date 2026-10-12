"""Add owner credentials, revocable sessions and shared login limits.

Revision ID: 6a1e9b32c704
Revises: 13b1315d1395
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '6a1e9b32c704'
down_revision = '13b1315d1395'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('owner_credentials',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False))
    op.create_table('owner_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('owner_credentials.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)))
    op.create_index('ix_owner_sessions_user_id', 'owner_sessions', ['user_id'])
    op.create_index('ix_owner_sessions_expires_at', 'owner_sessions', ['expires_at'])
    op.create_table('owner_login_buckets',
        sa.Column('key_hash', sa.String(64), primary_key=True),
        sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.CheckConstraint('attempts > 0', name='ck_owner_login_attempts_positive'))
    op.create_index('ix_owner_login_buckets_window_started_at', 'owner_login_buckets', ['window_started_at'])


def downgrade():
    op.drop_table('owner_login_buckets')
    op.drop_table('owner_sessions')
    op.drop_table('owner_credentials')
