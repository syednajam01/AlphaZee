import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

OPS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('deploy', OPS / 'deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
SHA = 'a' * 40
HEAD = 'a81f92c6d430'
OLD = '6e4a2b8d0c1f'


def manifest():
    return {'sha': SHA, 'sequence': 2, 'api': 'ghcr.io/syednajam01/alphazee-api@sha256:' + '1' * 64,
            'web': 'ghcr.io/syednajam01/alphazee-web@sha256:' + '2' * 64, 'backward_compatible_heads': []}


class ReleaseTransaction(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.release = self.root / 'releases' / SHA
        self.release.mkdir(parents=True)
        self.config = {'state_dir': str(self.root), 'env_file': '/private/env', 'project': 'alphazee-prod',
                       'restore_proof': '/private/proof.json',
                       'domain': 'alphazee.tech', 'deployment_dir': '/live', 'compose_files': ['/live/compose.prod.yml'],
                       'volumes': {'pgdata': 'real-db', 'catalog_media': 'real-media', 'caddy_data': 'real-tls', 'caddy_config': 'real-caddy'}}
        self.deployer = deploy.Deployer(self.config)
        self.deployer.environment = self.root / 'private.env'
        self.deployer.environment.write_text('SAMPLE=value\n')
        self.previous = {'sha': 'b' * 40, 'sequence': 1, 'head': HEAD, 'files': ['old.yml'], 'backward_compatible_heads': []}
        self.previous.update(env_file=str(self.deployer.environment), env_sha256=deploy.hashlib.sha256(self.deployer.environment.read_bytes()).hexdigest())
        deploy.atomic_json(self.root / 'current.json', self.previous)
        deploy.atomic_json(self.release / 'manifest.json', manifest())
        self.deployer.inventory = Mock()
        self.deployer.check_prerequisites = Mock()
        self.deployer.database_head = Mock(return_value=HEAD)
        self.deployer.compose = Mock()
        self.deployer.backup = Mock(return_value='private-backup-ref')
        self.deployer.activate = Mock()
        self.external = patch.object(deploy, 'run', return_value=HEAD).start()
        patch.object(deploy, 'recent_restore_proof').start()
        self.addCleanup(patch.stopall)

    def test_success_migrates_before_activation_and_records_previous(self):
        order = []
        self.deployer.backup.side_effect = lambda _: order.append('backup') or 'backup'
        self.deployer.compose.side_effect = lambda files, *args, **kwargs: order.append('migration' if 'migrate' in args else 'validate')
        self.deployer.activate.side_effect = lambda _: order.append('activate')
        self.deployer.deploy(self.release)
        self.assertEqual(order, ['validate', 'backup', 'migration', 'activate'])
        self.assertEqual(deploy.read_json(self.root / 'previous.json'), self.previous)
        self.assertEqual(deploy.read_json(self.root / 'current.json')['sha'], SHA)
        migration = self.deployer.compose.call_args_list[-1].args
        self.assertIn('--rm', migration)
        self.assertIn('--no-deps', migration)
        self.assertNotIn('--no-build', migration)
        self.assertIn('--pull', migration)

    def test_stale_workflow_never_pulls_or_backs_up(self):
        deploy.atomic_json(self.root / 'current.json', dict(self.previous, sequence=3))
        with self.assertRaisesRegex(deploy.DeploymentError, 'Stale'):
            self.deployer.deploy(self.release)
        self.external.assert_not_called()
        self.deployer.backup.assert_not_called()

    def test_backup_failure_prevents_migration_and_activation(self):
        self.deployer.backup.side_effect = deploy.DeploymentError('Backup failed')
        with self.assertRaises(deploy.DeploymentError):
            self.deployer.deploy(self.release)
        self.assertEqual(self.deployer.compose.call_count, 1)
        self.deployer.activate.assert_not_called()
        self.assertEqual(deploy.read_json(self.root / 'current.json'), self.previous)

    def test_migration_failure_never_replaces_api(self):
        def compose(files, *args, **kwargs):
            if 'migrate' in args:
                raise deploy.DeploymentError('Migration failed')
        self.deployer.compose.side_effect = compose
        with self.assertRaises(deploy.DeploymentError):
            self.deployer.deploy(self.release)
        self.deployer.activate.assert_not_called()
        self.assertEqual(deploy.read_json(self.root / 'current.json'), self.previous)

    def test_unreviewed_schema_change_is_blocked_before_backup(self):
        self.external.return_value = 'f' * 12
        with self.assertRaisesRegex(deploy.DeploymentError, 'explicit reviewed'):
            self.deployer.deploy(self.release)
        self.deployer.backup.assert_not_called()

    def test_bad_health_restores_previous_images_but_keeps_failed_status(self):
        self.deployer.activate.side_effect = [deploy.DeploymentError('Bad health'), None]
        with self.assertRaises(deploy.DeploymentError):
            self.deployer.deploy(self.release)
        self.assertEqual(self.deployer.activate.call_args_list[-1].args, (self.previous,))
        self.assertEqual(deploy.read_json(self.root / 'current.json'), self.previous)
        self.assertFalse((self.release / 'success.json').exists())

    def test_incompatible_partial_schema_never_auto_rolls_back(self):
        self.deployer.database_head.side_effect = [HEAD, 'f' * 12]
        self.deployer.activate.side_effect = deploy.DeploymentError('Bad health')
        with self.assertRaises(deploy.DeploymentError):
            self.deployer.deploy(self.release)
        self.assertEqual(self.deployer.activate.call_count, 1)

    def test_failed_recovery_does_not_claim_success(self):
        self.deployer.activate.side_effect = [deploy.DeploymentError('Bad new release'), deploy.DeploymentError('Bad recovery')]
        with self.assertRaisesRegex(deploy.DeploymentError, 'Bad recovery'):
            self.deployer.deploy(self.release)
        self.assertFalse((self.release / 'success.json').exists())

    def test_manual_rollback_uses_only_recorded_previous_and_preserves_sequence(self):
        target = dict(self.previous, sha='c' * 40, sequence=0)
        deploy.atomic_json(self.root / 'previous.json', target)
        self.deployer.rollback()
        self.deployer.activate.assert_called_once_with(target)
        self.assertEqual(deploy.read_json(self.root / 'current.json')['sequence'], 1)

    def test_manual_rollback_refuses_unknown_schema(self):
        deploy.atomic_json(self.root / 'previous.json', dict(self.previous, head=OLD))
        with self.assertRaisesRegex(deploy.DeploymentError, 'Schema compatibility'):
            self.deployer.rollback()
        self.deployer.activate.assert_not_called()

    def test_manual_rollback_does_not_revert_changed_checkout_or_bank_settings(self):
        deploy.atomic_json(self.root / 'previous.json', self.previous)
        self.deployer.environment.write_text('SAMPLE=changed-private-setting\n')
        with self.assertRaisesRegex(deploy.DeploymentError, 'changed private configuration'):
            self.deployer.rollback()
        self.deployer.activate.assert_not_called()

    def test_override_preserves_external_volume_names(self):
        path = self.deployer.override(self.release, 'api-digest', 'web-digest')
        data = deploy.read_json(path)
        self.assertEqual(data['volumes']['pgdata'], {'name': 'real-db', 'external': True})
        self.assertEqual(data['services']['migrate']['image'], 'api-digest')

    def test_backup_resumes_api_when_dump_fails(self):
        self.deployer.live = Mock()
        self.deployer.live.side_effect = ['0', None, deploy.DeploymentError('Dump failed'), None]
        self.config['restore_proof'] = 'proof.json'
        self.config['backup_storage_account'] = 'sampleprivate'
        self.config['backup_container'] = 'private-backups'
        self.external.side_effect = lambda args, **kwargs: '0 /sample' if args[0] == 'du' else ''
        with patch.object(deploy, 'recent_restore_proof'):
            with self.assertRaisesRegex(deploy.DeploymentError, 'Dump failed'):
                    deploy.Deployer.backup(self.deployer, SHA)
        self.assertEqual(self.deployer.live.call_args_list[-1].args, ('start', 'api'))


class Validation(unittest.TestCase):
    def test_mutable_foreign_or_malformed_images_rejected(self):
        for image in ['ghcr.io/syednajam01/alphazee-api:latest', 'ghcr.io/attacker/api@sha256:' + '1' * 64, '$(whoami)']:
            with self.subTest(image=image), self.assertRaises(deploy.DeploymentError):
                deploy.validate_manifest(dict(manifest(), api=image))

    def test_manifest_rejects_injected_sha_and_sequence(self):
        for change in [{'sha': '../x'}, {'sequence': 0}, {'backward_compatible_heads': ['head; false']}]:
            with self.subTest(change=change), self.assertRaises(deploy.DeploymentError):
                deploy.validate_manifest(dict(manifest(), **change))

    def test_rollback_requires_same_or_explicit_compatible_schema(self):
        self.assertTrue(deploy.rollback_allowed(HEAD, HEAD, []))
        self.assertFalse(deploy.rollback_allowed(HEAD, OLD, []))
        self.assertTrue(deploy.rollback_allowed(HEAD, OLD, [HEAD]))

    def test_config_refuses_uninspected_example_volumes(self):
        config = json.loads((OPS / 'host-config.example.json').read_text())
        with self.assertRaisesRegex(deploy.DeploymentError, 'volume names'):
            deploy.validate_config(config)

    def test_restore_proof_must_be_recent_and_include_matched_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'proof.json'
            for proof in [{'verified_at': '2000-01-01T00:00:00Z', 'restored_database_and_media': True, 'backup_reference':'sample'},
                          {'verified_at': deploy.datetime.now(deploy.timezone.utc).isoformat(), 'restored_database_and_media':False, 'backup_reference':'sample'}]:
                deploy.atomic_json(path, proof)
                with self.assertRaises(deploy.DeploymentError):
                    deploy.recent_restore_proof(path)

if __name__ == '__main__':
    unittest.main()
