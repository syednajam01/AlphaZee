"""Verify Hover Effects & Performance Smoothness across Homepage and Product Page."""
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-repairs/run_20261105_hover_perf'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT] {filename}", flush=True)

def hover_element(browser, rect):
    x = int(rect['left'] + rect['width'] / 2)
    y = int(rect['top'] + rect['height'] / 2)
    browser.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
    time.sleep(0.3)

def move_mouse_away(browser):
    browser.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 5, 'y': 5})
    time.sleep(0.2)

def main():
    print("=== STARTING HOVER & PERFORMANCE VERIFICATION ===", flush=True)

    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        b.set_viewport(1366, 768)

        # ---------------------------------------------------------
        # 1. HOMEPAGE: Smooth scroll & micro-interactions
        # ---------------------------------------------------------
        print("\n--- 1. Testing Homepage Interactions (1366x768) ---", flush=True)
        b.goto("http://localhost:13000/", wait_selector=".product-card")
        # Settle initial focus to prevent background reload during hover tests
        b.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 50, 'y': 50})
        time.sleep(1.2)
        b.wait_for_selector('.product-card')

        # 1a. Scroll frame test and rAF header scroll listener
        scroll_res = b.js("""
        (() => {
            return new Promise(resolve => {
                const startTime = performance.now();
                let frames = 0;
                let y = 0;
                function step() {
                    frames++;
                    y += 20;
                    window.scrollTo(0, y);
                    if (y < 400) {
                        requestAnimationFrame(step);
                    } else {
                        setTimeout(() => {
                            const elapsed = performance.now() - startTime;
                            const fps = (frames / (elapsed / 1000));
                            const isScrolled = document.querySelector('.site-header').classList.contains('is-scrolled');
                            resolve({ elapsedMs: elapsed, frames, fps, isScrolled });
                        }, 100);
                    }
                }
                requestAnimationFrame(step);
            });
        })()
        """)
        print(f"  Scroll Performance: {scroll_res['frames']} frames in {scroll_res['elapsedMs']:.1f}ms ({scroll_res['fps']:.1f} fps). Header is-scrolled: {scroll_res['isScrolled']}", flush=True)
        assert scroll_res['isScrolled'] == True, "Header should have is-scrolled class after scrolling 400px"

        # Scroll back to top
        b.js("window.scrollTo(0, 0)")
        time.sleep(0.3)
        top_scrolled = b.js("document.querySelector('.site-header').classList.contains('is-scrolled')")
        print(f"  Header removed is-scrolled at top: {not top_scrolled}", flush=True)
        assert top_scrolled == False, "Header should not have is-scrolled class at top"

        # 1b. Product Card Hover Effect
        b.js("window.scrollTo(0, 1000)")
        time.sleep(0.4)

        card_rect = b.js("""
        (() => {
            const card = document.querySelector('.product-card');
            if (!card) return null;
            const r = card.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        assert card_rect is not None, "Product card not found on homepage"

        card_normal = b.js("""
        (() => {
            const card = document.querySelector('.product-card');
            const s = window.getComputedStyle(card);
            return { transform: s.transform, boxShadow: s.boxShadow, borderColor: s.borderColor };
        })()
        """)

        hover_element(b, card_rect)

        card_hovered = b.js("""
        (() => {
            const card = document.querySelector('.product-card');
            if (!card) return null;
            const btn = card.querySelector('.product-card-btn');
            const img = card.querySelector('.product-card-img-primary');
            const s = window.getComputedStyle(card);
            const bs = btn ? window.getComputedStyle(btn) : null;
            const is = img ? window.getComputedStyle(img) : null;
            return {
                transform: s.transform,
                boxShadow: s.boxShadow,
                borderColor: s.borderColor,
                btnBg: bs ? bs.backgroundColor : null,
                btnColor: bs ? bs.color : null,
                imgTransform: is ? is.transform : null
            };
        })()
        """)
        print(f"  Product Card Normal:  transform={card_normal['transform']}, shadow={card_normal['boxShadow']}")
        print(f"  Product Card Hovered: transform={card_hovered['transform']}, shadow={card_hovered['boxShadow']}, btnBg={card_hovered['btnBg']}")
        save_screenshot(b, "hover_product_card_desktop.png")
        assert card_hovered['transform'] != 'none' and 'matrix' in card_hovered['transform'], "Product card must lift on hover"

        # 1c. Collection Card CTA Hover
        b.js("window.scrollTo(0, 400)")
        time.sleep(0.3)
        col_rect = b.js("""
        (() => {
            const col = document.querySelector('.collection-card');
            if (!col) return null;
            const r = col.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if col_rect:
            hover_element(b, col_rect)
            col_hover = b.js("""
            (() => {
                const col = document.querySelector('.collection-card');
                const cta = col.querySelector('.collection-card-cta');
                const cs = window.getComputedStyle(col);
                const as = cta ? window.getComputedStyle(cta) : null;
                return { colTransform: cs.transform, ctaTransform: as ? as.transform : null, ctaColor: as ? as.color : null };
            })()
            """)
            print(f"  Collection Card Hovered: colTransform={col_hover['colTransform']}, ctaTransform={col_hover['ctaTransform']}")
            assert col_hover['colTransform'] != 'none', "Collection card must lift on hover"

        # 1d. Filter Tabs Hover
        b.js("window.scrollTo(0, 850)")
        time.sleep(0.3)
        tab_rect = b.js("""
        (() => {
            const tabs = document.querySelectorAll('.filter-tabs .option-pill');
            const unsel = Array.from(tabs).find(t => !t.classList.contains('is-selected'));
            if (!unsel) return null;
            const r = unsel.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if tab_rect:
            hover_element(b, tab_rect)
            tab_hover = b.js("""
            (() => {
                const tabs = document.querySelectorAll('.filter-tabs .option-pill');
                const unsel = Array.from(tabs).find(t => !t.classList.contains('is-selected'));
                const s = window.getComputedStyle(unsel);
                return { transform: s.transform, bg: s.backgroundColor, border: s.borderColor, color: s.color };
            })()
            """)
            print(f"  Filter Tab Hovered: transform={tab_hover['transform']}, color={tab_hover['color']}")
            assert tab_hover['transform'] != 'none', "Filter tab must lift subtly on hover"

        # 1e. Reassurance Item Hover
        b.js("document.querySelector('.reassurance-item')?.scrollIntoView({ behavior: 'instant', block: 'center' })")
        time.sleep(0.3)
        reassurance_rect = b.js("""
        (() => {
            const item = document.querySelector('.reassurance-item');
            if (!item) return null;
            const r = item.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if reassurance_rect:
            hover_element(b, reassurance_rect)
            reassurance_hover = b.js("""
            (() => {
                const item = document.querySelector('.reassurance-item');
                const icon = item.querySelector('.reassurance-icon');
                const s = window.getComputedStyle(item);
                const is = icon ? window.getComputedStyle(icon) : null;
                return { itemTransform: s.transform, iconTransform: is ? is.transform : null };
            })()
            """)
            print(f"  Reassurance Hovered: itemTransform={reassurance_hover['itemTransform']}, iconTransform={reassurance_hover['iconTransform']}")
            assert reassurance_hover['itemTransform'] != 'none', "Reassurance item should lift on hover"

        # 1f. Navigation Link Hover
        b.js("window.scrollTo(0, 0)")
        time.sleep(0.3)
        nav_rect = b.js("""
        (() => {
            const nav = document.querySelector('.nav-link');
            if (!nav) return null;
            const r = nav.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if nav_rect:
            hover_element(b, nav_rect)
            nav_color = b.js("""
            (() => {
                const nav = document.querySelector('.nav-link');
                return window.getComputedStyle(nav).color;
            })()
            """)
            print(f"  Nav Link Hovered Color: {nav_color}")

        move_mouse_away(b)

        # ---------------------------------------------------------
        # 2. PRODUCT PAGE: Gallery, Controls, Related Items
        # ---------------------------------------------------------
        print("\n--- 2. Testing Product Page Interactions & Media Efficiency ---", flush=True)
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105", wait_selector=".product-page-title")
        b.cdp('Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': 50, 'y': 50})
        time.sleep(1.2)
        b.wait_for_selector('.product-page-title')

        # 2a. Gallery Thumbnail Hover
        thumb_rect = b.js("""
        (() => {
            const thumbs = document.querySelectorAll('.product-gallery-thumb');
            const inactive = Array.from(thumbs).find(t => !t.classList.contains('is-active'));
            if (!inactive) return null;
            const r = inactive.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if thumb_rect:
            hover_element(b, thumb_rect)
            thumb_hover = b.js("""
            (() => {
                const thumbs = document.querySelectorAll('.product-gallery-thumb');
                const inactive = Array.from(thumbs).find(t => !t.classList.contains('is-active'));
                const s = window.getComputedStyle(inactive);
                return { transform: s.transform, border: s.borderColor, shadow: s.boxShadow };
            })()
            """)
            print(f"  Gallery Thumb Hovered: transform={thumb_hover['transform']}, border={thumb_hover['border']}, shadow={thumb_hover['shadow']}")
            assert thumb_hover['transform'] != 'none', "Thumbnail must lift on hover"

        # 2b. Gallery Next Button Hover
        next_rect = b.js("""
        (() => {
            const btn = document.querySelector('#gallery-next-btn');
            if (!btn) return null;
            const r = btn.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if next_rect:
            hover_element(b, next_rect)
            next_hover = b.js("""
            (() => {
                const btn = document.querySelector('#gallery-next-btn');
                const s = window.getComputedStyle(btn);
                return { transform: s.transform, shadow: s.boxShadow, color: s.color };
            })()
            """)
            print(f"  Gallery Next Btn Hovered: transform={next_hover['transform']}, color={next_hover['color']}")
            assert next_hover['transform'] != 'none', "Gallery nav button must scale on hover"

        # 2c. Option Chip Hover
        chip_rect = b.js("""
        (() => {
            const chips = document.querySelectorAll('.option-chip');
            const unsel = Array.from(chips).find(c => !c.classList.contains('is-selected') && !c.disabled);
            if (!unsel) return null;
            const r = unsel.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if chip_rect:
            hover_element(b, chip_rect)
            chip_hover = b.js("""
            (() => {
                const chips = document.querySelectorAll('.option-chip');
                const unsel = Array.from(chips).find(c => !c.classList.contains('is-selected') && !c.disabled);
                const s = window.getComputedStyle(unsel);
                return { transform: s.transform, border: s.borderColor, bg: s.backgroundColor, color: s.color };
            })()
            """)
            print(f"  Option Chip Hovered: transform={chip_hover['transform']}, border={chip_hover['border']}, color={chip_hover['color']}")
            assert chip_hover['transform'] != 'none', "Option chip must lift on hover"

        # 2d. Stepper Qty Button Hover
        qty_rect = b.js("""
        (() => {
            const btn = document.querySelector('#qty-increase-btn');
            if (!btn) return null;
            const r = btn.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if qty_rect:
            hover_element(b, qty_rect)
            qty_hover = b.js("""
            (() => {
                const btn = document.querySelector('#qty-increase-btn');
                const s = window.getComputedStyle(btn);
                return { bg: s.backgroundColor, color: s.color };
            })()
            """)
            print(f"  Qty Button Hovered: bg={qty_hover['bg']}, color={qty_hover['color']}")

        # 2e. Add to Cart Button Hover
        cart_rect = b.js("""
        (() => {
            const btn = document.querySelector('#btn-add-to-cart');
            if (!btn || btn.disabled) return null;
            const r = btn.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if cart_rect:
            hover_element(b, cart_rect)
            cart_hover = b.js("""
            (() => {
                const btn = document.querySelector('#btn-add-to-cart');
                const s = window.getComputedStyle(btn);
                return { transform: s.transform, shadow: s.boxShadow };
            })()
            """)
            print(f"  Add to Cart Hovered: transform={cart_hover['transform']}, shadow={cart_hover['shadow']}")
            assert cart_hover['transform'] != 'none', "Add to Cart button must elevate on hover"

        save_screenshot(b, "hover_product_controls_desktop.png")

        # 2f. Related Products Section and Card Hover
        b.js("document.querySelector('.product-related-card')?.scrollIntoView({ behavior: 'instant', block: 'center' })")
        time.sleep(0.4)
        related_rect = b.js("""
        (() => {
            const card = document.querySelector('.product-related-card');
            if (!card) return null;
            const r = card.getBoundingClientRect();
            return { top: r.top, left: r.left, width: r.width, height: r.height };
        })()
        """)
        if related_rect:
            hover_element(b, related_rect)
            related_hover = b.js("""
            (() => {
                const card = document.querySelector('.product-related-card');
                const media = card.querySelector('.product-related-media');
                const title = card.querySelector('.product-related-card-title');
                const cs = window.getComputedStyle(card);
                const ms = media ? window.getComputedStyle(media) : null;
                const ts = title ? window.getComputedStyle(title) : null;
                return {
                    cardTransform: cs.transform,
                    mediaShadow: ms ? ms.boxShadow : null,
                    mediaBorder: ms ? ms.borderColor : null,
                    titleColor: ts ? ts.color : null
                };
            })()
            """)
            print(f"  Related Card Hovered: cardTransform={related_hover['cardTransform']}, titleColor={related_hover['titleColor']}, shadow={related_hover['mediaShadow']}")
            assert related_hover['cardTransform'] != 'none', "Related card must lift on hover"

        save_screenshot(b, "hover_product_related_desktop.png")

        # 2g. Image async decoding attribute check
        img_stats = b.js("""
        (() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            const asyncImgs = imgs.filter(i => i.decoding === 'async');
            return { total: imgs.length, asyncCount: asyncImgs.length };
        })()
        """)
        print(f"  Async Image Decoding: {img_stats['asyncCount']} of {img_stats['total']} images decoding='async'", flush=True)

        print("\n=== HOVER & PERFORMANCE ACCEPTANCE PASSED 100%! ===", flush=True)

if __name__ == '__main__':
    main()
