"""Read-only production inventory; run from the VM deployment checkout, not CI."""
import argparse
import json
import platform
from pathlib import Path
import subprocess


def output(args):
    return subprocess.check_output(args, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--compose-file', action='append', required=True)
    parser.add_argument('--project', default='alphazee-prod')
    args = parser.parse_args()
    base = ['docker', 'compose', '--project-name', args.project, '--env-file', args.env_file]
    for path in args.compose_file:
        base += ['-f', path]
    containers = {}
    for service in ('db', 'api', 'web'):
        identifier = output(base + ['ps', '-q', service])
        data = json.loads(output(['docker', 'inspect', identifier]))[0]
        containers[service] = {'image_id': data['Image'], 'image_reference': data['Config']['Image'],
            'mounts': [{'name': mount.get('Name'), 'target': mount['Destination'], 'type': mount['Type']}
                       for mount in data['Mounts']], 'running': data['State']['Running']}
    print(json.dumps({'architecture': platform.machine(), 'project': args.project, 'deployment_dir': str(Path.cwd()),
                      'compose_version': output(['docker', 'compose', 'version', '--short']), 'containers': containers}, indent=2))

if __name__ == '__main__':
    main()
