"""Additive migration: hover_image role, hero_slides table, and hero backfill.

Revision ID: 2c8a1b3e5f70
Revises: f27b6d91c083
Create Date: 2026-10-19
"""
import hashlib
from alembic import op
import sqlalchemy as sa

revision = '2c8a1b3e5f70'
down_revision = 'f27b6d91c083'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Expand role check constraint on product_media to include 'hover_image'
    op.drop_constraint('ck_product_media_role', 'product_media', type_='check')
    op.create_check_constraint(
        'ck_product_media_role',
        'product_media',
        "role IN ('primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster', 'hover_image')"
    )

    # 2. Add optional hover_image_url column on products for cached denormalization if present
    op.add_column('products', sa.Column('hover_image_url', sa.Text(), nullable=True))

    # 3. Create dedicated hero_slides table for homepage hero playlist
    op.create_table(
        'hero_slides',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('benefit', sa.Text(), nullable=True),
        sa.Column('video_asset_id', sa.String(32), sa.ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('poster_asset_id', sa.String(32), sa.ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('image_asset_id', sa.String(32), sa.ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('target_product_id', sa.String(100), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sa.Column('target_collection_id', sa.String(100), sa.ForeignKey('collections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('edit_version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('display_order >= 0', name='ck_hero_slide_order'),
        sa.CheckConstraint('video_asset_id IS NOT NULL OR image_asset_id IS NOT NULL OR poster_asset_id IS NOT NULL', name='ck_hero_slide_media'),
    )
    op.create_index('ix_hero_slides_order', 'hero_slides', ['display_order'])
    op.create_index('ix_hero_slides_enabled', 'hero_slides', ['is_enabled'])

    # 4. Backfill from existing products configured with is_hero = true
    bind = op.get_bind()
    hero_products = bind.execute(sa.text("""
        SELECT p.id, p.title, p.hero_benefit, p.hero_order, p.is_active, p.collection_id
        FROM products p
        WHERE p.is_hero = true
    """)).fetchall()

    for row in hero_products:
        p_id = row[0]
        p_title = row[1]
        p_benefit = row[2]
        p_order = row[3]
        p_active = row[4]
        p_coll = row[5]

        media_rows = bind.execute(sa.text("""
            SELECT role, asset_id FROM product_media WHERE product_id = :pid
        """), {'pid': p_id}).fetchall()
        roles = {m[0]: m[1] for m in media_rows}

        v_id = roles.get('hero_video')
        p_id_asset = roles.get('hero_poster')
        img_id = roles.get('hero_image') or roles.get('primary')

        if v_id or img_id or p_id_asset:
            slide_id = 'hero_' + hashlib.sha256(p_id.encode()).hexdigest()[:24]
            bind.execute(sa.text("""
                INSERT INTO hero_slides (
                    id, title, benefit, video_asset_id, poster_asset_id, image_asset_id,
                    display_order, is_enabled, target_product_id, target_collection_id,
                    edit_version, created_at, updated_at
                ) VALUES (
                    :id, :title, :benefit, :vid, :pid_asset, :img_id,
                    :order, :enabled, :prod_id, :coll_id,
                    1, now(), now()
                ) ON CONFLICT (id) DO NOTHING
            """), {
                'id': slide_id,
                'title': p_title,
                'benefit': p_benefit,
                'vid': v_id,
                'pid_asset': p_id_asset,
                'img_id': img_id,
                'order': p_order if p_order is not None else 0,
                'enabled': p_active,
                'prod_id': p_id,
                'coll_id': p_coll,
            })


def downgrade():
    bind = op.get_bind()
    if bind.scalar(sa.text("SELECT EXISTS(SELECT 1 FROM product_media WHERE role = 'hover_image')")):
        raise RuntimeError("Hover images exist on products. Detach them before downgrading.")
    op.drop_index('ix_hero_slides_enabled', 'hero_slides')
    op.drop_index('ix_hero_slides_order', 'hero_slides')
    op.drop_table('hero_slides')
    op.drop_column('products', 'hover_image_url')
    op.drop_constraint('ck_product_media_role', 'product_media', type_='check')
    op.create_check_constraint(
        'ck_product_media_role',
        'product_media',
        "role IN ('primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster')"
    )
