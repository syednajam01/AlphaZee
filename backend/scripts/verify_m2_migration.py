"""Disposable migration verification with historical catalog/order snapshots."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings


def main():
    source = make_url(settings.database_url)
    if source.get_backend_name() != 'postgresql' or source.host not in {'localhost', '127.0.0.1', '::1'} or source.query:
        raise RuntimeError('Require loopback PostgreSQL without query overrides')
    name = 'alphazee_m2_migration_' + uuid.uuid4().hex[:10] + '_test'
    admin = create_engine(source.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}" TEMPLATE template0')
    admin.dispose()
    target = source.set(database=name)
    env = {**os.environ, 'DATABASE_URL': target.render_as_string(hide_password=False), 'APP_ENV': 'test',
           'DEBUG': 'false', 'TEST_CHECKOUT_ENABLED': 'false'}
    def migrate(*args, expected_success=True):
        result = subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=ROOT / 'backend', env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if (result.returncode == 0) != expected_success:
            raise RuntimeError('Migration verification command failed')
    migrate('upgrade', 'c94e31f7d562')
    engine = create_engine(target, hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO collections(id,slug,name,is_active,display_order) VALUES ('sample-c','sample-c','SAMPLE',true,0)"))
        connection.execute(text("INSERT INTO products(id,slug,title,collection_id,image_url,is_active,is_hero,created_at,updated_at) VALUES ('sample-p','sample-p','SAMPLE Original','sample-c','/sample.png',true,false,now(),now()),('sample-inactive','sample-inactive','SAMPLE Inactive','sample-c',NULL,false,false,now(),now())"))
        variant_id = connection.scalar(text("INSERT INTO variants(sku,product_id,price_minor,is_active,availability) VALUES ('SAMPLE-M2-LEGACY','sample-p',12345,true,'AVAILABLE') RETURNING id"))
        order_id = connection.scalar(text("INSERT INTO orders(order_number,customer_name,customer_phone,shipping_address_line1,shipping_city,shipping_province,payment_method,payment_status,subtotal_minor,total_minor,order_status) VALUES ('SAMPLE-M2-LEGACY','SAMPLE','03001234567','SAMPLE Street','Lahore','Punjab','cod','pending',12345,12345,'placed') RETURNING id"))
        connection.execute(text("INSERT INTO order_lines(order_id,variant_id,product_title_snapshot,variant_sku_snapshot,unit_price_minor,quantity,line_total_minor) VALUES (:order,:variant,'SAMPLE Original','SAMPLE-M2-LEGACY',12345,1,12345)"), {'order': order_id, 'variant': variant_id})
    migrate('upgrade', 'head')
    with engine.begin() as connection:
        states = dict(connection.execute(text('SELECT id,status FROM products')).all())
        assert states == {'sample-p': 'published', 'sample-inactive': 'draft'}
        assert connection.scalar(text("SELECT image_url FROM products WHERE id='sample-p'")) == '/sample.png'
        connection.execute(text("INSERT INTO products(id,status,is_active,is_hero,legacy_media,created_at,updated_at) VALUES ('sample-draft','draft',false,false,false,now(),now())"))
        connection.execute(text("INSERT INTO variants(sku,product_id,price_minor,is_active,availability) VALUES ('SAMPLE-M2-DRAFT','sample-draft',NULL,false,'UNKNOWN')"))
    assert next(key for key in inspect(engine).get_foreign_keys('variants') if key['constrained_columns'] == ['product_id'])['options']['ondelete'] == 'RESTRICT'
    migrate('downgrade', 'c94e31f7d562', expected_success=False)
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT status FROM products WHERE id='sample-draft'")) == 'draft'
        assert connection.scalar(text('SELECT version_num FROM alembic_version')) == 'e15a9c2b7046'
        connection.execute(text("DELETE FROM variants WHERE product_id='sample-draft'"))
        connection.execute(text("DELETE FROM products WHERE id='sample-draft'"))
    try:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM products WHERE id='sample-p'"))
    except IntegrityError:
        pass
    else:
        raise RuntimeError('Referenced catalog record was deletable')
    migrate('downgrade', 'c94e31f7d562')
    migrate('upgrade', 'head')
    migrate('check')
    with engine.connect() as connection:
        assert connection.execute(text('SELECT product_title_snapshot,unit_price_minor FROM order_lines')).one() == ('SAMPLE Original', 12345)
        assert connection.scalar(text('SELECT count(*) FROM orders')) == 1
        assert connection.scalar(text('SELECT count(*) FROM variants')) == 1
    engine.dispose()
    report = {'phase': 'M2', 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'database': name,
              'prior_revision': 'c94e31f7d562', 'head_revision': 'e15a9c2b7046',
              'upgrade_downgrade_reupgrade': 'passed', 'incomplete_draft_downgrade_refused': True,
              'legacy_active_inactive_states_preserved': True, 'legacy_image_preserved': True,
              'referenced_product_delete_rejected': True, 'historical_order_snapshots_preserved': True,
              'alembic_check': 'passed', 'development_modified': False, 'database_retained': True}
    (ROOT / '.context/owner_catalog_migration_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
