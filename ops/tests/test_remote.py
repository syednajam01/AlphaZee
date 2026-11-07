import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

OPS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(OPS))
import remote
SHA = 'a' * 40


class AzureTransport(unittest.TestCase):
    def test_release_transport_is_encoded_and_fixed_to_private_directory(self):
        package = {'sha':SHA, 'files':{'deploy.py': 'print("arbitrary quoted text: \" $()")',
                                     'compose.prod.yml':'services: {}', 'manifest.json':'{}'}}
        result = remote.script('deploy', package)
        self.assertNotIn(package['files']['deploy.py'], result)
        self.assertIn("pathlib.Path('/var/lib/alphazee-cicd')", result)
        self.assertIn("directory=state/'releases'/data['sha']", result)
        self.assertIn("re.fullmatch('[a-f0-9]{40}'", result)
        self.assertIn('ALPHAZEE_REMOTE_OK:', result)
        compile(result.split("<<'ALPHAZEE_PY'\n")[1].split('\nALPHAZEE_PY')[0], '<guest-script>', 'exec')

    def test_control_plane_success_without_guest_marker_is_failure(self):
        environment = {'GITHUB_REF':'refs/heads/main', 'GITHUB_SHA':SHA,
                       'AZURE_RESOURCE_GROUP':'alphazee-staging','AZURE_VM_NAME':'alphazee-vm'}
        with patch.dict(os.environ, environment), patch.object(sys, 'argv', ['remote.py','rollback']), \
             patch.object(remote.subprocess, 'run') as command:
            command.return_value.returncode=0
            command.return_value.stdout=json.dumps({'value':[{'message':'Guest script failed despite request success'}]})
            with self.assertRaisesRegex(RuntimeError, 'did not confirm'):
                remote.main()

    def test_non_main_never_invokes_azure(self):
        with patch.dict(os.environ, {'GITHUB_REF':'refs/heads/feature'}), \
             patch.object(sys, 'argv', ['remote.py','rollback']), patch.object(remote.subprocess, 'run') as command:
            with self.assertRaisesRegex(RuntimeError, 'Only main'):
                remote.main()
            command.assert_not_called()

    def test_superseded_main_commit_is_skipped_before_credentials_or_vm_use(self):
        with patch.dict(os.environ, {'GITHUB_REF':'refs/heads/main','GITHUB_SHA':SHA}), \
             patch.object(sys, 'argv', ['remote.py','deploy']), patch.object(remote, 'latest_main', return_value='b'*40), \
             patch.object(remote.subprocess, 'run') as command:
            remote.main()
            command.assert_not_called()

if __name__ == '__main__':
    unittest.main()
