"""Bind order retries to checkout session and canonical request.

Revision ID: b79e3a2f0d61
Revises: 6a1e9b32c704
"""
from alembic import op
import sqlalchemy as sa

revision = 'b79e3a2f0d61'
down_revision = '6a1e9b32c704'
branch_labels = None
depends_on = None


def upgrade():
    # Historical orders have no authenticated checkout attempt. They remain
    # readable but cannot be replayed via an unbound legacy key.
    op.add_column('orders', sa.Column('checkout_session_hash', sa.String(64), nullable=True))
    op.add_column('orders', sa.Column('request_fingerprint', sa.String(64), nullable=True))


def downgrade():
    op.drop_column('orders', 'request_fingerprint')
    op.drop_column('orders', 'checkout_session_hash')
