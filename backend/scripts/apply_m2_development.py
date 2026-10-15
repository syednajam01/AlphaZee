"""Forward-only development rollout after isolated migration verification and backup."""
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
from sqlalchemy import create_engine, text
import verify_m0_baseline as baseline


def main():
    root = baseline.ROOT
    proof = json.loads((root / '.context/owner_catalog_migration_verification.json').read_text())
    if proof.get('head_revision') != 'e15a9c2b7046' or proof.get('alembic_check') != 'passed':
        raise RuntimeError('Isolated M2 migration proof is required')
    baseline.main(report_name='m2_pre_migration_backup.json', phase='M2 pre-migration', restore_prefix='alphazee_m2_restore_')
    before = json.loads((root / '.context/m2_pre_migration_backup.json').read_text())
    if before['revision'] != ['c94e31f7d562']:
        raise RuntimeError('Unexpected development revision; inspect instead of applying blindly')
    env = {**os.environ, 'DATABASE_URL': baseline.settings.database_url, 'APP_ENV': 'development',
           'TEST_CHECKOUT_ENABLED': 'false', 'DEBUG': 'false'}
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'e15a9c2b7046'],
                   cwd=root / 'backend', env=env, check=True)
    subprocess.run([sys.executable, '-m', 'alembic', 'check'], cwd=root / 'backend', env=env, check=True)
    engine = create_engine(baseline.settings.database_url, hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        after = baseline.fingerprint(connection)
        head = list(connection.scalars(text('SELECT version_num FROM alembic_version')))
    engine.dispose()
    assert head == ['e15a9c2b7046']
    assert {key: value['rows'] for key, value in after.items()} == {key: value['rows'] for key, value in before['tables'].items()}
    assert all(after[key] == value for key, value in before['tables'].items() if key not in {'products', 'variants', 'collections', 'alembic_version'})
    assert baseline.config_hashes() == before['config_hashes']
    report = {'phase': 'M2', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'database': 'alphazee_dev', 'prior_revision': before['revision'], 'revision': head,
        'backup': before['backup'], 'restore_database': before['restore_database'],
        'row_counts_preserved': True, 'non_catalog_row_digests_preserved': True, 'configuration_preserved': True,
        'alembic_check': 'passed', 'checkout_enabled': False, 'demo_data_inserted': False}
    (root / '.context/m2_development_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
