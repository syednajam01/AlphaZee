"""Durable managed catalog media, separate references and legacy URL preservation."""
from alembic import op
import sqlalchemy as sa

revision = 'f27b6d91c083'
down_revision = 'e15a9c2b7046'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('media_assets',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('storage_key', sa.String(50), nullable=False, unique=True),
        sa.Column('original_name', sa.String(200), nullable=False),
        sa.Column('kind', sa.String(10), nullable=False),
        sa.Column('content_type', sa.String(30), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Integer()),
        sa.Column('state', sa.String(10), nullable=False),
        sa.Column('edit_version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('poster_id', sa.String(32), sa.ForeignKey('media_assets.id', ondelete='RESTRICT')),
        sa.Column('creator_id', sa.UUID(), sa.ForeignKey('user_accounts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('image', 'video')", name='ck_media_kind'),
        sa.CheckConstraint("state IN ('ready', 'deleted')", name='ck_media_state'),
        sa.CheckConstraint('byte_size > 0 AND width > 0 AND height > 0', name='ck_media_dimensions'),
        sa.CheckConstraint('duration_ms IS NULL OR duration_ms BETWEEN 1 AND 120000', name='ck_media_duration'),
    )
    op.add_column('collections', sa.Column('image_media_id', sa.String(32)))
    op.create_foreign_key('collections_image_media_id_fkey', 'collections', 'media_assets', ['image_media_id'], ['id'], ondelete='RESTRICT')
    op.create_table('product_media',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.String(100), sa.ForeignKey('products.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('asset_id', sa.String(32), sa.ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('variant_id', sa.Integer(), sa.ForeignKey('variants.id', ondelete='RESTRICT')),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('alt_text', sa.Text(), nullable=False),
        sa.CheckConstraint("role IN ('primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster')", name='ck_product_media_role'),
        sa.CheckConstraint("variant_id IS NULL OR role = 'gallery'", name='ck_product_media_variant_role'),
        sa.CheckConstraint('display_order >= 0', name='ck_product_media_order'),
    )
    op.create_index('uq_product_media_link', 'product_media', ['product_id', 'asset_id', 'role', 'variant_id'], unique=True, postgresql_nulls_not_distinct=True)
    op.create_index('uq_product_media_single_role', 'product_media', ['product_id', 'role'], unique=True, postgresql_where=sa.text("role != 'gallery'"))
    op.create_index('ix_product_media_asset', 'product_media', ['asset_id'])


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT EXISTS(SELECT 1 FROM media_assets) OR EXISTS(SELECT 1 FROM product_media) OR EXISTS(SELECT 1 FROM collections WHERE image_media_id IS NOT NULL)')):
        raise RuntimeError('Managed assets exist. Restore a matched database/media backup instead of discarding media metadata.')
    op.drop_table('product_media')
    op.drop_constraint('collections_image_media_id_fkey', 'collections', type_='foreignkey')
    op.drop_column('collections', 'image_media_id')
    op.drop_table('media_assets')
