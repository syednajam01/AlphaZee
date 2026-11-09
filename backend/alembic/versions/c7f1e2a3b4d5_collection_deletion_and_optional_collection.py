"""Collection deletion and optional product collection membership.

Revision ID: c7f1e2a3b4d5
Revises: b4e2a1d9c7f0
Create Date: 2026-11-09 23:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'c7f1e2a3b4d5'
down_revision = 'b4e2a1d9c7f0'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Update ck_product_published_identity on products:
    # Allow published products to have collection_id IS NULL (belonging to 0 collections).
    op.drop_constraint('ck_product_published_identity', 'products', type_='check')
    op.create_check_constraint(
        'ck_product_published_identity',
        'products',
        "status != 'published' OR (title IS NOT NULL AND slug IS NOT NULL)"
    )

    # 2. Update foreign key products_collection_id_fkey on products to ON DELETE SET NULL
    op.drop_constraint('products_collection_id_fkey', 'products', type_='foreignkey')
    op.create_foreign_key(
        'products_collection_id_fkey',
        'products',
        'collections',
        ['collection_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # 1. Revert foreign key products_collection_id_fkey to ON DELETE RESTRICT
    op.drop_constraint('products_collection_id_fkey', 'products', type_='foreignkey')
    op.create_foreign_key(
        'products_collection_id_fkey',
        'products',
        'collections',
        ['collection_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # 2. Revert check constraint back to requiring collection_id IS NOT NULL for published products
    op.drop_constraint('ck_product_published_identity', 'products', type_='check')
    op.create_check_constraint(
        'ck_product_published_identity',
        'products',
        "status != 'published' OR (title IS NOT NULL AND slug IS NOT NULL AND collection_id IS NOT NULL)"
    )
