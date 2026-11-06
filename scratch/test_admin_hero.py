from pathlib import Path
import sys, time, json
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

OUT = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")

with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    b.goto("http://localhost:13000/admin")
    time.sleep(1)
    
    # Fill login form if visible
    has_form = b.js("!!document.querySelector('#admin-login-form')")
    print("Has login form:", has_form)
    if has_form:
        b.js("""(() => {
            document.querySelector('#admin-username').value = 'syed123';
            document.querySelector('#admin-password').value = 'Password123!';
            document.querySelector('#admin-login-form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        })()""")
        time.sleep(2)
        print("Logged in, current URL:", b.js("window.location.href"))

    # Check tabs
    tabs = b.js("""(() => {
        return Array.from(document.querySelectorAll('button[data-tab]')).map(b => b.dataset.tab);
    })()""")
    print("Available tabs:", tabs)

    # Click hero tab
    b.js("""(() => {
        const btn = document.querySelector('button[data-tab="hero"]');
        if (btn) btn.click();
    })()""")
    time.sleep(2)

    guide = b.js("""(() => {
        const c = document.querySelector('.hero-guidelines-card');
        return c ? c.innerText : null;
    })()""")
    print("Guidelines card text:\n", guide)

    b.capture_screenshot(str(OUT / "verify_admin_hero_guidelines.png"))
    print("Captured verify_admin_hero_guidelines.png successfully!")

