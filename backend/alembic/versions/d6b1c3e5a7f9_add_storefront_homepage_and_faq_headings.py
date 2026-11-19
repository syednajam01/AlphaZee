"""Add storefront homepage and faq headings to store_settings.

Revision ID: d6b1c3e5a7f9
Revises: c5a9b2d8e4f7
Create Date: 2026-11-19 04:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'd6b1c3e5a7f9'
down_revision = 'c5a9b2d8e4f7'
branch_labels = None
depends_on = None

DEFAULT_HP_COL_TITLE = 'Shop by collection'
DEFAULT_HP_COL_SUBTITLE = 'A place for every part of your wardrobe.'
DEFAULT_HP_PROD_TITLE = 'The current edit'
DEFAULT_HP_PROD_SUBTITLE = 'A curated selection of our latest pieces.'
DEFAULT_FAQ_TITLE = 'Before you order'
DEFAULT_FAQ_SUBTITLE = 'A few useful answers, all in one place.'


def upgrade():
    op.add_column(
        'store_settings',
        sa.Column('homepage_collections_title', sa.String(100), nullable=False, server_default=DEFAULT_HP_COL_TITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('homepage_collections_subtitle', sa.String(255), nullable=False, server_default=DEFAULT_HP_COL_SUBTITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('homepage_products_title', sa.String(100), nullable=False, server_default=DEFAULT_HP_PROD_TITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('homepage_products_subtitle', sa.String(255), nullable=False, server_default=DEFAULT_HP_PROD_SUBTITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('faq_section_title', sa.String(100), nullable=False, server_default=DEFAULT_FAQ_TITLE)
    )
    op.add_column(
        'store_settings',
        sa.Column('faq_section_subtitle', sa.String(255), nullable=False, server_default=DEFAULT_FAQ_SUBTITLE)
    )


def downgrade():
    op.drop_column('store_settings', 'faq_section_subtitle')
    op.drop_column('store_settings', 'faq_section_title')
    op.drop_column('store_settings', 'homepage_products_subtitle')
    op.drop_column('store_settings', 'homepage_products_title')
    op.drop_column('store_settings', 'homepage_collections_subtitle')
    op.drop_column('store_settings', 'homepage_collections_title')
