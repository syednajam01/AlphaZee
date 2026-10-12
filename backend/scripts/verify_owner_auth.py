"""Disposable migration + real HTTP session persistence verification. No browser."""
from datetime import datetime, timezone
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.config import settings
from app.models.auth import OwnerCredential
from app.models.suppliers import UserAccount
from app.services.owners import provision_owner


def main():
    original = make_url(settings.database_url)
    if original.get_backend_name() != 'postgresql' or original.host not in {'localhost', '127.0.0.1', '::1'} or original.query:
        raise RuntimeError('Verification requires a loopback PostgreSQL connection without query overrides.')
    database = f'alphazee_auth_{uuid.uuid4().hex[:10]}_test'
    assert database.endswith('_test') and database != original.database
    target = original.set(database=database)
    admin = create_engine(original.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as conn:
        assert not conn.scalar(text('SELECT 1 FROM pg_database WHERE datname=:name'), {'name': database})
        conn.exec_driver_sql(f'CREATE DATABASE "{database}"')
    admin.dispose()
    environment = {**os.environ, 'DATABASE_URL': target.render_as_string(hide_password=False),
                   'APP_ENV': 'test', 'TEST_CHECKOUT_ENABLED': 'false', 'DEBUG': 'false',
                   'ALLOWED_ORIGINS': 'http://localhost:3000'}

    def migrate(*arguments):
        subprocess.run([sys.executable, '-m', 'alembic', *arguments], cwd=BACKEND, env=environment, check=True)

    migrate('upgrade', '13b1315d1395')
    engine = create_engine(target, hide_parameters=True)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO user_accounts (auth_subject, display_name) VALUES ('SAMPLE-preserved', 'SAMPLE migration sentinel')"))
    migrate('upgrade', 'head')
    inspector = inspect(engine)
    assert {'owner_credentials', 'owner_sessions', 'owner_login_buckets'}.issubset(inspector.get_table_names())
    assert inspector.get_foreign_keys('owner_sessions')[0]['referred_table'] == 'owner_credentials'
    migrate('downgrade', '13b1315d1395')
    assert 'owner_sessions' not in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM user_accounts WHERE auth_subject='SAMPLE-preserved'")) == 1
    migrate('upgrade', 'head')
    with Session(engine) as db:
        provision_owner(db, 'sample_owner', 'SAMPLE-only-password-2026')
        db.commit()

    # Choose a free loopback port without replacing the user's running API.
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))

    def request(path, data=None, csrf=None):
        headers = {'Origin': 'http://localhost:3000'}
        if csrf: headers['X-CSRF-Token'] = csrf
        if data is not None: headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(origin + path, headers=headers,
            data=json.dumps(data).encode() if data is not None else None)
        try: response = client.open(req, timeout=5)
        except urllib.error.HTTPError as error: response = error
        with response:
            return response.status, json.loads(response.read())

    def start():
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
            '--port', str(port), '--no-proxy-headers'], cwd=BACKEND, env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for _ in range(60):
            if process.poll() is not None: raise RuntimeError('Disposable API exited before readiness.')
            try:
                if request('/api/v1/ready')[0] == 200: return process
            except (OSError, urllib.error.URLError): pass
            time.sleep(0.2)
        process.terminate(); process.wait(timeout=10)
        raise RuntimeError('Disposable API did not become ready.')

    process = start()
    try:
        status, session = request('/api/v1/auth/login', {'username': 'sample_owner', 'password': 'SAMPLE-only-password-2026'})
        assert status == 200
        assert request('/api/v1/admin/overview')[0] == 200
        assert request('/api/v1/auth/logout', {})[0] == 403
        process.terminate(); process.wait(timeout=10)
        process = start()
        assert request('/api/v1/auth/session')[0] == 200  # database-backed, survives process restart
        assert request('/api/v1/auth/logout', {}, session['csrf_token'])[0] == 200
        assert request('/api/v1/admin/overview')[0] == 401
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
        engine.dispose()

    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'test_database': database,
        'development_database_modified': False, 'migration_upgrade_downgrade_reupgrade': 'passed',
        'existing_user_sentinel_preserved': True, 'real_http_login': 'passed', 'real_http_csrf_rejection': 'passed',
        'session_survives_api_restart': True, 'real_http_logout_revocation': 'passed',
        'browser_used': False, 'test_database_retained': True}
    destination = BACKEND.parent / '.context' / 'phase_a_auth_verification.json'
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
