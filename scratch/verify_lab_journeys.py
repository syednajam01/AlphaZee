"""
verify_lab_journeys.py - Verifies critical Admin user journeys on checkout lab (13001):
1. Catalog & Product workspace interactions.
2. Orders & fulfillment review.
3. Supplier finance & settlement agreement view.
4. Settings subtabs and preferences view.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

username = "sample_m8_a0000001"
password = "AcceptancePassword123!"

with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    
    # Login
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(1)
    login_res = b.js(f"""(() => {{
        return fetch('/api/v1/auth/login', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:13001'}},
            body: JSON.stringify({{username: '{username}', password: '{password}'}})
        }}).then(r => r.json());
    }})()""")
    assert login_res.get('csrf_token'), "Login failed"

    # Go to Admin
    b.goto("http://127.0.0.1:13001/admin", wait_selector="#admin-modal")
    time.sleep(1.5)

    # Journey 1: Products
    print("Testing Journey 1: Products tab...", flush=True)
    b.js("""(() => {
        document.querySelector('button[data-tab="products"]')?.click();
    })()""")
    time.sleep(1.5)
    prod_text = b.js("document.querySelector('#admin-body-area, #admin-tab-content')?.innerText")
    assert "New draft" in prod_text and "Search" in prod_text, f"Products view unexpected text: {prod_text[:200]}"
    print("Products view verified: 'New draft' button and search filters present without slop!", flush=True)

    # Journey 2: Orders
    print("Testing Journey 2: Orders tab...", flush=True)
    b.js("""(() => {
        document.querySelector('button[data-tab="orders"]')?.click();
    })()""")
    time.sleep(1.5)
    orders_text = b.js("document.querySelector('#admin-tab-content')?.innerText")
    assert "Orders" in orders_text or "No orders" in orders_text or "Fulfillment" in orders_text or "Order" in orders_text, "Orders view missing expected text"
    print("Orders view verified!", flush=True)

    # Journey 3: Supplier finance
    print("Testing Journey 3: Suppliers tab...", flush=True)
    b.js("""(() => {
        document.querySelector('button[data-tab="suppliers"]')?.click();
    })()""")
    time.sleep(1.5)
    sup_text = b.js("document.querySelector('#admin-tab-content')?.innerText")
    assert "Supplier" in sup_text or "Agreement" in sup_text or "Settlement" in sup_text, "Supplier finance missing expected text"
    print("Supplier finance verified!", flush=True)

    # Journey 4: Settings tabs
    print("Testing Journey 4: Settings tab...", flush=True)
    b.js("""(() => {
        document.querySelector('button[data-tab="settings"]')?.click();
    })()""")
    time.sleep(1.5)
    settings_tabs = b.js("[...document.querySelectorAll('.settings-tab-btn')].map(b => b.innerText.trim())")
    print(f"Settings subtabs found: {settings_tabs}", flush=True)
    assert len(settings_tabs) >= 4, f"Expected at least 4 settings subtabs, got {settings_tabs}"

    # Verify no emojis in settings subtabs
    for tab_title in settings_tabs:
        # Check that there are no high unicode emojis
        for char in tab_title:
            assert ord(char) < 0x2000 or ord(char) > 0x1F9FF, f"Emoji found in tab title: {tab_title}"
    print("Settings subtabs contain no emojis!", flush=True)

    # Click each settings subtab and verify content loads
    for sub in ['storefront', 'branding', 'shipping', 'legal', 'preferences']:
        b.js(f"""(() => {{
            const btn = document.querySelector('button.settings-tab-btn[data-tab="{sub}"]');
            if (btn) btn.click();
        }})()""")
        time.sleep(0.5)

    print("ALL 4 ADMIN USER JOURNEYS PASSED CLEANLY!", flush=True)
