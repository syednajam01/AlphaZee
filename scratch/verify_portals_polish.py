"""
verify_portals_polish.py - Automated browser verification of:
1. Executive Admin Login screen & responsiveness (desktop & mobile).
2. Elimination of sidebar horizontal scroll line / overflow.
3. Luxury Vendor Login Portal & responsiveness (desktop & mobile).
4. Full vendor authentication and portal synchronization test (vendor_demo / VendorDemo123!).
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

OUT = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
OUT.mkdir(parents=True, exist_ok=True)

print("Starting comprehensive verification of login pages and sidebar scroll line...", flush=True)

# 1. Admin Login Page (Desktop & Mobile)
with RedesignBrowser(Path(".local/tmp")) as b:
    # Desktop
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(2)
    b.capture_screenshot(str(OUT / "verify_admin_login_desktop.png"))

    # Check sidebar is hidden
    sidebar_disp = b.js("window.getComputedStyle(document.querySelector('#admin-sidebar')).display")
    print(f"Admin logged out - sidebar display: {sidebar_disp}", flush=True)
    assert sidebar_disp == "none", f"Sidebar should be hidden when logged out, got {sidebar_disp}"

    # Check password toggle
    pw_type_before = b.js("document.querySelector('#admin-password').type")
    b.click("#btn-toggle-admin-pw")
    pw_type_after = b.js("document.querySelector('#admin-password').type")
    b.click("#btn-toggle-admin-pw")
    pw_type_reset = b.js("document.querySelector('#admin-password').type")
    print(f"Admin password toggle: {pw_type_before} -> {pw_type_after} -> {pw_type_reset}", flush=True)
    assert pw_type_before == "password" and pw_type_after == "text" and pw_type_reset == "password"

    # Mobile view
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    b.wait_for_selector(".admin-login-card", timeout=5)
    time.sleep(1)
    b.capture_screenshot(str(OUT / "verify_admin_login_mobile.png"))
    print("Admin login verified for desktop and mobile!", flush=True)

# 2. Admin Logged In - Verify No Horizontal Scroll Line
with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(1)
    b.js("""(() => {
        return fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:13001'},
            body: JSON.stringify({username: 'syed123', password: 'Password123!'})
        });
    })()""")
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(2)
    b.wait_for_selector("#admin-sidebar", timeout=5)

    # Check horizontal overflow on sidebar and content
    tab_overflow_x = b.js("window.getComputedStyle(document.querySelector('#admin-tab-content')).overflowX")
    sidebar_overflow_x = b.js("window.getComputedStyle(document.querySelector('#admin-sidebar')).overflowX")
    nav_overflow_x = b.js("window.getComputedStyle(document.querySelector('#admin-sidebar nav')).overflowX")
    print(f"Logged in overflow-x: tab_content={tab_overflow_x}, sidebar={sidebar_overflow_x}, nav={nav_overflow_x}", flush=True)
    assert tab_overflow_x == "hidden", f"Expected tab_content overflowX hidden, got {tab_overflow_x}"
    assert sidebar_overflow_x == "hidden", f"Expected sidebar overflowX hidden, got {sidebar_overflow_x}"
    assert nav_overflow_x == "hidden", f"Expected nav overflowX hidden, got {nav_overflow_x}"

    b.capture_screenshot(str(OUT / "verify_admin_dashboard_no_hline.png"))
    print("Admin dashboard horizontal scroll isolation verified!", flush=True)

# 3. Vendor Login Page (Desktop & Mobile)
with RedesignBrowser(Path(".local/tmp")) as b:
    # Desktop
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    b.goto("http://127.0.0.1:13001/vendor")
    time.sleep(2)
    b.capture_screenshot(str(OUT / "verify_vendor_login_desktop.png"))

    # Check body background
    body_bg = b.js("window.getComputedStyle(document.body).backgroundColor")
    print(f"Vendor login body background: {body_bg}", flush=True)

    # Check password toggle
    vp_pw_before = b.js("document.querySelector('#vp-password').type")
    b.click("#btn-toggle-vp-pw")
    vp_pw_after = b.js("document.querySelector('#vp-password').type")
    b.click("#btn-toggle-vp-pw")
    vp_pw_reset = b.js("document.querySelector('#vp-password').type")
    print(f"Vendor password toggle: {vp_pw_before} -> {vp_pw_after} -> {vp_pw_reset}", flush=True)
    assert vp_pw_before == "password" and vp_pw_after == "text" and vp_pw_reset == "password"

    # Mobile view
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    b.wait_for_selector(".vp-login-card", timeout=5)
    time.sleep(1)
    b.capture_screenshot(str(OUT / "verify_vendor_login_mobile.png"))
    print("Vendor login verified for desktop and mobile!", flush=True)

# 4. Vendor Portal Logged In Verification (vendor_demo / VendorDemo123!)
with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    b.goto("http://127.0.0.1:13001/vendor")
    time.sleep(1)
    b.wait_for_selector("#vp-username", timeout=5)
    b.js("""(() => {
        document.querySelector('#vp-username').value = 'vendor_demo';
        document.querySelector('#vp-password').value = 'VendorDemo123!';
        document.querySelector('#vp-login-btn').click();
    })()""")
    time.sleep(3)
    b.wait_for_selector(".vp-header", timeout=8)
    shop_badge = b.js("document.querySelector('.vp-shop-badge').textContent")
    print(f"Logged in vendor shop badge: {shop_badge}", flush=True)
    assert "SAMPLE" in shop_badge or len(shop_badge) > 0
    b.capture_screenshot(str(OUT / "verify_vendor_portal_logged_in.png"))
    print("Vendor Portal logged in successfully verified!", flush=True)

print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!", flush=True)

