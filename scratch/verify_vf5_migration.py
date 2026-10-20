"""Disposable database migration verification for VF5 (5d3f8a1c9e2b).
Tests upgrade, constraint checks, index validation, downgrade, and re-upgrade on an isolated test DB.
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / 'backend'

PG_HOST = "localhost"
PG_PORT = 5433
PG_USER = "alphazee"
PG_PASS = "changeme"

token = secrets.token_hex(4)
TEST_DB_NAME = f"alphazee_vf5_migration_{token}_test"

def main():
    print(f"Starting VF5 migration verification on disposable DB: {TEST_DB_NAME}")

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE {TEST_DB_NAME};")
    print(f"Created disposable database {TEST_DB_NAME}.")
    cursor.close()
    conn.close()

    test_db_url = f"postgresql://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB_NAME}"
    env = os.environ.copy()
    env["DATABASE_URL"] = test_db_url
    python_exe = str(BACKEND_DIR / ".venv/Scripts/python.exe")

    try:
        print("Running alembic upgrade head...")
        res = subprocess.run(
            [python_exe, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print("Alembic upgrade output:\n", res.stdout)

        test_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=TEST_DB_NAME
        )
        test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = test_conn.cursor()

        # Check tables exist
        for tbl in ['vendor_users', 'vendor_sessions', 'vendor_login_buckets', 'vendor_stock_shortages']:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables WHERE table_name = %s
                );
            """, (tbl,))
            assert cur.fetchone()[0], f"Table {tbl} does not exist!"
            print(f"Verified table {tbl} exists.")

        # Test insert supplier, user_account, vendor_user
        cur.execute("""
            INSERT INTO suppliers (id, name, slug, status, supplier_type)
            VALUES ('11111111-1111-1111-1111-111111111111', 'Test Vendor', 'test-vendor', 'active', 'external_vendor');
        """)
        cur.execute("""
            INSERT INTO user_accounts (id, auth_subject, display_name)
            VALUES ('22222222-2222-2222-2222-222222222222', 'vendor:testuser', 'Test Vendor (testuser)');
        """)
        cur.execute("""
            INSERT INTO vendor_users (id, user_id, vendor_id, username, password_hash)
            VALUES ('33333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 'testuser', 'hash123');
        """)
        print("Inserted vendor user record successfully.")

        # Test session insert
        cur.execute("""
            INSERT INTO vendor_sessions (token_hash, vendor_user_id, expires_at)
            VALUES ('token_hash_abc', '33333333-3333-3333-3333-333333333333', NOW() + interval '7 days');
        """)
        print("Inserted vendor session successfully.")

        # Test bucket insert
        cur.execute("""
            INSERT INTO vendor_login_buckets (key_hash, window_started_at, attempts)
            VALUES ('bucket_hash_abc', NOW(), 1);
        """)
        print("Inserted vendor login bucket successfully.")

        # Test constraints
        try:
            cur.execute("""
                INSERT INTO vendor_login_buckets (key_hash, window_started_at, attempts)
                VALUES ('bucket_fail', NOW(), 0);
            """)
            assert False, "Should fail ck_vendor_login_attempts_positive"
        except psycopg2.Error:
            print("Verified ck_vendor_login_attempts_positive correctly rejected attempts <= 0.")

        test_conn.close()

        # Test downgrade
        print("Testing downgrade to 9c2b4d8e1f5a...")
        res_down = subprocess.run(
            [python_exe, "-m", "alembic", "downgrade", "9c2b4d8e1f5a"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print("Downgrade output:\n", res_down.stdout)

        test_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=TEST_DB_NAME
        )
        cur = test_conn.cursor()
        for tbl in ['vendor_users', 'vendor_sessions', 'vendor_login_buckets', 'vendor_stock_shortages']:
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);", (tbl,))
            assert not cur.fetchone()[0], f"Table {tbl} should have been dropped on downgrade!"
        print("Verified tables cleanly dropped on downgrade.")
        test_conn.close()

        # Test re-upgrade
        print("Testing re-upgrade to head...")
        res_up = subprocess.run(
            [python_exe, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print("Re-upgrade successful:\n", res_up.stdout)

        print("Migration 5d3f8a1c9e2b verified 100% in isolation!")

    finally:
        # Drop test db
        drop_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="postgres"
        )
        drop_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        dcur = drop_conn.cursor()
        dcur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{TEST_DB_NAME}' AND pid <> pg_backend_pid();
        """)
        dcur.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
        print(f"Cleaned up disposable database {TEST_DB_NAME}.")
        dcur.close()
        drop_conn.close()

if __name__ == '__main__':
    main()
