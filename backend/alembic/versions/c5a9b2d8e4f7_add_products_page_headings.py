"""Add products_page_title and products_page_subtitle to store_settings.

Revision ID: c5a9b2d8e4f7
Revises: b4e8a1c9e3f6
Create Date: 2026-11-19 03:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'c5a9b2d8e4f7'
down_revision = 'b4e8a1c9e3f6'
branch_labels = None
depends_on = None

DEFAULT_TITLE = 'All Products'
DEFAULT_SUBTITLE = 'Find a piece that feels like you. Explore our complete catalog.'


def upgrade():
    op.add_column(
        'store_settings',
        sa.Column('products_page_title', sa.String(100), nullable=False, server_default=DEFAULT_TITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('products_page_subtitle', sa.String(255), nullable=False, server_default=DEFAULT_SUBTITLE)
    )


def downgrade():
    op.drop_column('store_settings', 'products_page_subtitle')
    op.drop_column('store_settings', 'products_page_title')
