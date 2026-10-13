"""Verify the G/F migration chain using a uniquely named disposable PostgreSQL DB."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.config import settings


def main():
    source = make_url(settings.database_url)
    if source.get_backend_name() != 'postgresql' or source.host not in {
            'localhost', '127.0.0.1', '::1'} or source.query:
        raise RuntimeError('Migration verification requires loopback PostgreSQL without query overrides.')
    name = f'alphazee_phase_v_{uuid.uuid4().hex[:10]}_test'
    target = source.set(database=name)
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as conn:
        assert not conn.scalar(text('SELECT 1 FROM pg_database WHERE datname=:name'), {'name': name})
        conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    admin.dispose()
    environment = {**os.environ, 'DATABASE_URL': target.render_as_string(hide_password=False),
                   'APP_ENV': 'test', 'TEST_CHECKOUT_ENABLED': 'false', 'DEBUG': 'false'}

    def migrate(*args):
        subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=BACKEND, env=environment,
                       check=True, stdout=subprocess.DEVNULL)

    migrate('upgrade', 'd61f4b8c2a90')
    engine = create_engine(target, hide_parameters=True)
    number = f'SAMPLE-V-MIGRATION-{uuid.uuid4().hex[:8]}'
    with engine.begin() as conn:
        order_id = conn.scalar(text('''INSERT INTO orders
            (order_number, customer_name, customer_phone, shipping_address_line1,
             shipping_city, shipping_province, payment_method, payment_status,
             subtotal_minor, total_minor, order_status)
            VALUES (:number, 'SAMPLE Migration Buyer', '03001234567', 'SAMPLE Street',
                    'Lahore', 'Punjab', 'cod', 'verified', 100000, 100000, 'delivered')
            RETURNING id'''), {'number': number})
        shipment_id = conn.scalar(text('''INSERT INTO shipments
            (order_id, courier_code, tracking_number, status, cod_amount_minor,
             cod_remitted_amount_minor, cod_remittance_status, cod_remittance_reference,
             delivered_at)
            VALUES (:order_id, 'manual', :number, 'delivered', 100000,
                    70000, 'remitted', 'SAMPLE-OLD-BANK-REF', now()) RETURNING id'''),
            {'order_id': order_id, 'number': number})

    migrate('upgrade', 'a72e901b4c63')
    assert 'fulfillment_kind' in {col['name'] for col in inspect(engine).get_columns('order_lines')}
    assert 'order_access_grants' in inspect(engine).get_table_names()
    migrate('upgrade', 'head')
    with engine.connect() as conn:
        row = conn.execute(text('''SELECT cod_remittance_status, cod_remitted_amount_minor
            FROM shipments WHERE id=:id'''), {'id': shipment_id}).one()
        assert row == ('partial', 70000)
        evidence = conn.execute(text('''SELECT id, amount_minor, reference, note
            FROM courier_settlement_entries WHERE shipment_id=:id'''), {'id': shipment_id}).one()
        assert evidence.amount_minor == 70000
        assert evidence.reference == f'legacy-remittance-{shipment_id}'
        assert 'SAMPLE-OLD-BANK-REF' in evidence.note
        assert conn.scalar(text('SELECT count(*) FROM refund_executions')) == 0
        trigger_names = set(conn.execute(text('''SELECT tgname FROM pg_trigger
            WHERE tgname IN ('courier_settlement_append_only', 'refund_execution_append_only')''')).scalars())
        assert trigger_names == {'courier_settlement_append_only', 'refund_execution_append_only'}
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE courier_settlement_entries SET note='changed' WHERE id=:id"),
                         {'id': evidence.id})
    except DBAPIError as error:
        assert 'Financial evidence is append-only' in str(error)
    else:
        raise AssertionError('Existing financial evidence was mutable.')

    migrate('downgrade', 'd61f4b8c2a90')
    with engine.connect() as conn:
        row = conn.execute(text('''SELECT cod_remittance_status, cod_remitted_amount_minor
            FROM shipments WHERE id=:id'''), {'id': shipment_id}).one()
        assert row == ('pending_remittance', 70000)
        assert conn.scalar(text('SELECT count(*) FROM orders WHERE id=:id'), {'id': order_id}) == 1
    migrate('upgrade', 'head')
    migrate('check')
    with engine.connect() as conn:
        assert conn.scalar(text('''SELECT count(*) FROM courier_settlement_entries
            WHERE shipment_id=:id'''), {'id': shipment_id}) == 1
        assert conn.scalar(text('''SELECT cod_remittance_status FROM shipments
            WHERE id=:id'''), {'id': shipment_id}) == 'partial'
    engine.dispose()
    report = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'database': name, 'database_kind': 'unique_disposable_test',
        'prior_revision': 'd61f4b8c2a90', 'head_revision': 'c94e31f7d562',
        'upgrade_downgrade_reupgrade': 'passed', 'legacy_short_payout': 'partial',
        'payout_receipt_imported_once': True, 'refund_cash_not_invented': True,
        'append_only_trigger_rejected_update': True, 'alembic_check': 'passed',
        'development_database_modified': False, 'database_retained_for_inspection': True,
        'browser_used': False,
    }
    output = BACKEND.parent / '.context' / 'phase_v_migration_verification.json'
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
