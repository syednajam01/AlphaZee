"""Verify Phase B1 Correctness & Customer Journey Improvements via headless Chrome CDP."""
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

OUT_DIR = ROOT / '.local/frontend-redesign/run_b1_gate'
OUT_DIR.mkdir(parents=True, exist_ok=True)

ORIGIN = "http://127.0.0.1:13001"
SLUG = "sample-m8-0d535c70"

def main():
    print(f"Starting B1 Browser Verification Gate on {ORIGIN}...", flush=True)
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "B1",
        "origin": ORIGIN,
        "product_slug": SLUG,
        "checks": [],
        "screenshots": {},
        "errors": []
    }

    with RedesignBrowser(OUT_DIR) as b:
        # =====================================================================
        # JOURNEY 1 & MOBILE HOMEPAGE (Viewport: 390x844)
        # =====================================================================
        print("\n--- 1. Testing Journey 1: Mobile Homepage & Hero Compactness ---", flush=True)
        b.set_viewport(390, 844, mobile=True)
        b.goto(f"{ORIGIN}/", wait_selector='.hero-section')
        time.sleep(1.5)

        hero_metrics = b.js("""(() => {
            const hero = document.querySelector('.hero-section');
            const notice = document.querySelector('.checkout-lab-notice');
            const statusBanner = hero ? hero.querySelector('.hero-catalog-status') : null;
            const featuredGrid = document.querySelector('#featured, .featured-grid, .product-grid');
            const rect = hero ? hero.getBoundingClientRect() : null;
            const winH = window.innerHeight;

            return {
                heroExists: Boolean(hero),
                hasDiagnosticBanner: Boolean(statusBanner),
                heroHeight: rect ? Math.round(rect.height) : 0,
                viewportHeight: winH,
                heroRatioToViewport: rect ? +(rect.height / winH).toFixed(2) : 0,
                catalogBelowVisibleOrClose: featuredGrid ? (featuredGrid.getBoundingClientRect().top < winH * 1.3) : false,
            };
        })()""")

        shot1 = b.capture_screenshot(OUT_DIR / "b1_mobile_home.png")
        results["screenshots"]["mobile_home"] = str(shot1)

        check_j1 = {
            "name": "Journey 1: Mobile Home Compact Hero (No Diagnostic Status Banner)",
            "metrics": hero_metrics,
            "passed": bool(
                hero_metrics["heroExists"] and
                not hero_metrics["hasDiagnosticBanner"] and
                hero_metrics["heroRatioToViewport"] <= 0.70
            )
        }
        results["checks"].append(check_j1)
        print("  Check J1:", check_j1, flush=True)

        # =====================================================================
        # JOURNEY 2 & E1 / E2: DESKTOP PRODUCT DECISION (Viewport: 1280x800)
        # =====================================================================
        print("\n--- 2. Testing Journey 2 & E1/E2: Desktop Product Decision ---", flush=True)
        b.set_viewport(1280, 800, mobile=False)
        b.goto(f"{ORIGIN}/products/{SLUG}", wait_selector='#btn-add-to-cart')
        time.sleep(1.5)

        e1_e2_metrics = b.js("""(() => {
            const page = document.querySelector('.product-page-container, .product-page-grid');
            const details = document.querySelector('.product-page-details');
            const detailsStyle = details ? window.getComputedStyle(details) : null;
            const bodyText = document.body.innerText;
            const sizeTable = document.querySelector('.size-guide-table');

            // Policy section
            const infoBlocks = Array.from(document.querySelectorAll('.product-info-block'));
            const deliveryBlock = infoBlocks.find(b => b.textContent.includes('Nationwide Delivery & Returns'));
            const deliveryText = deliveryBlock ? deliveryBlock.textContent : '';

            // Truthful material/care
            const matBlock = infoBlocks.find(b => b.textContent.includes('Material & Garment Care'));
            const matText = matBlock ? matBlock.textContent : '';

            // Sizing block
            const sizingBlock = infoBlocks.find(b => b.textContent.includes('Sizing & Fit'));
            const sizingText = sizingBlock ? sizingBlock.textContent : '';

            return {
                detailsSticky: details ? details.classList.contains('is-sticky') : false,
                detailsMaxHeight: detailsStyle ? detailsStyle.maxHeight : null,
                detailsOverflowY: detailsStyle ? detailsStyle.overflowY : null,
                hasNestedScrollbar: detailsStyle ? (detailsStyle.overflowY === 'auto' || detailsStyle.overflowY === 'scroll') : false,
                hasFabricatedCottonText: bodyText.includes('240 GSM combed cotton'),
                hasGenericSizeTable: Boolean(sizeTable),
                honestMaterialUnverified: matText.includes('Material composition not verified yet'),
                honestCareUnverified: matText.includes('Care instructions not verified yet'),
                honestSizingUnverified: sizingText.includes('Garment measurements not verified yet'),
                hasUnifiedDispatchPolicy: deliveryText.includes('24–48 hours'),
                hasUnifiedTransitPolicy: deliveryText.includes('3–5 business days nationwide'),
                hasUnifiedReturnPolicy: deliveryText.includes('7-day inspection and size-exchange policy'),
            };
        })()""")

        shot2 = b.capture_screenshot(OUT_DIR / "b1_desktop_product_details.png")
        results["screenshots"]["desktop_product_details"] = str(shot2)

        check_e1_e2_j2 = {
            "name": "E1/E2 & Journey 2: Truthful Fields, Unified Policies & Single Desktop Scroll",
            "metrics": e1_e2_metrics,
            "passed": bool(
                not e1_e2_metrics["hasNestedScrollbar"] and
                not e1_e2_metrics["hasFabricatedCottonText"] and
                not e1_e2_metrics["hasGenericSizeTable"] and
                e1_e2_metrics["honestMaterialUnverified"] and
                e1_e2_metrics["honestCareUnverified"] and
                e1_e2_metrics["honestSizingUnverified"] and
                e1_e2_metrics["hasUnifiedDispatchPolicy"] and
                e1_e2_metrics["hasUnifiedTransitPolicy"] and
                e1_e2_metrics["hasUnifiedReturnPolicy"]
            )
        }
        results["checks"].append(check_e1_e2_j2)
        print("  Check E1/E2 & J2:", check_e1_e2_j2, flush=True)

        # =====================================================================
        # E3: DELIBERATE SIZE SELECTION REQUIREMENT
        # =====================================================================
        print("\n--- 3. Testing E3: Deliberate Size Selection Requirement ---", flush=True)
        # Verify initial size state: multiple sizes exist, selectedSize is null
        initial_selection_state = b.js("""(() => {
            const sizeLabel = document.querySelector('#selected-size-name');
            const chips = Array.from(document.querySelectorAll('[data-option-size]'));
            const selectedChip = chips.find(c => c.classList.contains('is-selected'));
            return {
                sizeCount: chips.length,
                labelValue: sizeLabel ? sizeLabel.textContent.trim() : null,
                hasPreselectedChip: Boolean(selectedChip),
            };
        })()""")

        # Attempt to Add to Cart without selecting size
        b.click('#btn-add-to-cart')
        time.sleep(0.5)

        prompt_state = b.js("""(() => {
            const prompt = document.querySelector('#size-selection-prompt');
            const drawer = document.querySelector('#cart-drawer');
            const isDrawerOpen = drawer ? drawer.classList.contains('is-open') : false;
            return {
                promptExists: Boolean(prompt),
                promptVisible: prompt ? !prompt.hidden && window.getComputedStyle(prompt).display !== 'none' : false,
                promptText: prompt ? prompt.textContent.trim() : '',
                cartDrawerRemainedClosed: !isDrawerOpen,
            };
        })()""")

        shot3 = b.capture_screenshot(OUT_DIR / "b1_size_selection_prompt.png")
        results["screenshots"]["size_selection_prompt"] = str(shot3)

        # Now select size 'M'
        b.js("""(() => {
            const chip = document.querySelector('[data-option-size="M"]') || document.querySelector('[data-option-size]');
            if (chip) chip.click();
        })()""")
        time.sleep(0.5)

        post_select_state = b.js("""(() => {
            const prompt = document.querySelector('#size-selection-prompt');
            const sizeLabel = document.querySelector('#selected-size-name');
            return {
                promptHiddenNow: prompt ? prompt.hidden || window.getComputedStyle(prompt).display === 'none' : true,
                selectedSizeName: sizeLabel ? sizeLabel.textContent.trim() : '',
            };
        })()""")

        check_e3 = {
            "name": "E3: Deliberate Size Choice Enforced (Prompt Visible Until Selection)",
            "metrics": { **initial_selection_state, **prompt_state, **post_select_state },
            "passed": bool(
                initial_selection_state["sizeCount"] > 1 and
                not initial_selection_state["hasPreselectedChip"] and
                prompt_state["promptVisible"] and
                "select a size" in prompt_state["promptText"].lower() and
                prompt_state["cartDrawerRemainedClosed"] and
                post_select_state["promptHiddenNow"] and
                post_select_state["selectedSizeName"] == "M"
            )
        }
        results["checks"].append(check_e3)
        print("  Check E3:", check_e3, flush=True)

        # =====================================================================
        # JOURNEY 3: CART DRAWER & LAB NOTICE OFFSET
        # =====================================================================
        print("\n--- 4. Testing Journey 3: Cart Drawer & Lab Notice Top Offset ---", flush=True)
        # Now click Add to Cart with size 'M' selected
        b.click('#btn-add-to-cart')
        time.sleep(1.2)

        drawer_offset_metrics = b.js("""(() => {
            const notice = document.querySelector('.checkout-lab-notice');
            const drawer = document.querySelector('#cart-drawer');
            const header = drawer ? drawer.querySelector('.drawer-header') : null;
            const closeBtn = drawer ? drawer.querySelector('#cart-close-btn, [data-drawer-close]') : null;

            const noticeRect = notice ? notice.getBoundingClientRect() : null;
            const drawerRect = drawer ? drawer.getBoundingClientRect() : null;
            const headerRect = header ? header.getBoundingClientRect() : null;
            const closeRect = closeBtn ? closeBtn.getBoundingClientRect() : null;

            const labNoticeHeight = noticeRect ? Math.round(noticeRect.height) : 0;
            const drawerTop = drawerRect ? Math.round(drawerRect.top) : 0;
            const headerTop = headerRect ? Math.round(headerRect.top) : 0;

            // Check if drawer starts below notice
            const noOverlap = drawerTop >= (labNoticeHeight - 1);
            const headerVisibleAndClear = headerTop >= (labNoticeHeight - 1);

            return {
                labNoticeHeight,
                drawerTop,
                headerTop,
                noOverlap,
                headerVisibleAndClear,
                drawerIsOpen: drawer ? drawer.classList.contains('is-open') : false,
                cartItemCount: drawer ? drawer.querySelectorAll('.cart-item').length : 0,
            };
        })()""")

        shot4 = b.capture_screenshot(OUT_DIR / "b1_cart_drawer_offset.png")
        results["screenshots"]["cart_drawer_offset"] = str(shot4)

        check_j3 = {
            "name": "Journey 3: Cart Drawer Clear of Lab Notice (No Header Occlusion)",
            "metrics": drawer_offset_metrics,
            "passed": bool(
                drawer_offset_metrics["drawerIsOpen"] and
                drawer_offset_metrics["cartItemCount"] >= 1 and
                drawer_offset_metrics["noOverlap"] and
                drawer_offset_metrics["headerVisibleAndClear"]
            )
        }
        results["checks"].append(check_j3)
        print("  Check J3:", check_j3, flush=True)

        # Close the drawer
        b.click('#cart-close-btn')
        time.sleep(0.5)

        # =====================================================================
        # E4: ROUTE SWITCHING & METADATA CLEANUP
        # =====================================================================
        print("\n--- 5. Testing E4: Route Navigation & Metadata Cleanup ---", flush=True)
        # Navigate from product page back to Home route
        b.js("""(() => {
            const brandLink = document.querySelector('.header-brand-link, .nav-brand');
            if (brandLink) brandLink.click();
            else window.history.pushState(null, '', '/');
            window.dispatchEvent(new PopStateEvent('popstate'));
        })()""")
        time.sleep(1.0)

        home_meta_metrics = b.js("""(() => {
            const title = document.title;
            const descEl = document.querySelector('meta[name="description"]');
            const canonEl = document.querySelector('link[rel="canonical"]');
            const desc = descEl ? descEl.getAttribute('content') : '';
            const canonical = canonEl ? canonEl.getAttribute('href') : '';
            const productPageEl = document.querySelector('.product-page-container');

            return {
                title,
                description: desc,
                canonical,
                productPageDetached: !productPageEl,
                titleRestored: title.includes('AlphaZee') && !title.includes('SAMPLE M8'),
                canonicalRestored: canonical === '/' || canonical.endsWith('/'),
                descriptionRestored: desc.includes('streetwear') || desc.includes('AlphaZee'),
            };
        })()""")

        shot5 = b.capture_screenshot(OUT_DIR / "b1_home_metadata_restored.png")
        results["screenshots"]["home_metadata_restored"] = str(shot5)

        check_e4 = {
            "name": "E4: Route Switching Resets Title, Canonical & Description Metadata",
            "metrics": home_meta_metrics,
            "passed": bool(
                home_meta_metrics["titleRestored"] and
                home_meta_metrics["canonicalRestored"] and
                home_meta_metrics["descriptionRestored"] and
                home_meta_metrics["productPageDetached"]
            )
        }
        results["checks"].append(check_e4)
        print("  Check E4:", check_e4, flush=True)

    # Summary
    all_passed = all(c["passed"] for c in results["checks"])
    results["all_passed"] = all_passed
    print(f"\n=======================================================", flush=True)
    print(f"B1 Verification Gate Result: {'ALL PASS' if all_passed else 'FAILURES DETECTED'}", flush=True)
    print(f"Total Checks: {len(results['checks'])} | Passed: {sum(1 for c in results['checks'] if c['passed'])}", flush=True)
    print(f"=======================================================", flush=True)

    json_path = OUT_DIR / "b1_verification_results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Results saved to {json_path}", flush=True)

    if not all_passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
