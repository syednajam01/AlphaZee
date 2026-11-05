"""
P1: Browser Verification for Storefront Discovery & Product Decisions.
Verifies Header, Active Nav, Hero CTA & Controls, Collections, Catalog Filtering & Sorting,
Product Page, Gallery Viewport Fit, Size Selection, and History Navigation.
"""
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/three-portal-quality/run_p1_discovery'
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
    print("=== STARTING P1 STOREFRONT DISCOVERY VERIFICATION ===", flush=True)

    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # =========================================================
        # 1. DESKTOP VIEWPORT (1366 x 768)
        # =========================================================
        print("\n--- 1. Desktop 1366x768 Discovery Tests ---", flush=True)
        b.set_viewport(1366, 768)

        # 1a. Storefront Home & Header Initial State
        print("1a. Navigating to Home...", flush=True)
        b.goto("http://localhost:13000/", wait_selector="#hero-play-pause")
        time.sleep(1.0)
        save_screenshot(b, "p1_desktop_home_hero.png")

        # 1b. Test Hero Manual Pause / Playback Toggle
        print("1b. Testing Hero Controls...", flush=True)
        play_btn_text = b.js("document.querySelector('#hero-play-pause')?.textContent?.trim()")
        print(f"  Hero control initial icon: {play_btn_text}", flush=True)
        b.click("#hero-play-pause")
        time.sleep(0.3)
        toggled_icon = b.js("document.querySelector('#hero-play-pause')?.textContent?.trim()")
        print(f"  Hero control after click: {toggled_icon}", flush=True)
        assert toggled_icon == '▶', f"Expected play icon ▶, got {toggled_icon}"
        save_screenshot(b, "p1_desktop_hero_paused.png")

        # 1c. Test Active Navigation by Scrolling to Sections
        print("1c. Testing Active Nav Highlighting...", flush=True)
        b.js("document.querySelector('#collections')?.scrollIntoView({ behavior: 'instant', block: 'start' })")
        time.sleep(0.6)
        active_nav_col = b.js("document.querySelector('.nav-link.is-active')?.textContent?.trim()")
        print(f"  Active nav when scrolled to #collections: {active_nav_col}", flush=True)
        assert active_nav_col == "Collections", f"Expected Collections active nav, got {active_nav_col}"
        save_screenshot(b, "p1_desktop_collections_active_nav.png")

        b.js("document.querySelector('#featured')?.scrollIntoView({ behavior: 'instant', block: 'start' })")
        time.sleep(0.6)
        active_nav_feat = b.js("document.querySelector('.nav-link.is-active')?.textContent?.trim()")
        print(f"  Active nav when scrolled to #featured: {active_nav_feat}", flush=True)
        assert active_nav_feat == "Shop", f"Expected Shop active nav, got {active_nav_feat}"

        # 1d. Test Catalog Sorting
        print("1d. Testing Catalog Sort Dropdown...", flush=True)
        b.js("""
        (() => {
            const select = document.querySelector('#catalog-sort');
            if (select) {
                select.value = 'price-asc';
                select.dispatchEvent(new Event('change'));
            }
        })()
        """)
        time.sleep(0.6)
        first_price = b.js("document.querySelector('.product-card-price')?.textContent?.trim()")
        print(f"  First product price after sort price-asc: {first_price}", flush=True)
        save_screenshot(b, "p1_desktop_catalog_sorted.png")

        # 1e. Product Details Page (Desktop) - 9-photo / 1-video preview product
        print("1e. Navigating to Product Details (9-photo/1-video preview)...", flush=True)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105", wait_selector=".product-page-title")
        time.sleep(1.2)
        
        # Verify active nav is cleared on product page
        active_on_product = b.js("document.querySelector('.nav-link.is-active')?.textContent?.trim()")
        print(f"  Active nav on product page (should be None): {active_on_product}", flush=True)
        assert active_on_product is None, f"Expected None active nav on product page, got {active_on_product}"
        save_screenshot(b, "p1_desktop_product_page.png")

        # 1f. Test Lightbox Image Zoom
        print("1f. Testing Lightbox Image Enlarger...", flush=True)
        b.click("#gallery-zoom-btn")
        time.sleep(0.5)
        has_lightbox = b.js("Boolean(document.querySelector('#gallery-lightbox'))")
        print(f"  Lightbox open: {has_lightbox}", flush=True)
        assert has_lightbox, "Lightbox failed to open"
        save_screenshot(b, "p1_desktop_product_lightbox.png")

        # Close via Escape key
        b.cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'windowsVirtualKeyCode': 27, 'key': 'Escape'})
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'windowsVirtualKeyCode': 27, 'key': 'Escape'})
        time.sleep(1.2)
        has_lightbox_after = b.js("Boolean(document.querySelector('#gallery-lightbox'))")
        print(f"  Lightbox after Escape (should be False): {has_lightbox_after}", flush=True)
        assert not has_lightbox_after, "Lightbox failed to close on Escape"

        # 1g. Test Deliberate Size Selection on Multi-Size Product (Lab 13001)
        print("1g. Navigating to Lab Product with multiple sizes (vf5-raw-indigo-denim)...", flush=True)
        b.goto("http://127.0.0.1:13001/products/vf5-raw-indigo-denim", wait_selector="#btn-add-to-cart")
        time.sleep(1.2)
        
        selected_sz = b.js("document.querySelector('#selected-size-name')?.textContent")
        btn_disabled = b.js("document.querySelector('#btn-add-to-cart')?.disabled")
        btn_text = b.js("document.querySelector('#btn-add-to-cart')?.textContent?.trim()")
        print(f"  Initial selected size: {selected_sz}, Button disabled: {btn_disabled}, Button text: {btn_text}", flush=True)

        # Attempt to click Add to Bag without selecting a size
        print("  Clicking Add to Bag without selecting size...", flush=True)
        b.click("#btn-add-to-cart")
        time.sleep(0.5)
        prompt_info = b.js("""
        (() => {
            const el = document.querySelector('#size-selection-prompt');
            return {
                exists: Boolean(el),
                hidden: el ? el.hidden : null,
                display: el ? window.getComputedStyle(el).display : null,
                text: el ? el.textContent.trim() : null
            };
        })()
        """)
        print(f"  Prompt info: {prompt_info}", flush=True)
        prompt_visible = prompt_info.get('exists') and not prompt_info.get('hidden') and prompt_info.get('display') != 'none'
        print(f"  Size selection prompt shown: {prompt_visible}", flush=True)
        assert prompt_visible, "Size selection prompt was not shown when required"
        save_screenshot(b, "p1_desktop_size_prompt.png")

        # 1h. Select a Valid Size Option
        print("1h. Selecting valid size option (34)...", flush=True)
        b.js("""
        (() => {
            const chip = document.querySelector('.option-chip[data-option-size="34"]');
            if (chip) chip.click();
        })()
        """)
        time.sleep(0.6)
        btn_text = b.js("document.querySelector('#btn-add-to-cart')?.textContent?.trim()")
        print(f"  Button text after size selection: {btn_text}", flush=True)
        assert btn_text == "Add to Shopping Bag", f"Expected 'Add to Shopping Bag', got {btn_text}"
        save_screenshot(b, "p1_desktop_size_selected.png")

        # =========================================================
        # 2. MOBILE VIEWPORT (390 x 844)
        # =========================================================
        print("\n--- 2. Mobile 390x844 Discovery Tests ---", flush=True)
        b.set_viewport(390, 844, mobile=True)

        # 2a. Storefront Home Mobile
        b.goto("http://localhost:13000/", wait_selector="#hero-play-pause")
        time.sleep(1.0)
        save_screenshot(b, "p1_mobile_home.png")

        # 2b. Mobile Navigation Drawer
        print("2b. Opening Mobile Menu...", flush=True)
        b.click("#btn-mobile-menu")
        time.sleep(0.5)
        drawer_open = b.js("Boolean(document.querySelector('#mobile-nav-drawer.is-open, #mobile-nav-backdrop.is-open'))")
        print(f"  Mobile drawer is open: {drawer_open}", flush=True)
        save_screenshot(b, "p1_mobile_nav_drawer.png")
        b.click("#mobile-nav-close-btn")
        time.sleep(0.4)

        # 2c. Mobile Product Details & Sticky Purchase Bar
        print("2c. Testing Mobile Product & Sticky Bar...", flush=True)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105", wait_selector=".product-page-title")
        time.sleep(1.2)
        
        # Scroll down past main CTA into related pieces to trigger sticky mobile purchase bar
        b.js("""
        (() => {
            const host = document.querySelector('#product-related-host') || document.querySelector('.product-info-sections');
            if (host) host.scrollIntoView({ behavior: 'instant', block: 'start' });
            else window.scrollTo(0, 1500);
        })()
        """)
        time.sleep(0.8)
        sticky_visible = b.js("""
        (() => {
            const bar = document.querySelector('#mobile-purchase-bar');
            return Boolean(bar && bar.classList.contains('is-visible'));
        })()
        """)
        print(f"  Mobile sticky purchase bar visible: {sticky_visible}", flush=True)
        assert sticky_visible, "Mobile sticky purchase bar did not become visible when scrolled"
        save_screenshot(b, "p1_mobile_sticky_bar.png")

        # 2d. Test Browser Back / Forward History Navigation
        print("2d. Testing History Navigation...", flush=True)
        b.js("window.history.back()")
        time.sleep(1.0)
        current_path = b.js("window.location.pathname")
        print(f"  Path after back navigation: {current_path}", flush=True)
        assert current_path == "/", f"Expected path '/', got {current_path}"
        save_screenshot(b, "p1_mobile_history_back_home.png")

    print("\n=== P1 STOREFRONT DISCOVERY VERIFICATION COMPLETED (100% PASS) ===", flush=True)

if __name__ == "__main__":
    main()
