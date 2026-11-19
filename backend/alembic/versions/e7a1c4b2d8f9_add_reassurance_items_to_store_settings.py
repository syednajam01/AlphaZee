"""Add reassurance_items to store_settings.

Revision ID: e7a1c4b2d8f9
Revises: d6b1c3e5a7f9
Create Date: 2026-11-19 06:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

revision = 'e7a1c4b2d8f9'
down_revision = 'd6b1c3e5a7f9'
branch_labels = None
depends_on = None

DEFAULT_REASSURANCE_ITEMS = [
    {
        "id": "delivery",
        "title": "Delivery Information",
        "description": "Delivery coverage, charges and timing will be published before public ordering opens.",
        "icon": "truck"
    },
    {
        "id": "payments",
        "title": "Manual Verification",
        "description": "Enabled payment options appear at checkout. Bank transfers require confirmation of received funds before dispatch.",
        "icon": "shield-check"
    },
    {
        "id": "support",
        "title": "Direct Support",
        "description": "Support contact details will be published before public ordering opens.",
        "icon": "message-circle"
    }
]


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == 'postgresql'
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()
    default_clause = sa.text(f"'{json.dumps(DEFAULT_REASSURANCE_ITEMS)}'::jsonb") if is_pg else sa.text(f"'{json.dumps(DEFAULT_REASSURANCE_ITEMS)}'")

    op.add_column(
        'store_settings',
        sa.Column('reassurance_items', json_col, nullable=False, server_default=default_clause)
    )


def downgrade():
    op.drop_column('store_settings', 'reassurance_items')
