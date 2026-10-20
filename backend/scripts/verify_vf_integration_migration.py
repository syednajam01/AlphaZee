"""Upgrade/downgrade/re-upgrade only a freshly created disposable database."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text
from app.config import settings
from sqlalchemy.engine import make_url


def main():
    base = make_url(settings.database_url)
    if base.host not in {'localhost', '127.0.0.1'} or base.query:
        raise RuntimeError('Use loopback PostgreSQL without connection overrides.')
    name = f'alphazee_vf_repair_{secrets.token_hex(5)}_test'
    admin = create_engine(base.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    with admin.connect() as db:
        db.execute(text(f'CREATE DATABASE "{name}"'))
    target = base.set(database=name)
    env = dict(os.environ, DATABASE_URL=target.render_as_string(hide_password=False), DEBUG='false')
    backend = Path(__file__).resolve().parents[1]
    def alembic(*args):
        result = subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=backend, env=env,
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
    try:
        alembic('upgrade', '6e4a2b8d0c1f')
        legacy_engine = create_engine(target, hide_parameters=True)
        with legacy_engine.begin() as db:
            supplier = db.scalar(text("INSERT INTO suppliers(name,slug) VALUES ('SAMPLE legacy vendor','sample-legacy') RETURNING id"))
            db.execute(text("INSERT INTO products(id,title,slug,status,is_active,is_hero,created_at,updated_at) VALUES ('legacy-review','SAMPLE legacy tee','legacy-review','draft',false,false,now(),now())"))
            variant = db.scalar(text("INSERT INTO variants(product_id,sku,price_minor,is_active,availability) VALUES ('legacy-review','SAMPLE-LEGACY',200000,true,'AVAILABLE') RETURNING id"))
            mapping = db.scalar(text('INSERT INTO supplier_variants(supplier_id,variant_id,supplier_cost_minor) VALUES (:supplier,:variant,120000) RETURNING id'), {'supplier': supplier, 'variant': variant})
            db.execute(text('INSERT INTO inventory_balances(supplier_variant_id,on_hand) VALUES (:mapping,3)'), {'mapping': mapping})
            db.execute(text("INSERT INTO stock_events(supplier_variant_id,previous_on_hand,new_on_hand,delta,reason) VALUES (:mapping,0,3,3,'customer_return')"), {'mapping': mapping})
        legacy_engine.dispose()
        alembic('upgrade', 'head')
        alembic('downgrade', '6e4a2b8d0c1f')
        alembic('upgrade', 'head')
        engine = create_engine(target, hide_parameters=True)
        with engine.connect() as db:
            assert db.scalar(text('SELECT version_num FROM alembic_version')) == 'a81f92c6d430'
            assert db.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_name IN ('owned_stock_lots','owned_stock_allocations')")) == 2
            assert db.scalar(text("SELECT stock_management_source FROM products WHERE id='legacy-review'")) == 'vendor_managed'
            balance = db.execute(text('SELECT on_hand,ownership_review_required FROM inventory_balances WHERE supplier_variant_id=:id'), {'id': mapping}).one()
            assert balance == (3, True)
            assert db.scalar(text('SELECT count(*) FROM owned_stock_lots')) == 0
            assert db.scalar(text('SELECT count(*) FROM supplier_ledger_entries')) == 0
        engine.dispose()
        print('PASS: disposable database upgrade -> downgrade -> re-upgrade; ownership tables and new head verified.')
    finally:
        # This exact random database was created above, never an existing app/test DB.
        with admin.connect() as db:
            db.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


if __name__ == '__main__':
    main()
