import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_restore as restore
import deploy


class RestoreValidation(unittest.TestCase):
    def test_reference_cannot_select_another_account_or_escape_prefix(self):
        config={'backup_storage_account':'sampleaccount','backup_container':'sample-backups'}
        for reference in ['other/sample-backups/set', 'sampleaccount/sample-backups/../set',
                          'sampleaccount/sample-backups/set//x', 'sampleaccount/sample-backups/set?sig=secret']:
            with self.subTest(reference=reference), self.assertRaises(deploy.DeploymentError):
                restore.parse_reference(reference,config)
        self.assertEqual(restore.parse_reference('sampleaccount/sample-backups/manual-123',config),'manual-123')

    def test_archive_traversal_links_and_devices_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name,kind in [('../escape',tarfile.REGTYPE),('/absolute',tarfile.REGTYPE),
                              ('objects/link',tarfile.SYMTYPE),('device',tarfile.CHRTYPE)]:
                with tarfile.open(root/'media.tgz','w:gz') as archive:
                    member=tarfile.TarInfo(name);member.type=kind
                    archive.addfile(member)
                with self.subTest(name=name),self.assertRaises(deploy.DeploymentError):
                    restore.extract_media(root/'media.tgz',root)

    def test_real_file_extraction_and_every_checksum_are_checked(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); destination=root/'media';destination.mkdir()
            key='a'*32+'.png'; data=b'SAMPLE fixture content'
            with tarfile.open(root/'media.tgz','w:gz') as archive:
                member=tarfile.TarInfo('./objects/'+key);member.size=len(data)
                archive.addfile(member,io.BytesIO(data))
            restore.extract_media(root/'media.tgz',destination)
            asset={'storage_key':key,'byte_size':len(data),'checksum':hashlib.sha256(data).hexdigest()}
            self.assertEqual(restore.verify_media([asset],destination),1)
            with self.assertRaisesRegex(deploy.DeploymentError,'checksum'):
                restore.verify_media([dict(asset,checksum='0'*64)],destination)
            (destination/'objects'/key).unlink()
            with self.assertRaisesRegex(deploy.DeploymentError,'missing'):
                restore.verify_media([asset],destination)

    def test_missing_executable_has_actionable_sanitized_error(self):
        with patch.object(deploy.subprocess,'run',side_effect=FileNotFoundError('sensitive raw error')):
            with self.assertRaisesRegex(deploy.DeploymentError,'Azure CLI|install_vm_prerequisites') as error:
                deploy.run(['az','login','--identity'])
            self.assertNotIn('sensitive',str(error.exception))

    def test_missing_and_malformed_restore_proof_never_raise_raw_file_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'proof.json'
            with self.assertRaisesRegex(deploy.DeploymentError,'Restore proof is missing'):
                deploy.recent_restore_proof(path)
            for body in ['bad JSON',json.dumps({'verified_at':'not-a-time'}),json.dumps({'verified_at':'2026-11-08T00:00:00'})]:
                path.write_text(body);path.chmod(0o600)
                with self.assertRaisesRegex(deploy.DeploymentError,'malformed'):
                    deploy.recent_restore_proof(path)

    def test_failed_preflight_reports_all_missing_tools_before_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            config={'state_dir':temporary,'env_file':str(Path(temporary)/'missing.env'),
                    'compose_files':[str(Path(temporary)/'missing.yml')],'restore_proof':str(Path(temporary)/'proof.json')}
            instance=deploy.Deployer(config)
            with patch.object(deploy.shutil,'which',return_value=None):
                with self.assertRaises(deploy.DeploymentError) as error:
                    instance.check_prerequisites()
            message=str(error.exception)
            for detail in ('missing executable: az','missing executable: docker','missing host configuration','Restore proof is missing'):
                self.assertIn(detail,message)


if __name__=='__main__':
    unittest.main()
