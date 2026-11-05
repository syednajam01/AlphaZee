"""P0: Capture baseline screenshots and inventory across the three portals (Storefront, Admin, Vendor)."""
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/three-portal-quality/run_p0_baseline'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT SAVED] {filename}", flush=True)

def main():
    print("=== STARTING P0 BASELINE INVENTORY & SCREENSHOT CAPTURE ===", flush=True)

    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # =========================================================
        # 1. DESKTOP VIEWPORT (1366 x 768)
        # =========================================================
        print("\n--- 1. Desktop 1366x768 Baseline ---", flush=True)
        b.set_viewport(1366, 768)

        # 1a. Storefront Home
        b.goto("http://localhost:13000/", wait_selector=".site-header")
        time.sleep(0.8)
        save_screenshot(b, "p0_desktop_storefront_home.png")

        # 1b. Storefront Cart Drawer (Empty)
        b.click("#btn-cart")
        time.sleep(0.5)
        save_screenshot(b, "p0_desktop_storefront_cart_drawer.png")
        b.click("#cart-close-btn")
        time.sleep(0.3)

        # 1c. Storefront Order Tracking Modal
        b.click("a[href='#track']")
        time.sleep(0.5)
        save_screenshot(b, "p0_desktop_storefront_order_tracking.png")
        b.click("#tracking-close-btn")
        time.sleep(0.3)

        # 1d. Storefront Product Details Page
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105", wait_selector=".product-page-title")
        time.sleep(0.8)
        save_screenshot(b, "p0_desktop_storefront_product.png")

        # 1e. Storefront Checkout in Lab (13001)
        print("\n--- 1e. Storefront Lab Checkout (13001) ---", flush=True)
        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector="#btn-add-to-cart")
        time.sleep(0.6)
        # Select first available size if required
        b.js("""
        (() => {
            const chip = document.querySelector('.option-chip:not(:disabled)');
            if (chip) chip.click();
        })()
        """)
        time.sleep(0.3)
        # Click Add to Cart
        b.click("#btn-add-to-cart")
        time.sleep(0.6)
        # Click checkout inside cart drawer
        b.click("#btn-checkout")
        time.sleep(0.8)
        save_screenshot(b, "p0_desktop_storefront_checkout_lab.png")

        # 1f. Admin Portal Login
        print("\n--- 1f. Admin Portal Baseline ---", flush=True)
        b.goto("http://localhost:13000/admin", wait_selector="#admin-auth-form, .admin-page")
        time.sleep(1.0)
        save_screenshot(b, "p0_desktop_admin_portal.png")

        # 1g. Vendor Portal Login
        print("\n--- 1g. Vendor Portal Baseline ---", flush=True)
        b.goto("http://localhost:13000/vendor", wait_selector="#vp-login-form, .vendor-portal-container")
        time.sleep(1.0)
        save_screenshot(b, "p0_desktop_vendor_portal.png")

        # =========================================================
        # 2. MOBILE VIEWPORT (390 x 844)
        # =========================================================
        print("\n--- 2. Mobile 390x844 Baseline ---", flush=True)
        b.set_viewport(390, 844, mobile=True)

        # 2a. Storefront Home Mobile
        b.goto("http://localhost:13000/", wait_selector=".site-header")
        time.sleep(0.8)
        save_screenshot(b, "p0_mobile_storefront_home.png")

        # 2b. Storefront Mobile Nav Drawer
        b.click("#btn-mobile-menu")
        time.sleep(0.5)
        save_screenshot(b, "p0_mobile_storefront_nav_drawer.png")
        b.click("#mobile-nav-close-btn")
        time.sleep(0.3)

        # 2c. Storefront Cart Drawer Mobile
        b.click("#btn-cart")
        time.sleep(0.5)
        save_screenshot(b, "p0_mobile_storefront_cart_drawer.png")
        b.click("#cart-close-btn")
        time.sleep(0.3)

        # 2d. Storefront Product Mobile
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105", wait_selector=".product-page-title")
        time.sleep(0.8)
        save_screenshot(b, "p0_mobile_storefront_product.png")

        # 2e. Storefront Checkout Lab Mobile
        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector="#btn-add-to-cart")
        time.sleep(0.6)
        b.js("""
        (() => {
            const chip = document.querySelector('.option-chip:not(:disabled)');
            if (chip) chip.click();
        })()
        """)
        time.sleep(0.3)
        b.click("#btn-add-to-cart")
        time.sleep(0.6)
        b.click("#btn-checkout")
        time.sleep(0.8)
        save_screenshot(b, "p0_mobile_storefront_checkout_lab.png")

        # 2f. Admin Portal Mobile
        b.goto("http://localhost:13000/admin", wait_selector="#admin-auth-form, .admin-page")
        time.sleep(1.0)
        save_screenshot(b, "p0_mobile_admin_portal.png")

        # 2g. Vendor Portal Mobile
        b.goto("http://localhost:13000/vendor", wait_selector="#vp-login-form, .vendor-portal-container")
        time.sleep(1.0)
        save_screenshot(b, "p0_mobile_vendor_portal.png")

    print("\n=== P0 BASELINE CAPTURE COMPLETED SUCCESSFULLY ===", flush=True)

if __name__ == '__main__':
    main()
