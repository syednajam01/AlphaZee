"""Draft catalog lifecycle and versioned owner editing.

Revision ID: e15a9c2b7046
Revises: c94e31f7d562
"""
from alembic import op
import sqlalchemy as sa

revision = 'e15a9c2b7046'
down_revision = 'c94e31f7d562'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('collections', sa.Column('edit_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('products', sa.Column('status', sa.String(20), nullable=False, server_default='published'))
    op.add_column('products', sa.Column('edit_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('products', sa.Column('archived_at', sa.DateTime(timezone=True)))
    op.add_column('products', sa.Column('legacy_media', sa.Boolean(), nullable=False, server_default=sa.true()))
    for field in ('short_description', 'material', 'care', 'sizing'):
        op.add_column('products', sa.Column(field, sa.Text()))
    op.execute("UPDATE products SET status=CASE WHEN is_active THEN 'published' ELSE 'draft' END")
    for field, kind in [('title', sa.String(300)), ('slug', sa.String(100)), ('collection_id', sa.String(100))]:
        op.alter_column('products', field, existing_type=kind, nullable=True)
    op.create_check_constraint('ck_product_status', 'products', "status IN ('draft', 'published', 'archived')")
    op.create_check_constraint('ck_product_published_identity', 'products', "status != 'published' OR (title IS NOT NULL AND slug IS NOT NULL AND collection_id IS NOT NULL)")
    op.alter_column('variants', 'price_minor', existing_type=sa.Integer(), nullable=True)
    op.create_check_constraint('ck_variant_active_price', 'variants', 'NOT is_active OR price_minor IS NOT NULL')
    bind = op.get_bind()
    foreign_key = next(key for key in sa.inspect(bind).get_foreign_keys('variants') if key['constrained_columns'] == ['product_id'])
    op.drop_constraint(foreign_key['name'], 'variants', type_='foreignkey')
    op.create_foreign_key('variants_product_id_fkey', 'variants', 'products', ['product_id'], ['id'], ondelete='RESTRICT')


def downgrade():
    # Refuse a lossy downgrade rather than fabricate draft identity/prices or delete rows.
    if op.get_bind().scalar(sa.text('SELECT EXISTS(SELECT 1 FROM products WHERE title IS NULL OR slug IS NULL OR collection_id IS NULL) OR EXISTS(SELECT 1 FROM variants WHERE price_minor IS NULL)')):
        raise RuntimeError('Complete incomplete drafts before downgrading catalog lifecycle; no rows were deleted.')
    op.drop_constraint('variants_product_id_fkey', 'variants', type_='foreignkey')
    op.create_foreign_key('variants_product_id_fkey', 'variants', 'products', ['product_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('ck_variant_active_price', 'variants', type_='check')
    op.alter_column('variants', 'price_minor', existing_type=sa.Integer(), nullable=False)
    op.drop_constraint('ck_product_published_identity', 'products', type_='check')
    op.drop_constraint('ck_product_status', 'products', type_='check')
    for field, kind in [('title', sa.String(300)), ('slug', sa.String(100)), ('collection_id', sa.String(100))]:
        op.alter_column('products', field, existing_type=kind, nullable=False)
    for field in ('sizing', 'care', 'material', 'short_description', 'legacy_media', 'archived_at', 'edit_version', 'status'):
        op.drop_column('products', field)
    op.drop_column('collections', 'edit_version')
