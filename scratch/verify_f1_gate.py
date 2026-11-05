"""Verify Phase F1 Gate: Product media viewport fit, stage bounds, controls, thumbnails, and video."""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-repairs/run_20261105_f1'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

BASELINES = [
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
    print(f"  [SCREENSHOT] {filename}", flush=True)

def measure_product_stage(b):
    js = """
    (() => {
        const stage = document.querySelector('.product-gallery-stage');
        const media = document.querySelector('.product-gallery-media-wrapper img, .product-gallery-media-wrapper video');
        const counter = document.querySelector('.gallery-counter');
        const prevBtn = document.querySelector('#gallery-prev-btn');
        const nextBtn = document.querySelector('#gallery-next-btn');
        const zoomBtn = document.querySelector('#gallery-zoom-btn');
        const thumbs = document.querySelector('.product-gallery-thumbs');
        const thumbButtons = Array.from(document.querySelectorAll('.product-gallery-thumb'));
        
        const rStage = stage ? stage.getBoundingClientRect() : null;
        const rMedia = media ? media.getBoundingClientRect() : null;
        const rThumbs = thumbs ? thumbs.getBoundingClientRect() : null;
        
        return {
            window: { w: window.innerWidth, h: window.innerHeight, scrollY: window.scrollY },
            stage: rStage ? {
                top: rStage.top, bottom: rStage.bottom, height: rStage.height, width: rStage.width,
                fitsInViewport: rStage.bottom <= window.innerHeight
            } : null,
            media: rMedia ? {
                top: rMedia.top, bottom: rMedia.bottom, height: rMedia.height, width: rMedia.width,
                tag: media.tagName,
                objectFit: window.getComputedStyle(media).objectFit
            } : null,
            thumbs: rThumbs ? {
                top: rThumbs.top, bottom: rThumbs.bottom, height: rThumbs.height,
                count: thumbButtons.length,
                hasThumbImages: Boolean(document.querySelector('.thumb-media-img')),
                hasVideoBadge: Boolean(document.querySelector('.thumb-video-badge'))
            } : null,
            activeThumbIndex: thumbButtons.findIndex(b => b.classList.contains('is-active') || b.getAttribute('aria-pressed') === 'true'),
            counterText: counter ? counter.textContent.trim() : null
        };
    })()
    """
    return b.js(js)

def main():
    print("=== STARTING PHASE F1 VERIFICATION ===", flush=True)
    results = {}
    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        for vp in BASELINES:
            vp_name = vp["name"]
            print(f"\nVerifying Viewport: {vp_name} ({vp['w']}x{vp['h']})...", flush=True)
            b.set_viewport(vp["w"], vp["h"], mobile=vp["mobile"])
            b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
            b.wait_for_selector(".product-page-title", timeout=10)
            time.sleep(1.0)

            # Slide 1 (Image 1)
            m1 = measure_product_stage(b)
            save_screenshot(b, f"f1_{vp_name}_slide1.png")
            print(f"  Slide 1: Stage top={m1['stage']['top']} bottom={m1['stage']['bottom']} height={m1['stage']['height']} fits={m1['stage']['fitsInViewport']}", flush=True)
            
            # Click thumbnail 2 (Image 2)
            b.click('[data-gallery-index="1"]')
            time.sleep(0.4)
            m2 = measure_product_stage(b)
            save_screenshot(b, f"f1_{vp_name}_slide2.png")
            print(f"  Slide 2: Counter='{m2['counterText']}' fits={m2['stage']['fitsInViewport']}", flush=True)

            # Click thumbnail 3 (Image 3)
            b.click('[data-gallery-index="2"]')
            time.sleep(0.4)
            m3 = measure_product_stage(b)
            save_screenshot(b, f"f1_{vp_name}_slide3.png")
            print(f"  Slide 3: Counter='{m3['counterText']}' fits={m3['stage']['fitsInViewport']}", flush=True)

            # Click thumbnail 4 (Video)
            b.click('[data-gallery-index="3"]')
            time.sleep(0.4)
            m4 = measure_product_stage(b)
            save_screenshot(b, f"f1_{vp_name}_slide4_video.png")
            print(f"  Slide 4 (Video): Tag={m4['media']['tag']} Counter='{m4['counterText']}' fits={m4['stage']['fitsInViewport']}", flush=True)

            # Test video paused on slide change back to slide 1
            b.click('[data-gallery-index="0"]')
            time.sleep(0.3)

            results[vp_name] = {
                "slide1": m1, "slide2": m2, "slide3": m3, "slide4_video": m4
            }

        # Test Lightbox at 1366x768
        print("\nVerifying Lightbox zoom & Escape key...", flush=True)
        b.set_viewport(1366, 768, mobile=False)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1.0)
        
        b.click("#gallery-zoom-btn")
        time.sleep(0.5)
        has_lightbox = b.js('Boolean(document.querySelector("#gallery-lightbox"))')
        print(f"  Lightbox opened: {has_lightbox}", flush=True)
        save_screenshot(b, "f1_lightbox_open_1366x768.png")

        # Press Escape
        b.cdp("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape"})
        b.cdp("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape"})
        time.sleep(0.4)
        lightbox_closed = b.js('document.querySelector("#gallery-lightbox") === null')
        print(f"  Lightbox closed after Escape: {lightbox_closed}", flush=True)

    summary_file = OUT_DIR / "f1_verification_summary.json"
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nF1 Verification Summary written to {summary_file}", flush=True)

if __name__ == '__main__':
    main()

