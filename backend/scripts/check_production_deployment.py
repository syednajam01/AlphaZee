"""Fail closed before a production migration starts with example settings."""
import os
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def main() -> None:
    if os.environ.get('APP_ENV') != 'production':
        raise SystemExit('Production deployment requires APP_ENV=production.')
    if os.environ.get('DEBUG', '').lower() != 'false':
        raise SystemExit('Production deployment requires DEBUG=false.')
    if os.environ.get('TEST_CHECKOUT_ENABLED', '').lower() != 'false':
        raise SystemExit('Production deployment requires TEST_CHECKOUT_ENABLED=false.')

    domain = os.environ.get('SITE_DOMAIN', '').strip().lower()
    parsed = urlsplit(f'https://{domain}')
    if (not domain or parsed.netloc != domain or not parsed.hostname or
            parsed.username or parsed.password or
            parsed.path or parsed.query or parsed.fragment or
            domain.endswith('.example.com') or domain == 'example.com' or
            parsed.hostname in {'localhost', '127.0.0.1'}):
        raise SystemExit('Set SITE_DOMAIN to the real public DNS name.')
    if os.environ.get('ALLOWED_ORIGINS') != f'https://{domain}':
        raise SystemExit('ALLOWED_ORIGINS must be the exact HTTPS site origin.')

    try:
        database = make_url(os.environ['DATABASE_URL'])
    except (KeyError, ValueError, ArgumentError) as error:
        raise SystemExit('Set a valid production DATABASE_URL.') from error
    if (database.get_backend_name() != 'postgresql' or database.host != 'db' or
            database.port != 5432 or not database.database or not database.username or
            not database.password or len(database.password) < 20 or
            'REPLACE' in database.password.upper() or 'CHANGEME' in database.password.upper()):
        raise SystemExit('Use a strong production PostgreSQL URL pointing to db:5432.')

    print('Production deployment configuration passed preflight.')


if __name__ == '__main__':
    main()
