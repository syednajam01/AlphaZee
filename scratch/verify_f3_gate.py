"""Verify Phase F3 Gate: Homepage/hero editorial presentation, controls, media clarity, and browsing interactions."""
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-repairs/run_20261105_f3'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT] {filename}", flush=True)

def measure_hero(b):
    js = """
    (() => {
        const hero = document.querySelector('.hero-section');
        const mediaContainer = document.querySelector('.hero-bg-container');
        const activeMedia = document.querySelector('.hero-bg-media.is-active');
        const title = document.querySelector('.hero-title');
        const desc = document.querySelector('.hero-desc');
        const ctaBtn = document.querySelector('.hero-cta-btn');
        const secBtn = document.querySelector('.hero-secondary-btn');
        const controls = document.querySelector('.hero-controls');
        const indicator = document.querySelector('#hero-indicator');
        const playPauseBtn = document.querySelector('#hero-play-pause');
        const firstCard = document.querySelector('.product-card, .collection-card');

        function rect(el) {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height };
        }

        return {
            window: { w: window.innerWidth, h: window.innerHeight, scrollY: window.scrollY },
            heroRect: rect(hero),
            mediaContainerRect: rect(mediaContainer),
            activeMedia: activeMedia ? {
                tag: activeMedia.tagName,
                rect: rect(activeMedia),
                objectFit: window.getComputedStyle(activeMedia).objectFit,
                filter: window.getComputedStyle(activeMedia).filter,
                opacity: window.getComputedStyle(activeMedia).opacity,
                paused: activeMedia.tagName === 'VIDEO' ? activeMedia.paused : null
            } : null,
            titleRect: rect(title),
            ctaRect: rect(ctaBtn),
            secBtnRect: rect(secBtn),
            controlsRect: rect(controls),
            indicatorText: indicator ? indicator.textContent.trim() : null,
            playPauseText: playPauseBtn ? playPauseBtn.textContent.trim() : null,
            firstCardTop: firstCard ? firstCard.getBoundingClientRect().top : null
        };
    })()
    """
    return b.js(js)

def main():
    print("=== STARTING PHASE F3 VERIFICATION ===", flush=True)
    results = {}
    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # 1. Desktop 1366x768 verification
        print("\n--- Desktop 1366x768: Editorial Hero & Media Showcase ---", flush=True)
        b.set_viewport(1366, 768, mobile=False)
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(2.0)

        # Slide 1 (Muted Video)
        s1 = measure_hero(b)
        save_screenshot(b, "f3_desktop_1366x768_hero_slide1_video.png")
        print(f"  Slide 1: Active tag={s1['activeMedia']['tag']} objectFit={s1['activeMedia']['objectFit']} filter={s1['activeMedia']['filter']}", flush=True)
        print(f"  First Card Distance: {s1['firstCardTop']}px from top", flush=True)

        # Pause / Play toggle
        b.click("#hero-play-pause")
        time.sleep(0.3)
        pause_data = measure_hero(b)
        print(f"  After Pause click: button='{pause_data['playPauseText']}' videoPaused={pause_data['activeMedia']['paused']}", flush=True)
        save_screenshot(b, "f3_desktop_1366x768_hero_paused.png")

        b.click("#hero-play-pause") # resume
        time.sleep(0.3)

        # Navigate to Slide 2 (Image)
        b.click("#hero-next")
        time.sleep(0.6)
        s2 = measure_hero(b)
        save_screenshot(b, "f3_desktop_1366x768_hero_slide2_image.png")
        print(f"  Slide 2: Indicator='{s2['indicatorText']}' tag={s2['activeMedia']['tag']} filter={s2['activeMedia']['filter']}", flush=True)

        # Test hover card front/back swap in product grid
        print("\n--- Testing Product Grid Hover Front/Back Swap ---", flush=True)
        b.js("""
        (() => {
            const card = document.querySelector('.product-card');
            if (card) {
                card.scrollIntoView({ behavior: 'instant', block: 'center' });
            }
        })()
        """)
        time.sleep(0.5)
        save_screenshot(b, "f3_desktop_product_card_normal.png")

        # Simulate hover on card
        card_img_before = b.js("document.querySelector('.product-card img')?.src")
        b.js("""
        (() => {
            const card = document.querySelector('.product-card');
            if (card) {
                card.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
                card.classList.add('is-hovered');
            }
        })()
        """)
        time.sleep(0.3)
        save_screenshot(b, "f3_desktop_product_card_hovered.png")

        # 2. Mobile 390x844 verification
        print("\n--- Mobile 390x844: Stacked Editorial Hero ---", flush=True)
        b.set_viewport(390, 844, mobile=True)
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(2.0)

        m_data = measure_hero(b)
        save_screenshot(b, "f3_mobile_390x844_hero.png")
        print(f"  Mobile Hero height={m_data['heroRect']['height']}px, first card top={m_data['firstCardTop']}px", flush=True)

        # Mobile Menu drawer
        print("  Testing Mobile Navigation Drawer...", flush=True)
        b.click("#btn-mobile-menu")
        time.sleep(0.4)
        save_screenshot(b, "f3_mobile_390x844_drawer_open.png")
        drawer_visible = b.js('Boolean(document.querySelector(".mobile-nav-drawer.is-open, .drawer.is-open"))')
        print(f"  Drawer open: {drawer_visible}", flush=True)

        # Close drawer
        b.js('document.querySelector(".mobile-nav-close, [data-action=\\"close-drawer\\"], .drawer-backdrop")?.click()')
        time.sleep(0.4)

        # 3. Mobile 360x640 verification
        print("\n--- Mobile 360x640: Compact Viewport ---", flush=True)
        b.set_viewport(360, 640, mobile=True)
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(1.5)
        save_screenshot(b, "f3_mobile_360x640_hero.png")

        # 4. Reduced Motion preference check
        print("\n--- Reduced Motion Check ---", flush=True)
        b.cdp("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        time.sleep(1.5)
        rm_data = measure_hero(b)
        save_screenshot(b, "f3_reduced_motion_hero.png")
        print(f"  Reduced Motion active tag: {rm_data['activeMedia']['tag']}", flush=True)

        results = {
            "desktop_slide1": s1,
            "desktop_slide2": s2,
            "mobile_390x844": m_data,
            "reduced_motion": rm_data
        }

    summary_file = OUT_DIR / "f3_verification_summary.json"
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nF3 Verification Summary written to {summary_file}", flush=True)

if __name__ == '__main__':
    main()

