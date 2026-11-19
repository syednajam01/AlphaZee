"""Add footer_quote and support templates to store_settings.

Revision ID: f8b2d4c6e1a3
Revises: e7a1c4b2d8f9
Create Date: 2026-11-19 07:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'f8b2d4c6e1a3'
down_revision = 'e7a1c4b2d8f9'
branch_labels = None
depends_on = None

DEFAULT_FOOTER_QUOTE = "A considered selection of clothing and accessories. Find your next piece, and make it your own."
DEFAULT_WHATSAPP_PREFILL = "Hi AlphaZee, I have a question regarding my order:"
DEFAULT_EMAIL_SUBJECT = "AlphaZee Customer Inquiry"
DEFAULT_EMAIL_BODY = "Hi AlphaZee Team,\n\nI need assistance with:\n\nOrder Number (optional):\n"


def upgrade():
    op.add_column(
        'store_settings',
        sa.Column(
            'footer_quote',
            sa.String(length=300),
            nullable=False,
            server_default=sa.text(f"'{DEFAULT_FOOTER_QUOTE}'")
        )
    )
    op.add_column(
        'store_settings',
        sa.Column(
            'whatsapp_prefill_message',
            sa.String(length=255),
            nullable=True,
            server_default=sa.text(f"'{DEFAULT_WHATSAPP_PREFILL}'")
        )
    )
    op.add_column(
        'store_settings',
        sa.Column(
            'email_subject_template',
            sa.String(length=150),
            nullable=True,
            server_default=sa.text(f"'{DEFAULT_EMAIL_SUBJECT}'")
        )
    )
    op.add_column(
        'store_settings',
        sa.Column(
            'email_body_template',
            sa.Text(),
            nullable=True,
            server_default=sa.text(f"'{DEFAULT_EMAIL_BODY}'")
        )
    )


def downgrade():
    op.drop_column('store_settings', 'email_body_template')
    op.drop_column('store_settings', 'email_subject_template')
    op.drop_column('store_settings', 'whatsapp_prefill_message')
    op.drop_column('store_settings', 'footer_quote')
