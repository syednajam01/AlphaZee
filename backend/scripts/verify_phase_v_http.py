"""Terminal-only, read-mostly HTTP containment checks against local Docker dev stack."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[2]
WEB = 'http://127.0.0.1:13000'
API = 'http://127.0.0.1:18000'


def request(base, path, *, method='GET', payload=None, headers=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(base + path, data=body, method=method,
                  headers={'Content-Type': 'application/json', **(headers or {})})
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        content = response.read().decode('utf-8')
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = content
        return response.status, data


def main():
    checks = {}
    status, page = request(WEB, '/')
    assert status == 200 and '<html' in page.lower() and 'AlphaZee' in page
    checks['storefront_home'] = status
    for label, base in [('proxied', WEB), ('direct', API)]:
        status, data = request(base, '/api/v1/ready')
        assert status == 200 and data['database'] == 'connected'
        checks[f'{label}_ready'] = status
        status, data = request(base, '/api/v1/storefront/capabilities')
        assert status == 200 and data['checkout_enabled'] is False
        assert data['test_mode'] is False and data['payment_methods'] == ['cod']
        checks[f'{label}_checkout_enabled'] = False
        for path in ('/api/v1/admin/overview', '/api/v1/admin/catalog/variants'):
            status, _ = request(base, path)
            assert status == 401
            checks[f'{label}_{path.rsplit("/", 1)[-1]}_anonymous'] = status

    # The gate must reject even a direct API submission with a plausible payload.
    sample = {'customer_name': 'SAMPLE Gate Check', 'customer_phone': '03001234567',
              'shipping_address_line1': 'SAMPLE Street', 'shipping_city': 'Lahore',
              'shipping_province': 'Punjab', 'payment_method': 'cod',
              'items': [{'variant_id': 1, 'quantity': 1}]}
    status, _ = request(API, '/api/v1/orders', method='POST', payload=sample,
                        headers={'Idempotency-Key': f'chk_{uuid.uuid4().hex}',
                                 'Origin': 'http://localhost:13000'})
    assert status == 503
    checks['direct_public_order_post'] = status
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'target': 'local Docker development stack, loopback 13000/18000',
              'browser_used': False, 'checks': checks, 'passed': True}
    (ROOT / '.context' / 'phase_v_http_verification.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
