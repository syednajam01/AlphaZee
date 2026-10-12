"""Owner session security regression tests against guarded PostgreSQL fixtures."""
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from app.config import settings
from app.dependencies.auth import cookie_name, require_owner_session
from app.models.auth import OwnerCredential, OwnerSession
from app.models.suppliers import UserAccount
from app.services.session_store import utcnow, token_hash

ORIGIN = 'http://localhost:3000'
PASSWORD = 'SAMPLE-test-password-2026'


def sign_in(client, username='sample_owner', password=PASSWORD):
    return client.post('/api/v1/auth/login', headers={'Origin': ORIGIN},
                       json={'username': username, 'password': password})


def test_owner_login_route_exists_and_rejects_untrusted_origin(client):
    response = client.post('/api/v1/auth/login', json={'username': 'sample', 'password': 'not-a-password'},
                           headers={'Origin': 'https://untrusted.example'})
    assert response.status_code == 403


def test_shared_key_no_longer_authorizes_console(client):
    from app.config import settings
    assert client.get('/api/v1/admin/overview', headers={'X-Admin-Key': settings.admin_api_key}).status_code == 401


def test_login_cookie_session_and_logout_revocation(client, db_session, sample_owner):
    response = sign_in(client, username='SAMPLE_OWNER')
    assert response.status_code == 200
    cookie = response.headers['set-cookie']
    assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie and 'Path=/' in cookie
    assert response.headers['cache-control'] == 'no-store'
    token = client.cookies.get(cookie_name())
    stored = db_session.get(OwnerSession, token_hash(token))
    assert stored is not None and stored.token_hash != token
    assert 'password' not in response.text and token not in response.text
    csrf = response.json()['csrf_token']
    assert client.get('/api/v1/auth/session').json()['csrf_token'] == csrf
    assert client.get('/api/v1/admin/overview').status_code == 200
    assert client.post('/api/v1/auth/logout', headers={'Origin': ORIGIN, 'X-CSRF-Token': csrf}).status_code == 200
    assert client.get('/api/v1/auth/session').status_code == 401
    client.cookies.set(cookie_name(), token)
    assert client.get('/api/v1/admin/overview').status_code == 401


@pytest.mark.parametrize('headers', [{}, {'Origin': 'null'}, {'Origin': 'https://evil.example'},
                                     {'Origin': ORIGIN, 'Sec-Fetch-Site': 'cross-site'}])
def test_login_requires_trusted_origin(client, sample_owner, headers):
    assert client.post('/api/v1/auth/login', json={'username': 'sample_owner', 'password': PASSWORD}, headers=headers).status_code == 403


@pytest.mark.parametrize('headers', [
    {}, {'Origin': ORIGIN}, {'Origin': ORIGIN, 'X-CSRF-Token': 'wrong'},
    {'Origin': 'https://evil.example', 'X-CSRF-Token': 'valid'},
])
def test_admin_mutations_reject_csrf_before_work(client, sample_owner, headers):
    csrf = sign_in(client).json()['csrf_token']
    if headers.get('X-CSRF-Token') == 'valid':
        headers = {**headers, 'X-CSRF-Token': csrf}
    assert client.post('/api/v1/admin/orders/cancel-expired', headers=headers).status_code == 403
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 403
    assert client.get('/api/v1/auth/session').status_code == 200


def test_expired_disabled_and_reset_credentials_invalidate_sessions(client, db_session, sample_owner):
    from app.services.owners import provision_owner
    sign_in(client)
    token = client.cookies.get(cookie_name())
    stored = db_session.get(OwnerSession, token_hash(token))
    stored.expires_at = utcnow() - timedelta(seconds=1)
    db_session.flush()
    assert client.get('/api/v1/admin/overview').status_code == 401
    sign_in(client)
    sample_owner.enabled = False
    db_session.flush()
    assert client.get('/api/v1/admin/overview').status_code == 401
    sample_owner.enabled = True
    db_session.flush()
    sign_in(client)
    provision_owner(db_session, 'sample_owner', 'SAMPLE-replacement-password', reset_password=True)
    db_session.flush()
    assert client.get('/api/v1/admin/overview').status_code == 401
    assert sign_in(client, password=PASSWORD).status_code == 401
    assert sign_in(client, password='SAMPLE-replacement-password').status_code == 200


def test_inactive_user_cannot_login_or_use_existing_session(client, db_session, sample_owner):
    sign_in(client)
    user = db_session.get(UserAccount, sample_owner.user_id)
    user.is_active = False
    db_session.flush()
    assert client.get('/api/v1/admin/overview').status_code == 401
    assert sign_in(client).status_code == 401


def test_login_rotates_existing_cookie_and_rejects_forged_cookie(client, sample_owner):
    sign_in(client)
    old = client.cookies.get(cookie_name())
    sign_in(client)
    assert client.cookies.get(cookie_name()) != old
    current = client.cookies.get(cookie_name())
    client.cookies.clear()
    client.cookies.set(cookie_name(), old)
    assert client.get('/api/v1/auth/session').status_code == 401
    client.cookies.set(cookie_name(), 'x' * 43)
    assert client.get('/api/v1/auth/session').status_code == 401
    client.cookies.set(cookie_name(), current)
    assert client.get('/api/v1/auth/session').status_code == 200


def test_login_rate_limit_and_generic_failure(client, sample_owner):
    wrong = sign_in(client, password='wrong').json()
    unknown = sign_in(client, username='unknown_owner', password='wrong').json()
    assert wrong == unknown == {'detail': 'Invalid username or password'}
    for _ in range(4):
        assert sign_in(client, password='wrong').status_code == 401
    result = sign_in(client)
    assert result.status_code == 429 and result.headers['retry-after'] == '900'


def test_ip_limit_applies_across_usernames(client):
    for i in range(20):
        assert sign_in(client, username=f'unknown_{i}', password='wrong').status_code == 401
    assert sign_in(client, username='another_owner').status_code == 429


def test_password_not_reflected_in_validation_error(client):
    password = 'SENSITIVE-' * 30
    response = sign_in(client, password=password)
    assert response.status_code == 422 and password not in response.text


def test_production_cookie_has_secure_host_prefix(client, sample_owner, monkeypatch):
    monkeypatch.setattr(settings, 'app_env', 'production')
    response = sign_in(client)
    cookie = response.headers['set-cookie']
    assert '__Host-alphazee_owner=' in cookie and 'Secure' in cookie and 'Domain=' not in cookie


def test_all_admin_routes_require_owner_session():
    from app.main import app
    routes = [r for r in app.routes if r.path.startswith('/api/v1/admin/')]
    assert len(routes) > 15
    for route in routes:
        assert any(dep.call is require_owner_session for dep in route.dependant.dependencies), route.path


def test_passwords_are_salted_and_no_default_owner_is_created(client, db_session):
    from app.services.passwords import hash_password, verify_password
    assert db_session.scalar(select(func.count()).select_from(OwnerCredential)) == 0
    a, b = hash_password(PASSWORD), hash_password(PASSWORD)
    assert a != b and PASSWORD not in a
    assert verify_password(PASSWORD, a) and not verify_password('wrong', a)
    assert not verify_password(PASSWORD, 'bad-format')


def test_concurrent_login_limits_share_atomic_database_counters(test_engine):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import delete
    from sqlalchemy.orm import Session
    import uuid
    from app.models.auth import OwnerLoginBucket
    from app.services.session_store import consume_login_attempt
    identity = 'sample_' + uuid.uuid4().hex
    address = 'sample-ip-' + uuid.uuid4().hex

    def attempt(_):
        with Session(test_engine) as db:
            return consume_login_attempt(db, identity, address)

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))
        assert results.count(False) == 5
        assert results.count(True) == 3
    finally:
        with Session(test_engine) as db:
            db.execute(delete(OwnerLoginBucket).where(OwnerLoginBucket.key_hash.in_(
                [token_hash('account:' + identity), token_hash('ip:' + address)])))
            db.commit()
