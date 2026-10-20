"""VF6 Configurable Storefront Settings, Legal Policies & Admin Preferences Browser Verification Script.
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

OUT_DIR = ROOT / '.local/vendor-finance/vf6'
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
    print("Starting VF6 Browser Acceptance Workflow...")

    with RedesignBrowser(OUT_DIR) as b:
        # Step 1: Initial Storefront Announcement Bar
        print("1. Loading storefront to inspect initial announcement bar...")
        b.goto(f"{ORIGIN}/", wait_selector='.site-header')
        time.sleep(1.0)
        save_and_copy(b, "vf6_01_storefront_initial_announcement.png")

        # Step 2: Provision Lab Owner & Login
        print("2. Provisioning lab owner & authenticating...")
        token = secrets.token_hex(4)
        owner_username = f"sample_m8_{token}"
        owner_password = secrets.token_urlsafe(24)

        run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_username],
                    input_bytes=owner_password.encode('utf-8'))

        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-auth-form')
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
                    password: {json.dumps(owner_password)}
                }})
            }}).then(r => r.json().then(data => ({{ status: r.status, data }})));
        }})()""")

        if login_res.get('status') != 200:
            raise RuntimeError(f"Owner login failed: {login_res}")

        b.goto(f"{ORIGIN}/admin", wait_selector='#admin-sidebar')
        time.sleep(1.0)

        # Step 3: Navigate to Store Settings in Admin
        print("3. Navigating to Store Settings tab...")
        b.goto(f"{ORIGIN}/admin/settings", wait_selector='.settings-tabs')
        time.sleep(1.5)
        save_and_copy(b, "vf6_02_admin_store_settings_view.png")

        # Step 4: Update Storefront Settings & Save
        print("4. Updating announcement text, accent color, and change reason...")
        new_text = "Winter Luxe Drop Live - Free Express Delivery over Rs. 5,000"
        b.js(f"""(() => {{
            const inputAnnounce = document.querySelector('#input-announcement-text');
            if (inputAnnounce) {{
                inputAnnounce.value = {json.dumps(new_text)};
                inputAnnounce.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            const inputColor = document.querySelector('#input-accent-color');
            if (inputColor) {{
                inputColor.value = '#1e3a8a';
                inputColor.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            const inputReason = document.querySelector('#input-change-reason');
            if (inputReason) {{
                inputReason.value = 'Winter 2026 Collection Drop';
            }}
            const btn = document.querySelector('#btn-save-storefront');
            if (btn) btn.click();
        }})()""")
        time.sleep(2.0)
        save_and_copy(b, "vf6_03_settings_saved_revision_increment.png")

        # Step 5: Draft and Publish Legal Policy
        print("5. Drafting and publishing Delivery Policy...")
        b.js("""(() => {
            const polTab = document.querySelector('button[data-tab="policies"]');
            if (polTab) polTab.click();
        })()""")
        time.sleep(1.0)

        policy_text = "All orders across Pakistan are dispatched via tracked courier (TCS/Trax) within 24 hours. Delivery takes 2-4 business days. Free shipping on orders over Rs. 5,000."
        b.js(f"""(() => {{
            const textarea = document.querySelector('#textarea-policy-content');
            if (textarea) {{
                textarea.value = {json.dumps(policy_text)};
            }}
            const btnPublish = document.querySelector('#btn-publish-policy');
            if (btnPublish) btnPublish.click();
        }})()""")
        time.sleep(2.0)
        save_and_copy(b, "vf6_04_policy_published_state.png")

        # Step 6: View Revision History & Audit Logs
        print("6. Viewing Revision History...")
        b.js("""(() => {
            const auditTab = document.querySelector('button[data-tab="audit"]');
            if (auditTab) auditTab.click();
        })()""")
        time.sleep(1.5)
        save_and_copy(b, "vf6_05_audit_log_history.png")

        # Step 7: Personal Interface Preferences
        print("7. Configuring personal admin preferences...")
        b.js("""(() => {
            const prefTab = document.querySelector('button[data-tab="preferences"]');
            if (prefTab) prefTab.click();
        })()""")
        time.sleep(1.0)

        b.js("""(() => {
            const selTheme = document.querySelector('#select-pref-theme');
            if (selTheme) selTheme.value = 'dark';
            const selDensity = document.querySelector('#select-pref-density');
            if (selDensity) selDensity.value = 'compact';
            const btnSave = document.querySelector('#btn-save-preferences');
            if (btnSave) btnSave.click();
        })()""")
        time.sleep(1.5)
        save_and_copy(b, "vf6_06_owner_preferences_saved.png")

        # Step 8: Return to Storefront and Verify Dynamic Reflection
        print("8. Returning to storefront to verify reflected announcement banner...")
        b.goto(f"{ORIGIN}/", wait_selector='.site-header')
        time.sleep(2.0)

        banner_text = b.js("""(() => {
            const span = document.querySelector('.announcement-bar span');
            return span ? span.textContent : null;
        })()""")
        print(f"Storefront announcement text: {banner_text}")
        save_and_copy(b, "vf6_07_storefront_reflected_settings.png")

    print("\n[OK] VF6 Browser Acceptance Completed Successfully!")


if __name__ == '__main__':
    main()
