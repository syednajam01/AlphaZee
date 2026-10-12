"""Containment checks intentionally run without any database connection."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.database import get_db
from app.main import app


@pytest.mark.parametrize('authenticated', [False, True])
def test_public_order_creation_is_blocked_before_database_access(monkeypatch, authenticated):
    monkeypatch.setattr(settings, 'test_checkout_enabled', False)

    def forbidden_db():
        raise AssertionError('Disabled checkout must not open a database session')

    app.dependency_overrides[get_db] = forbidden_db
    try:
        with TestClient(app) as client:
            for path in ('/api/v1/orders', '/api/v1/orders/'):
                headers = {'X-Admin-Key': settings.admin_api_key} if authenticated else {}
                response = client.post(path, json={}, headers=headers)
                assert response.status_code == 503
                assert response.json()['detail'] == 'Checkout is temporarily unavailable. You can still browse and save your cart.'
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_capabilities_are_safe_and_health_remains_available(monkeypatch):
    monkeypatch.setattr(settings, 'test_checkout_enabled', False)
    with TestClient(app) as client:
        response = client.get('/api/v1/storefront/capabilities')
        assert response.status_code == 200
        assert response.json() == {'checkout_enabled': False, 'test_mode': False}
        assert response.headers['cache-control'] == 'no-store'
        assert client.get('/api/v1/health').status_code == 200


@pytest.mark.parametrize('environment,database', [
    ('production', 'postgresql://u:p@localhost:5433/alphazee_browser_test'),
    ('development', 'postgresql://u:p@localhost:5433/alphazee_browser_test'),
    ('test', 'postgresql://u:p@localhost:5433/alphazee_dev'),
    ('test', 'postgresql://u:p@remote.example:5433/alphazee_browser_test'),
    ('test', 'sqlite:///alphazee_test'),
    ('test', 'postgresql://u:p@localhost:5433/alphazee_browser_test?host=remote.example'),
])
def test_test_checkout_rejects_unsafe_configuration(environment, database):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env=environment, database_url=database,
                 test_checkout_enabled=True, admin_api_key='x' * 40)


def test_checkout_defaults_off_and_only_isolated_test_can_enable():
    assert not Settings(_env_file=None, test_checkout_enabled=False).checkout_enabled
    config = Settings(_env_file=None, app_env='test', test_checkout_enabled=True,
                      database_url='postgresql://u:p@127.0.0.1:5433/alphazee_browser_test')
    assert config.checkout_enabled


def test_isolated_test_mode_exposes_enabled_capability_and_reaches_order_service(monkeypatch):
    from unittest.mock import Mock
    from app.api.v1 import orders
    monkeypatch.setattr(settings, 'app_env', 'test')
    monkeypatch.setattr(settings, 'database_url', 'postgresql://u:p@localhost:5433/alphazee_browser_test')
    monkeypatch.setattr(settings, 'test_checkout_enabled', True)
    session = Mock()
    app.dependency_overrides[get_db] = lambda: session
    place = Mock(side_effect=ValueError('SAMPLE unavailable variant'))
    monkeypatch.setattr(orders, 'place_order', place)
    try:
        with TestClient(app) as client:
            assert client.get('/api/v1/storefront/capabilities').json() == {
                'checkout_enabled': True, 'test_mode': True,
            }
            assert client.get('/api/v1/orders/checkout-session').status_code == 200
            response = client.post('/api/v1/orders', headers={
                'Origin': 'http://localhost:3000', 'Idempotency-Key': 'chk_sample_test_submission_123456',
            }, json={
                'customer_name': 'SAMPLE Customer', 'customer_phone': '03001234567',
                'shipping_address_line1': 'SAMPLE Test address', 'shipping_city': 'Lahore',
                'shipping_province': 'Punjab',
                'payment_method': 'cod', 'items': [{'variant_id': 1, 'quantity': 1}],
            })
            assert response.status_code == 400
            place.assert_called_once()
            session.rollback.assert_called_once()
    finally:
        app.dependency_overrides.pop(get_db, None)
