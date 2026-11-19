"""Add media framing and focal coordinates to hero_slides, product_media, collections, and media_assets.

Revision ID: c9d8e7f6a5b4
Revises: f8b2d4c6e1a3
Create Date: 2026-11-20 00:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'c9d8e7f6a5b4'
down_revision = 'f8b2d4c6e1a3'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. hero_slides
    hero_cols = [c['name'] for c in inspector.get_columns('hero_slides')] if 'hero_slides' in inspector.get_table_names() else []
    if 'focal_x' not in hero_cols:
        op.add_column('hero_slides', sa.Column('focal_x', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'focal_y' not in hero_cols:
        op.add_column('hero_slides', sa.Column('focal_y', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'zoom_scale' not in hero_cols:
        op.add_column('hero_slides', sa.Column('zoom_scale', sa.Float(), nullable=False, server_default=sa.text('1.0')))

    # 2. product_media
    pm_cols = [c['name'] for c in inspector.get_columns('product_media')] if 'product_media' in inspector.get_table_names() else []
    if 'focal_x' not in pm_cols:
        op.add_column('product_media', sa.Column('focal_x', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'focal_y' not in pm_cols:
        op.add_column('product_media', sa.Column('focal_y', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'zoom_scale' not in pm_cols:
        op.add_column('product_media', sa.Column('zoom_scale', sa.Float(), nullable=False, server_default=sa.text('1.0')))

    # 3. collections
    col_cols = [c['name'] for c in inspector.get_columns('collections')] if 'collections' in inspector.get_table_names() else []
    if 'focal_x' not in col_cols:
        op.add_column('collections', sa.Column('focal_x', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'focal_y' not in col_cols:
        op.add_column('collections', sa.Column('focal_y', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'zoom_scale' not in col_cols:
        op.add_column('collections', sa.Column('zoom_scale', sa.Float(), nullable=False, server_default=sa.text('1.0')))
    if 'hover_focal_x' not in col_cols:
        op.add_column('collections', sa.Column('hover_focal_x', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'hover_focal_y' not in col_cols:
        op.add_column('collections', sa.Column('hover_focal_y', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'hover_zoom_scale' not in col_cols:
        op.add_column('collections', sa.Column('hover_zoom_scale', sa.Float(), nullable=False, server_default=sa.text('1.0')))

    # 4. media_assets
    ma_cols = [c['name'] for c in inspector.get_columns('media_assets')] if 'media_assets' in inspector.get_table_names() else []
    if 'focal_x' not in ma_cols:
        op.add_column('media_assets', sa.Column('focal_x', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'focal_y' not in ma_cols:
        op.add_column('media_assets', sa.Column('focal_y', sa.Integer(), nullable=False, server_default=sa.text('50')))
    if 'zoom_scale' not in ma_cols:
        op.add_column('media_assets', sa.Column('zoom_scale', sa.Float(), nullable=False, server_default=sa.text('1.0')))


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. media_assets
    ma_cols = [c['name'] for c in inspector.get_columns('media_assets')] if 'media_assets' in inspector.get_table_names() else []
    if 'zoom_scale' in ma_cols:
        op.drop_column('media_assets', 'zoom_scale')
    if 'focal_y' in ma_cols:
        op.drop_column('media_assets', 'focal_y')
    if 'focal_x' in ma_cols:
        op.drop_column('media_assets', 'focal_x')

    # 2. collections
    col_cols = [c['name'] for c in inspector.get_columns('collections')] if 'collections' in inspector.get_table_names() else []
    if 'hover_zoom_scale' in col_cols:
        op.drop_column('collections', 'hover_zoom_scale')
    if 'hover_focal_y' in col_cols:
        op.drop_column('collections', 'hover_focal_y')
    if 'hover_focal_x' in col_cols:
        op.drop_column('collections', 'hover_focal_x')
    if 'zoom_scale' in col_cols:
        op.drop_column('collections', 'zoom_scale')
    if 'focal_y' in col_cols:
        op.drop_column('collections', 'focal_y')
    if 'focal_x' in col_cols:
        op.drop_column('collections', 'focal_x')

    # 3. product_media
    pm_cols = [c['name'] for c in inspector.get_columns('product_media')] if 'product_media' in inspector.get_table_names() else []
    if 'zoom_scale' in pm_cols:
        op.drop_column('product_media', 'zoom_scale')
    if 'focal_y' in pm_cols:
        op.drop_column('product_media', 'focal_y')
    if 'focal_x' in pm_cols:
        op.drop_column('product_media', 'focal_x')

    # 4. hero_slides
    hero_cols = [c['name'] for c in inspector.get_columns('hero_slides')] if 'hero_slides' in inspector.get_table_names() else []
    if 'zoom_scale' in hero_cols:
        op.drop_column('hero_slides', 'zoom_scale')
    if 'focal_y' in hero_cols:
        op.drop_column('hero_slides', 'focal_y')
    if 'focal_x' in hero_cols:
        op.drop_column('hero_slides', 'focal_x')

