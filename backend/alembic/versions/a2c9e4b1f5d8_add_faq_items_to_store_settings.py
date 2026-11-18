"""Add faq_items to store_settings.

Revision ID: a2c9e4b1f5d8
Revises: f3b8a1c9e2d5
Create Date: 2026-11-19 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

revision = 'a2c9e4b1f5d8'
down_revision = 'f3b8a1c9e2d5'
branch_labels = None
depends_on = None

DEFAULT_FAQS = [
    {
        "id": "faq_del_1",
        "question": "How long does delivery take?",
        "answer": "Standard delivery across Pakistan takes 2 to 4 working days for major cities (Karachi, Lahore, Islamabad). Regional deliveries take 3 to 6 working days.",
        "category": "Delivery",
        "is_enabled": True,
        "display_order": 0
    },
    {
        "id": "faq_pay_2",
        "question": "How can I pay for my order?",
        "answer": "We accept Cash on Delivery (COD) nationwide and direct bank transfers with verification. Available options appear at checkout.",
        "category": "Payment",
        "is_enabled": True,
        "display_order": 1
    },
    {
        "id": "faq_ret_3",
        "question": "What is the return & exchange policy?",
        "answer": "We offer a 7-day return and exchange window for unworn items in their original packaging with tags attached.",
        "category": "Returns",
        "is_enabled": True,
        "display_order": 2
    },
    {
        "id": "faq_siz_4",
        "question": "How do I choose the correct size?",
        "answer": "Refer to the detailed size chart and measurements published on each product page before selecting your size.",
        "category": "Sizing",
        "is_enabled": True,
        "display_order": 3
    }
]


def upgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == 'postgresql'
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_pg else sa.JSON()
    default_clause = sa.text(f"'{json.dumps(DEFAULT_FAQS)}'::jsonb") if is_pg else sa.text(f"'{json.dumps(DEFAULT_FAQS)}'")

    op.add_column(
        'store_settings',
        sa.Column('faq_items', json_col, nullable=False, server_default=default_clause)
    )


def downgrade():
    op.drop_column('store_settings', 'faq_items')
