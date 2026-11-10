"""One-off, guarded image-cache maintenance; never removes containers or volumes."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

TARGET = '1f92c72a0b4ccc085f02c9f19ebdba5c01306234'
EXPECTED = 'a1b260c870f1468ee5e474ad7a5108e4795a68da'
REPO = re.compile(r'^ghcr\.io/syednajam01/alphazee-(?:api|web)@sha256:[a-f0-9]{64}$')

def removal_plan(images, protected, now):
    result = set()
    for item in images:
        if item['Id'] in protected:
            continue
        digests = item.get('RepoDigests') or []
        tags = item.get('RepoTags') or []
        if not digests or any(not REPO.fullmatch(ref) for ref in digests):
            continue
        if any(not tag.startswith(('ghcr.io/syednajam01/alphazee-api:', 'ghcr.io/syednajam01/alphazee-web:')) for tag in tags):
            continue
        try:
            age = (now - datetime.fromisoformat(item['Created'].replace('Z', '+00:00'))).total_seconds()
        except (ValueError, TypeError, KeyError):
            continue
        if age >= 86400:
            result.update(digests)
    return sorted(result)

def run(*args):
    result = subprocess.run(list(map(str, args)), text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'{args[0]} command failed; no force-removal fallback is permitted')
    return result.stdout.strip()

def guest():
    import fcntl
    import os
    import shutil
    import time
    state = Path('/var/lib/alphazee-cicd')
    assert os.geteuid() == 0 and state.resolve() == state and state.stat().st_uid == 0
    with (state / 'deploy.lock').open('r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = json.loads((state / 'current.json').read_text())
        previous = json.loads((state / 'previous.json').read_text())
        target = json.loads((state / 'releases' / TARGET / 'manifest.json').read_text())
        assert current['sha'] == EXPECTED and target['sha'] == TARGET, 'Release changed; inspect again'
        refs = {record[key] for record in [current, previous, target] for key in ['api', 'web']}
        protected = {json.loads(run('docker', 'image', 'inspect', ref))[0]['Id'] for ref in refs}
        containers = run('docker', 'ps', '-aq').splitlines()
        running_before = run('docker', 'ps', '--no-trunc', '--format', '{{.ID}} {{.Image}}')
        assert len(containers) >= 3 and len(running_before.splitlines()) >= 3
        protected.update(run('docker', 'inspect', '--format', '{{.Image}}', *containers).splitlines())
        volumes_before = run('docker', 'volume', 'ls', '--quiet')
        identifiers = sorted(set(run('docker', 'image', 'ls', '-aq', '--no-trunc').splitlines()))
        assert identifiers
        images = json.loads(run('docker', 'image', 'inspect', *identifiers))
        plan = removal_plan(images, protected, datetime.now(timezone.utc))
        assert len(plan) <= 100
        before = shutil.disk_usage(state).free
        for ref in plan:
            # Exact, reviewed repository digests only. Docker itself refuses
            # references in use; never force, prune volumes or remove containers.
            run('docker', 'image', 'rm', ref)
        for ref in refs:
            assert json.loads(run('docker', 'image', 'inspect', ref))[0]['Id'] in protected
        assert run('docker', 'ps', '--no-trunc', '--format', '{{.ID}} {{.Image}}') == running_before
        assert run('docker', 'volume', 'ls', '--quiet') == volumes_before
        time.sleep(5)
        after = shutil.disk_usage(state).free
        print(json.dumps({'removed_old_unreferenced_digests': len(plan), 'protected_image_ids': len(protected),
            'free_gib_before': round(before / 1024**3, 2), 'free_gib_after': round(after / 1024**3, 2),
            'containers_unchanged': True, 'volumes_unchanged': True, 'current_previous_target_preserved': True}))

def dispatch():
    code = Path(__file__).read_text()
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / 'reclaim.sh'
        script.write_text("set -eu\npython3 - --guest <<'ALPHAZEE_MAINTENANCE'\n" + code + '\nALPHAZEE_MAINTENANCE\n')
        report = json.loads(run('az', 'vm', 'run-command', 'invoke', '--resource-group', 'alphazee-staging',
            '--name', 'alphazee-vm', '--command-id', 'RunShellScript', '--scripts', '@' + str(script), '--output', 'json'))
        messages = '\n'.join(item.get('message', '') for item in report.get('value', []))
        print(messages)
        assert '"current_previous_target_preserved": true' in messages, 'Guest maintenance did not verify completion'

if __name__ == '__main__':
    guest() if sys.argv[1:] == ['--guest'] else dispatch()
