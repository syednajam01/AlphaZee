"""Exercise the stock migration on a retained, isolated PostgreSQL database."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app.config import settings


def main():
    original = make_url(settings.database_url)
    if original.get_backend_name() != 'postgresql' or original.host not in {
            'localhost', '127.0.0.1', '::1'} or original.query:
        raise RuntimeError('Verification requires loopback PostgreSQL without query overrides.')
    database = f'alphazee_phase_d_{uuid.uuid4().hex[:10]}_test'
    target = original.set(database=database)
    admin = create_engine(original.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as conn:
        assert not conn.scalar(text('SELECT 1 FROM pg_database WHERE datname=:name'), {'name': database})
        conn.exec_driver_sql(f'CREATE DATABASE "{database}"')
    admin.dispose()
    environment = {**os.environ, 'DATABASE_URL': target.render_as_string(hide_password=False),
                   'APP_ENV': 'test', 'TEST_CHECKOUT_ENABLED': 'false', 'DEBUG': 'false'}

    def migrate(*args):
        subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=BACKEND, env=environment,
                       check=True, stdout=subprocess.DEVNULL)

    migrate('upgrade', 'c4d8a71e29f0')
    engine = create_engine(target, hide_parameters=True)
    sentinel = f'SAMPLE-D-MIGRATION-{uuid.uuid4().hex[:8]}'
    with engine.begin() as conn:
        order_id = conn.scalar(text('''INSERT INTO orders
            (order_number, customer_name, customer_phone, shipping_address_line1,
             shipping_city, shipping_province, payment_method, payment_status,
             subtotal_minor, total_minor, order_status)
            VALUES (:number, 'SAMPLE Migration Buyer', '03001234567', 'SAMPLE Test Street',
                    'Lahore', 'Punjab', 'cod', 'pending', 100, 100, 'dispatched') RETURNING id'''),
            {'number': sentinel})
        shipment_id = conn.scalar(text('''INSERT INTO shipments
            (order_id, courier_code, tracking_number, status)
            VALUES (:order_id, 'manual', :number, 'dispatched') RETURNING id'''),
            {'order_id': order_id, 'number': sentinel})
    migrate('upgrade', 'head')
    with engine.connect() as conn:
        row = conn.execute(text('''SELECT stock_reconciliation_status, status FROM shipments
            WHERE id=:id'''), {'id': shipment_id}).one()
        assert row == ('legacy_review', 'dispatched')
        assert conn.scalar(text('SELECT count(*) FROM shipment_allocations')) == 0
        assert conn.scalar(text('SELECT count(*) FROM stock_events WHERE source_ref IS NOT NULL')) == 0
    assert {'received_quantity', 'sellable_quantity', 'damaged_quantity', 'inspection_notes'}.issubset(
        {c['name'] for c in inspect(engine).get_columns('shipment_allocations')})
    migrate('downgrade', 'c4d8a71e29f0')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT status FROM shipments WHERE id=:id'), {'id': shipment_id}) == 'dispatched'
    migrate('upgrade', 'head')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT stock_reconciliation_status FROM shipments WHERE id=:id'),
                           {'id': shipment_id}) == 'legacy_review'
    engine.dispose()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'test_database': database,
              'browser_used': False, 'upgrade_downgrade_reupgrade': 'passed',
              'historical_shipment_preserved': True, 'legacy_shipment_flagged': True,
              'stock_not_guessed_or_deducted': True, 'development_database_modified': False,
              'test_database_retained': True}
    (BACKEND.parent / '.context' / 'phase_d_migration_verification.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
