"""Prove an actual private Blob backup restores, without touching live volumes.

Root on the production VM. Temporary PostgreSQL has no network/ports and uses bounded tmpfs.
Proof is written only after pg_restore, revision, and every ready media checksum pass.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import sys
import tarfile
import tempfile
import time

from deploy import DeploymentError, atomic_json, read_json, run, validate_config


def parse_reference(reference, config):
    parts = reference.split('/', 2)
    if len(parts) != 3 or parts[:2] != [config['backup_storage_account'], config['backup_container']]:
        raise DeploymentError('Backup reference must belong to the configured private account/container')
    prefix = parts[2]
    if not re.fullmatch(r'[A-Za-z0-9_.\-/]+', prefix) or any(part in {'', '.', '..'} for part in prefix.split('/')):
        raise DeploymentError('Invalid backup reference prefix')
    return prefix


def extract_media(archive, destination):
    with tarfile.open(archive, 'r:gz') as source:
        members = source.getmembers()
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or not (member.isfile() or member.isdir()):
                raise DeploymentError('Media archive contains an unsafe path or link')
        if sum(member.size for member in members) + 1024**3 > shutil.disk_usage(destination).free:
            raise DeploymentError('Insufficient space for isolated media restore')
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as incoming, target.open('wb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing)


def verify_media(assets, directory):
    for asset in assets:
        key = asset['storage_key']
        if not re.fullmatch(r'[a-f0-9]{32}\.[a-z0-9]+', key):
            raise DeploymentError('Unexpected ready media storage key in restored database')
        path = directory / 'objects' / key
        if not path.is_file() or path.stat().st_size != asset['byte_size']:
            raise DeploymentError('Restored media is missing or its size differs from database metadata')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != asset['checksum']:
            raise DeploymentError('Restored media checksum differs from database metadata')
    return len(assets)


def verify(config, reference, write_proof=False):
    prefix = parse_reference(reference, config)
    run(['az', 'login', '--identity', '--output', 'none'])
    base = ['--auth-mode', 'login', '--account-name', config['backup_storage_account'], '--container-name', config['backup_container']]
    public = run(['az', 'storage', 'container', 'show', '--auth-mode', 'login', '--account-name', config['backup_storage_account'], '--name', config['backup_container'], '--query', 'properties.publicAccess', '-o', 'tsv'])
    if public.lower() not in {'', 'none', 'off'}:
        raise DeploymentError('Backup container is not private')
    state = Path(config['state_dir'])
    workspace = state / 'restore-tests'
    workspace.mkdir(mode=0o700, exist_ok=True)
    container = 'alphazee-restore-' + secrets.token_hex(8)
    created = False
    with tempfile.TemporaryDirectory(prefix='check-', dir=workspace) as temporary:
        directory = Path(temporary)
        def download(name):
            run(['az', 'storage', 'blob', 'download', *base, '--name', prefix + '/' + name, '--file', directory / name, '--output', 'none'])
        download('receipt.json')  # Completion receipt must exist before either data file is trusted.
        receipt = read_json(directory / 'receipt.json')
        if receipt.get('reference') != reference or receipt.get('database_and_media_quiesced') is not True:
            raise DeploymentError('Completion receipt does not attest to a matched quiesced backup')
        # Use a bounded scratch DB to avoid filling the live database disk or exhausting VM RAM.
        if not isinstance(receipt.get('database_bytes'), int) or not 0 < receipt['database_bytes'] <= 128 * 1024**2:
            raise DeploymentError('This on-VM verifier supports source databases up to 128 MiB; use a separately sized restore host for larger/older backups')
        available_kib = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
        if available_kib < 1024 * 1024:
            raise DeploymentError('At least 1 GiB available RAM is required for this isolated restore')
        if shutil.disk_usage(workspace).free < receipt.get('media_bytes', 0) * 2 + 2 * 1024**3:
            raise DeploymentError('Insufficient free space for backup downloads and media extraction')
        download('database.dump')
        download('media.tar.gz')
        media = directory / 'media'
        media.mkdir()
        extract_media(directory / 'media.tar.gz', media)
        # Reuse exactly the live PostgreSQL image ID, but never its network or storage.
        db = run(['docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=' + config['project'], '--filter', 'label=com.docker.compose.service=db'])
        if not re.fullmatch('[a-f0-9]{12,64}', db):
            raise DeploymentError('Expected one inventoried live DB container')
        image = run(['docker', 'inspect', '--format', '{{.Image}}', db])
        try:
            run(['docker', 'run', '-d', '--name', container, '--network', 'none', '--memory', '512m', '--cpus', '0.5',
                 '--tmpfs', '/var/lib/postgresql/data:rw,size=256m', '-e', 'POSTGRES_USER=restore',
                 '-e', 'POSTGRES_DB=restore_test', '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', image])
            created = True
            for attempt in range(30):
                try:
                    # Ignore the entrypoint's temporary initialization server; final postgres is PID 1.
                    run(['docker', 'exec', container, 'sh', '-c',
                         'test "$(head -n1 "$PGDATA/postmaster.pid")" = 1 && pg_isready -U restore -d restore_test'])
                    break
                except DeploymentError:
                    if attempt == 29:
                        raise
                    time.sleep(1)
            with (directory / 'database.dump').open('rb') as stream:
                run(['docker', 'exec', '-i', container, 'pg_restore', '--exit-on-error', '--no-owner', '--no-privileges', '-U', 'restore', '-d', 'restore_test'], stdin=stream)
            def query(sql):
                return run(['docker', 'exec', container, 'psql', '-v', 'ON_ERROR_STOP=1', '-U', 'restore', '-d', 'restore_test', '-tAc', sql])
            head = query('SELECT version_num FROM alembic_version')
            if head != receipt['schema_head']:
                raise DeploymentError('Restored migration revision does not match backup receipt')
            tables = int(query("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"))
            if tables < 1:
                raise DeploymentError('Database restored no application tables')
            assets = json.loads(query("SELECT COALESCE(json_agg(json_build_object('storage_key',storage_key,'byte_size',byte_size,'checksum',checksum)), '[]'::json) FROM media_assets WHERE state='ready'"))
            checked = verify_media(assets, media)
            # Only non-sensitive aggregate evidence is returned and persisted as proof.
            proof = {'verified_at': datetime.now(timezone.utc).isoformat(), 'restored_database_and_media': True,
                     'backup_reference': reference, 'schema_head': head, 'restored_tables': tables,
                     'ready_media_verified': checked, 'isolated_network': True}
        finally:
            if created:
                run(['docker', 'rm', '-f', container])  # Exact generated scratch name only; no production volumes.
        if write_proof:
            atomic_json(config['restore_proof'], proof)
            Path(config['restore_proof']).chmod(0o600)
        return proof


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=Path('/etc/alphazee-cicd.json'))
    parser.add_argument('--backup-reference', required=True)
    parser.add_argument('--write-proof', action='store_true')
    args = parser.parse_args()
    if os.name != 'posix' or os.geteuid() != 0:
        raise DeploymentError('Run on the configured Linux VM as root')
    info = args.config.stat()
    if info.st_uid != 0 or info.st_mode & 0o077:
        raise DeploymentError('Host configuration must be root-owned mode 600')
    config = read_json(args.config)
    validate_config(config)
    print(json.dumps(verify(config, args.backup_reference, args.write_proof), indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error) if isinstance(error, DeploymentError) else f'Restore verification failed ({type(error).__name__}); proof was not written', file=sys.stderr)
        sys.exit(1)
