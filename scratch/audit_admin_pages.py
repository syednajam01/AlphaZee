"""
Audit all Admin Console tabs for rough styling, unreadable text, contrast issues,
and capture screenshots of each tab and sub-tab.
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

OUT_DIR = ROOT / '.local/admin-audit'
OUT_DIR.mkdir(parents=True, exist_ok=True)

ORIGIN = "http://127.0.0.1:13001"

def run_lab_cmd(args, input_bytes=None):
    cmd = ['docker', 'compose', '-f', 'compose.checkout-lab.yml'] + args
    res = subprocess.run(cmd, cwd=str(ROOT), input=input_bytes, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"Lab command failed: {res.stderr.decode('utf-8', 'ignore')}")
    return res.stdout.decode('utf-8', 'ignore')

def run_lab_py(code):
    return run_lab_cmd(['exec', '-T', 'api', 'python', '-c', code])

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
    assert csrf, f"Owner login failed: {res}"
    return csrf

def main():
    print("=== AUDITING ADMIN PAGES ===", flush=True)

    token = secrets.token_hex(4)
    owner_user = f"sample_m8_{token}"
    owner_pass = secrets.token_urlsafe(20)
    run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_user],
                input_bytes=owner_pass.encode('utf-8'))

    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        b.set_viewport(1366, 768)
        login_owner(b, owner_user, owner_pass)

        b.goto(f"{ORIGIN}/admin", wait_selector="#admin-modal")
        time.sleep(1.0)

        # Audit Settings Tab & Sub-tabs
        print("\n--- Auditing Settings Tab ---", flush=True)
        b.click("button[data-tab='settings']")
        time.sleep(1.2)
        b.capture_screenshot(str(OUT_DIR / "audit_settings_storefront.png"))

        # Sub-tab: Shipping
        b.click("button.settings-tab-btn[data-tab='shipping']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "audit_settings_shipping.png"))

        # Sub-tab: Policies
        b.click("button.settings-tab-btn[data-tab='policies']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "audit_settings_policies.png"))

        # Sub-tab: Audit / Revisions
        b.click("button.settings-tab-btn[data-tab='audit']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "audit_settings_revisions.png"))

        # Sub-tab: Admin Preferences
        b.click("button.settings-tab-btn[data-tab='preferences']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "audit_settings_preferences.png"))

        # Inspect computed styles of preferences tab elements
        pref_styles = b.js("""
        (() => {
            const form = document.querySelector('#form-admin-preferences');
            if (!form) return null;
            const fieldsets = Array.from(form.querySelectorAll('fieldset'));
            const fieldsetInfo = fieldsets.map(fs => {
                const s = window.getComputedStyle(fs);
                const legend = fs.querySelector('legend');
                const ls = legend ? window.getComputedStyle(legend) : null;
                const p = fs.querySelector('p');
                const ps = p ? window.getComputedStyle(p) : null;
                const label = fs.querySelector('label');
                const lbs = label ? window.getComputedStyle(label) : null;
                const input = fs.querySelector('input');
                const is = input ? window.getComputedStyle(input) : null;
                return {
                    fsBorder: s.border,
                    fsBg: s.backgroundColor,
                    fsColor: s.color,
                    legendColor: ls ? ls.color : null,
                    pColor: ps ? ps.color : null,
                    labelColor: lbs ? lbs.color : null,
                    inputBg: is ? is.backgroundColor : null,
                    inputColor: is ? is.color : null
                };
            });
            const tabBtns = Array.from(document.querySelectorAll('.settings-tab-btn')).map(btn => {
                const s = window.getComputedStyle(btn);
                return {
                    text: btn.textContent.trim(),
                    bg: s.backgroundColor,
                    color: s.color,
                    border: s.border
                };
            });
            return { fieldsetInfo, tabBtns };
        })()
        """)
        print("Preference Styles:", json.dumps(pref_styles, indent=2))

        # Check Other Tabs
        tabs = ['overview', 'products', 'collections', 'hero', 'media', 'inventory', 'suppliers', 'orders', 'returns', 'coupons', 'expenses', 'analytics']
        for tab in tabs:
            btn = f"button[data-tab='{tab}']"
            b.click(btn)
            time.sleep(0.8)
            b.capture_screenshot(str(OUT_DIR / f"audit_tab_{tab}.png"))
            print(f"  Audited tab: {tab}", flush=True)

    print("\n=== AUDIT COMPLETE ===", flush=True)

if __name__ == "__main__":
    main()

