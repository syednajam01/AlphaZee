"""Local-only operator command. Passwords never appear in arguments or output."""
import argparse
from getpass import getpass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.engine import make_url
from app.config import settings
from app.database import SessionLocal
from app.services.owners import provision_owner


def main():
    parser = argparse.ArgumentParser(description='Create an owner, or explicitly reset a password and revoke sessions.')
    parser.add_argument('username')
    parser.add_argument('--reset-password', action='store_true')
    parser.add_argument('--allow-short-local-password', action='store_true', help='Explicit development-only credential; cannot log in in production')
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error('Use an interactive terminal so passwords can be entered without echo.')
    target = make_url(settings.database_url)
    print(f'Owner database: {target.host}:{target.port or 5432}/{target.database}')
    password = getpass('New owner password: ')
    if password != getpass('Repeat password: '):
        parser.error('Passwords do not match.')
    with SessionLocal() as db:
        try:
            provision_owner(db, args.username, password, reset_password=args.reset_password,
                            allow_short_local=args.allow_short_local_password)
            db.commit()
        except ValueError as error:
            db.rollback()
            parser.error(str(error))
    print('Owner credentials saved. Password resets revoke all existing sessions for that owner.')


if __name__ == '__main__':
    main()
