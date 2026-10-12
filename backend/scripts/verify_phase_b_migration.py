"""Verify the additive checkout migration on a unique disposable database."""
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
    if (original.get_backend_name() != 'postgresql' or original.host not in
            {'localhost', '127.0.0.1', '::1'} or original.query):
        raise RuntimeError('Verification requires loopback PostgreSQL without query overrides.')
    database = f'alphazee_phase_b_{uuid.uuid4().hex[:10]}_test'
    assert database != original.database and database.endswith('_test')
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

    migrate('upgrade', '6a1e9b32c704')
    engine = create_engine(target, hide_parameters=True)
    sentinel_number = f'SAMPLE-B-MIGRATION-{uuid.uuid4().hex[:8]}'
    with engine.begin() as conn:
        conn.execute(text('''INSERT INTO orders
            (order_number, customer_name, customer_phone, shipping_address_line1,
             shipping_city, shipping_province, payment_method, subtotal_minor, total_minor,
             idempotency_key)
            VALUES (:number, 'SAMPLE Migration Buyer', '03001234567', 'SAMPLE Test Street',
                    'Lahore', 'Punjab', 'cod', 100, 100, :key)'''),
            {'number': sentinel_number, 'key': f'SAMPLE-{uuid.uuid4().hex}'})
    migrate('upgrade', 'head')
    assert {'checkout_session_hash', 'request_fingerprint'}.issubset(
        {column['name'] for column in inspect(engine).get_columns('orders')})
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM orders WHERE order_number=:number'),
                           {'number': sentinel_number}) == 1
        assert conn.scalar(text('SELECT request_fingerprint FROM orders WHERE order_number=:number'),
                           {'number': sentinel_number}) is None
    migrate('downgrade', '6a1e9b32c704')
    assert 'request_fingerprint' not in {column['name'] for column in inspect(engine).get_columns('orders')}
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM orders WHERE order_number=:number'),
                           {'number': sentinel_number}) == 1
    migrate('upgrade', 'head')
    engine.dispose()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'test_database': database, 'browser_used': False,
              'upgrade_downgrade_reupgrade': 'passed', 'historical_order_preserved': True,
              'development_database_modified': False, 'test_database_retained': True}
    (BACKEND.parent / '.context' / 'phase_b_migration_verification.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
