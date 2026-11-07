"""Migration checks use only newly allocated loopback PostgreSQL databases."""
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from alembic.config import Config
from alembic.script import ScriptDirectory


def main():
    url = make_url(os.environ['DATABASE_URL'])
    if url.host not in {'127.0.0.1', 'localhost'} or url.query or url.get_backend_name() != 'postgresql':
        raise RuntimeError('CI migrations require loopback PostgreSQL without query overrides')
    config = Config(str(ROOT / 'backend/alembic.ini'))
    config.set_main_option('script_location', str(ROOT / 'backend/alembic'))
    heads = ScriptDirectory.from_config(config).get_heads()
    if len(heads) != 1:
        raise RuntimeError('Exactly one Alembic head is required')
    name = 'alphazee_ci_migrate_' + secrets.token_hex(6) + '_test'
    admin = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    target = url.set(database=name)
    env = dict(os.environ, DATABASE_URL=target.render_as_string(hide_password=False), APP_ENV='test',
               TEST_CHECKOUT_ENABLED='false', PRODUCTION_CHECKOUT_ENABLED='false', CHECKOUT_LAB='false')
    def migrate(*args):
        subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=ROOT / 'backend', env=env, check=True)
    try:
        migrate('upgrade', 'head')
        engine = create_engine(target)
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == heads[0]
        engine.dispose()
        # Reversible vendor/finance upgrade path, never a production downgrade.
        migrate('downgrade', '6e4a2b8d0c1f')
        migrate('upgrade', 'head')
        print('PASS: clean upgrade and supported downgrade/re-upgrade on disposable DB')
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()

if __name__ == '__main__':
    main()
