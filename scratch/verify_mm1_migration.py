"""Verify MM1 additive migration (hover_image, hero_slides) strictly on a disposable DB."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings

def main():
    source = make_url(settings.database_url)
    if source.get_backend_name() != 'postgresql' or source.host not in {'localhost', '127.0.0.1', '::1'} or source.query:
        raise RuntimeError('Require loopback PostgreSQL without query overrides')

    name = 'alphazee_mm1_migration_' + uuid.uuid4().hex[:10] + '_test'
    print(f"Creating disposable database: {name}...", flush=True)
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as c:
        c.exec_driver_sql(f'CREATE DATABASE "{name}" TEMPLATE template0')
    admin.dispose()

    target = source.set(database=name)
    env = {
        **os.environ,
        'DATABASE_URL': target.render_as_string(hide_password=False),
        'APP_ENV': 'test',
        'DEBUG': 'false',
        'TEST_CHECKOUT_ENABLED': 'false'
    }

    def migrate(*args, success=True):
        cmd = [sys.executable, '-m', 'alembic', *args]
        result = subprocess.run(cmd, cwd=ROOT / 'backend', env=env, capture_output=True)
        if (result.returncode == 0) != success:
            print("STDOUT:", result.stdout.decode(errors='replace')[-2000:])
            print("STDERR:", result.stderr.decode(errors='replace')[-2000:])
            raise RuntimeError(f'Migration {args} {"failed unexpectedly" if success else "succeeded unexpectedly"}')
        return result

    engine = create_engine(target, hide_parameters=True)
    try:
        # 1. Upgrade to previous head (f27b6d91c083)
        print("1. Upgrading to f27b6d91c083 (M3)...", flush=True)
        migrate('upgrade', 'f27b6d91c083')

        # Insert sample data to verify preservation
        with engine.begin() as c:
            c.execute(text("INSERT INTO collections(id,slug,name,image_url,is_active,display_order) VALUES ('sample-col','sample-col','SAMPLE Winter','/legacy.png',true,0)"))
            c.execute(text("INSERT INTO products(id,slug,title,collection_id,image_url,is_active,is_hero,hero_order,hero_benefit,created_at,updated_at) VALUES ('sample-prod','sample-prod','SAMPLE Jacket','sample-col','/legacy.png',true,true,1,'Warm streetwear drape',now(),now())"))
            creator = c.scalar(text("INSERT INTO user_accounts(auth_subject,is_active) VALUES ('SAMPLE-MM1',true) RETURNING id"))
            c.execute(text("INSERT INTO media_assets(id,storage_key,original_name,kind,content_type,byte_size,checksum,width,height,state,creator_id,created_at) VALUES ('asset1','asset1.png','front.png','image','image/png',100,'hash1',100,100,'ready',:creator,now())"), {'creator': creator})
            c.execute(text("INSERT INTO media_assets(id,storage_key,original_name,kind,content_type,byte_size,checksum,width,height,state,creator_id,created_at) VALUES ('asset2','asset2.png','hover.png','image','image/png',100,'hash2',100,100,'ready',:creator,now())"), {'creator': creator})
            c.execute(text("INSERT INTO media_assets(id,storage_key,original_name,kind,content_type,byte_size,checksum,width,height,duration_ms,state,creator_id,created_at) VALUES ('asset3','asset3.mp4','brand.mp4','video','video/mp4',500,'hash3',1920,1080,15000,'ready',:creator,now())"), {'creator': creator})
            c.execute(text("INSERT INTO product_media(product_id,asset_id,role,display_order,alt_text) VALUES ('sample-prod','asset1','primary',0,'Front')"))
            c.execute(text("INSERT INTO product_media(product_id,asset_id,role,display_order,alt_text) VALUES ('sample-prod','asset3','hero_video',1,'Brand Video')"))
            c.execute(text("INSERT INTO product_media(product_id,asset_id,role,display_order,alt_text) VALUES ('sample-prod','asset1','hero_poster',2,'Poster')"))

        # 2. Upgrade to head (2c8a1b3e5f70)
        print("2. Upgrading to head (2c8a1b3e5f70)...", flush=True)
        migrate('upgrade', 'head')

        # 3. Run alembic check to verify schema matches models
        print("3. Running alembic check...", flush=True)
        migrate('check')

        # 4. Verify data and constraints
        print("4. Verifying migrated data, backfill and hover_image...", flush=True)
        with engine.begin() as c:
            # Check version
            assert c.scalar(text("SELECT version_num FROM alembic_version")) == '2c8a1b3e5f70'

            # Verify backfill of is_hero product into hero_slides
            slide = c.execute(text("SELECT id, title, video_asset_id, poster_asset_id, target_product_id FROM hero_slides WHERE target_product_id = 'sample-prod'")).fetchone()
            assert slide is not None, "Hero slide was not backfilled from is_hero product"
            assert slide[1] == 'SAMPLE Jacket'
            assert slide[2] == 'asset3'
            assert slide[3] == 'asset1'
            print("  Hero slide backfill verified:", slide)

            # Insert a hover_image role
            c.execute(text("INSERT INTO product_media(product_id,asset_id,role,display_order,alt_text) VALUES ('sample-prod','asset2','hover_image',3,'Back')"))
            hover_count = c.scalar(text("SELECT count(*) FROM product_media WHERE role = 'hover_image'"))
            assert hover_count == 1, "Failed to insert hover_image role"
            print("  hover_image role inserted and verified!")

            # Verify duplicate hover_image role is rejected by uq_product_media_single_role
            try:
                with c.begin_nested():
                    c.execute(text("INSERT INTO product_media(product_id,asset_id,role,display_order,alt_text) VALUES ('sample-prod','asset1','hover_image',4,'Another Back')"))
                raise AssertionError("Duplicate hover_image was not rejected!")
            except Exception as e:
                if "duplicate key" in str(e) or "UniqueViolation" in str(e) or "uq_product_media_single_role" in str(e):
                    print("  Duplicate hover_image correctly rejected by unique constraint.")
                else:
                    raise

        # 5. Verify safe downgrade prevention when hover_image exists
        print("5. Verifying downgrade safety...", flush=True)
        migrate('downgrade', 'f27b6d91c083', success=False)

        # Remove hover_image and re-test downgrade
        with engine.begin() as c:
            c.execute(text("DELETE FROM product_media WHERE role = 'hover_image'"))
        migrate('downgrade', 'f27b6d91c083', success=True)

        with engine.begin() as c:
            assert c.scalar(text("SELECT version_num FROM alembic_version")) == 'f27b6d91c083'

        # 6. Re-upgrade to head
        print("6. Re-upgrading to head...", flush=True)
        migrate('upgrade', 'head')
        migrate('check')

        print("\n" + "=" * 70)
        print("MM1 MIGRATION VERIFICATION PASSED COMPLETELY ON DISPOSABLE DB")
        print("=" * 70)

    finally:
        engine.dispose()
        admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
        with admin.connect() as c:
            c.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.dispose()
        print(f"Dropped disposable database: {name}")

if __name__ == '__main__':
    main()
