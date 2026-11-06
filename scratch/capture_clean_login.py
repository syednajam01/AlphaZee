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
    
    # Click logout if logged in
    b.js("""(() => {
        const btn = document.querySelector('#btn-admin-logout');
        if (btn && !btn.hidden) btn.click();
    })()""")
    time.sleep(1.5)

    has_card = b.js('!!document.querySelector(".admin-login-card")')
    print('Has login card after logout:', has_card)
    b.capture_screenshot(str(OUT_DIR / "01_admin_login.png"))
    b.capture_screenshot(str(ARTIFACT_DIR / "unslop_01_admin_login.png"))
    print('Captured 01_admin_login.png successfully!')

    # Now log back in
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
    time.sleep(2)
    print('Logged back in, overview title:', b.js('document.querySelector("#admin-tab-content h2, #admin-tab-content h3")?.innerText'))

