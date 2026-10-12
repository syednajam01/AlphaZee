"""Start a separate loopback API after checking its isolated database target."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.config import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', default='.env.browser-test')
    args = parser.parse_args()
    path = Path(args.env_file).resolve()
    if not path.is_file():
        parser.error('Create .env.browser-test from .env.browser-test.example first.')
    current = Settings(_env_file=BACKEND / '.env')
    values = {key: value for key, value in dotenv_values(path).items() if value is not None}
    required = {'APP_ENV', 'DATABASE_URL', 'TEST_CHECKOUT_ENABLED'}
    if not required.issubset(values):
        parser.error('Test configuration must explicitly specify environment, database and checkout flag.')
    try:
        target = Settings(_env_file=None, **{key.lower(): value for key, value in values.items()})
        from sqlalchemy.engine import make_url
        current_url = make_url(current.database_url)
        target_url = make_url(target.database_url)
        if not target.checkout_enabled or target_url.database == current_url.database:
            raise ValueError('Test database must differ from the normal application database.')
    except Exception:
        parser.error('Unsafe test profile: require APP_ENV=test, TEST_CHECKOUT_ENABLED=true, a distinct loopback PostgreSQL *_test database and no connection query overrides.')
    print(f'SAMPLE / TEST API: 127.0.0.1:8001; database={target_url.database}', flush=True)
    # A child process receives test-only configuration. The existing app is untouched.
    result = subprocess.run(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8001'],
        cwd=BACKEND, env={**os.environ, **values},
    )
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
