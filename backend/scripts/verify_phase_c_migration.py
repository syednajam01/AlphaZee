"""Verify the Phase C upgrade on a unique, retained disposable database."""
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
    database = f'alphazee_phase_c_{uuid.uuid4().hex[:10]}_test'
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

    migrate('upgrade', 'b79e3a2f0d61')
    engine = create_engine(target, hide_parameters=True)
    sentinel = f'SAMPLE-C-MIGRATION-{uuid.uuid4().hex[:8]}'
    with engine.begin() as conn:
        conn.execute(text('''INSERT INTO orders
            (order_number, customer_name, customer_phone, shipping_address_line1,
             shipping_city, shipping_province, payment_method, payment_status,
             subtotal_minor, total_minor, payment_deadline_at)
            VALUES (:number, 'SAMPLE Migration Buyer', '03001234567', 'SAMPLE Test Street',
                    'Lahore', 'Punjab', 'bank_transfer', 'pending', 100, 100, now())'''),
            {'number': sentinel})
    migrate('upgrade', 'head')
    with engine.connect() as conn:
        row = conn.execute(text('''SELECT payment_deadline_at, payment_instructions_sent_at,
            payment_review_status FROM orders WHERE order_number=:number'''), {'number': sentinel}).one()
        assert row == (None, None, 'none')
    columns = {column['name'] for column in inspect(engine).get_columns('orders')}
    assert {'payment_instructions_sent_at', 'payment_review_status', 'payment_verified_at'}.issubset(columns)
    migrate('downgrade', 'b79e3a2f0d61')
    assert 'payment_review_status' not in {column['name'] for column in inspect(engine).get_columns('orders')}
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM orders WHERE order_number=:number'),
                           {'number': sentinel}) == 1
    migrate('upgrade', 'head')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT payment_review_status FROM orders WHERE order_number=:number'),
                           {'number': sentinel}) == 'none'
    engine.dispose()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'test_database': database, 'browser_used': False,
              'upgrade_downgrade_reupgrade': 'passed', 'historical_order_preserved': True,
              'premature_deadline_cleared': True, 'development_database_modified': False,
              'test_database_retained': True}
    (BACKEND.parent / '.context' / 'phase_c_migration_verification.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
