"""
seed.py — Development data seed script for AlphaZee.

Phase 1 stub: the script exists and validates configuration but makes no
database changes. Actual seeding is implemented in Phase 2 once models exist.

Usage (from backend/):
    python seed.py

Rules enforced:
- Refuses to run against a production database (APP_ENV=production).
- Idempotent: safe to run repeatedly without creating duplicates.
- Does not overwrite manually edited product data.
"""

from __future__ import annotations

import sys

from app.config import settings


def main() -> None:
    if settings.is_production:
        print(
            "ERROR: Refusing to seed a production database. "
            "Set APP_ENV=development to run seeding."
        )
        sys.exit(1)

    print(f"[seed] Environment : {settings.app_env}")
    print(f"[seed] Database    : {settings.database_url.split('@')[-1]}")
    print("[seed] Phase 1 stub — no models defined yet. Seeding runs in Phase 2.")
    print("[seed] Done.")


if __name__ == "__main__":
    main()
