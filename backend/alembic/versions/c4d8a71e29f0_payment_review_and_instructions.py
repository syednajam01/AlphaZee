"""Record bank instruction handoff, receipt verification and expiry review.

Revision ID: c4d8a71e29f0
Revises: b79e3a2f0d61
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'c4d8a71e29f0'
down_revision = 'b79e3a2f0d61'
branch_labels = None
depends_on = None


def upgrade():
    columns = [
        sa.Column('payment_instructions_sent_at', sa.DateTime(timezone=True)),
        sa.Column('payment_instructions_channel', sa.String(32)),
        sa.Column('payment_instructions_reference', sa.String(200)),
        sa.Column('payment_instructions_sent_by_user_id', UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL')),
        sa.Column('payment_bank_name_snapshot', sa.String(120)),
        sa.Column('payment_account_title_snapshot', sa.String(120)),
        sa.Column('payment_account_number_snapshot', sa.String(64)),
        sa.Column('payment_iban_snapshot', sa.String(34)),
        sa.Column('payment_verified_at', sa.DateTime(timezone=True)),
        sa.Column('payment_verified_by_user_id', UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL')),
        sa.Column('payment_review_status', sa.String(32), nullable=False, server_default='none'),
        sa.Column('payment_review_started_at', sa.DateTime(timezone=True)),
        sa.Column('payment_reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('payment_reviewed_by_user_id', UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL')),
        sa.Column('payment_review_note', sa.Text()),
    ]
    for column in columns:
        op.add_column('orders', column)
    op.create_check_constraint('ck_orders_payment_review_status', 'orders',
        "payment_review_status IN ('none', 'required', 'resolved_paid', 'released_unpaid')")
    op.create_index('idx_orders_payment_review_status', 'orders', ['payment_review_status'])
    # Old four-hour timestamps were computed at checkout, so none establishes
    # that payment instructions were actually handed to a customer.
    op.execute("UPDATE orders SET payment_deadline_at = NULL WHERE payment_method = 'bank_transfer' AND payment_status = 'pending'")


def downgrade():
    op.drop_index('idx_orders_payment_review_status', table_name='orders')
    op.drop_constraint('ck_orders_payment_review_status', 'orders', type_='check')
    for name in (
        'payment_review_note', 'payment_reviewed_by_user_id', 'payment_reviewed_at',
        'payment_review_started_at', 'payment_review_status', 'payment_verified_by_user_id',
        'payment_verified_at', 'payment_iban_snapshot', 'payment_account_number_snapshot',
        'payment_account_title_snapshot', 'payment_bank_name_snapshot',
        'payment_instructions_sent_by_user_id', 'payment_instructions_reference',
        'payment_instructions_channel', 'payment_instructions_sent_at',
    ):
        op.drop_column('orders', name)
