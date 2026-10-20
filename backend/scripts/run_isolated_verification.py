"""Run pytest in a newly created disposable database; capture terminal evidence."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.config import settings


def main():
    root = Path(__file__).resolve().parents[2]
    base = make_url(settings.database_url)
    if base.host not in {'localhost', '127.0.0.1'} or base.query:
        raise RuntimeError('Only loopback PostgreSQL without query overrides is supported.')
    name = f'alphazee_verify_{secrets.token_hex(5)}_test'
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as db:
        db.execute(text(f'CREATE DATABASE "{name}"'))
    env = dict(os.environ, TEST_DATABASE_URL=base.set(host='127.0.0.1', database=name).render_as_string(hide_password=False),
               DEBUG='false', PYTHONUNBUFFERED='1')
    target = root / '.local' / 'vf-terminal-verification.txt'
    target.parent.mkdir(exist_ok=True)
    try:
        print(f'Running against new disposable database {name}; evidence: .local/vf-terminal-verification.txt', flush=True)
        args = sys.argv[1:] or ['backend/tests']
        with target.open('w', encoding='utf-8') as output:
            result = subprocess.run([sys.executable, '-u', '-m', 'pytest', *args,
                '-vv', '--tb=short', '-p', 'no:cacheprovider', '-o', 'faulthandler_timeout=120',
                '--basetemp=.local/vf-isolated-pytest', '--junitxml=.local/vf-terminal-verification.xml'],
                cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT)
        print('\n'.join(target.read_text(encoding='utf-8').splitlines()[-18:]), flush=True)
        return result.returncode
    finally:
        with admin.connect() as db:
            db.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
