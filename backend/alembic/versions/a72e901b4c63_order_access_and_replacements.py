"""Order-scoped customer access and independent exchange fulfillment.

Revision ID: a72e901b4c63
Revises: d61f4b8c2a90
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'a72e901b4c63'
down_revision = 'd61f4b8c2a90'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('order_returns', sa.Column('replacement_charge_minor', sa.Integer(), nullable=False,
                                              server_default='0'))
    op.create_check_constraint('ck_order_returns_replacement_charge_nonnegative', 'order_returns',
                               'replacement_charge_minor >= 0')
    op.create_table('order_access_grants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('issued_by_user_id', UUID(as_uuid=True), sa.ForeignKey('user_accounts.id', ondelete='SET NULL')),
        sa.Column('issue_note', sa.Text()))
    op.create_index('ix_order_access_grants_order_id', 'order_access_grants', ['order_id'])
    op.create_table('order_access_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('grant_id', UUID(as_uuid=True), sa.ForeignKey('order_access_grants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)))
    op.create_index('ix_order_access_sessions_grant_id', 'order_access_sessions', ['grant_id'])
    op.create_table('order_access_attempts',
        sa.Column('key_hash', sa.String(64), primary_key=True),
        sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.CheckConstraint('attempts > 0', name='ck_order_access_attempts_positive'))

    op.add_column('order_lines', sa.Column('fulfillment_kind', sa.String(20), nullable=False, server_default='original'))
    op.add_column('order_lines', sa.Column('replacement_return_id', UUID(as_uuid=True)))
    op.create_foreign_key('fk_order_lines_replacement_return', 'order_lines', 'order_returns',
                          ['replacement_return_id'], ['id'], ondelete='RESTRICT')
    op.create_check_constraint('ck_order_lines_fulfillment_kind', 'order_lines',
        "fulfillment_kind IN ('original', 'replacement')")
    op.create_check_constraint('ck_order_lines_replacement_link', 'order_lines',
        "(fulfillment_kind = 'original' AND replacement_return_id IS NULL) OR "
        "(fulfillment_kind = 'replacement' AND replacement_return_id IS NOT NULL)")
    op.create_index('uq_order_lines_replacement_return', 'order_lines', ['replacement_return_id'], unique=True,
        postgresql_where=sa.text('replacement_return_id IS NOT NULL'))
    op.add_column('shipments', sa.Column('replacement_return_id', UUID(as_uuid=True),
        sa.ForeignKey('order_returns.id', ondelete='RESTRICT')))
    op.create_index('uq_shipments_replacement_return', 'shipments', ['replacement_return_id'], unique=True,
        postgresql_where=sa.text('replacement_return_id IS NOT NULL'))


def downgrade():
    op.drop_index('uq_shipments_replacement_return', table_name='shipments')
    op.drop_column('shipments', 'replacement_return_id')
    op.drop_index('uq_order_lines_replacement_return', table_name='order_lines')
    op.drop_constraint('fk_order_lines_replacement_return', 'order_lines', type_='foreignkey')
    op.drop_constraint('ck_order_lines_replacement_link', 'order_lines', type_='check')
    op.drop_constraint('ck_order_lines_fulfillment_kind', 'order_lines', type_='check')
    op.drop_column('order_lines', 'replacement_return_id')
    op.drop_column('order_lines', 'fulfillment_kind')
    op.drop_table('order_access_attempts')
    op.drop_index('ix_order_access_sessions_grant_id', table_name='order_access_sessions')
    op.drop_table('order_access_sessions')
    op.drop_index('ix_order_access_grants_order_id', table_name='order_access_grants')
    op.drop_table('order_access_grants')
    op.drop_constraint('ck_order_returns_replacement_charge_nonnegative', 'order_returns', type_='check')
    op.drop_column('order_returns', 'replacement_charge_minor')
