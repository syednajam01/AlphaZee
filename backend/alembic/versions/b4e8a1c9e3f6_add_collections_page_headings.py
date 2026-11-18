"""Add collections_page_title and collections_page_subtitle to store_settings.

Revision ID: b4e8a1c9e3f6
Revises: a2c9e4b1f5d8
Create Date: 2026-11-19 02:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'b4e8a1c9e3f6'
down_revision = 'a2c9e4b1f5d8'
branch_labels = None
depends_on = None

DEFAULT_TITLE = 'All Collections'
DEFAULT_SUBTITLE = 'Explore our complete range of curated wardrobe edits.'


def upgrade():
    op.add_column(
        'store_settings',
        sa.Column('collections_page_title', sa.String(100), nullable=False, server_default=DEFAULT_TITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('collections_page_subtitle', sa.String(255), nullable=False, server_default=DEFAULT_SUBTITLE)
    )


def downgrade():
    op.drop_column('store_settings', 'collections_page_subtitle')
    op.drop_column('store_settings', 'collections_page_title')
