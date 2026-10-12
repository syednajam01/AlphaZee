"""add reservation and order idempotency keys

Revision ID: e5c83f14a091
Revises: 8f6817131a9a
Create Date: 2026-10-12 23:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5c83f14a091'
down_revision: Union[str, None] = '8f6817131a9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add idempotency_key column to stock_reservations
    op.add_column(
        'stock_reservations',
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
    )
    op.create_index(
        'uq_sr_idempotency_open',
        'stock_reservations',
        ['idempotency_key'],
        unique=True,
        postgresql_where=sa.text("stage NOT IN ('cancelled', 'returned') AND idempotency_key IS NOT NULL"),
    )

    # 2. Add idempotency_key column to orders
    op.add_column(
        'orders',
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
    )
    op.create_index(
        'uq_orders_idempotency_key',
        'orders',
        ['idempotency_key'],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_orders_idempotency_key',
        table_name='orders',
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_column('orders', 'idempotency_key')

    op.drop_index(
        'uq_sr_idempotency_open',
        table_name='stock_reservations',
        postgresql_where=sa.text("stage NOT IN ('cancelled', 'returned') AND idempotency_key IS NOT NULL"),
    )
    op.drop_column('stock_reservations', 'idempotency_key')
