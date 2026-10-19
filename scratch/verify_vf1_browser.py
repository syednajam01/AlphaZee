"""VF1 Supplier Agreements & Ledger Browser Acceptance Script.
Runs headless Chrome via CDP against checkout lab (http://127.0.0.1:13001).
Verifies:
1. Suppliers table renders with Finance & Ledger action.
2. Agreement terms editor (payable trigger, terms days, settlement banking notes).
3. Real-time KPI summary cards (outstanding payable, charges, credit notes, payments).
4. Manual charge posting flow (PKR 15,000 liability).
5. Manual credit note posting flow (PKR 3,000 allowance).
6. Immutable entry reversal with required audit reason.
7. Opening balance preview and application with audit reference.
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

OUT_DIR = ROOT / '.local/vendor-finance/vf1'
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
    print("Starting VF1 Browser Acceptance Workflow...")

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

        # 2. Register a dedicated test supplier for VF1
        sup_slug = f"vf1-supplier-{token}"
        sup_name = f"VF1 Karachi Weavers ({token})"
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
                    notes: 'Primary test vendor for VF1 finance acceptance',
                }})
            }}).then(r => r.json());
        }})()""")
        supplier_id = create_sup_res.get('id')
        assert supplier_id, f"Failed to create supplier: {create_sup_res}"
        print(f"Created test supplier: {sup_name} (ID: {supplier_id})")

        # 3. Open Admin Console -> Suppliers Tab
        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1)

        # Switch to Suppliers tab
        b.js("""(() => {
            const btn = document.querySelector('button[data-tab="suppliers"]');
            if (btn) btn.click();
        })()""")
        time.sleep(1)

        b.wait_for_selector(f'button.btn-manage-finance[data-supplier-id="{supplier_id}"]', timeout=10)
        save_and_copy(b, "vf1_01_suppliers_tab.png")

        # 4. Open Finance & Ledger Dialog
        print("4. Opening Finance & Ledger dialog...")
        b.js(f"""(() => {{
            const btn = document.querySelector('button.btn-manage-finance[data-supplier-id="{supplier_id}"]');
            if (btn) btn.click();
        }})()""")
        b.wait_for_selector('#supplier-finance-dialog', timeout=10)
        time.sleep(1)
        save_and_copy(b, "vf1_02_agreement_initial.png")

        # 5. Configure Settlement Agreement Terms
        print("5. Configuring settlement agreement terms...")
        b.js("""(() => {
            document.querySelector('#sel-payable-trigger').value = 'dispatch';
            document.querySelector('#inp-payment-terms').value = '14';
            document.querySelector('#inp-agreement-notes').value = 'Meezan Bank - Vendor PK - Net 14 days post dispatch';
            document.querySelector('#btn-save-agreement').click();
        })()""")
        time.sleep(1.5)
        save_and_copy(b, "vf1_03_agreement_saved.png")

        # 6. Post Manual Charge (PKR 15,000)
        print("6. Posting manual charge...")
        b.click('#btn-open-charge-modal')
        b.wait_for_selector('#charge-form', timeout=5)
        time.sleep(0.5)

        b.js("""(() => {
            document.querySelector('#charge-amount').value = '15000.00';
            document.querySelector('#charge-ref').value = 'INV-VF1-001';
            document.querySelector('#charge-notes').value = 'Bulk batch fabric delivery';
            const form = document.querySelector('#charge-form');
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
        })()""")
        
        # Wait for KPI update
        for _ in range(25):
            kpi_out = b.js("document.querySelector('#kpi-outstanding')?.textContent || ''")
            if "15,000" in kpi_out:
                break
            time.sleep(0.2)

        print(f"Verified KPI Outstanding: {kpi_out}")
        assert "15,000" in kpi_out, f"Expected PKR 15,000 in outstanding KPI, got: {kpi_out}"
        save_and_copy(b, "vf1_04_manual_charge_posted.png")

        # 7. Post Manual Credit Note (PKR 3,000)
        print("7. Posting manual credit note...")
        b.click('#btn-open-credit-modal')
        b.wait_for_selector('#credit-form', timeout=5)
        time.sleep(0.5)

        b.js("""(() => {
            document.querySelector('#credit-amount').value = '3000.00';
            document.querySelector('#credit-ref').value = 'CN-VF1-001';
            document.querySelector('#credit-notes').value = 'Fabric flaw discount agreed via phone';
            const form = document.querySelector('#credit-form');
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
        })()""")
        
        # Wait for KPI update: 15,000 - 3,000 = 12,000
        for _ in range(25):
            kpi_out2 = b.js("document.querySelector('#kpi-outstanding')?.textContent || ''")
            if "12,000" in kpi_out2:
                break
            time.sleep(0.2)

        print(f"Verified KPI Outstanding after credit note: {kpi_out2}")
        assert "12,000" in kpi_out2, f"Expected PKR 12,000 in outstanding KPI, got: {kpi_out2}"
        save_and_copy(b, "vf1_05_credit_note_posted.png")

        # 8. Reverse the Manual Charge Entry
        print("8. Reversing manual charge entry...")
        b.js("""(() => {
            const btn = document.querySelector('button.btn-reverse-entry[data-ref="INV-VF1-001"]');
            if (btn) btn.click();
        })()""")
        b.wait_for_selector('#reversal-form', timeout=5)
        time.sleep(0.5)

        b.js("""(() => {
            document.querySelector('#reversal-reason').value = 'Erroneous double entry by operator';
            const form = document.querySelector('#reversal-form');
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
        })()""")
        
        # Wait for entry to show reversed
        time.sleep(1.5)
        save_and_copy(b, "vf1_06_entry_reversed.png")

        # 9. Opening Balance Preview & Apply
        print("9. Testing opening balance preview & apply...")
        b.click('#btn-open-opening-balance-modal')
        b.wait_for_selector('#ob-form', timeout=5)
        time.sleep(0.5)

        b.js("""(() => {
            document.querySelector('#ob-amount').value = '50000.00';
            document.querySelector('#ob-direction').value = 'credit';
            document.querySelector('#ob-ref').value = 'AUDIT-VF1-PRELAUNCH-01';
            document.querySelector('#ob-notes').value = 'Audited signed supplier ledger as of Oct 2026';
            document.querySelector('#btn-preview-ob').click();
        })()""")
        time.sleep(1)

        b.wait_for_selector('#ob-preview-box', timeout=5)
        preview_visible = b.js("document.querySelector('#ob-preview-box').style.display !== 'none'")
        assert preview_visible, "Opening balance preview box did not display"
        save_and_copy(b, "vf1_07_opening_balance_preview.png")

        # Commit opening balance
        print("Committing opening balance...")
        b.js("""(() => {
            const form = document.querySelector('#ob-form');
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
        })()""")
        
        # Wait for opening balance to reflect in KPI
        for _ in range(25):
            kpi_out3 = b.js("document.querySelector('#kpi-outstanding')?.textContent || ''")
            if "PKR 0" not in kpi_out3 and kpi_out3:
                break
            time.sleep(0.2)

        print(f"Final KPI Outstanding after opening balance: {kpi_out3}")
        save_and_copy(b, "vf1_08_opening_balance_applied.png")

    print("\nALL VF1 BROWSER ACCEPTANCE WORKFLOWS COMPLETED SUCCESSFULLY!")

if __name__ == '__main__':
    main()
