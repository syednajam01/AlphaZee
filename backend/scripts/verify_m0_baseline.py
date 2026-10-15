"""Read-only development baseline plus a snapshot-consistent private backup/restore.

Run from the repository root. Only a fresh generated *_test database is written.
The restore contains private development data; never use it for browser fixtures.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from verify_phase_v_http import request

COMPOSE = ['docker', 'compose', '--env-file', '.env.docker.local']


def command(args, **kwargs):
    result = subprocess.run(args, cwd=ROOT, stderr=subprocess.PIPE, **kwargs)
    if result.returncode:
        # Never echo subprocess/config/SQL errors that could contain secrets.
        raise RuntimeError(f'{args[0]} command failed (exit {result.returncode})')
    return result


def fingerprint(connection):
    connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
    result = {}
    for table in sorted(inspect(connection).get_table_names(schema='public')):
        identifier = connection.dialect.identifier_preparer.quote(table)
        digest = hashlib.sha256()
        count = 0
        rows = connection.execution_options(stream_results=True).execute(text(
            f'SELECT row_to_json(t)::text FROM public.{identifier} t '
            'ORDER BY row_to_json(t)::text COLLATE "C"'))
        for row in rows:
            digest.update(row[0].encode('utf-8') + b'\n')
            count += 1
        result[table] = {'rows': count, 'sha256': digest.hexdigest()}
    return result


def config_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ('backend/.env', '.env.docker.local', 'docker-compose.yml', 'compose.prod.yml')
            if (ROOT / name).is_file()}


def schema_manifest(connection):
    queries = {
        'columns': "SELECT table_name,column_name,data_type,is_nullable,column_default "
                   "FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position",
        'constraints': "SELECT c.relname,k.conname,pg_get_constraintdef(k.oid) FROM pg_constraint k "
                       "JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
                       "WHERE n.nspname='public' ORDER BY c.relname,k.conname",
        'indexes': "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' "
                   "ORDER BY tablename,indexname",
        'triggers': "SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname",
        'sequences': "SELECT sequencename,data_type,start_value,min_value,max_value,increment_by,cycle,"
                     "cache_size,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename",
    }
    return {key: [list(row) for row in connection.execute(text(query))]
            for key, query in queries.items()}


def normalized_schema_manifest(connection):
    payload = schema_manifest(connection)
    # pg_restore reparses varchar[] -> text[] casts as per-element text casts.
    # Normalize only these equivalent generated forms; retain other SQL details.
    def normalize(value):
        if not isinstance(value, str):
            return value
        value = re.sub(r"\(\(ARRAY\[([^\]]*)\]\)::text\[\]\)",
                       lambda match: '(ARRAY[' + match[1].replace('::character varying', '::text') + '])', value)
        return re.sub(r"\(('(?:[^']|'')*')::character varying\)::text", r'\1::text', value)
    payload = {key: [[normalize(value) for value in row] for row in rows]
               for key, rows in payload.items()}
    return payload


def schema_fingerprint(connection):
    return hashlib.sha256(json.dumps(normalized_schema_manifest(connection), default=str, sort_keys=True).encode()).hexdigest()


def http_checks():
    checks = {}
    for label, base in [('web', 'http://127.0.0.1:13000'), ('api', 'http://127.0.0.1:18000')]:
        status, data = request(base, '/api/v1/ready')
        if status != 200 or data.get('database') != 'connected':
            raise RuntimeError('Local readiness failed')
        checks[label + '_ready'] = status
        status, data = request(base, '/api/v1/storefront/capabilities')
        if status != 200 or data.get('checkout_enabled') is not False or data.get('test_mode') is not False:
            raise RuntimeError('Normal checkout containment failed')
        checks[label + '_capabilities'] = data
        for path in ('/admin/overview', '/admin/catalog/variants'):
            status, _ = request(base, '/api/v1' + path)
            if status != 401:
                raise RuntimeError('Anonymous owner access was accepted')
            checks[label + path] = status
        status, _ = request(base, '/api/v1/orders', method='POST', payload={
            'customer_name': 'SAMPLE M0 Gate', 'customer_phone': '03001234567',
            'shipping_address_line1': 'SAMPLE Street', 'shipping_city': 'Lahore',
            'shipping_province': 'Punjab', 'payment_method': 'cod',
            'items': [{'variant_id': 1, 'quantity': 1}]},
            headers={'Origin': 'http://localhost:13000', 'Idempotency-Key': 'm0_' + uuid.uuid4().hex})
        if status != 503:
            raise RuntimeError('Direct/proxied public order containment failed')
        checks[label + '_order_post'] = status
    return checks


def main(*, report_name='m0_baseline_verification.json', phase='M0', restore_prefix='alphazee_m0_restore_'):
    url = make_url(settings.database_url)
    if (settings.app_env != 'development' or settings.checkout_enabled
            or url.get_backend_name() != 'postgresql' or url.query
            or url.host not in {'localhost', '127.0.0.1', '::1'}
            or url.port != 5433 or url.database != 'alphazee_dev'):
        raise RuntimeError('Requires the normal loopback development database on port 5433')
    engine = create_engine(url, hide_parameters=True, connect_args={'connect_timeout': 5})
    if Path(report_name).name != report_name or not restore_prefix.replace('_', '').isalnum():
        raise RuntimeError('Invalid internal evidence identifiers')
    restore_name = restore_prefix + uuid.uuid4().hex[:12] + '_test'
    backup_dir = ROOT / '.local' / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (restore_name + '.dump')
    if command(['git', 'check-ignore', str(backup)], stdout=subprocess.PIPE).returncode != 0:
        raise RuntimeError('Private backup path is not ignored by Git')
    hashes_before = config_hashes()
    checks = http_checks()
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as source:
        with source.begin():
            source.execute(text('SET TRANSACTION READ ONLY'))
            source.execute(text("SET LOCAL statement_timeout = '60s'"))
            system_id = str(source.scalar(text('SELECT system_identifier FROM pg_control_system()')))
            container_id = command(COMPOSE + ['exec', '-T', 'db', 'psql', '-U', url.username,
                '-d', url.database, '-Atc', 'SELECT system_identifier FROM pg_control_system()'],
                stdout=subprocess.PIPE).stdout.decode().strip()
            if system_id != container_id:
                raise RuntimeError('Compose DB is not the inspected development PostgreSQL instance')
            before = fingerprint(source)
            schema_before = schema_fingerprint(source)
            revisions = list(source.scalars(text('SELECT version_num FROM alembic_version')))
            snapshot = source.scalar(text('SELECT pg_export_snapshot()'))
            with backup.open('xb') as output:
                command(COMPOSE + ['exec', '-T', 'db', 'pg_dump', '-U', url.username,
                    '-d', url.database, '--format=custom', '--no-owner', '--no-acl',
                    '--snapshot=' + snapshot], stdout=output)
    admin = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as connection:
        # No DROP/--clean; only our fresh, internally generated destination is writable.
        if connection.scalar(text('SELECT 1 FROM pg_database WHERE datname=:name'), {'name': restore_name}):
            raise RuntimeError('Restore destination already exists')
        connection.exec_driver_sql(f'CREATE DATABASE "{restore_name}" TEMPLATE template0')
    admin.dispose()
    with backup.open('rb') as input_file:
        command(COMPOSE + ['exec', '-T', 'db', 'pg_restore', '-U', url.username,
            '-d', restore_name, '--exit-on-error', '--no-owner', '--no-acl'],
            stdin=input_file, stdout=subprocess.DEVNULL)
    restored_engine = create_engine(url.set(database=restore_name), hide_parameters=True)
    with restored_engine.begin() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        restored = fingerprint(connection)
        restored_schema = schema_fingerprint(connection)
    with engine.begin() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        after = fingerprint(connection)
        schema_after = schema_fingerprint(connection)
    restored_engine.dispose()
    engine.dispose()
    if (before != restored or before != after or hashes_before != config_hashes()
            or schema_before != restored_schema or schema_before != schema_after):
        raise RuntimeError('Restored data, development data or configuration fingerprint mismatch')
    report = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'phase': phase,
        'python': platform.python_version(),
        'git_head': command(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE).stdout.decode().strip(),
        'working_tree': command(['git', 'status', '--short'], stdout=subprocess.PIPE).stdout.decode().splitlines(),
        'source': {'host': url.host, 'port': url.port, 'database': url.database},
        'revision': revisions, 'http': checks, 'tables': before,
        'config_hashes': hashes_before, 'config_unchanged': True,
        'backup': str(backup.relative_to(ROOT)), 'backup_bytes': backup.stat().st_size,
        'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
        'restore_database': restore_name, 'restore_matches_all_public_table_rows': True,
        'source_table_rows_unchanged': True, 'restore_retained': True,
        'private_restore_not_a_browser_fixture': True, 'browser_executed': False,
        'schema_and_sequences_sha256': schema_before,
        'restore_schema_and_sequences_match': True,
        'media_storage': 'No managed file storage exists yet; M3 will add it',
    }
    (ROOT / '.context' / report_name).write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('phase', 'revision', 'backup',
        'restore_database', 'restore_matches_all_public_table_rows', 'source_table_rows_unchanged',
        'config_unchanged')}, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        detail = str(error) if type(error) is RuntimeError else type(error).__name__
        print(f'M0 verification failed: {detail}', file=sys.stderr)
        raise SystemExit(1)
