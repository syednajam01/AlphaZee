"""Add hover_image_url and hover_image_media_id to collections.

Revision ID: d3f8a1c9e2b4
Revises: c7f1e2a3b4d5
Create Date: 2026-11-10 14:35:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'd3f8a1c9e2b4'
down_revision = 'c7f1e2a3b4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('collections', sa.Column('hover_image_url', sa.Text(), nullable=True))
    op.add_column('collections', sa.Column('hover_image_media_id', sa.String(length=32), nullable=True))
    op.create_foreign_key(
        'fk_collections_hover_image_media_id',
        'collections', 'media_assets',
        ['hover_image_media_id'], ['id'],
        ondelete='RESTRICT'
    )


def downgrade():
    op.drop_constraint('fk_collections_hover_image_media_id', 'collections', type_='foreignkey')
    op.drop_column('collections', 'hover_image_media_id')
    op.drop_column('collections', 'hover_image_url')
