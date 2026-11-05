"""Phase F4: Extended Regression Matrix across 768x1024, 1920x1080, 320x568, 200% Zoom, Keyboard Navigation, and Lab Checkout Isolation."""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-repairs/run_20261105_f4_regression'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT] {filename}", flush=True)

def check_overflow_and_bounds(b):
    js = """
    (() => {
        const doc = document.documentElement;
        const stage = document.querySelector('.product-gallery-stage');
        const cta = document.querySelector('.btn-add-to-cart, #btn-add-to-cart');
        return {
            window: { w: window.innerWidth, h: window.innerHeight },
            scrollWidth: doc.scrollWidth,
            clientWidth: doc.clientWidth,
            hasHorizontalOverflow: doc.scrollWidth > doc.clientWidth,
            stageBottom: stage ? stage.getBoundingClientRect().bottom : null,
            stageFits: stage ? (stage.getBoundingClientRect().bottom <= window.innerHeight) : null,
            ctaVisible: cta ? (cta.getBoundingClientRect().top < doc.scrollHeight) : null
        };
    })()
    """
    return b.js(js)

def main():
    print("=== STARTING PHASE F4 EXTENDED REGRESSION MATRIX ===", flush=True)
    matrix_results = {}
    
    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # 1. Tablet Portrait (768x1024)
        print("\n--- 1. Tablet Portrait (768x1024) ---", flush=True)
        b.set_viewport(768, 1024, mobile=True)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1.0)
        m_768 = check_overflow_and_bounds(b)
        save_screenshot(b, "f4_tablet_768x1024_product.png")
        print(f"  Stage fits: {m_768['stageFits']}, overflow: {m_768['hasHorizontalOverflow']}", flush=True)
        matrix_results["768x1024"] = m_768

        # Home on Tablet
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(1.0)
        save_screenshot(b, "f4_tablet_768x1024_home.png")

        # 2. Full HD Desktop (1920x1080)
        print("\n--- 2. Full HD Desktop (1920x1080) ---", flush=True)
        b.set_viewport(1920, 1080, mobile=False)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1.0)
        m_1920 = check_overflow_and_bounds(b)
        save_screenshot(b, "f4_desktop_1920x1080_product.png")
        print(f"  Stage fits: {m_1920['stageFits']}, overflow: {m_1920['hasHorizontalOverflow']}", flush=True)
        matrix_results["1920x1080"] = m_1920

        # Home on Full HD
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(1.0)
        save_screenshot(b, "f4_desktop_1920x1080_home.png")

        # 3. Narrow Phone (320x568 - iPhone SE / narrow screen)
        print("\n--- 3. Narrow Phone (320x568) ---", flush=True)
        b.set_viewport(320, 568, mobile=True)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1.0)
        m_320 = check_overflow_and_bounds(b)
        save_screenshot(b, "f4_narrow_320x568_product.png")
        print(f"  Stage fits: {m_320['stageFits']}, overflow: {m_320['hasHorizontalOverflow']}", flush=True)
        matrix_results["320x568"] = m_320

        # 4. 200% Desktop Browser Zoom
        print("\n--- 4. Desktop 200% Browser Zoom (1440x900 base @ scale factor 2) ---", flush=True)
        # Using deviceScaleFactor 2 simulates high DPI / 200% zoom
        b.set_viewport(720, 450, mobile=False, device_scale_factor=2)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1.0)
        m_zoom = check_overflow_and_bounds(b)
        save_screenshot(b, "f4_desktop_200pct_zoom_product.png")
        print(f"  200% Zoom: overflow={m_zoom['hasHorizontalOverflow']}, CTA reachable={m_zoom['ctaVisible']}", flush=True)
        matrix_results["200pct_zoom"] = m_zoom

        # 5. Keyboard Navigation Focus Smoke Check
        print("\n--- 5. Keyboard Navigation Smoke Check ---", flush=True)
        b.set_viewport(1366, 768, mobile=False)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1.0)

        # Tab through elements
        focused_tags = []
        for _ in range(8):
            b.cdp("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Tab", "code": "Tab"})
            b.cdp("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Tab", "code": "Tab"})
            time.sleep(0.1)
            active_info = b.js("""
            (() => {
                const el = document.activeElement;
                if (!el) return null;
                return { tag: el.tagName, id: el.id, cls: el.className, text: el.textContent.trim().slice(0, 30) };
            })()
            """)
            focused_tags.append(active_info)

        print(f"  Keyboard focused elements sequence ({len(focused_tags)} tabs):", flush=True)
        for idx, f in enumerate(focused_tags):
            if f:
                print(f"    Tab {idx+1}: <{f['tag']} id='{f['id']}' class='{f['cls']}'> '{f['text']}'", flush=True)
        save_screenshot(b, "f4_keyboard_focus_active.png")

        # 6. Lab Checkout Isolation Smoke Check (127.0.0.1:13001)
        print("\n--- 6. Lab Checkout Isolation Check (http://127.0.0.1:13001) ---", flush=True)
        b.goto("http://127.0.0.1:13001/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(1.5)
        lab_title = b.js("document.title")
        print(f"  Lab Home Title: {lab_title}", flush=True)
        save_screenshot(b, "f4_lab_13001_home.png")

        # Verify normal stack rejected checkout (HTTP 503 check)
        import urllib.request
        normal_checkout_status = None
        try:
            req = urllib.request.Request("http://127.0.0.1:18000/api/v1/orders", data=b"{}", headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            normal_checkout_status = e.code
        print(f"  Normal stack order endpoint status: HTTP {normal_checkout_status} (Expected 503)", flush=True)
        matrix_results["normal_checkout_status"] = normal_checkout_status

    summary_file = OUT_DIR / "f4_matrix_summary.json"
    summary_file.write_text(json.dumps(matrix_results, indent=2), encoding="utf-8")
    print(f"\nF4 Extended Regression Summary written to {summary_file}", flush=True)

if __name__ == '__main__':
    main()

