"""Verify additive media migration and safe downgrade only on a disposable DB."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings


def main():
    source = make_url(settings.database_url)
    if source.get_backend_name() != 'postgresql' or source.host not in {'localhost', '127.0.0.1', '::1'} or source.query:
        raise RuntimeError('Require loopback PostgreSQL without query overrides')
    name = 'alphazee_m3_migration_' + uuid.uuid4().hex[:10] + '_test'
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as c: c.exec_driver_sql(f'CREATE DATABASE "{name}" TEMPLATE template0')
    admin.dispose()
    target = source.set(database=name)
    env = {**os.environ, 'DATABASE_URL': target.render_as_string(hide_password=False), 'APP_ENV': 'test', 'DEBUG': 'false', 'TEST_CHECKOUT_ENABLED': 'false'}
    def migrate(*args, success=True):
        result = subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=ROOT / 'backend', env=env, capture_output=True)
        if (result.returncode == 0) != success:
            print(result.stderr.decode(errors='replace')[-4000:])
            raise RuntimeError('Migration verification failed')
    migrate('upgrade', 'e15a9c2b7046')
    engine = create_engine(target, hide_parameters=True)
    with engine.begin() as c:
        c.execute(text("INSERT INTO collections(id,slug,name,image_url,is_active,display_order) VALUES ('sample-c','sample-c','SAMPLE','/legacy.png',true,0)"))
        c.execute(text("INSERT INTO products(id,slug,title,collection_id,image_url,is_active,is_hero,created_at,updated_at) VALUES ('sample-p','sample-p','SAMPLE','sample-c','/legacy.png',true,false,now(),now())"))
        before = c.scalar(text("SELECT row_to_json(products)::text FROM products WHERE id='sample-p'"))
    migrate('upgrade', 'head')
    migrate('check')
    with engine.begin() as c:
        assert c.scalar(text("SELECT row_to_json(products)::text FROM products WHERE id='sample-p'")) == before
        assert c.scalar(text("SELECT image_url FROM collections WHERE id='sample-c'")) == '/legacy.png'
        creator = c.scalar(text("INSERT INTO user_accounts(auth_subject,is_active) VALUES ('SAMPLE-M3-MIGRATION',true) RETURNING id"))
        c.execute(text("INSERT INTO media_assets(id,storage_key,original_name,kind,content_type,byte_size,checksum,width,height,state,creator_id,created_at) VALUES (:id,:key,'SAMPLE.png','image','image/png',100,:hash,32,24,'ready',:creator,now())"),
                  {'id': 'a'*32, 'key': 'a'*32+'.png', 'hash': 'b'*64, 'creator': creator})
    migrate('downgrade', 'e15a9c2b7046', success=False)
    with engine.begin() as c:
        assert c.scalar(text('SELECT version_num FROM alembic_version')) == 'f27b6d91c083'
        assert c.scalar(text('SELECT count(*) FROM media_assets')) == 1
        c.execute(text('DELETE FROM media_assets'))
    migrate('downgrade', 'e15a9c2b7046')
    migrate('upgrade', 'head')
    migrate('check')
    engine.dispose()
    report = {'phase': 'M3', 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'database': name,
              'prior_revision': 'e15a9c2b7046', 'head_revision': 'f27b6d91c083', 'upgrade_downgrade_reupgrade': 'passed',
              'nonempty_media_downgrade_refused': True, 'legacy_product_rows_and_urls_preserved': True,
              'alembic_check': 'passed', 'development_modified': False, 'database_retained': True}
    (ROOT / '.context/m3_migration_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
