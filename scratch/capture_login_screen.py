from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
    b.cdp('Network.clearBrowserCookies')
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)
    has_card = b.js('!!document.querySelector(".admin-login-card")')
    has_modal = b.js('!!document.querySelector("#admin-modal")')
    print('Has login card:', has_card, 'Has admin modal:', has_modal)
    b.capture_screenshot('.local/unslop-admin/after/01_admin_login.png')
    b.capture_screenshot(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8\unslop_01_admin_login.png")
    print('Done!')

