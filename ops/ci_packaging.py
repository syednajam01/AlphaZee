"""Validate production Compose and its preflight using synthetic credentials only."""
import json
import os
import subprocess
from pathlib import Path
import secrets
import tempfile

from deploy import migration_args


def main():
    env = dict(os.environ, COMPOSE_PROJECT_NAME='alphazee-ci-packaging',
               POSTGRES_USER='ci', POSTGRES_PASSWORD='ci-only-password-long-enough', POSTGRES_DB='ci_app',
               DATABASE_URL='postgresql://ci:ci-only-password-long-enough@db:5432/ci_app',
               SITE_DOMAIN='ci.alphazee.tech', APP_ENV='production', DEBUG='false',
               TEST_CHECKOUT_ENABLED='false', ALLOWED_ORIGINS='https://ci.alphazee.tech',
               PRODUCTION_CHECKOUT_ENABLED='false')
    def validate(values):
        subprocess.run(['docker', 'compose', '-f', 'compose.prod.yml', 'config', '--quiet'], env=values, check=True)
        args = ['docker', 'run', '--rm']
        for key in ('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB', 'DATABASE_URL', 'SITE_DOMAIN',
                    'APP_ENV', 'DEBUG', 'TEST_CHECKOUT_ENABLED', 'ALLOWED_ORIGINS', 'PRODUCTION_CHECKOUT_ENABLED'):
            args += ['-e', key]
        return subprocess.run(args + ['alphazee-ci-api', 'python', 'scripts/check_production_deployment.py'],
                              env=values, capture_output=True).returncode
    assert validate(env) == 0, 'Valid production fixture rejected'
    assert validate(dict(env, DEBUG='true')) != 0, 'Debug deployment accepted'
    assert validate(dict(env, TEST_CHECKOUT_ENABLED='true')) != 0, 'Test checkout accepted'
    assert validate(dict(env, POSTGRES_PASSWORD='weak')) != 0, 'Mismatched credentials accepted'
    run = ['docker', 'run', '--rm']
    for name in ('DATABASE_URL', 'APP_ENV', 'DEBUG', 'TEST_CHECKOUT_ENABLED', 'PRODUCTION_CHECKOUT_ENABLED', 'ALLOWED_ORIGINS', 'SITE_DOMAIN'):
        run += ['-e', name]
    subprocess.run(run + ['alphazee-ci-api', 'python', '-c',
        'from app.main import app; from alembic.config import Config; from alembic.script import ScriptDirectory; '
        'assert any(r.path == "/api/v1/release" for r in app.routes); '
        'assert len(ScriptDirectory.from_config(Config("alembic.ini")).get_heads()) == 1; print("PASS: production API imports and migration discovery")'],
        env=env, check=True)
    # Exercise the actual production migration CLI against a fresh, private Docker DB.
    # This catches invalid Compose options that mocked orchestration tests cannot detect.
    with tempfile.TemporaryDirectory() as temporary:
        override = Path(temporary) / 'images.json'
        override.write_text(json.dumps({'services': {'api': {'image': 'alphazee-ci-api'},
            'migrate': {'image': 'alphazee-ci-api'}, 'web': {'image': 'alphazee-ci-web'}}}))
        project = 'alphazee-package-test-' + secrets.token_hex(6)
        command = ['docker', 'compose', '--project-name', project, '-f', 'compose.prod.yml', '-f', str(override)]
        try:
            subprocess.run(command + ['up', '-d', '--wait', 'db'], env=env, check=True)
            subprocess.run(command + migration_args(), env=env, check=True)
            print('PASS: real production migration container completed on a disposable Compose database')
        finally:
            # Only this randomly created packaging-test project, never the live project.
            subprocess.run(command + ['down', '--volumes'], env=env, check=True)
    print('PASS: production image preflight and unsafe configuration rejection')

if __name__ == '__main__':
    main()
