"""
capture_unslop_admin.py - Captures post-unslop screenshots of all 13 Admin Portal views
on checkout lab (http://127.0.0.1:13001/admin) for desktop (1440x900) and mobile (390x844).
Saves to .local/unslop-admin/after/ and to artifact directory.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / ".local/unslop-admin/after"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")

# 1. Provision lab acceptance owner (must be sample_m8_[a-f0-9]{8})
username = "sample_m8_a0000001"
password = "AcceptancePassword123!"

print(f"Provisioning {username} in checkout lab...", flush=True)
cmd = ['docker', 'compose', '-f', 'compose.checkout-lab.yml', 'exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', username]
res = subprocess.run(cmd, input=password.encode('utf-8'), capture_output=True)
print("Provision output:", res.stdout.decode('utf-8', 'ignore'), flush=True)

# Clear rate limit bucket
cmd_clear = ['docker', 'compose', '-f', 'compose.checkout-lab.yml', 'exec', '-T', 'api', 'python', '-c', 
'''from app.database import SessionLocal
from app.models.auth import OwnerLoginBucket
db = SessionLocal()
db.query(OwnerLoginBucket).delete()
db.commit()
db.close()''']
subprocess.run(cmd_clear, capture_output=True)

with RedesignBrowser(Path(".local/tmp")) as b:
    # Desktop Viewport (1440 x 900)
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    
    # 1. Login screen
    print("Capturing 01_admin_login...", flush=True)
    b.goto("http://127.0.0.1:13001/admin", wait_selector=".admin-login-card")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "01_admin_login.png"))
    shutil.copy2(OUT_DIR / "01_admin_login.png", ARTIFACT_DIR / "unslop_01_admin_login.png")

    # Log in via API fetch with Origin
    print("Logging in...", flush=True)
    login_res = b.js(f"""(() => {{
        return fetch('/api/v1/auth/login', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:13001'}},
            body: JSON.stringify({{username: '{username}', password: '{password}'}})
        }}).then(r => r.json());
    }})()""")
    csrf = login_res.get('csrf_token')
    print("Login response:", login_res.get('username'), "CSRF token length:", len(csrf or ''))
    assert csrf, f"Login failed: {login_res}"

    # Navigate to admin console
    b.goto("http://127.0.0.1:13001/admin", wait_selector="#admin-modal")
    time.sleep(2)

    tabs = [
        ('overview', '02_overview.png', 'unslop_02_overview.png'),
        ('products', '03_products.png', 'unslop_03_products.png'),
        ('hero', '04_hero_playlist.png', 'unslop_04_hero_playlist.png'),
        ('inventory', '05_inventory.png', 'unslop_05_inventory.png'),
        ('orders', '06_orders.png', 'unslop_06_orders.png'),
        ('suppliers', '07_suppliers.png', 'unslop_07_suppliers.png'),
        ('expenses', '08_expenses.png', 'unslop_08_expenses.png'),
        ('analytics', '09_reports.png', 'unslop_09_reports.png'),
        ('settings', '10_settings.png', 'unslop_10_settings.png'),
    ]

    for tab_id, filename, art_name in tabs:
        print(f"Capturing tab: {tab_id} -> {filename}...", flush=True)
        b.js(f"""(() => {{
            const btn = document.querySelector('button[data-tab="{tab_id}"]');
            if (btn) btn.click();
        }})()""")
        time.sleep(1.5)
        b.capture_screenshot(str(OUT_DIR / filename))
        shutil.copy2(OUT_DIR / filename, ARTIFACT_DIR / art_name)

    # Profile preferences subtab under settings
    print("Capturing 11_profile_preferences...", flush=True)
    b.js("""(() => {
        const btn = document.querySelector('button.settings-tab-btn[data-tab="preferences"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "11_profile_preferences.png"))
    shutil.copy2(OUT_DIR / "11_profile_preferences.png", ARTIFACT_DIR / "unslop_11_profile_preferences.png")

    # 3. Mobile Viewport (390 x 844)
    print("Switching to mobile viewport (390x844)...", flush=True)
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    
    print("Capturing 12_mobile_overview...", flush=True)
    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="overview"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "12_mobile_overview.png"))
    shutil.copy2(OUT_DIR / "12_mobile_overview.png", ARTIFACT_DIR / "unslop_12_mobile_overview.png")

    print("Capturing 13_mobile_settings...", flush=True)
    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="settings"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "13_mobile_settings.png"))
    shutil.copy2(OUT_DIR / "13_mobile_settings.png", ARTIFACT_DIR / "unslop_13_mobile_settings.png")

print("All 13 post-unslop screenshots captured successfully!", flush=True)
