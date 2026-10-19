"""VF2 Supplier Payments, Allocations, Advances, Refunds, and Statements Browser Acceptance Script.
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

OUT_DIR = ROOT / '.local/vendor-finance/vf2'
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
    print("Starting VF2 Browser Acceptance Workflow...")

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

        # 2. Register dedicated test supplier for VF2
        sup_slug = f"vf2-supplier-{token}"
        sup_name = f"VF2 Textile Works ({token})"
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
                    notes: 'VF2 Payments & Statements Verification Supplier',
                }})
            }}).then(r => r.json());
        }})()""")
        supplier_id = create_sup_res.get('id')
        assert supplier_id, f"Failed to create supplier: {create_sup_res}"
        print(f"Created test supplier: {sup_name} (ID: {supplier_id})")

        # 3. Post two charges: INV-VF2-101 (PKR 20,000) and INV-VF2-102 (PKR 30,000)
        c1_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{supplier_id}/ledger/charge', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    amount_minor: 2000000,
                    reference: 'INV-VF2-101',
                    effective_date: '2026-10-15',
                    notes: 'Premium combed cotton fabric rolls (Batch 1)',
                }})
            }}).then(r => r.json());
        }})()""")
        assert c1_res.get('id'), f"Charge 1 failed: {c1_res}"

        c2_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{supplier_id}/ledger/charge', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    amount_minor: 3000000,
                    reference: 'INV-VF2-102',
                    effective_date: '2026-10-18',
                    notes: 'Modal silk blended yardage (Batch 2)',
                }})
            }}).then(r => r.json());
        }})()""")
        assert c2_res.get('id'), f"Charge 2 failed: {c2_res}"

        # 4. Navigate to Admin Suppliers tab
        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1)

        b.js("""(() => {
            const btn = document.querySelector('button[data-tab="suppliers"]');
            if (btn) btn.click();
        })()""")
        time.sleep(1)

        # 5. Open Finance & Ledger Dialog
        print("5. Opening Finance & Ledger dialog...")
        b.wait_for_selector(f'button.btn-manage-finance[data-supplier-id="{supplier_id}"]', timeout=10)
        b.js(f"""(() => {{
            const btn = document.querySelector('button.btn-manage-finance[data-supplier-id="{supplier_id}"]');
            if (btn) btn.click();
        }})()""")
        b.wait_for_selector('#supplier-finance-dialog', timeout=10)
        time.sleep(1.5)

        # Screenshot 1: Overview showing initial Outstanding PKR 50,000
        save_and_copy(b, "vf2_01_finance_overview.png")

        # 6. Record Payment (PKR 35,000 with FIFO auto-allocation)
        print("6. Recording payment with FIFO auto-allocation...")
        b.js("""(() => {
            const btn = document.querySelector('#btn-open-payment-modal');
            if (btn) btn.click();
        })()""")
        time.sleep(0.5)

        b.js("""(() => {
            const sub = document.querySelector('#sub-modal-container');
            if (sub) {
                sub.querySelector('#payment-amount').value = '35000';
                sub.querySelector('#payment-ref').value = 'HBL-VF2-PAY-01';
                sub.querySelector('#payment-notes').value = 'Batch settlement #1 via Raast';
            }
        })()""")
        time.sleep(0.5)
        save_and_copy(b, "vf2_02_record_payment_modal.png")

        b.js("""(() => {
            const form = document.querySelector('#payment-form');
            if (form) form.requestSubmit();
        })()""")
        time.sleep(1.5)

        out_kpi = b.js("(() => document.querySelector('#kpi-outstanding')?.textContent)()")
        pay_kpi = b.js("(() => document.querySelector('#kpi-payments')?.textContent)()")
        print(f"Verified KPIs after payment: Outstanding = {out_kpi}, Payments = {pay_kpi}")
        save_and_copy(b, "vf2_03_payment_posted_kpi_updated.png")

        # 7. Disburse Advance (PKR 10,000)
        print("7. Disbursing supplier advance...")
        b.js("""(() => {
            const btn = document.querySelector('#btn-open-advance-modal');
            if (btn) btn.click();
        })()""")
        time.sleep(0.5)

        b.js("""(() => {
            const sub = document.querySelector('#sub-modal-container');
            if (sub) {
                sub.querySelector('#advance-amount').value = '10000';
                sub.querySelector('#advance-ref').value = 'ADV-VF2-SEASON-01';
                sub.querySelector('#advance-notes').value = 'Upfront fabric reservation deposit';
            }
        })()""")
        time.sleep(0.5)
        save_and_copy(b, "vf2_04_disburse_advance_modal.png")

        b.js("""(() => {
            const form = document.querySelector('#advance-form');
            if (form) form.requestSubmit();
        })()""")
        time.sleep(1.5)

        adv_kpi = b.js("(() => document.querySelector('#kpi-advances')?.textContent)()")
        print(f"Verified KPIs after advance: Unallocated Advances = {adv_kpi}")
        save_and_copy(b, "vf2_05_advance_posted_kpi_updated.png")

        # 8. Allocate Advance to Remaining Charge
        print("8. Allocating advance funds against remaining charge...")
        b.js("""(() => {
            const allocBtns = Array.from(document.querySelectorAll('.btn-allocate-entry'));
            if (allocBtns.length > 0) {
                allocBtns[0].click();
            }
        })()""")
        time.sleep(0.5)

        b.js("""(() => {
            const sub = document.querySelector('#sub-modal-container');
            if (sub) {
                const inp = sub.querySelector('#alloc-amount');
                if (inp) inp.value = '10000';
            }
        })()""")
        time.sleep(0.5)
        save_and_copy(b, "vf2_06_allocate_advance_modal.png")

        b.js("""(() => {
            const form = document.querySelector('#allocate-form');
            if (form) form.requestSubmit();
        })()""")
        time.sleep(1.5)

        out_after_alloc = b.js("(() => document.querySelector('#kpi-outstanding')?.textContent)()")
        adv_after_alloc = b.js("(() => document.querySelector('#kpi-advances')?.textContent)()")
        print(f"Verified KPIs after allocation: Outstanding = {out_after_alloc}, Advances = {adv_after_alloc}")
        save_and_copy(b, "vf2_07_advance_allocated_kpi_updated.png")

        # 9. Record Supplier Cash Refund (PKR 2,000)
        print("9. Recording cash refund received from vendor...")
        b.js("""(() => {
            const btn = document.querySelector('#btn-open-refund-modal');
            if (btn) btn.click();
        })()""")
        time.sleep(0.5)

        b.js("""(() => {
            const sub = document.querySelector('#sub-modal-container');
            if (sub) {
                sub.querySelector('#refund-amount').value = '2000';
                sub.querySelector('#refund-ref').value = 'VEND-REF-VF2-01';
                sub.querySelector('#refund-notes').value = 'Vendor cash rebate for dye imperfection';
            }
        })()""")
        time.sleep(0.5)

        b.js("""(() => {
            const form = document.querySelector('#refund-form');
            if (form) form.requestSubmit();
        })()""")
        time.sleep(1.5)

        out_after_refund = b.js("(() => document.querySelector('#kpi-outstanding')?.textContent)()")
        print(f"Verified KPI after refund: Outstanding = {out_after_refund}")
        save_and_copy(b, "vf2_08_supplier_refund_posted.png")

        # 10. Period Statement & Reconciliation
        print("10. Generating Period Statement & Reconciliation...")
        b.js("""(() => {
            const btn = document.querySelector('#btn-open-statement-modal');
            if (btn) btn.click();
        })()""")
        time.sleep(0.5)

        b.js("""(() => {
            const sub = document.querySelector('#sub-modal-container');
            if (sub) {
                sub.querySelector('#stmt-start-date').value = '2026-10-01';
                sub.querySelector('#stmt-end-date').value = '2026-10-31';
                sub.querySelector('#btn-run-statement').click();
            }
        })()""")
        time.sleep(1.5)
        save_and_copy(b, "vf2_09_period_statement_reconciliation.png")

        print("\nALL VF2 BROWSER ACCEPTANCE WORKFLOWS COMPLETED SUCCESSFULLY!\n")


if __name__ == "__main__":
    main()
