"""Reconcile legacy payout status and make financial evidence append-only.

Revision ID: c94e31f7d562
Revises: b83f20d6a451
"""
from alembic import op

revision = 'c94e31f7d562'
down_revision = 'b83f20d6a451'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE shipments SET cod_remittance_status = CASE
            WHEN cod_remitted_amount_minor >= cod_amount_minor THEN 'remitted'
            WHEN cod_remittance_status = 'disputed' THEN 'disputed'
            ELSE 'partial' END
        WHERE cod_amount_minor > 0 AND cod_remitted_amount_minor > 0
    """)
    op.execute("""
        CREATE FUNCTION reject_financial_evidence_change() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Financial evidence is append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""CREATE TRIGGER courier_settlement_append_only
        BEFORE UPDATE OR DELETE ON courier_settlement_entries
        FOR EACH ROW EXECUTE FUNCTION reject_financial_evidence_change()""")
    op.execute("""CREATE TRIGGER refund_execution_append_only
        BEFORE UPDATE OR DELETE ON refund_executions
        FOR EACH ROW EXECUTE FUNCTION reject_financial_evidence_change()""")


def downgrade():
    op.execute('DROP TRIGGER refund_execution_append_only ON refund_executions')
    op.execute('DROP TRIGGER courier_settlement_append_only ON courier_settlement_entries')
    op.execute('DROP FUNCTION reject_financial_evidence_change()')
