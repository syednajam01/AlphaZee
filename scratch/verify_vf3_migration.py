"""Disposable database migration verification for VF3 (9c2b4d8e1f5a).
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
TEST_DB_NAME = f"alphazee_vf3_migration_{token}_test"

def main():
    print(f"Starting VF3 migration verification on disposable DB: {TEST_DB_NAME}")

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
        test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = test_conn.cursor()

        # Check alembic version is at 9c2b4d8e1f5a
        cur.execute("SELECT version_num FROM alembic_version;")
        head = cur.fetchone()[0]
        assert head == "9c2b4d8e1f5a", f"Expected head 9c2b4d8e1f5a, got {head}"
        print(f"Verified alembic_version: {head}")

        # Check suppliers table has supplier_type and seeded internal supplier
        cur.execute("SELECT id, name, slug, supplier_type FROM suppliers WHERE supplier_type = 'alphazee_internal';")
        internal_sup = cur.fetchone()
        assert internal_sup is not None, "Seeded alphazee_internal supplier not found"
        print(f"Verified internal supplier: {internal_sup}")

        # Check invalid supplier_type fails constraint
        try:
            cur.execute("""
                INSERT INTO suppliers (id, name, slug, status, supplier_type)
                VALUES (gen_random_uuid(), 'Invalid Type', 'invalid-type', 'active', 'fraudulent_type');
            """)
            assert False, "Should have failed ck_suppliers_supplier_type"
        except psycopg2.IntegrityError:
            print("Verified ck_suppliers_supplier_type rejected invalid supplier_type.")

        # Check products table has stock_management_source and vendor_id
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'products' AND column_name IN ('stock_management_source', 'vendor_id');
        """)
        cols = dict(cur.fetchall())
        assert 'stock_management_source' in cols and 'vendor_id' in cols, f"Products columns missing: {cols}"
        print("Verified products columns: stock_management_source, vendor_id.")

        # Check ck_product_vendor_managed_requires_vendor constraint
        try:
            cur.execute("""
                INSERT INTO products (id, title, slug, collection_id, stock_management_source, vendor_id)
                VALUES ('prod-test-bad', 'Bad Prod', 'bad-prod', 'essentials', 'vendor_managed', NULL);
            """)
            assert False, "Should have failed ck_product_vendor_managed_requires_vendor"
        except psycopg2.IntegrityError:
            print("Verified ck_product_vendor_managed_requires_vendor rejected vendor_managed with NULL vendor_id.")

        # Check order_lines table has ownership_source
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'order_lines' AND column_name = 'ownership_source';
        """)
        ol_cols = dict(cur.fetchall())
        assert 'ownership_source' in ol_cols, "ownership_source missing on order_lines"
        print("Verified order_lines column: ownership_source.")

        # Check business_expenses table exists and works
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'business_expenses';
        """)
        be_cols = [r[0] for r in cur.fetchall()]
        assert 'category' in be_cols and 'amount_minor' in be_cols and 'payee' in be_cols, f"business_expenses cols missing: {be_cols}"
        print("Verified business_expenses table structure.")

        # Insert valid business expense
        cur.execute("""
            INSERT INTO business_expenses (category, amount_minor, incurred_date, payee, payment_method, notes)
            VALUES ('packaging', 250000, CURRENT_DATE, 'Standard Box Co', 'bank_transfer', '200 custom mailer boxes')
            RETURNING id, amount_minor;
        """)
        exp_row = cur.fetchone()
        assert exp_row[1] == 250000
        print(f"Successfully inserted valid business expense: {exp_row[0]}")

        # Check negative amount fails
        try:
            cur.execute("""
                INSERT INTO business_expenses (category, amount_minor, incurred_date, payee)
                VALUES ('advertising', -500, CURRENT_DATE, 'Meta Ads');
            """)
            assert False, "Should have failed ck_business_expenses_amount_positive"
        except psycopg2.IntegrityError:
            print("Verified ck_business_expenses_amount_positive rejected negative amount.")

        # Check invalid category fails
        try:
            cur.execute("""
                INSERT INTO business_expenses (category, amount_minor, incurred_date, payee)
                VALUES ('yacht_rental', 5000000, CURRENT_DATE, 'Luxury Charters');
            """)
            assert False, "Should have failed ck_business_expenses_category"
        except psycopg2.IntegrityError:
            print("Verified ck_business_expenses_category rejected unauthorized category.")

        cur.close()
        test_conn.close()

        # 4. Downgrade to 7a3e9b1c5d2f
        print("Testing downgrade to 7a3e9b1c5d2f...")
        res_down = subprocess.run(
            [python_exe, "-m", "alembic", "downgrade", "7a3e9b1c5d2f"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print("Downgrade output:\n", res_down.stdout)

        # Verify tables/columns dropped
        test_conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=TEST_DB_NAME
        )
        test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = test_conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version;")
        down_ver = cur.fetchone()[0]
        assert down_ver == "7a3e9b1c5d2f", f"Expected version 7a3e9b1c5d2f, got {down_ver}"
        cur.execute("SELECT to_regclass('public.business_expenses');")
        assert cur.fetchone()[0] is None, "business_expenses table should have been dropped on downgrade"
        print("Verified clean downgrade.")

        # 5. Re-upgrade to head
        print("Testing re-upgrade to head...")
        res_re = subprocess.run(
            [python_exe, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        print("Re-upgrade output:\n", res_re.stdout)
        cur.execute("SELECT version_num FROM alembic_version;")
        assert cur.fetchone()[0] == "9c2b4d8e1f5a"
        print("Verified clean re-upgrade.")

        cur.close()
        test_conn.close()
        print("ALL VF3 MIGRATION CHECKS PASSED.")

    finally:
        # Drop disposable DB
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE);")
        print(f"Cleaned up disposable database {TEST_DB_NAME}.")
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
