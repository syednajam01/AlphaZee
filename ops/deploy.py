"""Linux VM release transaction. Invoked only by trusted main-branch automation.

No shell evaluation of environment files, no database downgrades or volume removal.
Configuration is root-owned /etc/alphazee-cicd.json; see the runbook before installing.
"""
from __future__ import annotations
import argparse
import hashlib
from datetime import datetime, timezone
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from urllib.request import urlopen


class DeploymentError(RuntimeError):
    pass


def migration_args():
    # compose run has no --no-build flag. No --build plus a pre-pulled digest avoids builds.
    return ['run', '--rm', '--no-deps', '--pull', 'never', 'migrate']


def run(args, *, output=None, stdin=None):
    try:
        result = subprocess.run([str(arg) for arg in args], stdout=output or subprocess.PIPE,
                                stderr=subprocess.PIPE, stdin=stdin)
    except FileNotFoundError:
        name = Path(str(args[0])).name
        hint = ' Run sudo bash ops/install_vm_prerequisites.sh on the VM.' if name == 'az' else ''
        raise DeploymentError(f'Required executable is missing: {name}.{hint}') from None
    if result.returncode:
        # Commands can contain environment configuration; never echo arguments/stderr.
        cmd_summary = [str(a) for a in args if not str(a).startswith('-') and '/' not in str(a) and '\\' not in str(a)][:3]
        cmd_name = ' '.join(cmd_summary) or Path(str(args[0])).name
        raise DeploymentError(f'External command failed ({cmd_name}, exit {result.returncode})')
    return (result.stdout or b'').decode().strip() if output is None else ''


def read_json(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, data):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def validate_manifest(data):
    if not re.fullmatch('[0-9a-f]{40}', data.get('sha', '')):
        raise DeploymentError('Invalid release SHA')
    if not isinstance(data.get('sequence'), int) or data['sequence'] < 1:
        raise DeploymentError('Invalid workflow sequence')
    for name in ('api', 'web'):
        if not re.fullmatch(r'ghcr\.io/syednajam01/alphazee-' + name + r'@sha256:[a-f0-9]{64}', data.get(name, '')):
            raise DeploymentError('Only expected digest-pinned images may be deployed')
    approved = data.get('backward_compatible_heads', [])
    if not isinstance(approved, list) or any(not re.fullmatch('[a-f0-9]{12,40}', head) for head in approved):
        raise DeploymentError('Invalid migration compatibility policy')


def validate_config(config):
    if config.get('project') != 'alphazee-prod' or config.get('domain') != 'alphazee.tech':
        raise DeploymentError('Production project/domain must match the inventoried installation')
    for field in ('deployment_dir', 'env_file', 'state_dir', 'restore_proof'):
        if not PurePosixPath(config[field]).is_absolute():
            raise DeploymentError('Host paths must be absolute')
    if Path(config['state_dir']).resolve() == Path(config['deployment_dir']).resolve():
        raise DeploymentError('Release state must be separate from the live checkout')
    if config['state_dir'] != '/var/lib/alphazee-cicd':
        raise DeploymentError('Run Command transport requires /var/lib/alphazee-cicd')
    if set(config['volumes']) != {'pgdata', 'catalog_media', 'caddy_data', 'caddy_config'}:
        raise DeploymentError('All four existing volume identities must be specified')
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) or 'REPLACE' in name for name in config['volumes'].values()):
        raise DeploymentError('Inspect and set existing volume names before deployment')
    if not isinstance(config.get('expected_checkout_enabled'), bool):
        raise DeploymentError('Record the existing checkout setting')
    if not config.get('compose_files') or any(not PurePosixPath(path).is_absolute() for path in config['compose_files']):
        raise DeploymentError('Existing Compose files must be explicitly inventoried')
    if not re.fullmatch('[a-z0-9]{3,24}', config.get('backup_storage_account', '')):
        raise DeploymentError('Configure the private Azure backup storage account')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', config.get('backup_container', '')):
        raise DeploymentError('Invalid backup container')
    if not config.get('product_slug') or 'REPLACE' in config['product_slug']:
        raise DeploymentError('Set an active product slug for live read-only checks')


def rollback_allowed(current_head, target_head, compatible):
    return current_head == target_head or current_head in compatible


def recent_restore_proof(path):
    try:
        info = Path(path).stat()
    except FileNotFoundError:
        raise DeploymentError(f'Restore proof is missing: {path}. Complete a real isolated DB/media restore with ops/verify_restore.py; do not fabricate proof.') from None
    if os.name == 'posix' and os.geteuid() == 0 and (info.st_uid != 0 or info.st_mode & 0o077):
        raise DeploymentError('Restore proof must be root-owned mode 600')
    try:
        proof = read_json(path)
        date = datetime.fromisoformat(proof['verified_at'].replace('Z', '+00:00'))
        if date.tzinfo is None or proof.get('restored_database_and_media') is not True or not isinstance(proof.get('backup_reference'), str) or not proof['backup_reference'].strip():
            raise ValueError('Invalid proof fields')
    except (ValueError, KeyError, TypeError, AttributeError):
        raise DeploymentError('Restore proof is malformed; generate it with a successful ops/verify_restore.py run.') from None
    age = (datetime.now(timezone.utc) - date).total_seconds()
    if not proof.get('restored_database_and_media') or not proof.get('backup_reference') or not 0 <= age <= 30 * 86400:
        raise DeploymentError('A demonstrated DB/media restore within 30 days is required')


class Deployer:
    def __init__(self, config):
        self.config = config
        self.state = Path(config['state_dir'])
        self.environment = Path(config['env_file'])

    def check_prerequisites(self, require_proof=True):
        issues = []
        for name in ('docker', 'az', 'tar', 'du'):
            if not shutil.which(name):
                issues.append(f'missing executable: {name}')
        for path in [self.environment, *self.config['compose_files']]:
            if not Path(path).is_file():
                issues.append(f'missing host configuration file: {path}')
        if require_proof:
            try:
                recent_restore_proof(self.config['restore_proof'])
            except DeploymentError as error:
                issues.append(str(error))
        if issues:
            raise DeploymentError('VM prerequisites incomplete: ' + '; '.join(issues))

    def compose(self, files, *args, env_file=None, **kwargs):
        command = ['docker', 'compose', '--project-name', self.config['project'], '--env-file', env_file or self.environment,
                   '--project-directory', self.config['deployment_dir']]
        for path in files:
            command += ['-f', path]
        return run(command + list(args), **kwargs)

    def live(self, *args, **kwargs):
        return self.compose(self.config['compose_files'], *args, **kwargs)

    def database_head(self):
        head = self.live('exec', '-T', 'db', 'sh', '-c',
                         'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version_num FROM alembic_version"')
        if not re.fullmatch('[a-f0-9]{12,40}', head):
            raise DeploymentError('Expected exactly one current schema revision')
        return head

    def inventory(self):
        for volume in self.config['volumes'].values():
            run(['docker', 'volume', 'inspect', volume])  # Refuse to create substitute volumes.
        for service, expected in (('db', [('pgdata', '/var/lib/postgresql/data')]),
                                  ('api', [('catalog_media', '/var/lib/alphazee/catalog-media')]),
                                  ('web', [('caddy_data', '/data'), ('caddy_config', '/config')])):
            container = self.live('ps', '-q', service)
            if not container:
                try:
                    self.live('start', service)
                except DeploymentError:
                    self.live('up', '-d', '--no-deps', service)
                container = self.live('ps', '-q', service)
            if not container or '\n' in container:
                raise DeploymentError('Expected one running container for each production service')
            actual = json.loads(run(['docker', 'inspect', container]))[0]
            mounts = {(item.get('Name'), item['Destination']) for item in actual['Mounts'] if item['Type'] == 'volume'}
            if not {(self.config['volumes'][key], target) for key, target in expected} <= mounts:
                raise DeploymentError('Existing container mounts do not match the recorded volume identities')

    def override(self, directory, api, web):
        path = Path(directory) / 'images.json'
        atomic_json(path, {'services': {'api': {'image': api}, 'migrate': {'image': api}, 'web': {'image': web}},
                           'volumes': {key: {'name': value, 'external': True} for key, value in self.config['volumes'].items()}})
        return path

    def snapshot_environment(self, directory):
        path = Path(directory) / '.env.snapshot'
        shutil.copyfile(self.environment, path)
        path.chmod(0o600)
        return {'env_file': str(path), 'env_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def can_restore(self, current_head, target, compatible):
        # Do not silently reopen checkout or restore old bank credentials after a deliberate config change.
        return (hashlib.sha256(self.environment.read_bytes()).hexdigest() == target.get('env_sha256')
                and rollback_allowed(current_head, target['head'], compatible))

    def bootstrap(self, head):
        current_file = self.state / 'current.json'
        if current_file.exists():
            return read_json(current_file)
        directory = self.state / 'releases' / 'bootstrap'
        directory.mkdir(parents=True, exist_ok=True)
        files = []
        for index, original in enumerate(self.config['compose_files']):
            target = directory / f'compose-{index}.yml'
            shutil.copyfile(original, target)
            files.append(str(target))
        def image(service):
            container = self.live('ps', '-q', service)
            return run(['docker', 'inspect', '--format', '{{.Image}}', container])
        files.append(str(self.override(directory, image('api'), image('web'))))
        baseline = {'sha': 'bootstrap', 'sequence': 0, 'head': head, 'files': files, 'backward_compatible_heads': [],
                    **self.snapshot_environment(directory)}
        atomic_json(current_file, baseline)
        return baseline

    def backup(self, sha):
        run(['az', 'login', '--identity', '--output', 'none'])
        public_access = run(['az', 'storage', 'container', 'show', '--auth-mode', 'login',
                             '--account-name', self.config['backup_storage_account'],
                             '--name', self.config['backup_container'], '--query', 'properties.publicAccess', '-o', 'tsv'])
        if public_access.lower() not in {'', 'none', 'off'}:
            raise DeploymentError('Backup container must be private')
        mount = run(['docker', 'volume', 'inspect', '--format', '{{.Mountpoint}}', self.config['volumes']['catalog_media']])
        media_bytes = int(run(['du', '-sb', mount]).split()[0])
        database_bytes = int(self.live('exec', '-T', 'db', 'sh', '-c',
                             'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT pg_database_size(current_database())"'))
        required = self.config.get('minimum_free_bytes', 3 * 1024**3) + media_bytes + database_bytes * 2
        if shutil.disk_usage(self.state).free < required:
            raise DeploymentError('Not enough free disk to capture a backup without endangering the running database')
        directory = self.state / 'backups' / (sha + '-' + str(time.time_ns()))
        directory.mkdir(parents=True, mode=0o700)
        # These are the only app writers in the inventoried architecture. Other jobs must be quiesced separately.
        self.live('stop', '--timeout', '60', 'api')
        try:
            dump = directory / 'database.dump'
            with dump.open('wb') as stream:
                self.live('exec', '-T', 'db', 'sh', '-c',
                          'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc', output=stream)
            with dump.open('rb') as stream:
                self.live('exec', '-T', 'db', 'pg_restore', '--list', stdin=stream)
            # tar is system-provided on the Linux VM; originals are only read.
            run(['tar', '-C', mount, '-czf', directory / 'media.tar.gz', '.'])
        finally:
            try:
                self.live('start', 'api')
            except DeploymentError:
                self.live('up', '-d', '--no-deps', 'api')
        # Resume customer traffic before uploading the captured, consistent snapshot.
        account = self.config['backup_storage_account']
        container = self.config['backup_container']
        prefix = directory.name
        for name in ('database.dump', 'media.tar.gz'):
            path = directory / name
            remote = prefix + '/' + name
            run(['az', 'storage', 'blob', 'upload', '--auth-mode', 'login', '--account-name', account,
                 '--container-name', container, '--name', remote, '--file', path, '--overwrite', 'false', '--validate-content', '--output', 'none'])
            actual = run(['az', 'storage', 'blob', 'show', '--auth-mode', 'login', '--account-name', account,
                          '--container-name', container, '--name', remote, '--query', 'properties.contentLength', '-o', 'tsv'])
            if int(actual) != path.stat().st_size:
                raise DeploymentError('Off-host backup size verification failed')
        reference = f'{account}/{container}/{prefix}'
        receipt = directory / 'receipt.json'
        atomic_json(receipt, {'sha': sha, 'reference': reference, 'schema_head': self.database_head(),
                    'database_bytes': database_bytes, 'media_bytes': media_bytes,
                    'created_at': datetime.now(timezone.utc).isoformat(), 'database_and_media_quiesced': True})
        # Completion manifest is uploaded last. A partial upload never counts as a matched recovery set.
        run(['az', 'storage', 'blob', 'upload', '--auth-mode', 'login', '--account-name', account,
             '--container-name', container, '--name', prefix + '/receipt.json', '--file', receipt,
             '--overwrite', 'false', '--validate-content', '--output', 'none'])
        # Remove only the two newly generated temporary copies, after verified off-host upload.
        # Persistent DB/media volumes and the off-host recovery set are never deleted here.
        for name in ('database.dump', 'media.tar.gz'):
            (directory / name).unlink()
        return reference

    def smoke(self, release):
        from urllib.parse import quote
        base = 'https://' + self.config['domain']
        def fetch(path):
            with urlopen(base + path, timeout=15) as response:
                return response.read()
        last = None
        for attempt in range(12):
            try:
                ready = json.loads(fetch('/api/v1/ready'))
                if ready.get('status') != 'ready' or ready.get('database') != 'connected':
                    raise DeploymentError('Database readiness failed')
                capabilities = json.loads(fetch('/api/v1/storefront/capabilities'))
                if capabilities.get('test_mode') is not False or capabilities.get('checkout_enabled') != self.config['expected_checkout_enabled']:
                    raise DeploymentError('Production checkout settings changed unexpectedly')
                for path in ('/', '/admin', '/vendor', '/products/' + quote(self.config['product_slug'], safe='')):
                    html = fetch(path).decode()
                    if 'id="app"' not in html or 'SAMPLE CHECKOUT LAB' in html:
                        raise DeploymentError('Unexpected production HTML')
                # Confirm catalog contract too: SPA fallback HTTP 200 is insufficient.
                product = json.loads(fetch('/api/v1/products/' + quote(self.config['product_slug'], safe='')))
                if not product.get('id'):
                    raise DeploymentError('Configured product no longer resolves')
                if release['sha'] != 'bootstrap':
                    for path in ('/release.json', '/api/v1/release'):
                        if json.loads(fetch(path)).get('sha') != release['sha']:
                            raise DeploymentError('Wrong deployed release')
                return
            except Exception as error:
                last = error
                time.sleep(5)
        raise DeploymentError('HTTPS smoke checks failed; inspect VM privately') from last

    def activate(self, release):
        for service in ('api', 'web'):
            self.compose(release['files'], 'up', '-d', '--no-deps', '--no-build', '--force-recreate', '--wait', '--wait-timeout', '120', service,
                         env_file=release['env_file'])
        self.smoke(release)

    def rollback(self):
        current = read_json(self.state / 'current.json')
        previous = read_json(self.state / 'previous.json')
        if not self.can_restore(self.database_head(), previous, current.get('backward_compatible_heads', [])):
            raise DeploymentError('Schema compatibility or changed private configuration prevents rollback; use a reviewed forward fix')
        self.activate(previous)
        atomic_json(self.state / 'previous.json', current)
        atomic_json(self.state / 'current.json', dict(previous, sequence=max(current['sequence'], previous['sequence'])))

    def deploy(self, directory):
        directory = Path(directory).resolve()
        manifest = read_json(directory / 'manifest.json')
        validate_manifest(manifest)
        self.check_prerequisites()
        self.inventory()
        head = self.database_head()
        previous = self.bootstrap(head)
        if manifest['sequence'] <= previous['sequence']:
            raise DeploymentError('Stale or already applied workflow sequence')
        if shutil.disk_usage(self.state).free < self.config.get('minimum_free_bytes', 3 * 1024**3):
            raise DeploymentError('Insufficient disk space before image pull/backup')
        recent_restore_proof(self.config['restore_proof'])
        for image in (manifest['api'], manifest['web']):
            run(['docker', 'pull', image])
        target_head = run(['docker', 'run', '--rm', '--entrypoint', 'python', manifest['api'], '-c',
                          'from alembic.config import Config; from alembic.script import ScriptDirectory; print(ScriptDirectory.from_config(Config("alembic.ini")).get_current_head())'])
        if not re.fullmatch('[a-f0-9]{12,40}', target_head):
            raise DeploymentError('Candidate must have one migration head')
        if head != target_head and target_head not in manifest['backward_compatible_heads']:
            raise DeploymentError('New migration requires an explicit reviewed backward-compatible head in ops/migration-policy.json')
        files = [str(directory / 'compose.prod.yml'), str(self.override(directory, manifest['api'], manifest['web']))]
        environment = self.snapshot_environment(directory)
        self.compose(files, 'config', '--quiet', env_file=environment['env_file'])
        backup = self.backup(manifest['sha'])
        # run always creates a new container; never reuse a stale completed migrate job.
        self.compose(files, *migration_args(), env_file=environment['env_file'])
        release = dict(manifest, head=target_head, files=files, backup=backup, **environment)
        try:
            self.activate(release)
        except DeploymentError:
            if self.can_restore(self.database_head(), previous, manifest['backward_compatible_heads']):
                self.activate(previous)
            raise
        atomic_json(self.state / 'previous.json', previous)
        atomic_json(self.state / 'current.json', release)
        atomic_json(directory / 'success.json', release)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['deploy', 'rollback', 'inventory', 'backup', 'preflight'])
    parser.add_argument('--release', type=Path)
    parser.add_argument('--config', type=Path, default=Path('/etc/alphazee-cicd.json'))
    args = parser.parse_args()
    if os.name != 'posix' or os.geteuid() != 0:
        raise DeploymentError('Deployment requires the configured Linux VM root context')
    info = args.config.stat()
    if info.st_uid != 0 or info.st_mode & 0o077:
        raise DeploymentError('Host config must be root-owned mode 600')
    config = read_json(args.config)
    validate_config(config)
    if args.operation == 'deploy' and platform.machine().lower() not in {'x86_64', 'amd64'}:
        raise DeploymentError('This release builder supports x86-64 VMs; configure a tested ARM runner before deploying to ARM')
    state = Path(config['state_dir'])
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    if state.resolve() != state or state.stat().st_uid != 0 or state.stat().st_mode & 0o077:
        raise DeploymentError('Release state must be a root-owned private directory without symlinks')
    import fcntl
    with (state / 'deploy.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        deployer = Deployer(config)
        if args.operation == 'preflight':
            deployer.check_prerequisites()
            deployer.inventory()
            deployer.database_head()
            run(['az', 'login', '--identity', '--output', 'none'])
            access = run(['az', 'storage', 'container', 'show', '--auth-mode', 'login', '--account-name', config['backup_storage_account'], '--name', config['backup_container'], '--query', 'properties.publicAccess', '-o', 'tsv'])
            if access.lower() not in {'', 'none', 'off'}:
                raise DeploymentError('Backup container must be private')
            print('PASS: VM prerequisites, restore proof, storage access, inventory and schema')
        elif args.operation == 'inventory':
            deployer.inventory()
            print('PASS: existing production volume identities verified')
        elif args.operation == 'backup':
            deployer.check_prerequisites(require_proof=False)
            deployer.inventory()
            print('Backup saved privately: ' + deployer.backup('manual'))
        elif args.operation == 'deploy':
            if args.release is None or not args.release.resolve().is_relative_to(state / 'releases'):
                raise DeploymentError('Release must be inside the private release directory')
            deployer.deploy(args.release)
            print('ALPHAZEE_DEPLOY_OK:' + read_json(args.release / 'manifest.json')['sha'])
        else:
            deployer.rollback()
            print('ALPHAZEE_ROLLBACK_OK')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No subprocess stderr, URL credentials or private environment values in CI logs.
        message = str(error) if isinstance(error, DeploymentError) else f'Unexpected {type(error).__name__}; inspect the VM privately'
        print('Deployment stopped: ' + message, file=sys.stderr)
        print('ALPHAZEE_DEPLOY_ERROR:' + json.dumps({'message': message}), file=sys.stderr)
        sys.exit(1)
