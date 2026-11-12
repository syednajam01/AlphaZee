"""GitHub runner: transfer a non-secret release payload using Azure Run Command."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def latest_main():
    request = Request('https://api.github.com/repos/syednajam01/AlphaZee/commits/main', headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    with urlopen(request, timeout=20) as response:
        return json.load(response)['sha']


def payload():
    sha = os.environ['GITHUB_SHA']
    if not re.fullmatch('[a-f0-9]{40}', sha):
        raise RuntimeError('Expected a full commit SHA')
    from deploy import validate_manifest
    manifest = {'sha': sha, 'sequence': int(os.environ['GITHUB_RUN_NUMBER']),
                'api': os.environ['API_IMAGE'], 'web': os.environ['WEB_IMAGE'],
                **json.loads((ROOT / 'ops/migration-policy.json').read_text())}
    validate_manifest(manifest)
    return {'sha': sha, 'files': {
        'deploy.py': (ROOT / 'ops/deploy.py').read_text(),
        'compose.prod.yml': (ROOT / 'compose.prod.yml').read_text(),
        'manifest.json': json.dumps(manifest)}}


def script(operation, package=None):
    if operation == 'rollback':
        return "set -eu\npython3 /var/lib/alphazee-cicd/runner.py rollback\n"
    encoded = base64.b64encode(json.dumps(package).encode()).decode()
    # All paths are fixed or validated SHA hex. The payload has no secrets, shell text or user fields to interpolate.
    return f'''set -eu
umask 077
python3 - <<'ALPHAZEE_PY'
import base64,json,pathlib,re,subprocess
data=json.loads(base64.b64decode('{encoded}'))
assert re.fullmatch('[a-f0-9]{{40}}',data['sha'])
assert set(data['files']) == {{'deploy.py','compose.prod.yml','manifest.json'}}
state=pathlib.Path('/var/lib/alphazee-cicd')
state.mkdir(exist_ok=True,mode=0o700)
assert state.resolve()==state and state.stat().st_uid==0 and not state.stat().st_mode & 0o077
directory=state/'releases'/data['sha']
assert not directory.is_symlink()
directory.mkdir(parents=True,exist_ok=True,mode=0o700)
for name,contents in data['files'].items():
    (directory/name).write_text(contents)
subprocess.run(['python3',str(directory/'deploy.py'),'deploy','--release',str(directory)],check=True)
# Rollback bootstrap is updated only after an actually successful deployment.
runner=pathlib.Path('/var/lib/alphazee-cicd/runner.py')
runner.write_text(data['files']['deploy.py'])
print('ALPHAZEE_REMOTE_OK:'+data['sha'])
ALPHAZEE_PY
'''


def main():
    operation = sys.argv[1]
    if operation not in {'deploy', 'rollback'}:
        raise RuntimeError('Unknown operation')
    if os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise RuntimeError('Only main may access production')
    if operation == 'deploy' and latest_main() != os.environ['GITHUB_SHA']:
        print('Superseded release skipped: main has moved forward')
        return
    group = os.environ['AZURE_RESOURCE_GROUP']
    vm = os.environ['AZURE_VM_NAME']
    if (group, vm) != ('alphazee-staging', 'alphazee-vm'):
        raise RuntimeError('Unexpected Azure deployment target')
    package = payload() if operation == 'deploy' else None
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'command.sh'
        path.write_text(script(operation, package))
        result = subprocess.run(['az', 'vm', 'run-command', 'invoke', '--resource-group', group, '--name', vm,
                                 '--command-id', 'RunShellScript', '--scripts', '@' + str(path), '--output', 'json'],
                                text=True, capture_output=True)
        marker = 'ALPHAZEE_REMOTE_OK:' + os.environ['GITHUB_SHA'] if operation == 'deploy' else 'ALPHAZEE_ROLLBACK_OK'
        if result.returncode:
            summary = os.environ.get('GITHUB_STEP_SUMMARY')
            if summary:
                try:
                    with open(summary, 'a', encoding='utf-8') as stream:
                        clean_err = re.sub(r'[\r\n]+', ' ', result.stderr)[:500]
                        stream.write(f'Azure command invocation failed (code {result.returncode}): {clean_err}\n')
                except Exception:
                    pass
            clean_msg = re.sub(r'[\r\n]+', ' ', result.stderr)[:300] if result.stderr else f'exit {result.returncode}'
            print(f'::error title=Azure Command Failed::{clean_msg}')
            raise RuntimeError('Azure command failed; inspect the workflow identity and VM agent')
        # Azure may report a successful control-plane invocation despite a failed guest script.
        messages = '\n'.join(value.get('message', '') for value in json.loads(result.stdout).get('value', []))
        if marker not in messages:
            # Only forward explicitly sanitized deployment errors; never arbitrary guest stderr.
            for match in re.finditer(r'ALPHAZEE_DEPLOY_ERROR:(\{.*?\})', messages):
                try:
                    detail = json.loads(match.group(1))['message']
                    print(f'::error title=Guest Deployment Failed::{detail}')
                    raise RuntimeError('Guest deployment failed: ' + str(detail)[:1800])
                except (ValueError, KeyError, TypeError):
                    continue
            for line in messages.splitlines():
                line = line.strip()
                if line.startswith('ALPHAZEE_DEPLOY_ERROR:'):
                    try:
                        detail = json.loads(line.split(':', 1)[1])['message']
                        print(f'::error title=Guest Deployment Failed::{detail}')
                        raise RuntimeError('Guest deployment failed: ' + str(detail)[:1800])
                    except (ValueError, KeyError, TypeError):
                        continue
            summary = os.environ.get('GITHUB_STEP_SUMMARY')
            if summary:
                try:
                    with open(summary, 'a', encoding='utf-8') as stream:
                        stream.write(f'Guest deployment messages (marker missing):\n```\n{messages[:1200]}\n```\n')
                except Exception:
                    pass
            clean_preview = re.sub(r'[\r\n]+', ' ', messages)[:300]
            print(f'::error title=Guest Missing Marker::{clean_preview}')
            raise RuntimeError('Guest deployment did not confirm success; inspect the VM privately')
        print(marker)
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as stream:
                stream.write(f'Production {operation} succeeded: `{os.environ["GITHUB_SHA"]}`\n')

if __name__ == '__main__':
    main()
