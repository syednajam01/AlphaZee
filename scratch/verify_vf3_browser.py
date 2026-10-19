"""VF3 Product Stock Responsibility & Business Expenses Browser Acceptance Script.
Runs headless Chrome via CDP against checkout lab (http://127.0.0.1:13001).
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

OUT_DIR = ROOT / '.local/vendor-finance/vf3'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_ARTIFACTS = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity-ide\brain\ca17e23f-7699-47ff-83c4-deb583790c47")

ORIGIN = "http://127.0.0.1:13001"
LAB_COMPOSE = ['docker', 'compose', '-f', 'compose.checkout-lab.yml']

def run_lab_cmd(args, input_bytes=None):
    cmd = LAB_COMPOSE + args
    res = subprocess.run(cmd, cwd=ROOT, input=input_bytes, capture_output=True, check=True)
    return res.stdout.decode('utf-8', errors='replace').strip()

def save_and_copy(b, filename):
    local_path = OUT_DIR / filename
    b.capture_screenshot(str(local_path))
    if BRAIN_ARTIFACTS.exists():
        shutil.copy2(local_path, BRAIN_ARTIFACTS / filename)
    print(f"Captured: {filename}")

def main():
    print("Starting VF3 Browser Acceptance Workflow...")

    with RedesignBrowser(OUT_DIR) as b:
        # 1. Provision Lab Owner & Authenticate
        print("1. Provisioning lab owner & authenticating...")
        token = secrets.token_hex(4)
        owner_username = f"sample_m8_{token}"
        owner_password = secrets.token_urlsafe(24)

        run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_username],
                    input_bytes=owner_password.encode('utf-8'))

        b.goto(f"{ORIGIN}/", wait_selector='.hero-section')
        time.sleep(0.5)

        login_res = b.js(f"""(() => {{
            return fetch('/api/v1/auth/login', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    username: {json.dumps(owner_username)},
                    password: {json.dumps(owner_password)},
                }})
            }}).then(r => r.json());
        }})()""")
        csrf_token = login_res.get('csrf_token')
        assert csrf_token, f"Login failed: {login_res}"
        print(f"Logged in lab owner: {owner_username}")

        # 2. Register an external vendor shop
        sup_slug = f"vf3-vendor-{token}"
        sup_name = f"VF3 Apparel Works ({token})"
        create_sup_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    name: {json.dumps(sup_name)},
                    slug: {json.dumps(sup_slug)},
                    status: 'active',
                    notes: 'VF3 Vendor Managed Stock Shop',
                }})
            }}).then(r => r.json());
        }})()""")
        vendor_id = create_sup_res.get('id')
        assert vendor_id, f"Failed to create supplier: {create_sup_res}"
        print(f"Created vendor shop: {sup_name} (ID: {vendor_id})")

        # 3. Create a test product draft via API
        product_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{}}),
            }}).then(r => r.json());
        }})()""")
        product_id = product_res.get('id')
        assert product_id, f"Failed to create product draft: {product_res}"
        print(f"Created product draft ID: {product_id}")

        # 4. Open Admin Console -> Products & Catalog Tab
        print("2. Opening Admin Console Products & Catalog...")
        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1)

        # Switch to products tab
        b.js("""(() => {
            const btn = document.querySelector('[data-tab="products"]');
            if (btn) btn.click();
        })()""")
        print("Waiting for products list...")
        found = b.wait_for_selector(f'[data-edit-product="{product_id}"]', timeout=10)
        print(f"Found product edit button: {found}")

        # Edit our product
        clicked = b.js(f"""(() => {{
            const btn = document.querySelector('[data-edit-product="{product_id}"]');
            if (btn) {{
                btn.click();
                return true;
            }}
            return false;
        }})()""")
        print(f"Clicked edit button: {clicked}")
        print("Waiting for product edit form...")
        box_found = b.wait_for_selector('.stock-responsibility-box', timeout=10)
        print(f"Stock responsibility box found: {box_found}")
        if not box_found:
            print("Current status text:", b.js("() => document.querySelector('#catalog-status')?.textContent"))
            print("Tab content text:", b.js("() => document.querySelector('#admin-tab-content')?.innerText?.slice(0, 500)"))
            print("Console logs:", b.console_logs[-10:])
            print("Errors:", b.errors)

        # Verify stock responsibility box is visible
        has_box = b.js("Boolean(document.querySelector('.stock-responsibility-box'))")
        assert has_box, "Stock responsibility box missing in CatalogWorkspace"

        # Check default: alphazee_managed
        default_checked = b.js("Boolean(document.querySelector('#source-alphazee')?.checked)")
        assert default_checked, "Default stock management source should be alphazee_managed"

        save_and_copy(b, 'vf3_01_stock_source_alphazee.png')

        # Toggle to vendor_managed
        print("3. Toggling to vendor_managed and selecting vendor shop...")
        b.js(f"""(() => {{
            const vendorRadio = document.querySelector('#source-vendor');
            vendorRadio.click();
            vendorRadio.dispatchEvent(new Event('change', {{ bubbles: true }}));
            const select = document.querySelector('#catalog-vendor-id');
            select.value = '{vendor_id}';
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            const titleInput = document.querySelector('input[name="title"]');
            if (titleInput) {{
                titleInput.value = 'VF3 Silk Kurta';
                titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }})()""")
        time.sleep(0.5)

        save_and_copy(b, 'vf3_02_stock_source_vendor_selected.png')

        # Save product
        print("4. Saving product with vendor_managed source...")
        b.js("""(() => {
            const form = document.querySelector('#catalog-product-form');
            if (form) form.requestSubmit();
        })()""")

        # Wait for product save to finish
        start = time.time()
        while time.time() - start < 15:
            st = b.js("(document.querySelector('#catalog-status')?.textContent || '')")
            if "Product and media saved" in st or "saved" in st.lower():
                break
            time.sleep(0.3)

        status_text = b.js("(document.querySelector('#catalog-status')?.textContent || '')")
        print(f"Product save status: {status_text}")

        saved_prod = b.js(f"""(() => {{
            return fetch('/api/v1/admin/products/{product_id}', {{
                headers: {{ 'X-CSRF-Token': {json.dumps(csrf_token)} }}
            }}).then(r => r.json());
        }})()""")
        assert saved_prod.get('stock_management_source') == 'vendor_managed', f"Expected vendor_managed, got: {saved_prod}"
        assert saved_prod.get('vendor_id') == vendor_id, f"Expected vendor_id {vendor_id}, got: {saved_prod}"
        print(f"Product verified on backend: source={saved_prod.get('stock_management_source')}, vendor_id={saved_prod.get('vendor_id')}")

        save_and_copy(b, 'vf3_03_saved_vendor_product.png')

        # 5. Business Expenses Tab
        print("5. Navigating to Business Expenses tab...")
        b.js("window.onbeforeunload = null;")
        b.goto(f"{ORIGIN}/admin/expenses", wait_selector='#kpi-total-incurred')
        time.sleep(1.0)

        # Verify policy banner
        has_banner = b.js("document.body.innerText.includes('AlphaZee strictly bears all RTO')")
        assert has_banner, "AlphaZee RTO policy banner missing in Business Expenses view"

        save_and_copy(b, 'vf3_04_business_expenses_initial.png')

        # 6. Record Expense 1: Packaging & Boxes (PKR 1,500)
        print("6. Opening Record Expense Modal for Packaging...")
        b.wait_for_selector('#btn-open-record-expense', timeout=10)
        b.js("""(() => {
            const btn = document.querySelector('#btn-open-record-expense');
            if (btn) btn.click();
        })()""")
        b.wait_for_selector('#record-expense-modal', timeout=10)
        time.sleep(0.5)

        b.js("""(() => {
            document.querySelector('#exp-category').value = 'packaging';
            document.querySelector('#exp-amount').value = '1500';
            document.querySelector('#exp-payee').value = 'Karachi Packaging Works';
            document.querySelector('#exp-reference').value = 'PKG-2026-001';
            document.querySelector('#exp-payment-method').value = 'bank_transfer';
            document.querySelector('#exp-notes').value = '150 custom shipping boxes and polybags';
        })()""")
        time.sleep(0.5)

        save_and_copy(b, 'vf3_05_record_expense_modal.png')

        # Submit Expense 1
        b.js("""(() => {
            const form = document.querySelector('#record-expense-form');
            if (form) form.requestSubmit();
        })()""")
        # Wait for modal 1 to close
        start = time.time()
        while time.time() - start < 10:
            if not b.js("Boolean(document.querySelector('#record-expense-modal'))"):
                break
            time.sleep(0.3)
        modal_open = b.js("Boolean(document.querySelector('#record-expense-modal'))")
        print("Expense 1 modal closed:", not modal_open)

        # 7. Record Expense 2: RTO Transport (AlphaZee-Borne) (PKR 350)
        print("7. Recording RTO Transport Expense (AlphaZee-Borne)...")
        b.wait_for_selector('#btn-open-record-expense', timeout=10)
        b.click('#btn-open-record-expense')
        b.wait_for_selector('#record-expense-modal', timeout=10)
        time.sleep(0.5)

        b.js("""(() => {
            document.querySelector('#exp-category').value = 'rto_transport';
            document.querySelector('#exp-amount').value = '350';
            document.querySelector('#exp-payee').value = 'Trax Express Logistics';
            document.querySelector('#exp-reference').value = 'TRX-RTO-9941';
            document.querySelector('#exp-payment-method').value = 'courier_deduction';
            document.querySelector('#exp-notes').value = 'RTO return freight deduction borne 100% by AlphaZee (zero deduction from vendor)';
        })()""")
        time.sleep(0.5)

        # Submit Expense 2
        b.js("""(() => {
            const form = document.querySelector('#record-expense-form');
            if (form) form.requestSubmit();
        })()""")
        # Wait for modal 2 to close
        start = time.time()
        while time.time() - start < 10:
            if not b.js("Boolean(document.querySelector('#record-expense-modal'))"):
                break
            time.sleep(0.3)
        modal_open2 = b.js("Boolean(document.querySelector('#record-expense-modal'))")
        print("Expense 2 modal closed:", not modal_open2)

        # 8. Verify Table & KPIs
        print("8. Verifying KPI summaries and expenses table...")
        start = time.time()
        while time.time() - start < 10:
            tbody = b.js("(document.querySelector('#expense-table-body')?.innerText || '')")
            if "TRX-RTO-9941" in tbody and "PKG-2026-001" in tbody:
                break
            time.sleep(0.3)

        total_incurred_text = b.js("(document.querySelector('#kpi-total-incurred')?.textContent?.trim() || '')")
        freight_text = b.js("(document.querySelector('#kpi-total-freight')?.textContent?.trim() || '')")
        tbody_text = b.js("(document.querySelector('#expense-table-body')?.innerText || '')")
        print(f"Total Incurred KPI: {total_incurred_text}, Freight KPI: {freight_text}")

        assert "PKR" in total_incurred_text, f"Expected PKR in total incurred, got {total_incurred_text}"
        assert "PKR" in freight_text, f"Expected PKR in freight, got {freight_text}"
        assert "TRX-RTO-9941" in tbody_text, f"Expected TRX-RTO-9941 in expenses table, got: {tbody_text}"
        assert "PKG-2026-001" in tbody_text, f"Expected PKG-2026-001 in expenses table, got: {tbody_text}"

        save_and_copy(b, 'vf3_06_expenses_recorded_summary.png')

        # 9. Test Category Filter
        print("9. Filtering by RTO Transport category...")
        b.js("""(() => {
            const select = document.querySelector('#expense-filter-category');
            if (select) {
                select.value = 'rto_transport';
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }
        })()""")
        time.sleep(1.5)

        table_text = b.js("(document.querySelector('#expense-table-body')?.innerText || '')")
        assert "TRX-RTO-9941" in table_text, f"Expected RTO expense in filtered table, got: {table_text}"
        assert "PKG-2026-001" not in table_text, f"Packaging expense should be filtered out, got: {table_text}"

        save_and_copy(b, 'vf3_07_expenses_filtered_rto.png')

    print("\n[SUCCESS] VF3 Browser Acceptance Verification 100% PASSED!")

if __name__ == '__main__':
    main()
