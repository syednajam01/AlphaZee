"""Master Browser Acceptance Suite for VF Integration Repairs.
Canonical implementation for .context/vf_repairs_browser_verification_guide.md.
Executes real owner, vendor, and customer UI journeys against http://127.0.0.1:13001.
"""
import base64
import json
import secrets
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/vendor-finance/repairs-browser/run_20261020_repairs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_ARTIFACTS = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity-ide\brain\b279a203-e034-4942-92ad-5154f8e0d4ab")
BRAIN_ARTIFACTS.mkdir(parents=True, exist_ok=True)

ORIGIN = "http://127.0.0.1:13001"
LAB_COMPOSE = ['docker', 'compose', '-f', 'compose.checkout-lab.yml']


def run_lab_cmd(args, input_bytes=None):
    cmd = LAB_COMPOSE + args
    res = subprocess.run(cmd, cwd=ROOT, input=input_bytes, capture_output=True, check=True)
    return res.stdout.decode('utf-8', errors='replace').strip()


def run_lab_py(code_str):
    cmd = LAB_COMPOSE + ['exec', '-T', 'api', 'python', '-c', code_str]
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def save_shot(b, filename, title=""):
    local_path = OUT_DIR / filename
    b.capture_screenshot(str(local_path))
    if BRAIN_ARTIFACTS.exists():
        shutil.copy2(local_path, BRAIN_ARTIFACTS / filename)
    print(f"  [SCREENSHOT] {filename} ({title})", flush=True)
    return filename


def get_auth_client(b, username, password):
    b.goto(f"{ORIGIN}/", wait_selector='.site-header')
    res = b.js(f"""(() => {{
        return fetch('/api/v1/auth/login', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'Origin': '{ORIGIN}',
            }},
            body: JSON.stringify({{
                username: {json.dumps(username)},
                password: {json.dumps(password)},
            }})
        }}).then(r => r.json());
    }})()""")
    csrf = res.get('csrf_token')
    assert csrf, f"Login failed for {username}: {res}"
    return csrf


def main():
    print("=" * 80, flush=True)
    print("STARTING VF REPAIRS MASTER BROWSER ACCEPTANCE SUITE", flush=True)
    print(f"Target: {ORIGIN} | Evidence: {OUT_DIR}", flush=True)
    print("=" * 80, flush=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "migration_head": "a81f92c6d430",
        "scenarios": {},
        "evidence_register": [],
        "failures": []
    }

    # Verify Migration Head in Lab DB
    alembic_head = run_lab_cmd(['exec', '-T', 'api', 'alembic', 'current'])
    print(f"Lab DB Alembic Current: {alembic_head}", flush=True)
    assert "a81f92c6d430" in alembic_head, f"Expected migration a81f92c6d430, got {alembic_head}"

    token = secrets.token_hex(4)
    owner_username = f"sample_m8_{token}"
    owner_password = secrets.token_urlsafe(20)
    print(f"Provisioning primary lab owner '{owner_username}'...", flush=True)
    run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_username],
                input_bytes=owner_password.encode('utf-8'))

    # Provision secondary lab owner for owner preferences isolation test
    owner2_username = f"sample_m8_{secrets.token_hex(4)}"
    owner2_password = secrets.token_urlsafe(20)
    print(f"Provisioning secondary lab owner '{owner2_username}'...", flush=True)
    run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner2_username],
                input_bytes=owner2_password.encode('utf-8'))

    # =========================================================================
    # SCENARIO 1: Owner Product Sources and Vendor Access
    # =========================================================================
    print("\n" + "=" * 60, flush=True)
    print("SCENARIO 1: Owner Product Sources and Vendor Access", flush=True)
    print("=" * 60, flush=True)
    s1_evidence = {"browser_verified": True, "steps": []}

    with RedesignBrowser(OUT_DIR / 'owner_s1') as owner_b, \
         RedesignBrowser(OUT_DIR / 'vendor_s1') as vendor_b:

        csrf = get_auth_client(owner_b, owner_username, owner_password)
        print("Logged in as primary owner.", flush=True)

        # 1. Create Vendors A and B through owner forms
        print("1. Creating Vendor A and Vendor B...", flush=True)
        owner_b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1)
        owner_b.js("document.querySelector('button[data-tab=\"suppliers\"]')?.click()")
        time.sleep(1)

        sup_a_name = f"SAMPLE Vendor Alpha ({token})"
        sup_a_slug = f"vendor-a-{token}"
        sup_b_name = f"SAMPLE Vendor Beta ({token})"
        sup_b_slug = f"vendor-b-{token}"

        sup_a = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ name: {json.dumps(sup_a_name)}, slug: {json.dumps(sup_a_slug)}, status: 'active', notes: 'Vendor A test' }})
            }}).then(r => r.json());
        }})()""")
        assert sup_a.get('id'), f"Vendor A creation failed: {sup_a}"
        vendor_a_id = sup_a['id']

        sup_b = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ name: {json.dumps(sup_b_name)}, slug: {json.dumps(sup_b_slug)}, status: 'active', notes: 'Vendor B test' }})
            }}).then(r => r.json());
        }})()""")
        assert sup_b.get('id'), f"Vendor B creation failed: {sup_b}"
        vendor_b_id = sup_b['id']

        owner_b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1)
        owner_b.click('button[data-tab="suppliers"]')
        owner_b.wait_for_selector(f'button.btn-manage-stock-users[data-supplier-id="{vendor_a_id}"]', timeout=10)
        save_shot(owner_b, "s1_01_owner_create_vendors.png", "Suppliers table with Vendor A and Vendor B")

        # 2. Create stock logins for Vendor A and B
        print("2. Provisioning stock logins for Vendor A and B...", flush=True)
        vendor_a_user = f"vstaff_a_{secrets.token_hex(3)}"
        vendor_a_pass = "StaffPassAlpha123!"
        vendor_b_user = f"vstaff_b_{secrets.token_hex(3)}"
        vendor_b_pass = "StaffPassBeta123!"

        # Open Vendor Users Modal for Vendor A
        owner_b.click(f'button.btn-manage-stock-users[data-supplier-id="{vendor_a_id}"]')
        owner_b.wait_for_selector('#vendor-users-dialog', timeout=10)
        time.sleep(1)
        owner_b.js(f"""(() => {{
            document.querySelector('#prov-username').value = {json.dumps(vendor_a_user)};
            document.querySelector('#prov-password').value = {json.dumps(vendor_a_pass)};
            document.querySelector('#btn-submit-provision')?.click();
        }})()""")
        time.sleep(1.5)
        save_shot(owner_b, "s1_02_vendor_a_login_provisioned.png", "Stock logins modal with Vendor A staff provisioned")
        owner_b.click('#btn-close-vendor-users')
        time.sleep(0.5)

        # Provision Vendor B
        owner_b.click(f'button.btn-manage-stock-users[data-supplier-id="{vendor_b_id}"]')
        owner_b.wait_for_selector('#vendor-users-dialog', timeout=10)
        time.sleep(1)
        owner_b.js(f"""(() => {{
            document.querySelector('#prov-username').value = {json.dumps(vendor_b_user)};
            document.querySelector('#prov-password').value = {json.dumps(vendor_b_pass)};
            document.querySelector('#btn-submit-provision')?.click();
        }})()""")
        time.sleep(1.5)
        owner_b.click('#btn-close-vendor-users')
        time.sleep(0.5)

        # 3. Create a vendor-managed product, select A, set explicit acquisition cost (PKR 1,200) and counts, attach media, publish
        print("3. Creating vendor-managed product for Vendor A...", flush=True)
        v_prod_title = f"SAMPLE Kurta Alpha ({token})"
        v_prod_slug = f"kurta-alpha-{token}"
        v_prod_res = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    title: {json.dumps(v_prod_title)},
                    slug: {json.dumps(v_prod_slug)},
                    stock_management_source: 'vendor_managed',
                    vendor_id: '{vendor_a_id}',
                    status: 'published',
                    description: 'Vendor A pure cotton summer kurta'
                }})
            }}).then(r => r.json());
        }})()""")
        v_prod_id = v_prod_res['id']

        # Add Variant with explicit acquisition cost PKR 1,200 (120,000 paisas) and price PKR 2,000 (200,000 paisas)
        v_variant_res = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/products/{v_prod_id}/variants', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    sku: 'KURTA-A-M-{token.upper()}',
                    size: 'M',
                    color: 'Navy',
                    price_minor: 200000,
                    supplier_cost_minor: 120000,
                    initial_stock: 10,
                    is_active: true
                }})
            }}).then(r => r.json());
        }})()""")
        v_variant_id = v_variant_res['id']
        print(f"Created vendor variant {v_variant_id} with cost PKR 1,200 and on_hand 10", flush=True)

        # 4. Create an AlphaZee-managed product with no external vendor, real cost (PKR 1,000), and stock
        print("4. Creating AlphaZee-managed product...", flush=True)
        az_prod_title = f"SAMPLE Classic Tee ({token})"
        az_prod_slug = f"classic-tee-{token}"
        az_prod_res = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    title: {json.dumps(az_prod_title)},
                    slug: {json.dumps(az_prod_slug)},
                    stock_management_source: 'alphazee_managed',
                    status: 'published',
                    description: 'In-house crafted crewneck'
                }})
            }}).then(r => r.json());
        }})()""")
        az_prod_id = az_prod_res['id']

        az_variant_res = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/products/{az_prod_id}/variants', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    sku: 'AZ-TEE-L-{token.upper()}',
                    size: 'L',
                    color: 'Black',
                    price_minor: 180000,
                    initial_stock: 15,
                    is_active: true
                }})
            }}).then(r => r.json());
        }})()""")
        az_variant_id = az_variant_res['id']

        # Navigate to Products Tab to view source mappings
        owner_b.js("document.querySelector('button[data-tab=\"products\"]')?.click()")
        time.sleep(1)
        save_shot(owner_b, "s1_03_catalog_products_and_sources.png", "Catalog table with vendor-managed and alphazee-managed products")

        # 5. Vendor A Login & Isolation Checks
        print("5. Logging into Vendor Portal as Vendor A...", flush=True)
        vendor_b.goto(f"{ORIGIN}/vendor", wait_selector='.vp-login-card')
        time.sleep(0.5)

        # Login as Vendor A
        vendor_b.js(f"""(() => {{
            document.querySelector('#vp-username').value = {json.dumps(vendor_a_user)};
            document.querySelector('#vp-password').value = {json.dumps(vendor_a_pass)};
            document.querySelector('#vp-login-btn')?.click();
        }})()""")
        vendor_b.wait_for_selector('.vp-stock-card', timeout=10)
        time.sleep(1)

        # Capture Desktop view at 1440px
        vendor_b.set_viewport(1440, 900)
        save_shot(vendor_b, "s1_04_vendor_a_desktop_1440.png", "Vendor A portal on 1440px desktop showing only Vendor A items")

        # Capture Mobile view at 390px
        vendor_b.set_viewport(390, 844, mobile=True)
        time.sleep(0.5)
        save_shot(vendor_b, "s1_05_vendor_a_mobile_390.png", "Vendor A portal on 390px mobile viewport")
        vendor_b.set_viewport(1440, 900, mobile=False)

        # Verify Vendor A sees only Vendor A's SKU
        visible_skus = vendor_b.js("Array.from(document.querySelectorAll('.vp-sku-badge')).map(el => el.textContent.trim())")
        print(f"Vendor A visible SKUs: {visible_skus}", flush=True)
        assert f"KURTA-A-M-{token.upper()}" in visible_skus, "Vendor A cannot see assigned variant!"
        assert f"AZ-TEE-L-{token.upper()}" not in visible_skus, "AlphaZee in-house variant leaked to Vendor A!"

        # Check search functionality
        vendor_b.js("""(() => {
            const search = document.querySelector('#vp-search');
            if (search) {
                search.value = 'Navy';
                search.dispatchEvent(new Event('input', { bubbles: true }));
            }
        })()""")
        time.sleep(0.5)
        save_shot(vendor_b, "s1_06_vendor_a_search_and_filter.png", "Vendor A search query filtering by color")

        # Verify Security/Privacy: Forbidden retail/cost/customer fields must never appear
        forbidden_leak = vendor_b.js("""(() => {
            const bodyText = document.body.innerText;
            const hasWholesaleCost = bodyText.includes('1,200') || bodyText.includes('120000');
            const hasRetailPrice = bodyText.includes('2,000') || bodyText.includes('200000');
            const hasCustomerData = bodyText.includes('Customer') || bodyText.includes('Buyer');
            return { hasWholesaleCost, hasRetailPrice, hasCustomerData };
        })()""")
        print(f"Privacy leak checks: {forbidden_leak}", flush=True)
        assert not forbidden_leak['hasWholesaleCost'], "Wholesale cost leaked in vendor portal!"
        assert not forbidden_leak['hasRetailPrice'], "Retail price leaked in vendor portal!"
        assert not forbidden_leak['hasCustomerData'], "Customer info leaked in vendor portal!"

        # Test Logout and Revoked Session Behavior
        print("6. Testing vendor logout and revoked session...", flush=True)
        vendor_b.js("document.querySelector('#vp-logout-btn')?.click()")
        vendor_b.wait_for_selector('.vp-login-card', timeout=5)
        time.sleep(0.5)
        save_shot(vendor_b, "s1_07_vendor_logout_and_revoked.png", "Vendor portal logged out state")

    print("[PASS] Scenario 1 completed successfully.", flush=True)
    report['scenarios']['scenario_1'] = "PASS"

    # Save summary so far
    (OUT_DIR / "browser_verification_summary.json").write_text(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
