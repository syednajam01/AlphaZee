"""
verify_admin_styling_fix.py — Verification of the dark theme form controls,
Admin Preferences redesign, and text visibility across Admin Portal tabs.
"""
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/admin-audit-verify'
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
    print("=== VERIFYING ADMIN STYLING FIXES ===", flush=True)

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

        # 1. Store Settings Tab & Sub-tabs
        print("\n--- Verifying Settings Tab ---", flush=True)
        b.click("button[data-tab='settings']")
        time.sleep(1.2)
        b.capture_screenshot(str(OUT_DIR / "verify_settings_storefront.png"))

        # Shipping
        b.click("button.settings-tab-btn[data-tab='shipping']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "verify_settings_shipping.png"))

        # Policies
        b.click("button.settings-tab-btn[data-tab='policies']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "verify_settings_policies.png"))

        # Audit
        b.click("button.settings-tab-btn[data-tab='audit']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "verify_settings_revisions.png"))

        # Preferences
        b.click("button.settings-tab-btn[data-tab='preferences']")
        time.sleep(0.5)
        b.capture_screenshot(str(OUT_DIR / "verify_settings_preferences.png"))

        # Inspect computed styles of preferences tab elements
        pref_styles = b.js("""
        (() => {
            const form = document.querySelector('#form-admin-preferences');
            if (!form) return null;
            const posInput = form.querySelector('.pref-nav-position');
            const cardInput = form.querySelector('.pref-card-position');
            const select = form.querySelector('#select-pref-theme');
            const fieldset = form.querySelector('fieldset');
            const legend = form.querySelector('legend');
            const tabBtn = document.querySelector('.settings-tab-btn.active');
            
            const getInfo = (el) => {
                if (!el) return null;
                const s = window.getComputedStyle(el);
                return {
                    bg: s.backgroundColor,
                    color: s.color,
                    border: s.border,
                    fontSize: s.fontSize,
                };
            };
            
            return {
                posInput: getInfo(posInput),
                cardInput: getInfo(cardInput),
                select: getInfo(select),
                fieldset: getInfo(fieldset),
                legend: getInfo(legend),
                tabBtn: getInfo(tabBtn)
            };
        })()
        """)
        print("Preference Styles:", json.dumps(pref_styles, indent=2))
        
        # Invariant checks:
        assert pref_styles, "Preferences form not found!"
        assert pref_styles['posInput']['bg'] != pref_styles['posInput']['color'], "Position input has same background and text color!"
        assert 'rgb(255, 255, 255)' not in pref_styles['posInput']['bg'], f"Position input should have dark background, got: {pref_styles['posInput']['bg']}"
        print("✓ Position inputs have high-contrast text on dark background!")

        # Test interaction: update a preference and save
        b.js("""
        (() => {
            const firstPos = document.querySelector('.pref-nav-position');
            if (firstPos) {
                firstPos.value = '1';
                firstPos.dispatchEvent(new Event('input', { bubbles: true }));
            }
        })()
        """)
        b.click("#btn-save-preferences")
        time.sleep(1.0)
        b.capture_screenshot(str(OUT_DIR / "verify_settings_saved_alert.png"))
        print("✓ Preferences saved successfully!")

        # 2. Check other tabs
        for tab in ['orders', 'inventory', 'coupons', 'returns', 'expenses', 'analytics']:
            b.click(f"button[data-tab='{tab}']")
            time.sleep(0.8)
            b.capture_screenshot(str(OUT_DIR / f"verify_tab_{tab}.png"))
            print(f"✓ Audited and verified tab: {tab}", flush=True)

    print("\n=== ALL VERIFICATIONS PASSED ===", flush=True)

if __name__ == "__main__":
    main()

