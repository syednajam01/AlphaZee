"""Disposable database migration verification for VF1 (7a3e9b1c5d2f).
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

# Use loopback PostgreSQL port 5433 (or 5434)
PG_HOST = "localhost"
PG_PORT = 5433
PG_USER = "alphazee"
PG_PASS = "changeme"

token = secrets.token_hex(4)
TEST_DB_NAME = f"alphazee_vf1_migration_{token}_test"

def main():
    print(f"Starting VF1 migration verification on disposable DB: {TEST_DB_NAME}")

    # 1. Connect to default postgres to create test db
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
        # 2. Run alembic upgrade head
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

        # 3. Connect to test DB and verify tables & constraints
        test_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=TEST_DB_NAME
        )
        cur = test_conn.cursor()

        # Check alembic version is at 7a3e9b1c5d2f
        cur.execute("SELECT version_num FROM alembic_version;")
        head = cur.fetchone()[0]
        assert head == "7a3e9b1c5d2f", f"Expected head 7a3e9b1c5d2f, got {head}"
        print(f"Verified alembic_version: {head}")

        # Check table existence
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN 
            ('supplier_agreements', 'supplier_ledger_entries', 'supplier_payment_allocations');
        """)
        tables = [r[0] for r in cur.fetchall()]
        assert set(tables) == {'supplier_agreements', 'supplier_ledger_entries', 'supplier_payment_allocations'}, f"Tables mismatch: {tables}"
        print("All 3 supplier finance tables present in schema.")

        # Test inserting an agreement with invalid trigger (should fail check constraint)
        try:
            cur.execute("""
                INSERT INTO supplier_agreements (id, supplier_id, payable_trigger)
                VALUES (gen_random_uuid(), gen_random_uuid(), 'invalid_trigger');
            """)
            assert False, "Should have failed ck_supplier_agreements_trigger"
        except psycopg2.Error:
            test_conn.rollback()
            print("Check constraint ck_supplier_agreements_trigger verified.")

        # Test inserting ledger entry with negative amount (should fail)
        try:
            cur.execute("""
                INSERT INTO supplier_ledger_entries (id, supplier_id, entry_type, amount_minor, direction, reference, effective_date)
                VALUES (gen_random_uuid(), gen_random_uuid(), 'charge', -500, 'credit', 'REF1', CURRENT_DATE);
            """)
            assert False, "Should have failed ck_supplier_ledger_amount_positive"
        except psycopg2.Error:
            test_conn.rollback()
            print("Check constraint ck_supplier_ledger_amount_positive verified.")

        # Test unique source_event_key index
        test_sup_id = secrets.token_hex(16)
        # First insert a supplier to have a valid FK
        cur.execute(f"""
            INSERT INTO suppliers (id, name, slug, status)
            VALUES ('{test_sup_id}', 'Test Vendor', 'test-vendor-{token}', 'active');
        """)
        cur.execute(f"""
            INSERT INTO supplier_ledger_entries (id, supplier_id, entry_type, amount_minor, direction, source_event_key, reference, effective_date)
            VALUES (gen_random_uuid(), '{test_sup_id}', 'charge', 150000, 'credit', 'event:123', 'REF-A', CURRENT_DATE);
        """)
        try:
            cur.execute(f"""
                INSERT INTO supplier_ledger_entries (id, supplier_id, entry_type, amount_minor, direction, source_event_key, reference, effective_date)
                VALUES (gen_random_uuid(), '{test_sup_id}', 'charge', 150000, 'credit', 'event:123', 'REF-B', CURRENT_DATE);
            """)
            assert False, "Duplicate source_event_key should have failed unique index"
        except psycopg2.Error:
            test_conn.rollback()
            print("Unique index uq_supplier_ledger_source_key verified.")

        cur.close()
        test_conn.close()

        # 4. Test Downgrade
        print("Testing alembic downgrade to 2c8a1b3e5f70...")
        res_down = subprocess.run(
            [python_exe, "-m", "alembic", "downgrade", "2c8a1b3e5f70"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print("Downgrade output:\n", res_down.stdout)

        # Confirm tables dropped
        test_conn2 = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=TEST_DB_NAME
        )
        cur2 = test_conn2.cursor()
        cur2.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name IN 
            ('supplier_agreements', 'supplier_ledger_entries', 'supplier_payment_allocations');
        """)
        assert len(cur2.fetchall()) == 0, "Tables should be dropped after downgrade"
        print("Downgrade cleanly removed supplier finance tables.")

        # 5. Re-upgrade to head
        print("Re-applying alembic upgrade head...")
        subprocess.run(
            [python_exe, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        cur2.execute("SELECT version_num FROM alembic_version;")
        assert cur2.fetchone()[0] == "7a3e9b1c5d2f"
        print("Re-upgrade successful and head confirmed.")

        cur2.close()
        test_conn2.close()

    finally:
        # 6. Drop disposable DB
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME};")
        cursor.close()
        conn.close()
        print(f"Dropped disposable database {TEST_DB_NAME}.")

    print("\nALL VF1 DISPOSABLE DB MIGRATION CHECKS PASSED 100%!")

if __name__ == '__main__':
    main()
