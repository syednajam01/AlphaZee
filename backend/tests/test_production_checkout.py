"""Production release must not weaken the lab gate or secure browser identity."""
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.config import Settings, settings
from app.main import app


def config(**changes):
    values = dict(app_env='production', debug=False, production_checkout_enabled=True,
        database_url='postgresql://shop:strong-local-fixture-password@db:5432/shop',
        allowed_origins=['https://shop.valid-domain.org'], test_checkout_enabled=False, checkout_lab=False)
    values.update(changes)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize('changes', [
    {'app_env': 'development'}, {'app_env': 'test'}, {'debug': True},
    {'test_checkout_enabled': True}, {'checkout_lab': True},
    {'database_url': 'postgresql://u:short@db:5432/shop'},
    {'database_url': 'postgresql://u:strong-local-fixture-password@db:5432/shop_test'},
    {'database_url': 'postgresql://u:strong-local-fixture-password@db:5432/shop?host=other'},
    {'allowed_origins': ['http://shop.valid-domain.org']},
])
def test_invalid_release_fails_startup(changes):
    with pytest.raises(ValidationError):
        config(**changes)


def test_release_opt_in_and_kill_switch():
    assert config().checkout_enabled
    assert not config(production_checkout_enabled=False).checkout_enabled
    assert not config().test_checkout_allowed


def test_production_browser_session_and_capability(monkeypatch):
    for key in ('app_env', 'debug', 'production_checkout_enabled', 'database_url', 'allowed_origins',
                'test_checkout_enabled', 'checkout_lab'):
        monkeypatch.setattr(settings, key, getattr(config(), key))
    with TestClient(app, base_url='https://shop.valid-domain.org') as client:
        capabilities = client.get('/api/v1/storefront/capabilities').json()
        assert capabilities['checkout_enabled'] is True and capabilities['test_mode'] is False
        response = client.get('/api/v1/orders/checkout-session')
        assert response.status_code == 200
        cookie = response.headers['set-cookie'].lower()
        assert '__host-alphazee_checkout=' in cookie
        assert all(flag in cookie for flag in ('secure', 'httponly', 'samesite=strict', 'path=/'))
        monkeypatch.setattr(settings, 'production_checkout_enabled', False)
        assert client.get('/api/v1/orders/checkout-session').status_code == 503
        assert client.post('/api/v1/orders/quote', json={}).status_code == 503
        assert client.post('/api/v1/orders', json={}).status_code == 503


@pytest.mark.parametrize('release,valid', [('true', True), ('false', True), ('typo', False)])
def test_deployment_preflight_release_switch(monkeypatch, release, valid):
    import runpy
    from pathlib import Path
    for key, value in dict(APP_ENV='production', DEBUG='false', TEST_CHECKOUT_ENABLED='false',
        CHECKOUT_LAB='false', PRODUCTION_CHECKOUT_ENABLED=release, SITE_DOMAIN='shop.valid-domain.org',
        ALLOWED_ORIGINS='https://shop.valid-domain.org', POSTGRES_USER='shop',
        POSTGRES_PASSWORD='strong-local-fixture-password', POSTGRES_DB='shop',
        DATABASE_URL='postgresql://shop:strong-local-fixture-password@db:5432/shop').items():
        monkeypatch.setenv(key, value)
    path = Path(__file__).resolve().parents[1] / 'scripts/check_production_deployment.py'
    if valid:
        runpy.run_path(str(path), run_name='__main__')
    else:
        with pytest.raises(SystemExit, match='true or false'):
            runpy.run_path(str(path), run_name='__main__')
