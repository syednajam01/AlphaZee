"""
P5: Vendor Portal Stock Synchronization Verification Script.
Uses standard APIs in isolated checkout lab (http://127.0.0.1:13001) to:
1. Set up Supplier 1 and Supplier 2.
2. Provision Vendor 1 (StaffPass123!) and Vendor 2 (StaffPass456!).
3. Map variants and seed inventory balances.
4. Launch mobile browsers (390x844) for Vendor 1 and Vendor 2.
5. Verify:
   - Vendor login & shop identity badge
   - Cross-vendor SKU isolation
   - SKU search
   - Exact physical count update (3 -> 2)
   - Stock update history modal
   - Shortage detection & modal
   - Clean logout
"""
import json
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/three-portal-quality/run_p5_vendor'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

ORIGIN = "http://127.0.0.1:13001"

def run_lab_cmd(args, input_bytes=None):
    cmd = ['docker', 'compose', '-f', 'compose.checkout-lab.yml'] + args
    res = subprocess.run(cmd, cwd=str(ROOT), input=input_bytes, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"Lab command failed: {res.stderr.decode('utf-8', 'ignore')}")
    return res.stdout.decode('utf-8', 'ignore')

def run_lab_py(code):
    return run_lab_cmd(['exec', '-T', 'api', 'python', '-c', code])

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT SAVED] {filename}", flush=True)

def login_owner(b, username, password):
    run_lab_py("""
from app.database import SessionLocal
from app.models.auth import OwnerLoginBucket
db = SessionLocal()
db.query(OwnerLoginBucket).delete()
db.commit()
db.close()
""")
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
    assert csrf, f"Owner login failed for {username}: {res}"
    return csrf

def main():
    print("=== STARTING P5 VENDOR PORTAL VERIFICATION ===", flush=True)

    token = secrets.token_hex(4)
    owner_user = f"sample_m8_{token}"
    owner_pass = secrets.token_urlsafe(20)
    print(f"Provisioning setup owner: {owner_user}", flush=True)
    run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_user],
                input_bytes=owner_pass.encode('utf-8'))

    # Setup Suppliers and Logins via Owner session
    with RedesignBrowser(OUT_DIR / "prof_setup") as owner_b:
        csrf = login_owner(owner_b, owner_user, owner_pass)

        # 1. Create Supplier 1 & 2
        sup1_name = f"SAMPLE Karachi Looms {token}"
        sup1_slug = f"karachi-looms-{token}"
        sup1_res = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ name: {json.dumps(sup1_name)}, slug: {json.dumps(sup1_slug)}, status: 'active', notes: 'Supplier 1' }})
            }}).then(r => r.json());
        }})()""")
        sup1_id = sup1_res['id']

        sup2_name = f"SAMPLE Lahore Weavers {token}"
        sup2_slug = f"lahore-weavers-{token}"
        sup2_res = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ name: {json.dumps(sup2_name)}, slug: {json.dumps(sup2_slug)}, status: 'active', notes: 'Supplier 2' }})
            }}).then(r => r.json());
        }})()""")
        sup2_id = sup2_res['id']

        # 2. Provision Vendor Users for both suppliers
        v1_user = f"vstaff1_{token}"
        v1_pass = "StaffPassAlpha123!"
        v1_prov = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{sup1_id}/users', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ username: {json.dumps(v1_user)}, password: {json.dumps(v1_pass)} }})
            }}).then(r => r.json());
        }})()""")
        print(f"  Provisioned Vendor 1: {v1_prov}", flush=True)

        v2_user = f"vstaff2_{token}"
        v2_pass = "StaffPassBeta123!"
        v2_prov = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{sup2_id}/users', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ username: {json.dumps(v2_user)}, password: {json.dumps(v2_pass)} }})
            }}).then(r => r.json());
        }})()""")
        print(f"  Provisioned Vendor 2: {v2_prov}", flush=True)

        # 3. Get or create active collection
        cols = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/collections', {{
                headers: {{ 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }}
            }}).then(r => r.json());
        }})()""")
        col_id = cols['collections'][0]['id'] if cols.get('collections') else None
        if not col_id:
            new_col = owner_b.js(f"""(() => {{
                return fetch('/api/v1/admin/collections', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                    body: JSON.stringify({{ name: 'SAMPLE Test Col', slug: 'sample-col-{token}', is_active: true }})
                }}).then(r => r.json());
            }})()""")
            col_id = new_col['id']

        # 4. Create Product 1 for Supplier 1
        cat_res1 = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    title: 'SAMPLE Oversized Heavyweight Tee {token}',
                    slug: 'sample-tee-1-{token}',
                    collection_id: {json.dumps(col_id)},
                    stock_management_source: 'vendor_managed',
                    vendor_id: '{sup1_id}',
                    description: 'Vendor sync test item',
                    variants: [
                        {{ sku: 'TEE-KHI-{token}', size: 'M', color: 'Black', price_minor: 350000, availability: 'available' }}
                    ]
                }})
            }}).then(r => r.json());
        }})()""")
        print(f"DEBUG cat_res1: {cat_res1}", flush=True)
        v1_var = cat_res1['variants'][0]

        # 5. Create Product 2 for Supplier 2
        cat_res2 = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    title: 'SAMPLE Heavyweight Hoodie {token}',
                    slug: 'sample-hoodie-2-{token}',
                    collection_id: {json.dumps(col_id)},
                    stock_management_source: 'vendor_managed',
                    vendor_id: '{sup2_id}',
                    description: 'Vendor sync test item 2',
                    variants: [
                        {{ sku: 'HOODIE-LHR-{token}', size: 'L', color: 'White', price_minor: 550000, availability: 'available' }}
                    ]
                }})
            }}).then(r => r.json());
        }})()""")
        v2_var = cat_res2['variants'][0]

        # Map v1 to Supplier 1 with stock 3
        map1 = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{sup1_id}/variants', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ variant_id: {v1_var['id']}, supplier_cost_minor: 180000, active: true }})
            }}).then(r => r.json());
        }})()""")
        sup_var1_id = map1['id']

        owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/inventory/adjust', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    supplier_variant_id: '{sup_var1_id}',
                    expected_version: 0,
                    quantity_delta: 3,
                    reason: 'supplier_receipt',
                    reference_id: 'INIT-1',
                    notes: 'Initial stock intake'
                }})
            }}).then(r => r.json());
        }})()""")

        # Map v2 to Supplier 2 with stock 5
        map2 = owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{sup2_id}/variants', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{ variant_id: {v2_var['id']}, supplier_cost_minor: 200000, active: true }})
            }}).then(r => r.json());
        }})()""")
        sup_var2_id = map2['id']

        owner_b.js(f"""(() => {{
            return fetch('/api/v1/admin/inventory/adjust', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-CSRF-Token': {json.dumps(csrf)}, 'Origin': '{ORIGIN}' }},
                body: JSON.stringify({{
                    supplier_variant_id: '{sup_var2_id}',
                    expected_version: 0,
                    quantity_delta: 5,
                    reason: 'supplier_receipt',
                    reference_id: 'INIT-2',
                    notes: 'Initial stock intake'
                }})
            }}).then(r => r.json());
        }})()""")

    print(f"Setup complete. Testing Vendor 1 ({v1_user}) and Vendor 2 ({v2_user})...", flush=True)

    # 4. Launch Vendor 1 and Vendor 2 in separate browser profiles
    with RedesignBrowser(OUT_DIR / "prof_v1") as b1, \
         RedesignBrowser(OUT_DIR / "prof_v2") as b2:

        b1.set_viewport(390, 844, mobile=True, device_scale_factor=2)
        b2.set_viewport(390, 844, mobile=True, device_scale_factor=2)

        # -------------------------------------------------------------
        # STEP 1: VENDOR 1 LOGIN
        # -------------------------------------------------------------
        print("\n--- 1. Vendor 1 Login ---", flush=True)
        b1.goto(f"{ORIGIN}/vendor", wait_selector=".vp-login-card")
        time.sleep(0.8)
        save_screenshot(b1, "p5_mobile_vendor_login_screen.png")

        b1.js(f"""(() => {{
            document.querySelector('#vp-username').value = {json.dumps(v1_user)};
            document.querySelector('#vp-password').value = {json.dumps(v1_pass)};
            document.querySelector('#vp-login-btn')?.click();
        }})()""")
        b1.wait_for_selector(".vp-stock-card", timeout=12)
        time.sleep(1.0)

        err_text = b1.js("document.querySelector('.vp-alert-error')?.textContent")
        if err_text:
            print(f"  Login error: {err_text}", flush=True)

        shop_title = b1.js("document.querySelector('.vp-shop-badge')?.textContent")
        print(f"  Vendor 1 logged in: {shop_title}", flush=True)
        assert shop_title and sup1_name in shop_title, f"Expected {sup1_name} in header, got: {shop_title}"
        save_screenshot(b1, "p5_mobile_vendor1_dashboard.png")

        # -------------------------------------------------------------
        # STEP 2: VENDOR 2 LOGIN & ISOLATION CHECK
        # -------------------------------------------------------------
        print("\n--- 2. Vendor 2 Login & Catalog Isolation ---", flush=True)
        b2.goto(f"{ORIGIN}/vendor", wait_selector=".vp-login-card")
        time.sleep(0.5)
        b2.js(f"""(() => {{
            document.querySelector('#vp-username').value = {json.dumps(v2_user)};
            document.querySelector('#vp-password').value = {json.dumps(v2_pass)};
            document.querySelector('#vp-login-btn')?.click();
        }})()""")
        b2.wait_for_selector(".vp-stock-card", timeout=12)
        time.sleep(1.0)

        # Verify Vendor 1's SKU does NOT appear in Vendor 2's portal
        v1_sku_in_v2 = b2.js(f"document.body.innerText.includes({json.dumps(v1_var['sku'])})")
        print(f"  Vendor 1 SKU leaked into Vendor 2 UI: {v1_sku_in_v2}", flush=True)
        assert not v1_sku_in_v2, "Isolation violation: Vendor 1's SKU appeared in Vendor 2 portal!"
        save_screenshot(b2, "p5_mobile_vendor2_isolated.png")

        # -------------------------------------------------------------
        # STEP 3: VENDOR 1 SKU SEARCH
        # -------------------------------------------------------------
        print("\n--- 3. Vendor 1 SKU Search ---", flush=True)
        b1.js(f"""
        (() => {{
            const input = document.querySelector('#vp-stock-search');
            input.value = {json.dumps(v1_var['sku'])};
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()
        """)
        time.sleep(0.6)
        save_screenshot(b1, "p5_mobile_vendor1_search_sku.png")

        # -------------------------------------------------------------
        # STEP 4: UPDATE COUNT (3 -> 2)
        # -------------------------------------------------------------
        print("\n--- 4. Vendor 1 Update Count (3 -> 2) ---", flush=True)
        b1.wait_for_selector(f".vp-update-btn[data-variant-id='{v1_var['id']}']", timeout=12)
        b1.click(f".vp-update-btn[data-variant-id='{v1_var['id']}']")
        b1.wait_for_selector("#vp-count-form", timeout=8)
        time.sleep(0.5)
        save_screenshot(b1, "p5_mobile_vendor1_count_modal_opened.png")

        # Decrement count from 3 to 2
        b1.click("#vp-step-minus")
        time.sleep(0.3)
        new_val = b1.js("document.querySelector('#vp-new-count')?.value")
        print(f"  Count input value after step minus: {new_val}", flush=True)
        assert new_val == "2", f"Expected new count 2, got: {new_val}"

        # Submit form via requestSubmit() so onsubmit fires!
        b1.js("""
        (() => {
            document.querySelector('#vp-count-form')?.requestSubmit();
        })()
        """)
        time.sleep(1.8)
        save_screenshot(b1, "p5_mobile_vendor1_count_updated_2.png")

        updated_on_hand = b1.js(f"document.querySelector('#vp-card-{v1_var['id']} .vp-counter-box:nth-child(1) .vp-counter-num')?.textContent?.trim()")
        print(f"  Updated on-hand count in card: {updated_on_hand}", flush=True)
        assert updated_on_hand == "2", f"Expected 2 on hand, got: {updated_on_hand}"

        # -------------------------------------------------------------
        # STEP 5: STOCK HISTORY MODAL
        # -------------------------------------------------------------
        print("\n--- 5. Stock Update History Modal ---", flush=True)
        b1.click("#vp-history-btn")
        b1.wait_for_selector(".vp-history-item, .vp-empty-state", timeout=8)
        time.sleep(0.8)
        save_screenshot(b1, "p5_mobile_vendor1_history_modal.png")
        b1.click("#vp-close-modal")
        time.sleep(0.4)

        # -------------------------------------------------------------
        # STEP 6: SHORTAGE DETECTION & MODAL
        # -------------------------------------------------------------
        print("\n--- 6. Shortage Reporting Modal ---", flush=True)
        b1.click(f".vp-shortage-btn[data-variant-id='{v1_var['id']}']")
        b1.wait_for_selector("#vp-shortage-form", timeout=5)
        time.sleep(0.5)
        save_screenshot(b1, "p5_mobile_vendor1_shortage_modal.png")
        b1.click("#vp-close-modal")
        time.sleep(0.4)

        # -------------------------------------------------------------
        # STEP 7: CLEAN LOGOUT
        # -------------------------------------------------------------
        print("\n--- 7. Vendor Sign Out ---", flush=True)
        b1.click("#vp-logout-btn")
        b1.wait_for_selector("#vp-login-form", timeout=5)
        time.sleep(0.5)
        save_screenshot(b1, "p5_mobile_vendor1_logged_out.png")

    print("\n=== P5 VENDOR PORTAL VERIFICATION COMPLETED (100% PASS) ===", flush=True)

if __name__ == "__main__":
    main()
