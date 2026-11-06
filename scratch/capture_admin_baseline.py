"""
capture_admin_baseline.py - Captures baseline screenshots of all key Admin Portal views
before unslopping so we have clear before-and-after evidence.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / ".local/unslop-admin/baseline"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    
    # 1. Login screen
    print("Capturing login screen...", flush=True)
    b.goto("http://localhost:13000/admin")
    time.sleep(1)
    b.capture_screenshot(str(OUT_DIR / "01_admin_login.png"))

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
    time.sleep(2)

    # 2. Tabs to capture
    tabs = [
        ('overview', '02_overview.png'),
        ('products', '03_products.png'),
        ('hero', '04_hero_playlist.png'),
        ('inventory', '05_inventory.png'),
        ('orders', '06_orders.png'),
        ('suppliers', '07_suppliers.png'),
        ('expenses', '08_expenses.png'),
        ('reports', '09_reports.png'),
        ('settings', '10_settings.png'),
        ('profile', '11_profile_preferences.png')
    ]

    for tab_id, filename in tabs:
        print(f"Capturing tab: {tab_id}...", flush=True)
        b.js(f"""(() => {{
            const btn = document.querySelector('button[data-tab="{tab_id}"]');
            if (btn) btn.click();
        }})()""")
        time.sleep(1.2)
        b.capture_screenshot(str(OUT_DIR / filename))

    # Also capture mobile view of overview and settings
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="overview"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1)
    b.capture_screenshot(str(OUT_DIR / "12_mobile_overview.png"))

    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="settings"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1)
    b.capture_screenshot(str(OUT_DIR / "13_mobile_settings.png"))

print("Baseline screenshots captured successfully in .local/unslop-admin/baseline/", flush=True)

