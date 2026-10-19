"""MM0 Baseline Capture Script for AlphaZee Admin Media & Collections.
Confined strictly to checkout lab (http://127.0.0.1:13001).
"""
import base64
import json
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/admin-media/baseline'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_ARTIFACTS = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity-ide\brain\ca17e23f-7699-47ff-83c4-deb583790c47")

ORIGIN = "http://127.0.0.1:13001"
LAB_COMPOSE = ['docker', 'compose', '-f', 'compose.checkout-lab.yml']

def run_lab_cmd(args, input_bytes=None):
    cmd = LAB_COMPOSE + args
    res = subprocess.run(cmd, cwd=ROOT, input=input_bytes, capture_output=True, check=True)
    return res.stdout.decode('utf-8', errors='replace').strip()

def main():
    print("=" * 70, flush=True)
    print("STARTING MM0 BASELINE SCREENSHOT CAPTURE", flush=True)
    print("=" * 70, flush=True)

    with RedesignBrowser(OUT_DIR) as b:
        b.set_viewport(1440, 900)

        def save_and_copy(filename):
            local_path = OUT_DIR / filename
            b.capture_screenshot(str(local_path))
            print(f"  Captured: {local_path}", flush=True)
            if BRAIN_ARTIFACTS.exists():
                dest = BRAIN_ARTIFACTS / filename
                shutil.copy2(local_path, dest)
                print(f"  Copied to brain: {dest}", flush=True)

        # 1. Homepage Hero baseline
        print("\n1. Navigating to Storefront Home...", flush=True)
        b.goto(f"{ORIGIN}/", wait_selector='.hero-section')
        time.sleep(1.0)
        save_and_copy("mm0_baseline_storefront_hero.png")

        # 2. Storefront Product Listing baseline
        print("\n2. Scrolling to Storefront Featured Products...", flush=True)
        b.goto(f"{ORIGIN}/#featured", wait_selector='.product-card')
        time.sleep(1.0)
        save_and_copy("mm0_baseline_storefront_grid.png")

        # 3. Provision Lab Owner & Sign In
        print("\n3. Provisioning lab owner for Admin Console inspection...", flush=True)
        token = secrets.token_hex(4)
        owner_username = f"sample_m8_{token}"
        owner_password = secrets.token_urlsafe(24)

        run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_username],
                    input_bytes=owner_password.encode('utf-8'))

        print(f"Logging in as {owner_username}...", flush=True)
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
        print("Login response:", login_res.get('username', login_res), flush=True)

        # Mount Admin Console
        b.goto(f"{ORIGIN}/admin", wait_selector='#btn-admin-logout')
        time.sleep(1.2)

        # Click on Products tab
        print("Navigating to Products tab...", flush=True)
        b.click('.admin-tab-btn[data-tab="products"]')
        time.sleep(1.5)
        save_and_copy("mm0_baseline_admin_products_list.png")

        # Click on first product "Edit product"
        print("Clicking Edit product...", flush=True)
        b.click('[data-edit-product]')
        time.sleep(1.5)
        save_and_copy("mm0_baseline_admin_product_editor.png")

        # Click on Collections tab
        print("Navigating to Collections tab...", flush=True)
        b.click('.admin-tab-btn[data-tab="collections"]')
        time.sleep(1.5)
        save_and_copy("mm0_baseline_admin_collections.png")

        # Click on Media Library tab
        print("Navigating to Media Library tab...", flush=True)
        b.click('.admin-tab-btn[data-tab="media"]')
        time.sleep(1.5)
        save_and_copy("mm0_baseline_admin_media_library.png")

    print("\n" + "=" * 70, flush=True)
    print("MM0 BASELINE CAPTURE COMPLETED SUCCESSFULLY", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
