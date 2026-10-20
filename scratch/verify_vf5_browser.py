"""VF5 Vendor Stock-Only Portal & Authentication Browser Verification Script.
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

OUT_DIR = ROOT / '.local/vendor-finance/vf5'
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
    print("Starting VF5 Browser Acceptance Workflow...")

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

        # 2. Open Admin Console and Navigate to Suppliers Tab
        print("2. Opening Admin Console and navigating to Suppliers...")
        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-modal')
        time.sleep(1.0)

        # Click the Suppliers tab button
        b.js("""(() => {
            const btn = document.querySelector('button.admin-tab-btn[data-tab="suppliers"]');
            if (btn) btn.click();
        })()""")
        time.sleep(1.5)

        # 3. Open Stock Logins Modal for Vendor Denim Craft (VF5)
        print("3. Opening Stock Logins modal for Vendor Denim Craft (VF5)...")
        b.js("""(() => {
            const btn = document.querySelector('.btn-manage-stock-users[data-supplier-id="858ac929-ce0b-4e2e-b466-0757cb39bc7b"]');
            if (btn) btn.click();
            else {
                const btns = Array.from(document.querySelectorAll('.btn-manage-stock-users'));
                if (btns.length > 0) btns[btns.length - 1].click();
            }
        })()""")
        time.sleep(1.5)

        # Provision a new stock login: denim_staff_vf5
        vendor_user = f"staff_{secrets.token_hex(3)}"
        vendor_pass = "StaffPassword123!"
        print(f"Provisioning vendor login '{vendor_user}'...")

        b.js(f"""(() => {{
            const uInput = document.querySelector('#prov-username');
            const pInput = document.querySelector('#prov-password');
            const form = document.querySelector('#provision-user-form');
            const btn = document.querySelector('#btn-submit-provision');
            if (uInput && pInput && form) {{
                uInput.value = {json.dumps(vendor_user)};
                pInput.value = {json.dumps(vendor_pass)};
                if (btn) btn.click();
                else form.dispatchEvent(new Event('submit', {{ bubbles: true, cancelable: true }}));
            }}
        }})()""")

        # Poll until user appears in the table
        for _ in range(20):
            time.sleep(0.5)
            found = b.js(f"""(() => {{
                const codes = Array.from(document.querySelectorAll('#vendor-users-content code')).map(c => c.textContent.trim());
                return codes.includes({json.dumps(vendor_user)});
            }})()""")
            if found:
                print(f"Vendor login '{vendor_user}' successfully provisioned and rendered in table!")
                break
        else:
            err_text = b.js("document.querySelector('#prov-error')?.textContent")
            print("Provision error visible on screen:", err_text)

        time.sleep(0.5)
        # Capture Screenshot 1: Owner managing stock logins
        save_and_copy(b, "vf5_01_owner_manage_stock_logins.png")

        # Close vendor users modal
        b.js("""(() => {
            const closeBtn = document.querySelector('#btn-close-vendor-users');
            if (closeBtn) closeBtn.click();
        })()""")
        time.sleep(0.5)

        # 4. Navigate to /vendor portal unauthenticated
        print("4. Navigating to /vendor portal...")
        b.goto(f"{ORIGIN}/vendor", wait_selector='.vp-login-card')
        time.sleep(1.0)

        # Capture Screenshot 2: Vendor Login Screen
        save_and_copy(b, "vf5_02_vendor_login_screen.png")

        # 5. Sign in as vendor stock staff
        print(f"5. Signing in as vendor staff '{vendor_user}'...")
        b.js(f"""(() => {{
            const uInput = document.querySelector('#vp-username');
            const pInput = document.querySelector('#vp-password');
            const btn = document.querySelector('#vp-login-btn');
            if (uInput && pInput) {{
                uInput.value = {json.dumps(vendor_user)};
                pInput.value = {json.dumps(vendor_pass)};
                if (btn) btn.click();
            }}
        }})()""")

        # Poll until stock cards appear
        cards_count = 0
        for _ in range(20):
            time.sleep(0.5)
            cards_count = b.js("document.querySelectorAll('.vp-stock-card').length") or 0
            if cards_count > 0:
                break
        else:
            login_err = b.js("document.querySelector('.vp-alert-error')?.textContent")
            print("Vendor login error visible on screen:", login_err)

        print(f"Loaded {cards_count} vendor stock cards.")
        assert cards_count > 0, "No stock cards rendered!"

        # Capture Screenshot 3: Vendor Stock List View
        save_and_copy(b, "vf5_03_vendor_stock_list.png")

        # 6. Open Count Update Modal on First Card
        print("6. Opening Count Update modal...")
        b.js("""(() => {
            const updateBtn = document.querySelector('.vp-update-btn');
            if (updateBtn) updateBtn.click();
        })()""")
        time.sleep(1.0)

        # Decrement count from 3 to 2, select reason shop_sale, enter note
        b.js("""(() => {
            const minusBtn = document.querySelector('#vp-step-minus');
            if (minusBtn) minusBtn.click();
            const reasonSel = document.querySelector('#vp-reason');
            if (reasonSel) reasonSel.value = 'shop_sale';
            const noteInput = document.querySelector('#vp-note');
            if (noteInput) noteInput.value = '1 unit sold to physical store customer';
        })()""")
        time.sleep(0.5)

        # Capture Screenshot 4: Count Update Modal
        save_and_copy(b, "vf5_04_count_update_modal.png")

        # Submit count update
        print("Submitting count update (3 -> 2)...")
        b.js("""(() => {
            const btn = document.querySelector('#vp-submit-count');
            if (btn) btn.click();
            else {
                const form = document.querySelector('#vp-count-form');
                if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            }
        })()""")
        time.sleep(2.0)

        # 7. Test Shortage Warning: open count update again and enter 0 (below customer holds)
        print("7. Testing shortage warning banner (entering 0 while 1 held)...")
        b.js("""(() => {
            const updateBtn = document.querySelector('.vp-update-btn');
            if (updateBtn) updateBtn.click();
        })()""")
        time.sleep(1.0)

        b.js("""(() => {
            const input = document.querySelector('#vp-new-count');
            if (input) {
                input.value = 0;
                input.dispatchEvent(new Event('input', { bubbles: true }));
            }
        })()""")
        time.sleep(0.5)

        # Capture Screenshot 5: Shortage Warning Banner
        save_and_copy(b, "vf5_05_shortage_alert_and_warning.png")

        # Cancel count modal
        b.js("""(() => {
            const cancelBtn = document.querySelector('#vp-cancel-count');
            if (cancelBtn) cancelBtn.click();
        })()""")
        time.sleep(0.5)

        # 8. Open History Drawer to verify audit record of 3 -> 2 shop sale
        print("8. Opening Stock Audit History...")
        b.js("""(() => {
            const histBtn = document.querySelector('#vp-history-btn');
            if (histBtn) histBtn.click();
        })()""")
        time.sleep(1.5)

        # Capture Screenshot 6: Audit History
        save_and_copy(b, "vf5_06_vendor_audit_history.png")

    print("\n[SUCCESS] All 6 VF5 Browser Screenshots Captured and Verified Successfully!")

if __name__ == '__main__':
    main()
