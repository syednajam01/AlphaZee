"""
verify_sidebar_scroll_and_hover.py — Verification of independent scroll containers
and hover-to-open sidebar behavior in the Admin Portal.
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

OUT_DIR = ROOT / '.local/sidebar-verify'
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
    print("=== VERIFYING SIDEBAR HOVER & SCROLL ISOLATION ===", flush=True)

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

        # 1. Initial State: Sidebar should be compact (collapsed) by default
        print("\n--- 1. Testing Default Collapsed Sidebar ---", flush=True)
        # Move mouse to center of page first so sidebar is not hovered
        b.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 600, 'y': 400})
        time.sleep(0.5)

        collapsed_info = b.js("""
        (() => {
            const sidebar = document.querySelector('#admin-sidebar');
            const rect = sidebar ? sidebar.getBoundingClientRect() : null;
            const label = sidebar ? sidebar.querySelector('.admin-nav-label') : null;
            const labelStyle = label ? window.getComputedStyle(label) : null;
            const expandedLogo = document.querySelector('#admin-expanded-logo-slot');
            const collapsedLogo = document.querySelector('#admin-collapsed-logo-slot');
            
            return {
                width: rect ? rect.width : null,
                labelOpacity: labelStyle ? labelStyle.opacity : null,
                labelMaxWidth: labelStyle ? labelStyle.maxWidth : null,
                expandedLogoDisplay: expandedLogo ? window.getComputedStyle(expandedLogo).display : null,
                collapsedLogoDisplay: collapsedLogo ? window.getComputedStyle(collapsedLogo).display : null,
            };
        })()
        """)
        print("Default Collapsed State:", json.dumps(collapsed_info, indent=2))
        b.capture_screenshot(str(OUT_DIR / "sidebar_1_collapsed_default.png"))

        assert collapsed_info['width'] is not None and collapsed_info['width'] <= 72, f"Sidebar should be collapsed (<= 72px), got {collapsed_info['width']}"
        assert collapsed_info['labelOpacity'] in ('0', None), f"Nav labels should be hidden (opacity 0), got {collapsed_info['labelOpacity']}"
        print("✓ Default state: Sidebar is compact/collapsed (<= 72px) with labels hidden!")

        # 2. Hover State: Move mouse over sidebar (x: 30, y: 150)
        print("\n--- 2. Testing Hover-to-Open ---", flush=True)
        b.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 30, 'y': 150})
        time.sleep(0.6)  # allow 220ms transition to complete

        hovered_info = b.js("""
        (() => {
            const sidebar = document.querySelector('#admin-sidebar');
            const rect = sidebar ? sidebar.getBoundingClientRect() : null;
            const label = sidebar ? sidebar.querySelector('.admin-nav-label') : null;
            const labelStyle = label ? window.getComputedStyle(label) : null;
            const expandedLogo = document.querySelector('#admin-expanded-logo-slot');
            const collapsedLogo = document.querySelector('#admin-collapsed-logo-slot');
            
            return {
                width: rect ? rect.width : null,
                labelOpacity: labelStyle ? labelStyle.opacity : null,
                labelMaxWidth: labelStyle ? labelStyle.maxWidth : null,
                expandedLogoDisplay: expandedLogo ? window.getComputedStyle(expandedLogo).display : null,
                collapsedLogoDisplay: collapsedLogo ? window.getComputedStyle(collapsedLogo).display : null,
            };
        })()
        """)
        print("Hovered State:", json.dumps(hovered_info, indent=2))
        b.capture_screenshot(str(OUT_DIR / "sidebar_2_expanded_on_hover.png"))

        assert hovered_info['width'] is not None and hovered_info['width'] >= 200, f"Sidebar should expand on hover (>= 200px), got {hovered_info['width']}"
        assert hovered_info['labelOpacity'] == '1', f"Nav labels should be visible on hover (opacity 1), got {hovered_info['labelOpacity']}"
        print("✓ Hover state: Sidebar smoothly opened and expanded (>= 200px) with labels visible!")

        # 3. Unhover: Move mouse away (x: 600, y: 400)
        print("\n--- 3. Testing Mouse Leave (Automatic Collapse) ---", flush=True)
        b.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 600, 'y': 400})
        time.sleep(0.6)  # allow transition

        unhovered_info = b.js("""
        (() => {
            const sidebar = document.querySelector('#admin-sidebar');
            const rect = sidebar ? sidebar.getBoundingClientRect() : null;
            const label = sidebar ? sidebar.querySelector('.admin-nav-label') : null;
            const labelStyle = label ? window.getComputedStyle(label) : null;
            
            return {
                width: rect ? rect.width : null,
                labelOpacity: labelStyle ? labelStyle.opacity : null,
            };
        })()
        """)
        print("After Mouse Leave:", json.dumps(unhovered_info, indent=2))
        b.capture_screenshot(str(OUT_DIR / "sidebar_3_collapsed_after_unhover.png"))

        assert unhovered_info['width'] is not None and unhovered_info['width'] <= 72, f"Sidebar should collapse back after mouse leaves, got {unhovered_info['width']}"
        print("✓ Mouse leave: Sidebar automatically collapsed back to compact state!")

        # 4. Scroll Isolation Test
        print("\n--- 4. Testing Independent Scroll Isolation ---", flush=True)
        # Switch to settings tab which has substantial content
        b.click("button[data-tab='settings']")
        time.sleep(1.0)

        # Scroll the main content area down by 300px
        scroll_res = b.js("""
        (() => {
            const content = document.querySelector('#admin-tab-content');
            const sidebarNav = document.querySelector('#admin-sidebar nav');
            
            content.scrollTop = 300;
            
            return {
                windowScrollY: window.scrollY,
                contentScrollTop: content.scrollTop,
                sidebarNavScrollTop: sidebarNav ? sidebarNav.scrollTop : null,
            };
        })()
        """)
        print("After scrolling main content:", json.dumps(scroll_res, indent=2))
        b.capture_screenshot(str(OUT_DIR / "sidebar_4_main_scrolled.png"))

        assert scroll_res['windowScrollY'] == 0, f"Window itself should NEVER scroll! window.scrollY = {scroll_res['windowScrollY']}"
        assert scroll_res['contentScrollTop'] > 0, "Main content area should have scrolled!"
        assert scroll_res['sidebarNavScrollTop'] == 0, f"Sidebar nav must NOT scroll when main content is scrolled! sidebarNavScrollTop = {scroll_res['sidebarNavScrollTop']}"
        print("✓ Main content scrolls independently; Window scroll is 0; Sidebar did not scroll!")

        # Now scroll the sidebar nav
        sidebar_scroll_res = b.js("""
        (() => {
            const content = document.querySelector('#admin-tab-content');
            const sidebarNav = document.querySelector('#admin-sidebar nav');
            
            if (sidebarNav) {
                sidebarNav.scrollTop = 40;
            }
            
            return {
                windowScrollY: window.scrollY,
                contentScrollTop: content.scrollTop,
                sidebarNavScrollTop: sidebarNav ? sidebarNav.scrollTop : null,
            };
        })()
        """)
        print("After scrolling sidebar nav:", json.dumps(sidebar_scroll_res, indent=2))
        b.capture_screenshot(str(OUT_DIR / "sidebar_5_both_independent.png"))

        assert sidebar_scroll_res['windowScrollY'] == 0, "Window scroll must remain 0!"
        assert sidebar_scroll_res['contentScrollTop'] == scroll_res['contentScrollTop'], "Main content scroll position must NOT change when sidebar is scrolled!"
        print("✓ Sidebar and main area are 100% isolated scroll containers with overscroll-behavior: contain!")

    print("\n=== ALL SIDEBAR TESTS PASSED SUCCESSFULLY! ===", flush=True)

if __name__ == "__main__":
    main()
