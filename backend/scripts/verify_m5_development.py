"""Read-only delivery checks for the usual local Docker application."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.config import settings
from app.database import SessionLocal, engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['M5','M6','M7','M8'], default='M5')
    phase = parser.parse_args().phase
    url = make_url(settings.database_url)
    assert settings.is_development and url.host == 'db' and url.database == 'alphazee_dev'
    assert not settings.checkout_enabled
    engine.echo = False
    with SessionLocal() as db:
        counts = {table: db.scalar(text(f'SELECT count(*) FROM {table}')) for table in
                  ('products', 'collections', 'media_assets', 'orders', 'supplier_variants')}
        owner = db.execute(text("SELECT enabled, password_hash FROM owner_credentials WHERE username = 'syed123'")).one()
        assert owner.enabled and owner.password_hash
        head = db.scalar(text('SELECT version_num FROM alembic_version'))
    checks = {}
    for path, expected in [('/storefront/capabilities', 200), ('/products', 200),
                           ('/catalog/products/nonexistent-m6-product', 404), ('/admin/orders',401),
                           ('/admin/analytics/profit-loss',401), ('/admin/returns',401), ('/admin/catalog/variants/1/stock', 401),
                           ('/admin/inventory/00000000-0000-0000-0000-000000000001/holds', 401)]:
        try: response = urllib.request.urlopen('http://127.0.0.1:8000/api/v1' + path, timeout=15)
        except urllib.error.HTTPError as error: response = error
        with response:
            assert response.status == expected
            if path.endswith('/capabilities'): assert json.load(response)['checkout_enabled'] is False
        checks[path] = expected
    print(json.dumps({'phase':phase, 'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'database':'alphazee_dev', 'source_row_counts':counts, 'owner_account_present_enabled':True,
        'plaintext_password_recorded':False, 'migration_head':head, 'schema_changes':False,
        'public_checkout_enabled':False, 'http_checks':checks}, indent=2))


if __name__ == '__main__': main()
