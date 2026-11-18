"""Resequence existing hero slides with video priority and sequential display orders.

Revision ID: f3b8a1c9e2d5
Revises: e5a7b9c1d3f2
Create Date: 2026-11-18 23:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = 'f3b8a1c9e2d5'
down_revision = 'e5a7b9c1d3f2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'hero_slides' in inspector.get_table_names():
        slides = bind.execute(sa.text(
            "SELECT id, video_asset_id, created_at FROM hero_slides ORDER BY "
            "CASE WHEN video_asset_id IS NOT NULL THEN 0 ELSE 1 END, "
            "created_at ASC, id ASC"
        )).fetchall()
        for idx, row in enumerate(slides):
            bind.execute(
                sa.text("UPDATE hero_slides SET display_order = :order WHERE id = :id"),
                {"order": idx, "id": row[0]}
            )


def downgrade():
    pass
