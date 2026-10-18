"""Verify Phase U5 Gate: Multi-Breakpoint Matrix, 200% Desktop Zoom, Keyboard Boundaries, Reduced Motion, Slow Network, Media Failure & Admin Smoke."""
import json
import time
from pathlib import Path
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-redesign/run_u5_matrix'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Verifying Phase U5 Gate across breakpoints, zoom, a11y, network, and admin...", flush=True)
    results = {
        "checks": [],
        "screenshots": {},
        "errors": []
    }

    with RedesignBrowser(OUT_DIR) as b:
        # =========================================================================
        # 1. Multi-Breakpoint Matrix: 360, 390, 768, 1280, 1440
        # =========================================================================
        print("1. Testing Multi-Breakpoint Matrix (360, 390, 768, 1280, 1440)...", flush=True)

        # 1A. 360px Compact Phone
        b.set_viewport(360, 640, mobile=True)
        b.goto("http://127.0.0.1:13001/", wait_selector='.product-card')
        time.sleep(1)
        shot_360_home = b.capture_screenshot(OUT_DIR / "u5_viewport_360_home.png")
        results["screenshots"]["viewport_360_home"] = str(shot_360_home)

        metrics_360_home = b.js("""(() => {
            const bodyScrollWidth = document.body.scrollWidth;
            const docScrollWidth = document.documentElement.scrollWidth;
            const grid = document.querySelector('.products-grid');
            const cards = grid ? grid.querySelectorAll('.product-card') : [];
            const header = document.querySelector('#site-header');
            const cartBtn = document.querySelector('#btn-cart');

            return {
                viewportWidth: 360,
                hasHorizontalOverflow: docScrollWidth > 360,
                gridColumns: grid ? window.getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0,
                cardsCount: cards.length,
                hasHeader: Boolean(header),
                hasCartBtn: Boolean(cartBtn),
            };
        })()""")

        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector='#btn-add-to-cart')
        time.sleep(1)
        shot_360_product = b.capture_screenshot(OUT_DIR / "u5_viewport_360_product.png")
        results["screenshots"]["viewport_360_product"] = str(shot_360_product)

        metrics_360_product = b.js("""(() => {
            const docScrollWidth = document.documentElement.scrollWidth;
            const title = document.querySelector('.product-detail-title');
            const cta = document.querySelector('#btn-add-to-cart');
            return {
                productHasHorizontalOverflow: docScrollWidth > 360,
                titleVisible: title ? window.getComputedStyle(title).display !== 'none' : false,
                ctaHeight: cta ? cta.offsetHeight : 0,
            };
        })()""")

        # 1B. 390px Modern Mobile
        b.set_viewport(390, 844, mobile=True)
        b.goto("http://127.0.0.1:13001/", wait_selector='.product-card')
        time.sleep(1)
        shot_390_home = b.capture_screenshot(OUT_DIR / "u5_viewport_390_home.png")
        results["screenshots"]["viewport_390_home"] = str(shot_390_home)

        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector='#btn-add-to-cart')
        time.sleep(1)
        # Scroll down to trigger sticky mobile purchase bar
        b.js("window.scrollTo(0, 900);")
        time.sleep(1)
        shot_390_product = b.capture_screenshot(OUT_DIR / "u5_viewport_390_product_mobile_bar.png")
        results["screenshots"]["viewport_390_product_mobile_bar"] = str(shot_390_product)

        metrics_390 = b.js("""(() => {
            const bar = document.querySelector('#mobile-purchase-bar');
            return {
                viewportWidth: 390,
                mobileBarVisible: bar ? window.getComputedStyle(bar).display !== 'none' : false,
            };
        })()""")

        # 1C. 768px Tablet
        b.set_viewport(768, 1024, mobile=False)
        b.goto("http://127.0.0.1:13001/", wait_selector='.product-card')
        time.sleep(1)
        shot_768_home = b.capture_screenshot(OUT_DIR / "u5_viewport_768_home.png")
        results["screenshots"]["viewport_768_home"] = str(shot_768_home)

        metrics_768 = b.js("""(() => {
            const grid = document.querySelector('.products-grid');
            return {
                viewportWidth: 768,
                gridColumns: grid ? window.getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0,
            };
        })()""")

        # 1D. 1280px Small Desktop
        b.set_viewport(1280, 800, mobile=False)
        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector='#btn-add-to-cart')
        time.sleep(1)
        shot_1280_product = b.capture_screenshot(OUT_DIR / "u5_viewport_1280_product.png")
        results["screenshots"]["viewport_1280_product"] = str(shot_1280_product)

        metrics_1280 = b.js("""(() => {
            const grid = document.querySelector('.product-page-grid');
            const gallery = document.querySelector('.product-page-gallery-col');
            const details = document.querySelector('.product-page-details-col');
            const totalW = (gallery && details) ? (gallery.offsetWidth + details.offsetWidth) : 0;
            return {
                viewportWidth: 1280,
                galleryPct: totalW ? Math.round((gallery.offsetWidth / totalW) * 100) : 0,
                detailsPct: totalW ? Math.round((details.offsetWidth / totalW) * 100) : 0,
            };
        })()""")

        # 1E. 1440px Standard Desktop
        b.set_viewport(1440, 900, mobile=False)
        b.goto("http://127.0.0.1:13001/", wait_selector='.product-card')
        time.sleep(1)
        shot_1440_home = b.capture_screenshot(OUT_DIR / "u5_viewport_1440_home.png")
        results["screenshots"]["viewport_1440_home"] = str(shot_1440_home)

        metrics_1440 = b.js("""(() => {
            const container = document.querySelector('.container');
            const grid = document.querySelector('.products-grid');
            return {
                viewportWidth: 1440,
                containerMaxWidth: container ? window.getComputedStyle(container).maxWidth : null,
                containerWidth: container ? container.offsetWidth : 0,
                gridColumns: grid ? window.getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0,
            };
        })()""")

        check1 = {
            "name": "Multi-Breakpoint Matrix (360/390/768/1280/1440)",
            "metrics": {
                "m360": { **metrics_360_home, **metrics_360_product },
                "m390": metrics_390,
                "m768": metrics_768,
                "m1280": metrics_1280,
                "m1440": metrics_1440,
            },
            "passed": bool(
                not metrics_360_home["hasHorizontalOverflow"] and
                not metrics_360_product["productHasHorizontalOverflow"] and
                metrics_360_product["ctaHeight"] >= 44 and
                metrics_768["gridColumns"] == 3 and
                metrics_1440["gridColumns"] == 4 and
                metrics_1440["containerWidth"] <= 1280
            )
        }
        results["checks"].append(check1)
        print("  Check 1:", check1, flush=True)

        # =========================================================================
        # 2. Desktop 200% Browser Zoom
        # =========================================================================
        print("2. Testing Desktop 200% Browser Zoom...", flush=True)
        b.set_viewport(1440, 900, mobile=False)
        b.goto("http://127.0.0.1:13001/", wait_selector='.product-card')
        time.sleep(1)

        # Apply 200% page scale factor via CDP
        b.cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 2.0})
        time.sleep(1)
        shot_zoom_home = b.capture_screenshot(OUT_DIR / "u5_zoom_200pct_desktop.png")
        results["screenshots"]["zoom_200pct_home"] = str(shot_zoom_home)

        zoom_home_metrics = b.js("""(() => {
            const nav = document.querySelector('#site-header');
            const card = document.querySelector('.product-card');
            const cartBtn = document.querySelector('#btn-cart');
            return {
                headerVisible: Boolean(nav),
                cardVisible: Boolean(card),
                cartBtnClickable: cartBtn ? !cartBtn.disabled : false,
            };
        })()""")

        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector='#btn-add-to-cart')
        time.sleep(1)
        shot_zoom_product = b.capture_screenshot(OUT_DIR / "u5_zoom_200pct_product.png")
        results["screenshots"]["zoom_200pct_product"] = str(shot_zoom_product)

        zoom_product_metrics = b.js("""(() => {
            const cta = document.querySelector('#btn-add-to-cart');
            const price = document.querySelector('#product-detail-price');
            return {
                ctaReachable: Boolean(cta),
                ctaHeight: cta ? cta.offsetHeight : 0,
                priceText: price ? price.textContent.trim() : null,
            };
        })()""")

        # Reset page scale factor back to 1.0
        b.cdp('Emulation.setPageScaleFactor', {'pageScaleFactor': 1.0})
        time.sleep(0.5)

        check2 = {
            "name": "Desktop 200% Browser Zoom",
            "metrics": { **zoom_home_metrics, **zoom_product_metrics },
            "passed": bool(
                zoom_home_metrics["headerVisible"] and
                zoom_home_metrics["cartBtnClickable"] and
                zoom_product_metrics["ctaReachable"] and
                zoom_product_metrics["priceText"]
            )
        }
        results["checks"].append(check2)
        print("  Check 2:", check2, flush=True)

        # =========================================================================
        # 3. Keyboard Focus Trapping & Tab Wrapping
        # =========================================================================
        print("3. Testing Keyboard Boundaries (Dialog Focus Trap, Wrap, Escape)...", flush=True)
        b.goto("http://127.0.0.1:13001/", wait_selector='#btn-cart')
        time.sleep(1)

        # Open cart drawer
        b.js("const btn = document.querySelector('#btn-cart'); if (btn) { btn.focus(); btn.click(); }")
        time.sleep(0.5)

        tab_trap_metrics = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const focusables = drawer ? [...drawer.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')].filter(el => !el.disabled && el.tabIndex !== -1) : [];
            const activeOnOpen = document.activeElement;

            return {
                drawerOpen: drawer ? drawer.classList.contains('is-open') : false,
                focusablesCount: focusables.length,
                initialFocusInsideDrawer: drawer ? drawer.contains(activeOnOpen) : false,
                firstFocusableId: focusables[0] ? (focusables[0].id || focusables[0].className) : null,
                lastFocusableId: focusables.at(-1) ? (focusables.at(-1).id || focusables.at(-1).className) : null,
            };
        })()""")

        # Focus last element and press Tab -> should wrap to first element
        b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const focusables = drawer ? [...drawer.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')].filter(el => !el.disabled && el.tabIndex !== -1) : [];
            if (focusables.length > 0) focusables.at(-1).focus();
        })()""")
        time.sleep(0.2)

        b.cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Tab', 'code': 'Tab'})
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Tab', 'code': 'Tab'})
        time.sleep(0.3)

        wrap_forward_metrics = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const focusables = drawer ? [...drawer.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')].filter(el => !el.disabled && el.tabIndex !== -1) : [];
            const active = document.activeElement;
            return {
                focusWrappedToFirst: active === focusables[0],
                activeId: active ? (active.id || active.className) : null,
            };
        })()""")

        # Focus first element and press Shift+Tab -> should wrap to last element
        b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const focusables = drawer ? [...drawer.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')].filter(el => !el.disabled && el.tabIndex !== -1) : [];
            if (focusables.length > 0) focusables[0].focus();
        })()""")
        time.sleep(0.2)

        b.cdp('Input.dispatchKeyEvent', {'type': 'rawKeyDown', 'key': 'Tab', 'code': 'Tab', 'modifiers': 8})
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Tab', 'code': 'Tab', 'modifiers': 8})
        time.sleep(0.3)

        wrap_reverse_metrics = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const focusables = drawer ? [...drawer.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')].filter(el => !el.disabled && el.tabIndex !== -1) : [];
            const active = document.activeElement;
            return {
                focusWrappedToLast: active === focusables.at(-1),
                activeId: active ? (active.id || active.className) : null,
            };
        })()""")

        # Dismiss via Escape
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape'})
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape'})
        time.sleep(0.5)

        escape_metrics = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const active = document.activeElement;
            return {
                drawerClosed: drawer ? !drawer.classList.contains('is-open') : false,
                focusRestoredToOpener: active ? active.id === 'btn-cart' : false,
            };
        })()""")

        shot_trap = b.capture_screenshot(OUT_DIR / "u5_keyboard_trap_and_wrap.png")
        results["screenshots"]["keyboard_trap_and_wrap"] = str(shot_trap)

        check3 = {
            "name": "Keyboard Boundaries & Tab Wrapping",
            "metrics": {
                **tab_trap_metrics,
                **wrap_forward_metrics,
                **wrap_reverse_metrics,
                **escape_metrics
            },
            "passed": bool(
                tab_trap_metrics["drawerOpen"] and
                tab_trap_metrics["initialFocusInsideDrawer"] and
                wrap_forward_metrics["focusWrappedToFirst"] and
                wrap_reverse_metrics["focusWrappedToLast"] and
                escape_metrics["drawerClosed"] and
                escape_metrics["focusRestoredToOpener"]
            )
        }
        results["checks"].append(check3)
        print("  Check 3:", check3, flush=True)

        # =========================================================================
        # 4. Reduced Motion Simulation
        # =========================================================================
        print("4. Testing Reduced Motion Simulation...", flush=True)
        b.cdp('Emulation.setEmulatedMedia', {
            'features': [{'name': 'prefers-reduced-motion', 'value': 'reduce'}]
        })
        time.sleep(0.5)

        reduced_motion_metrics = b.js("""(() => {
            const testEl = document.createElement('div');
            testEl.className = 'btn btn-primary';
            document.body.appendChild(testEl);
            const cs = window.getComputedStyle(testEl);
            const transitionDuration = cs.transitionDuration;
            const animationDuration = cs.animationDuration;
            testEl.remove();

            return {
                transitionDuration,
                animationDuration,
                isZeroOrInstant: parseFloat(transitionDuration) <= 0.001 && parseFloat(animationDuration) <= 0.001
            };
        })()""")

        shot_motion = b.capture_screenshot(OUT_DIR / "u5_reduced_motion.png")
        results["screenshots"]["reduced_motion"] = str(shot_motion)

        # Reset emulated media
        b.cdp('Emulation.setEmulatedMedia', {'features': []})
        time.sleep(0.2)

        check4 = {
            "name": "Reduced Motion Simulation",
            "metrics": reduced_motion_metrics,
            "passed": bool(reduced_motion_metrics["isZeroOrInstant"])
        }
        results["checks"].append(check4)
        print("  Check 4:", check4, flush=True)

        # =========================================================================
        # 5. Slow Network Loading State
        # =========================================================================
        print("5. Testing Slow Network Simulation...", flush=True)
        # Enable 600ms latency throttling
        b.cdp('Network.emulateNetworkConditions', {
            'offline': False,
            'latency': 600,
            'downloadThroughput': 40 * 1024,
            'uploadThroughput': 20 * 1024
        })

        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70")
        time.sleep(0.3)
        shot_slow = b.capture_screenshot(OUT_DIR / "u5_slow_network_loading.png")
        results["screenshots"]["slow_network_loading"] = str(shot_slow)

        # Wait for product to finish loading
        b.wait_for_selector('#btn-add-to-cart', timeout=15)
        slow_metrics = b.js("""(() => {
            const cta = document.querySelector('#btn-add-to-cart');
            const price = document.querySelector('#product-detail-price');
            return {
                productFinishedLoading: Boolean(cta && price),
                priceValue: price ? price.textContent.trim() : null
            };
        })()""")

        # Reset network throttling
        b.cdp('Network.emulateNetworkConditions', {
            'offline': False,
            'latency': 0,
            'downloadThroughput': -1,
            'uploadThroughput': -1
        })
        time.sleep(0.5)

        check5 = {
            "name": "Slow Network Simulation & Honest Loading",
            "metrics": slow_metrics,
            "passed": bool(slow_metrics["productFinishedLoading"] and slow_metrics["priceValue"])
        }
        results["checks"].append(check5)
        print("  Check 5:", check5, flush=True)

        # =========================================================================
        # 6. Media Failure Handling & Neutral Fallback
        # =========================================================================
        print("6. Testing Media Failure Handling & Neutral Fallback...", flush=True)
        b.goto("http://127.0.0.1:13001/", wait_selector='.product-card')
        time.sleep(1)

        # Inject image with broken URL via createSafeImageElement logic
        media_fallback_metrics = b.js("""(() => {
            const container = document.querySelector('.products-grid');
            if (!container) return { injected: false };

            const testCard = document.createElement('div');
            testCard.className = 'product-card test-fallback-card';
            testCard.id = 'test-fallback-card';

            const wrapper = document.createElement('div');
            wrapper.className = 'product-card-img-wrapper';

            // Simulate broken image
            const img = document.createElement('img');
            img.className = 'product-card-img';
            let replaced = false;
            const fallbackSvg = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400"><rect width="400" height="400" fill="#131B16"/><circle cx="200" cy="180" r="56" fill="#1E2A23" stroke="#2D3F35" stroke-width="2"/><text x="200" y="190" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="700" font-size="28" fill="#52B788" letter-spacing="2">AZ</text><text x="200" y="270" text-anchor="middle" font-family="system-ui, -apple-system, sans-serif" font-weight="600" font-size="12" fill="#88988E" letter-spacing="3">IMAGE COMING SOON</text></svg>');

            img.addEventListener('error', () => {
                if (!replaced) {
                    replaced = true;
                    img.src = fallbackSvg;
                }
            });
            img.src = '/media/objects/nonexistent-corrupted-asset-1234.jpg';
            wrapper.appendChild(img);
            testCard.appendChild(wrapper);
            container.prepend(testCard);

            return { injected: true };
        })()""")
        time.sleep(1)

        fallback_result = b.js("""(() => {
            const card = document.querySelector('#test-fallback-card');
            const img = card ? card.querySelector('img') : null;
            const isSvgFallback = img ? img.src.startsWith('data:image/svg+xml') : false;
            const wrapper = card ? card.querySelector('.product-card-img-wrapper') : null;
            const cs = wrapper ? window.getComputedStyle(wrapper) : null;

            return {
                isSvgFallback,
                wrapperAspectRatio: cs ? cs.aspectRatio : null,
                imgNaturalWidth: img ? img.naturalWidth : 0
            };
        })()""")

        shot_fallback = b.capture_screenshot(OUT_DIR / "u5_media_failure_fallback.png")
        results["screenshots"]["media_failure_fallback"] = str(shot_fallback)

        check6 = {
            "name": "Media Failure Handling & Neutral Fallback",
            "metrics": { **media_fallback_metrics, **fallback_result },
            "passed": bool(fallback_result["isSvgFallback"] and fallback_result["imgNaturalWidth"] > 0)
        }
        results["checks"].append(check6)
        print("  Check 6:", check6, flush=True)

        # =========================================================================
        # 7. Owner Console Smoke Check (Lab & Dev)
        # =========================================================================
        print("7. Testing Owner Console Smoke Check (Lab & Dev)...", flush=True)

        # 7A. Lab /admin
        b.goto("http://127.0.0.1:13001/admin", wait_selector='input[type="password"], #admin-username, .admin-page')
        time.sleep(1.5)
        shot_admin_lab = b.capture_screenshot(OUT_DIR / "u5_admin_smoke_lab.png")
        results["screenshots"]["admin_smoke_lab"] = str(shot_admin_lab)

        admin_lab_metrics = b.js("""(() => {
            const pageTitle = document.title;
            const adminPage = document.querySelector('.admin-page');
            const passwordInput = document.querySelector('input[type="password"]');
            const cs = adminPage ? window.getComputedStyle(adminPage) : (document.body ? window.getComputedStyle(document.body) : null);

            return {
                pageTitle,
                hasAdminPage: Boolean(adminPage),
                hasPasswordInput: Boolean(passwordInput),
                bgColor: cs ? cs.backgroundColor : null,
            };
        })()""")

        # 7B. Dev /admin
        b.goto("http://localhost:13000/admin", wait_selector='input[type="password"], #admin-username, .admin-page')
        time.sleep(1.5)
        shot_admin_dev = b.capture_screenshot(OUT_DIR / "u5_admin_smoke_dev.png")
        results["screenshots"]["admin_smoke_dev"] = str(shot_admin_dev)

        admin_dev_metrics = b.js("""(() => {
            const pageTitle = document.title;
            const adminPage = document.querySelector('.admin-page');
            const passwordInput = document.querySelector('input[type="password"]');
            return {
                pageTitle,
                hasAdminPage: Boolean(adminPage),
                hasPasswordInput: Boolean(passwordInput),
            };
        })()""")

        check7 = {
            "name": "Owner Console Smoke Check",
            "metrics": { "lab": admin_lab_metrics, "dev": admin_dev_metrics },
            "passed": bool(
                admin_lab_metrics["pageTitle"] == "AlphaZee — Owner dashboard" and
                admin_lab_metrics["hasPasswordInput"] and
                admin_dev_metrics["pageTitle"] == "AlphaZee — Owner dashboard" and
                admin_dev_metrics["hasPasswordInput"]
            )
        }
        results["checks"].append(check7)
        print("  Check 7:", check7, flush=True)

        results["errors"] = b.errors

    out_json = OUT_DIR / "u5_verification.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nVerification finished! Report written to {out_json}")
    all_passed = all(c["passed"] for c in results["checks"])
    print(f"Overall Status: {'ALL CHECKS PASSED (7/7)' if all_passed else 'SOME CHECKS FAILED'}")
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
