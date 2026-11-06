"""
capture_admin_after.py - Captures post-unslop screenshots of all key Admin Portal views
at desktop (1440x900) and mobile (390x844).
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / ".local/unslop-admin/after"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")

with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    
    # 1. Login screen
    print("Capturing post-unslop login screen...", flush=True)
    b.goto("http://localhost:13000/admin")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "01_admin_login.png"))
    b.capture_screenshot(str(ARTIFACT_DIR / "unslop_01_admin_login.png"))

    # Log in
    b.js("""(() => {
        const u = document.querySelector('#admin-username');
        const p = document.querySelector('#admin-password');
        const f = document.querySelector('#admin-login-form');
        if (u && p && f) {
            u.value = 'syed123';
            p.value = 'Password123!';
            f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
    })()""")
    time.sleep(2.5)

    # 2. Tabs to capture
    tabs = [
        ('overview', '02_overview.png', 'unslop_02_overview.png'),
        ('products', '03_products.png', 'unslop_03_products.png'),
        ('hero', '04_hero_playlist.png', 'unslop_04_hero_playlist.png'),
        ('inventory', '05_inventory.png', 'unslop_05_inventory.png'),
        ('orders', '06_orders.png', 'unslop_06_orders.png'),
        ('suppliers', '07_suppliers.png', 'unslop_07_suppliers.png'),
        ('expenses', '08_expenses.png', 'unslop_08_expenses.png'),
        ('reports', '09_reports.png', 'unslop_09_reports.png'),
        ('settings', '10_settings.png', 'unslop_10_settings.png'),
    ]

    for tab_id, filename, art_name in tabs:
        print(f"Capturing tab: {tab_id}...", flush=True)
        b.js(f"""(() => {{
            const btn = document.querySelector('button[data-tab="{tab_id}"]');
            if (btn) btn.click();
        }})()""")
        time.sleep(1.5)
        b.capture_screenshot(str(OUT_DIR / filename))
        b.capture_screenshot(str(ARTIFACT_DIR / art_name))

    # Profile preferences subtab under settings
    print("Capturing profile preferences subtab...", flush=True)
    b.js("""(() => {
        const btn = document.querySelector('button.settings-tab-btn[data-tab="preferences"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "11_profile_preferences.png"))
    b.capture_screenshot(str(ARTIFACT_DIR / "unslop_11_profile_preferences.png"))

    # 3. Mobile captures
    print("Capturing mobile overview & settings...", flush=True)
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="overview"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "12_mobile_overview.png"))
    b.capture_screenshot(str(ARTIFACT_DIR / "unslop_12_mobile_overview.png"))

    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="settings"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.5)
    b.capture_screenshot(str(OUT_DIR / "13_mobile_settings.png"))
    b.capture_screenshot(str(ARTIFACT_DIR / "unslop_13_mobile_settings.png"))

print("Post-unslop screenshots captured successfully!", flush=True)

