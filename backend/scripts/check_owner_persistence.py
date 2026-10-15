"""Verify a chosen development owner's login before/after database and API restart."""
import argparse
from datetime import datetime, timezone
import getpass
import http.cookiejar
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.models.auth import OwnerCredential


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('username')
    args = parser.parse_args()
    url = make_url(settings.database_url)
    if not sys.stdin.isatty() or not settings.is_development or settings.checkout_enabled or url.host != 'localhost' or url.port != 5433 or url.database != 'alphazee_dev':
        raise RuntimeError('Requires an interactive terminal and the normal development database')
    password = getpass.getpass('Owner password (hidden): ')
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(path, payload=None):
        req = urllib.request.Request('http://localhost:13000/api/v1' + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Origin': 'http://localhost:13000', 'Content-Type': 'application/json'})
        with opener.open(req, timeout=10) as response: return json.load(response)
    login = call('/auth/login', {'username': args.username, 'password': password})
    engine = create_engine(settings.database_url, hide_parameters=True, pool_pre_ping=True)
    with engine.connect() as db:
        before = db.execute(select(OwnerCredential.user_id, OwnerCredential.password_hash).where(OwnerCredential.username == args.username)).one()
    compose = ['docker', 'compose', '--env-file', '.env.docker.local']
    subprocess.run(compose + ['restart', 'db', 'api'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 90
    while True:
        try:
            current = call('/auth/session')
            assert current['username'] == args.username
            break
        except Exception:
            if time.monotonic() > deadline: raise RuntimeError('Account/session did not recover after restart') from None
            time.sleep(.5)
    with engine.connect() as db:
        after = db.execute(select(OwnerCredential.user_id, OwnerCredential.password_hash).where(OwnerCredential.username == args.username)).one()
    engine.dispose()
    assert before == after
    assert call('/auth/login', {'username': args.username, 'password': password})['username'] == args.username
    password = None
    container = subprocess.check_output(compose + ['ps', '-q', 'db'], cwd=ROOT).decode().strip()
    mounts = json.loads(subprocess.check_output(['docker', 'inspect', container], cwd=ROOT))[0]['Mounts']
    volume = next(m['Name'] for m in mounts if m['Destination'] == '/var/lib/postgresql/data')
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'username': args.username,
              'account_and_password_hash_preserved': True, 'login_after_database_api_restart': True,
              'existing_unexpired_session_survives': True, 'database_volume': volume, 'plaintext_password_saved': False}
    (ROOT / '.context/m3_owner_persistence_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Owner login and persistent account verified after database/API restart. No password recorded.')


if __name__ == '__main__': main()
