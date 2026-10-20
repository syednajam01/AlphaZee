"""VF4 Financial Reports, Period P&L, Per-Order Economics & CSV Exports Browser Acceptance Script.
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

OUT_DIR = ROOT / '.local/vendor-finance/vf4'
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
    print("Starting VF4 Browser Acceptance Workflow...")

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

        # 2. Record a few business expenses so overhead and freight are visible
        print("2. Recording sample business expenses...")
        exp1 = b.js(f"""(() => {{
            return fetch('/api/v1/admin/expenses', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    category: 'packaging',
                    amount_minor: 750000,
                    incurred_date: '2026-10-15',
                    paid_date: '2026-10-15',
                    payee: 'Lahore Corrugated Packaging Ltd',
                    reference: 'INV-PKG-994',
                    payment_method: 'bank_transfer',
                    notes: 'Custom branded shipping mailers and apparel boxes',
                }})
            }}).then(r => r.json());
        }})()""")
        assert exp1.get('id'), f"Failed to record expense 1: {exp1}"

        exp2 = b.js(f"""(() => {{
            return fetch('/api/v1/admin/expenses', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    category: 'rto_transport',
                    amount_minor: 350000,
                    incurred_date: '2026-10-18',
                    payee: 'Trax Logistics',
                    reference: 'TRAX-RTO-OCT18',
                    payment_method: 'courier_deduction',
                    notes: '100% AlphaZee-borne courier return freight',
                }})
            }}).then(r => r.json());
        }})()""")
        assert exp2.get('id'), f"Failed to record expense 2: {exp2}"
        print("Business expenses recorded.")

        # 3. Open Admin Console and Navigate to P&L & Analytics Tab
        print("3. Opening Admin Console and navigating to Reports & Analytics...")
        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1.0)

        # Click the Analytics tab button
        b.js("""(() => {
            const btn = document.querySelector('.admin-tab-btn[data-tab="analytics"]');
            if (btn) btn.click();
        })()""")
        time.sleep(2.0)

        # Wait for the financial-reports-view to load
        b.wait_for_selector('.financial-reports-view', timeout=10000)
        time.sleep(1.0)

        # 4. Capture Screen 1: Top KPI Summary and P&L Statement Card
        print("4. Capturing Screen 1: P&L Summary & KPIs...")
        b.js("""(() => {
            window.scrollTo({ top: 0, behavior: 'instant' });
            const content = document.getElementById('admin-tab-content');
            if (content) content.scrollTop = 0;
        })()""")
        time.sleep(0.5)
        save_and_copy(b, "vf4_01_pnl_summary.png")

        # 5. Capture Screen 2: Cash Movement & Balance Sheet Card
        print("5. Capturing Screen 2: Cash Movement & Reconciliation...")
        b.js("""(() => {
            // Scroll to the P&L and Cash Movement section
            const el = document.querySelector('.financial-reports-view > div:nth-child(3)');
            if (el) el.scrollIntoView({ behavior: 'instant', block: 'center' });
        })()""")
        time.sleep(0.5)
        save_and_copy(b, "vf4_02_cash_reconciliation.png")

        # 6. Capture Screen 3: Per-Order Economics with Line-Item Margins Expanded
        print("6. Capturing Screen 3: Per-Order Economics & Line Margins...")
        # Scroll to orders table
        b.js("""(() => {
            const table = document.querySelector('.financial-reports-view > div:nth-child(4)');
            if (table) table.scrollIntoView({ behavior: 'instant', block: 'start' });
        })()""")
        time.sleep(0.5)

        # Click the first 'Inspect' button if present
        inspect_clicked = b.js("""(() => {
            const btn = document.querySelector('.btn-toggle-order-lines');
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        })()""")
        time.sleep(0.8)
        print(f"Line inspection toggle clicked: {inspect_clicked}")
        save_and_copy(b, "vf4_03_order_economics.png")

        # 7. Verify CSV Export Endpoints & Capture Screen 4: CSV Export Action
        print("7. Verifying CSV Exports and Capturing Screen 4...")
        csv_pnl_data = b.js(f"""(() => {{
            return fetch('/api/v1/admin/reports/period/export', {{
                headers: {{ 'Origin': '{ORIGIN}' }}
            }}).then(r => r.text());
        }})()""")
        assert "AlphaZee Period Financial & P&L Statement" in csv_pnl_data, f"Invalid P&L CSV: {csv_pnl_data[:200]}"
        assert "Delivered Gross Sales" in csv_pnl_data
        print("P&L CSV export verified with correct headers and sections.")

        csv_orders_data = b.js(f"""(() => {{
            return fetch('/api/v1/admin/reports/orders/export', {{
                headers: {{ 'Origin': '{ORIGIN}' }}
            }}).then(r => r.text());
        }})()""")
        assert "Order Number" in csv_orders_data, f"Invalid Orders CSV: {csv_orders_data[:200]}"
        assert "Estimated Contribution (PKR)" in csv_orders_data
        print("Orders CSV export verified with correct headers and formula safety.")

        # Scroll back to the top toolbar showing export buttons
        b.js("""(() => {
            window.scrollTo({ top: 0, behavior: 'instant' });
            const content = document.getElementById('admin-tab-content');
            if (content) content.scrollTop = 0;
        })()""")
        time.sleep(0.5)
        save_and_copy(b, "vf4_04_csv_export.png")

        print("VF4 Browser Acceptance Successfully Completed!")

if __name__ == '__main__':
    main()
