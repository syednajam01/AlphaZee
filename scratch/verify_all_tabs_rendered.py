from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / ".local/unslop-admin/after"
ARTIFACT_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")

with RedesignBrowser(Path('.local/tmp')) as b:
    b.cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    # Log in as syed123
    b.js("""(() => {
        const u = document.querySelector('#admin-username');
        const p = document.querySelector('#admin-password');
        const f = document.querySelector('#admin-auth-form');
        if (u && p && f) {
            u.value = 'syed123';
            p.value = 'Password123!';
            f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
    })()""")
    time.sleep(2.5)

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
        b.js(f"""(() => {{
            const btn = document.querySelector('button[data-tab="{tab_id}"]');
            if (btn) btn.click();
        }})()""")
        time.sleep(1.2)
        txt = b.js('document.querySelector("#admin-tab-content")?.innerText.slice(0, 80)')
        print(f"Tab {tab_id} text: {repr(txt)}")
        b.capture_screenshot(str(OUT_DIR / filename))
        b.capture_screenshot(str(ARTIFACT_DIR / art_name))

    # Preferences tab
    b.js("""(() => {
        const btn = document.querySelector('button.settings-tab-btn[data-tab="preferences"]');
        if (btn) btn.click();
    })()""")
    time.sleep(1.2)
    txt_pref = b.js('document.querySelector("#admin-tab-content")?.innerText.slice(0, 80)')
    print(f"Tab preferences text: {repr(txt_pref)}")
    b.capture_screenshot(str(OUT_DIR / "11_profile_preferences.png"))
    b.capture_screenshot(str(ARTIFACT_DIR / "unslop_11_profile_preferences.png"))

print("Verified and recaptured all tabs!")

