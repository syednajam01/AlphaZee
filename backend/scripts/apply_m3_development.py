"""Forward-only media rollout after disposable proof and a verified backup restore."""
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from sqlalchemy import create_engine, text
import verify_m0_baseline as baseline


def main():
    root = baseline.ROOT
    proof = json.loads((root / '.context/m3_migration_verification.json').read_text())
    if proof.get('head_revision') != 'f27b6d91c083' or proof.get('alembic_check') != 'passed':
        raise RuntimeError('Isolated M3 migration proof is required')
    baseline.main(report_name='m3_pre_migration_backup.json', phase='M3 pre-migration', restore_prefix='alphazee_m3_restore_')
    before = json.loads((root / '.context/m3_pre_migration_backup.json').read_text())
    if before['revision'] != ['e15a9c2b7046']: raise RuntimeError('Unexpected development revision')
    env = {**os.environ, 'DATABASE_URL': baseline.settings.database_url, 'APP_ENV': 'development', 'TEST_CHECKOUT_ENABLED': 'false', 'DEBUG': 'false'}
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'f27b6d91c083'], cwd=root / 'backend', env=env, check=True)
    subprocess.run([sys.executable, '-m', 'alembic', 'check'], cwd=root / 'backend', env=env, check=True)
    engine = create_engine(baseline.settings.database_url, hide_parameters=True)
    with engine.begin() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        after = baseline.fingerprint(c)
        head = list(c.scalars(text('SELECT version_num FROM alembic_version')))
    engine.dispose()
    assert head == ['f27b6d91c083']
    assert all(after[k]['rows'] == v['rows'] for k,v in before['tables'].items())
    assert all(after[k] == v for k,v in before['tables'].items() if k not in {'collections', 'alembic_version'})
    assert after['media_assets']['rows'] == 0 and after['product_media']['rows'] == 0
    assert baseline.config_hashes() == before['config_hashes']
    report = {'phase': 'M3', 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'database': 'alphazee_dev',
              'prior_revision': before['revision'], 'revision': head, 'backup': before['backup'], 'restore_database': before['restore_database'],
              'all_existing_row_counts_preserved': True, 'non_collection_row_digests_preserved': True, 'configuration_preserved': True,
              'owner_credentials_preserved': True, 'alembic_check': 'passed', 'checkout_enabled': False, 'demo_data_inserted': False}
    (root / '.context/m3_development_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
