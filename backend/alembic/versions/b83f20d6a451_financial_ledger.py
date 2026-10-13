"""Append-only courier settlement and executed refund evidence.

Revision ID: b83f20d6a451
Revises: a72e901b4c63
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'b83f20d6a451'
down_revision = 'a72e901b4c63'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('courier_settlement_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('shipment_id', UUID(as_uuid=True), sa.ForeignKey('shipments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('entry_type', sa.String(32), nullable=False),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(120), nullable=False),
        sa.Column('note', sa.Text()),
        sa.Column('final_statement', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('recorded_by_user_id', UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL')),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_minor > 0', name='ck_courier_settlement_amount_positive'),
        sa.CheckConstraint("entry_type IN ('receipt', 'outbound_shipping', 'rto_shipping', 'other_deduction')",
                           name='ck_courier_settlement_entry_type'))
    op.create_index('uq_courier_settlement_reference', 'courier_settlement_entries', ['reference'], unique=True)
    op.create_index('ix_courier_settlement_shipment', 'courier_settlement_entries', ['shipment_id'])
    op.create_table('refund_executions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('return_id', UUID(as_uuid=True), sa.ForeignKey('order_returns.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(120), nullable=False),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('note', sa.Text()),
        sa.Column('recorded_by_user_id', UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL')),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_minor > 0', name='ck_refund_execution_amount_positive'))
    op.create_index('uq_refund_execution_reference', 'refund_executions', ['reference'], unique=True)
    op.create_index('ix_refund_execution_return', 'refund_executions', ['return_id'])
    op.drop_constraint('ck_shipments_cod_remittance_status', 'shipments', type_='check')
    op.create_check_constraint('ck_shipments_cod_remittance_status', 'shipments',
        "cod_remittance_status IN ('pending_remittance', 'partial', 'remitted', 'not_applicable', 'disputed')")
    # Preserve historical payout claims without manufacturing deductions or refund cash.
    op.execute("""
        INSERT INTO courier_settlement_entries
            (shipment_id, entry_type, amount_minor, reference, note, recorded_at)
        SELECT id, 'receipt', cod_remitted_amount_minor,
               'legacy-remittance-' || id::text,
               'Imported from pre-ledger payout snapshot; review original bank reference: ' ||
                   COALESCE(cod_remittance_reference, '(missing)'),
               COALESCE(cod_remitted_at, created_at)
        FROM shipments WHERE cod_remitted_amount_minor > 0
    """)


def downgrade():
    op.drop_constraint('ck_shipments_cod_remittance_status', 'shipments', type_='check')
    op.execute("UPDATE shipments SET cod_remittance_status = 'pending_remittance' WHERE cod_remittance_status = 'partial'")
    op.create_check_constraint('ck_shipments_cod_remittance_status', 'shipments',
        "cod_remittance_status IN ('pending_remittance', 'remitted', 'not_applicable', 'disputed')")
    op.drop_index('ix_refund_execution_return', table_name='refund_executions')
    op.drop_index('uq_refund_execution_reference', table_name='refund_executions')
    op.drop_table('refund_executions')
    op.drop_index('ix_courier_settlement_shipment', table_name='courier_settlement_entries')
    op.drop_index('uq_courier_settlement_reference', table_name='courier_settlement_entries')
    op.drop_table('courier_settlement_entries')
