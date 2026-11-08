"""Real Docker PostgreSQL restore with SAMPLE data and mocked Blob transport only."""
import hashlib
import io
import json
from pathlib import Path
import secrets
import shutil
import sys
import tarfile
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy
import verify_restore


def main():
    project = 'alphazee-restore-fixture-' + secrets.token_hex(5)
    source = project + '-db'
    created = False
    original_read_text = Path.read_text
    try:
        deploy.run(['docker','run','-d','--name',source,'--network','none','--memory','256m',
                    '--label','com.docker.compose.project='+project,'--label','com.docker.compose.service=db',
                    '--tmpfs','/var/lib/postgresql/data:rw,size=128m','-e','POSTGRES_USER=restore',
                    '-e','POSTGRES_DB=restore_test','-e','POSTGRES_HOST_AUTH_METHOD=trust','postgres:16-alpine'])
        created = True
        for attempt in range(40):
            try:
                deploy.run(['docker','exec',source,'sh','-c','test "$(head -n1 "$PGDATA/postmaster.pid")" = 1 && pg_isready -U restore -d restore_test'])
                break
            except deploy.DeploymentError:
                if attempt==39: raise
                time.sleep(1)
        key='a'*32+'.png'; content=b'SAMPLE restore fixture'; checksum=hashlib.sha256(content).hexdigest()
        sql="CREATE TABLE alembic_version(version_num text); INSERT INTO alembic_version VALUES ('a81f92c6d430'); CREATE TABLE media_assets(state text,storage_key text,byte_size bigint,checksum text); CREATE TABLE sample_orders(id int); INSERT INTO sample_orders VALUES (1); "
        sql+=f"INSERT INTO media_assets VALUES ('ready','{key}',{len(content)},'{checksum}');"
        deploy.run(['docker','exec',source,'psql','-v','ON_ERROR_STOP=1','-U','restore','-d','restore_test','-c',sql])
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); blobs=root/'sample-blobs';blobs.mkdir()
            with (blobs/'database.dump').open('wb') as output:
                deploy.run(['docker','exec',source,'pg_dump','-U','restore','-d','restore_test','-Fc'],output=output)
            with tarfile.open(blobs/'media.tar.gz','w:gz') as archive:
                item=tarfile.TarInfo('objects/'+key);item.size=len(content);archive.addfile(item,io.BytesIO(content))
            receipt={'reference':'sampleaccount/sample-backups/sample-set','database_and_media_quiesced':True,
                     'schema_head':'a81f92c6d430','database_bytes':16*1024**2,'media_bytes':len(content)}
            (blobs/'receipt.json').write_text(json.dumps(receipt))
            config={'state_dir':str(root),'project':project,'backup_storage_account':'sampleaccount',
                    'backup_container':'sample-backups','restore_proof':str(root/'proof.json')}
            real_run=deploy.run
            def commands(args,**kwargs):
                if args[0]!='az': return real_run(args,**kwargs)
                if args[1:4]==['storage','blob','download']:
                    name=Path(args[args.index('--name')+1]).name
                    shutil.copyfile(blobs/name,args[args.index('--file')+1])
                return ''
            def read_text(path,*args,**kwargs):
                return 'MemAvailable: 2097152 kB\n' if path.as_posix()=='/proc/meminfo' else original_read_text(path,*args,**kwargs)
            with patch.object(verify_restore,'run',side_effect=commands),patch.object(Path,'read_text',read_text):
                proof=verify_restore.verify(config,receipt['reference'],True)
            assert proof['ready_media_verified']==1 and proof['restored_tables']==3
            assert json.loads((root/'proof.json').read_text())['restored_database_and_media'] is True
            assert real_run(['docker','exec',source,'psql','-U','restore','-d','restore_test','-tAc','SELECT count(*) FROM sample_orders'])=='1'
            print('PASS: real isolated PostgreSQL dump/restore, media checksum, genuine proof creation and source data preservation; Blob transport was synthetic')
    finally:
        if created: deploy.run(['docker','rm','-f',source])


if __name__=='__main__':main()
