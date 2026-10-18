"""Verify Phase U1 Gate: Product Routing & Deep Links."""
import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-redesign/run_u1_routing'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Verifying Phase U1 Gate on http://127.0.0.1:13001 ...")
    results = {
        "checks": [],
        "screenshots": {},
        "errors": []
    }

    with RedesignBrowser(OUT_DIR) as b:
        # 1. Direct URL navigation to valid product slug
        slug = "sample-m8-0d535c70"
        url = f"http://127.0.0.1:13001/products/{slug}"
        print(f"Navigating to direct product URL: {url}")
        b.goto(url, wait_selector='.product-page-title')
        b.wait_for_selector('.product-page-title', timeout=10)

        title = b.js("document.title")
        has_product_title = b.js("Boolean(document.querySelector('.product-page-title'))")
        product_title_text = b.js("document.querySelector('.product-page-title')?.textContent")
        price_text = b.js("document.querySelector('#product-detail-price')?.textContent")
        has_add_to_cart = b.js("Boolean(document.querySelector('#btn-add-to-cart'))")

        shot1 = b.capture_screenshot(OUT_DIR / "u1_direct_url_product.png")
        results["screenshots"]["direct_url"] = str(shot1)

        check_direct = {
            "name": "Direct URL Navigation",
            "url": url,
            "title": title,
            "has_title": has_product_title,
            "product_title": product_title_text,
            "price": price_text,
            "has_cta": has_add_to_cart,
            "passed": bool(has_product_title and "AlphaZee" in title)
        }
        results["checks"].append(check_direct)
        print("  Direct URL Check:", check_direct)

        # 2. Page Reload / Refresh on direct URL
        print("Reloading page on product URL...")
        b.cdp('Page.reload')
        time.sleep(2)
        title_after_reload = b.js("document.title")
        has_title_after_reload = b.js("Boolean(document.querySelector('.product-page-title'))")

        shot2 = b.capture_screenshot(OUT_DIR / "u1_reload_product.png")
        results["screenshots"]["reload"] = str(shot2)

        check_reload = {
            "name": "Page Reload on Deep Link",
            "title": title_after_reload,
            "has_title": has_title_after_reload,
            "passed": bool(has_title_after_reload and "AlphaZee" in title_after_reload)
        }
        results["checks"].append(check_reload)
        print("  Page Reload Check:", check_reload)

        # 3. Valid / Invalid Variant Query parameter
        # First fetch variants from page
        variants_info = b.js("""
            [...document.querySelectorAll('[data-option-size]')].map(el => el.dataset.optionSize)
        """)
        url_with_invalid_variant = f"http://127.0.0.1:13001/products/{slug}?variant=invalid_99999"
        print(f"Navigating to invalid variant query: {url_with_invalid_variant}")
        b.goto(url_with_invalid_variant)
        time.sleep(2)
        has_title_invalid_var = b.js("Boolean(document.querySelector('.product-page-title'))")
        shot3 = b.capture_screenshot(OUT_DIR / "u1_invalid_variant_fallback.png")
        results["screenshots"]["invalid_variant"] = str(shot3)

        check_invalid_var = {
            "name": "Invalid Variant Query Fallback",
            "url": url_with_invalid_variant,
            "has_title": has_title_invalid_var,
            "passed": bool(has_title_invalid_var)
        }
        results["checks"].append(check_invalid_var)
        print("  Invalid Variant Query Check:", check_invalid_var)

        # 4. Invalid Slug (404 / Unavailable Product)
        url_invalid_slug = "http://127.0.0.1:13001/products/nonexistent-archived-piece-1234"
        print(f"Navigating to invalid slug: {url_invalid_slug}")
        b.goto(url_invalid_slug)
        time.sleep(2)

        has_unavailable_title = b.js("Boolean(document.querySelector('.product-unavailable-title'))")
        unavailable_text = b.js("document.querySelector('.product-unavailable-title')?.textContent")
        has_explore_btn = b.js("Boolean(document.querySelector('.product-unavailable-view .btn-primary'))")

        shot4 = b.capture_screenshot(OUT_DIR / "u1_invalid_slug_unavailable.png")
        results["screenshots"]["invalid_slug"] = str(shot4)

        check_invalid_slug = {
            "name": "Invalid Slug / Archived Product",
            "url": url_invalid_slug,
            "has_unavailable_screen": has_unavailable_title,
            "title_text": unavailable_text,
            "has_return_btn": has_explore_btn,
            "passed": bool(has_unavailable_title and has_explore_btn)
        }
        results["checks"].append(check_invalid_slug)
        print("  Invalid Slug Check:", check_invalid_slug)

        # 5. Back / Forward Navigation
        print("Testing Back / Forward SPA history...")
        b.goto("http://127.0.0.1:13001/")
        time.sleep(2)
        is_home_init = b.js("Boolean(document.querySelector('#featured'))")

        # Click product card media link
        has_media_link = b.js("Boolean(document.querySelector('.product-card-media-link'))")
        if has_media_link:
            b.click('.product-card-media-link')
            b.wait_for_selector('.product-page-title', timeout=8)
            is_product_after_click = b.js("Boolean(document.querySelector('.product-page-title'))")

            # Go Back
            b.js("window.history.back()")
            b.wait_for_selector('#featured', timeout=8)
            is_home_after_back = b.js("Boolean(document.querySelector('#featured'))")

            # Go Forward
            b.js("window.history.forward()")
            b.wait_for_selector('.product-page-title', timeout=8)
            is_product_after_forward = b.js("Boolean(document.querySelector('.product-page-title'))")

            shot5 = b.capture_screenshot(OUT_DIR / "u1_history_forward_product.png")
            results["screenshots"]["history_forward"] = str(shot5)

            check_history = {
                "name": "SPA History Back/Forward",
                "is_home_init": is_home_init,
                "is_product_after_click": is_product_after_click,
                "is_home_after_back": is_home_after_back,
                "is_product_after_forward": is_product_after_forward,
                "passed": bool(is_home_init and is_product_after_click and is_home_after_back and is_product_after_forward)
            }
            results["checks"].append(check_history)
            print("  Back/Forward Check:", check_history)

        # 6. Mobile Viewport Check (390x844)
        print("Checking mobile product layout (390x844)...")
        b.cdp('Emulation.setDeviceMetricsOverride', {
            'width': 390,
            'height': 844,
            'deviceScaleFactor': 2,
            'mobile': True
        })
        b.goto(f"http://127.0.0.1:13001/products/{slug}", wait_selector='.product-page-title')
        b.wait_for_selector('.product-page-title', timeout=10)

        has_mobile_title = b.js("Boolean(document.querySelector('.product-page-title'))")
        has_mobile_bar = b.js("Boolean(document.querySelector('#mobile-purchase-bar'))")

        shot6 = b.capture_screenshot(OUT_DIR / "u1_mobile_product_page.png")
        results["screenshots"]["mobile_product"] = str(shot6)

        check_mobile = {
            "name": "Mobile Product Page Shell",
            "has_title": has_mobile_title,
            "has_mobile_bar": has_mobile_bar,
            "passed": bool(has_mobile_title and has_mobile_bar)
        }
        results["checks"].append(check_mobile)
        print("  Mobile Product Page Check:", check_mobile)

        results["errors"] = b.errors
        (OUT_DIR / "u1_verification.json").write_text(json.dumps(results, indent=2))
        print("U1 Gate verification completed successfully.")

if __name__ == '__main__':
    main()
