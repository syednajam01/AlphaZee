"""Phase F0: Reproduce and prioritize baseline defects on Home and Product page."""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-repairs/run_20261105_reproduce'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    {"name": "1366x768_desktop", "w": 1366, "h": 768, "mobile": False},
    {"name": "1440x900_desktop", "w": 1440, "h": 900, "mobile": False},
    {"name": "390x844_mobile", "w": 390, "h": 844, "mobile": True},
    {"name": "360x640_mobile", "w": 360, "h": 640, "mobile": True},
    {"name": "844x390_landscape", "w": 844, "h": 390, "mobile": True},
]

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"Captured screenshot: {filename}", flush=True)

def measure_home(browser):
    js_code = """
    (() => {
        const doc = document.documentElement;
        const body = document.body;
        const hero = document.querySelector('.hero-section');
        const heroBgMedia = document.querySelector('.hero-bg-media.is-active');
        const heroTitle = document.querySelector('.hero-title');
        const heroDesc = document.querySelector('.hero-desc');
        const heroCta = document.querySelector('.hero-cta-btn, .btn-hero');
        const heroControls = document.querySelector('.hero-controls');
        const header = document.querySelector('header, .header-container');
        const announcement = document.querySelector('.announcement-bar, .proto-banner, .prototype-announcement');
        const firstCard = document.querySelector('.product-card, .collection-card');
        
        function getStyles(el) {
            if (!el) return null;
            const cs = window.getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return {
                rect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height },
                color: cs.color,
                backgroundColor: cs.backgroundColor,
                fontSize: cs.fontSize,
                filter: cs.filter,
                objectFit: cs.objectFit,
                opacity: cs.opacity
            };
        }

        return {
            viewport: { width: window.innerWidth, height: window.innerHeight },
            scroll: {
                x: window.scrollX,
                y: window.scrollY,
                scrollWidth: doc.scrollWidth,
                scrollHeight: doc.scrollHeight,
                clientWidth: doc.clientWidth,
                clientHeight: doc.clientHeight,
                hasHorizontalOverflow: doc.scrollWidth > doc.clientWidth
            },
            header: getStyles(header),
            announcement: getStyles(announcement),
            hero: getStyles(hero),
            heroBgMedia: getStyles(heroBgMedia),
            heroTitle: getStyles(heroTitle),
            heroDesc: getStyles(heroDesc),
            heroCta: getStyles(heroCta),
            heroControls: getStyles(heroControls),
            firstCardDistance: firstCard ? firstCard.getBoundingClientRect().top : null
        };
    })()
    """
    return browser.js(js_code)

def measure_product(browser):
    js_code = """
    (() => {
        const doc = document.documentElement;
        const stage = document.querySelector('.product-gallery-stage');
        const media = document.querySelector('.product-gallery-media-wrapper img, .product-gallery-media-wrapper video');
        const prevBtn = document.querySelector('#gallery-prev-btn');
        const nextBtn = document.querySelector('#gallery-next-btn');
        const zoomBtn = document.querySelector('#gallery-zoom-btn');
        const counter = document.querySelector('#gallery-counter');
        const thumbs = document.querySelector('.product-gallery-thumbs');
        const thumbItems = Array.from(document.querySelectorAll('.product-gallery-thumb, .product-gallery-thumbs button')).map(t => {
            const cs = window.getComputedStyle(t);
            const r = t.getBoundingClientRect();
            return {
                text: t.textContent.trim(),
                width: r.width,
                height: r.height,
                color: cs.color,
                bg: cs.backgroundColor,
                border: cs.border
            };
        });
        const header = document.querySelector('header, .header-container');
        const breadcrumb = document.querySelector('.product-breadcrumb');
        const title = document.querySelector('.product-page-title, h1');
        const price = document.querySelector('.product-page-price, .price-display');
        const addToCart = document.querySelector('.btn-add-to-cart, #add-to-cart-btn, button[data-action="add-to-cart"]');
        const sizeOptions = Array.from(document.querySelectorAll('.option-pill, .size-pill, [data-option-type="size"]')).map(o => {
            const cs = window.getComputedStyle(o);
            return {
                text: o.textContent.trim(),
                color: cs.color,
                bg: cs.backgroundColor,
                border: cs.borderColor,
                isSelected: o.classList.contains('is-selected') || o.getAttribute('aria-pressed') === 'true'
            };
        });

        function getStyles(el) {
            if (!el) return null;
            const cs = window.getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return {
                rect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height },
                color: cs.color,
                backgroundColor: cs.backgroundColor,
                fontSize: cs.fontSize,
                aspectRatio: cs.aspectRatio,
                minHeight: cs.minHeight,
                maxHeight: cs.maxHeight,
                objectFit: cs.objectFit
            };
        }

        return {
            viewport: { width: window.innerWidth, height: window.innerHeight },
            scroll: {
                x: window.scrollX,
                y: window.scrollY,
                scrollWidth: doc.scrollWidth,
                scrollHeight: doc.scrollHeight,
                clientWidth: doc.clientWidth,
                clientHeight: doc.clientHeight,
                hasHorizontalOverflow: doc.scrollWidth > doc.clientWidth
            },
            header: getStyles(header),
            breadcrumb: getStyles(breadcrumb),
            stage: getStyles(stage),
            media: getStyles(media),
            stageFitsInViewport: stage ? (stage.getBoundingClientRect().bottom <= window.innerHeight) : false,
            prevBtn: getStyles(prevBtn),
            nextBtn: getStyles(nextBtn),
            zoomBtn: getStyles(zoomBtn),
            counter: getStyles(counter),
            thumbsContainer: getStyles(thumbs),
            thumbItems: thumbItems,
            title: getStyles(title),
            price: getStyles(price),
            addToCart: getStyles(addToCart),
            sizeOptions: sizeOptions
        };
    })()
    """
    return browser.js(js_code)

def main():
    results = {"home": {}, "product": {}, "errors": {}}
    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # 1. Test Home across all viewports
        for vp in VIEWPORTS:
            vp_name = vp["name"]
            print(f"Testing Home at {vp_name} ({vp['w']}x{vp['h']})...", flush=True)
            b.set_viewport(vp["w"], vp["h"], mobile=vp["mobile"])
            b.goto("http://localhost:13000/", wait_selector=".hero-section", timeout=10)
            time.sleep(1.5) # Allow render & video setup
            
            data = measure_home(b)
            results["home"][vp_name] = data
            
            shot_name = f"f0_baseline_home_{vp_name}.png"
            save_screenshot(b, shot_name)

        # 2. Test Product Preview across all viewports
        for vp in VIEWPORTS:
            vp_name = vp["name"]
            print(f"Testing Product Preview at {vp_name} ({vp['w']}x{vp['h']})...", flush=True)
            b.set_viewport(vp["w"], vp["h"], mobile=vp["mobile"])
            b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
            b.wait_for_selector(".product-page-title", timeout=10)
            time.sleep(1.0)
            
            data = measure_product(b)
            results["product"][vp_name] = data
            
            shot_name = f"f0_baseline_product_{vp_name}.png"
            save_screenshot(b, shot_name)

            # Also click next slide to test second slide at 1366x768 and 390x844
            if vp_name in ["1366x768_desktop", "390x844_mobile"]:
                if b.js('Boolean(document.querySelector("#gallery-next-btn"))'):
                    b.click("#gallery-next-btn")
                    time.sleep(0.5)
                    shot_slide2 = f"f0_baseline_product_slide2_{vp_name}.png"
                    save_screenshot(b, shot_slide2)

        results["errors"]["console"] = b.console_logs
        results["errors"]["runtime"] = b.errors
        results["errors"]["http"] = b.http_errors

    report_path = OUT_DIR / "f0_reproduction_data.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Reproduction data written to {report_path}", flush=True)

if __name__ == '__main__':
    main()

