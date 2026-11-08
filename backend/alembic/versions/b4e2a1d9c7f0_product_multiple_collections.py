"""Allow products to belong to multiple collections via product_collections.

Revision ID: b4e2a1d9c7f0
Revises: a81f92c6d430
Create Date: 2026-11-09 03:55:00
"""
from alembic import op
import sqlalchemy as sa

revision = 'b4e2a1d9c7f0'
down_revision = 'a81f92c6d430'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'product_collections',
        sa.Column('product_id', sa.String(length=100), nullable=False),
        sa.Column('collection_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'collection_id'),
    )
    op.create_index('ix_product_collections_collection_id', 'product_collections', ['collection_id'], unique=False)
    op.create_index('ix_product_collections_product_id', 'product_collections', ['product_id'], unique=False)

    # Backfill product_collections from existing products.collection_id
    op.execute("""
        INSERT INTO product_collections (product_id, collection_id)
        SELECT p.id, p.collection_id
        FROM products p
        JOIN collections c ON c.id = p.collection_id
        WHERE p.collection_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    op.drop_index('ix_product_collections_product_id', table_name='product_collections')
    op.drop_index('ix_product_collections_collection_id', table_name='product_collections')
    op.drop_table('product_collections')
