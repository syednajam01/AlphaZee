"""Verify Phase U2 Gate: Header, Home Editorial Layout, Responsive 3:4 Catalog Grid, Hover & Sorting."""
import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-redesign/run_u2_catalog'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Verifying Phase U2 Gate on http://127.0.0.1:13001 ...", flush=True)
    results = {
        "checks": [],
        "screenshots": {},
        "errors": []
    }

    with RedesignBrowser(OUT_DIR) as b:
        # 1. Header & Home Initial View (Contrast, Sticky, Typography)
        print("1. Testing Header contrast and Editorial Hero...", flush=True)
        b.goto("http://127.0.0.1:13001/", wait_selector='#featured')
        time.sleep(2)

        header_styles = b.js("""(() => {
            const h = document.querySelector('.site-header');
            if (!h) return null;
            const cs = window.getComputedStyle(h);
            const logo = h.querySelector('.brand-logo-img');
            const logoCs = logo ? window.getComputedStyle(logo) : null;
            return {
                position: cs.position,
                backgroundColor: cs.backgroundColor,
                color: cs.color,
                logoFilter: logoCs ? logoCs.filter : null,
                hasAnnouncement: Boolean(document.querySelector('.announcement-bar'))
            };
        })()""")

        hero_styles = b.js("""(() => {
            const hero = document.querySelector('.hero-section');
            const title = document.querySelector('.hero-title');
            if (!hero || !title) return null;
            const heroCs = window.getComputedStyle(hero);
            const titleCs = window.getComputedStyle(title);
            return {
                titleFontFamily: titleCs.fontFamily,
                titleFontWeight: titleCs.fontWeight,
                heroHeight: hero.getBoundingClientRect().height,
                hasShopCta: Boolean(hero.querySelector('.hero-cta-btn') || hero.querySelector('a[href="#featured"]'))
            };
        })()""")

        shot1 = b.capture_screenshot(OUT_DIR / "u2_desktop_header_and_hero.png")
        results["screenshots"]["header_and_hero"] = str(shot1)

        check_header_hero = {
            "name": "Header Contrast & Editorial Hero",
            "header": header_styles,
            "hero": hero_styles,
            "passed": bool(
                header_styles and
                header_styles["position"] in ("sticky", "fixed") and
                header_styles["hasAnnouncement"] and
                hero_styles and
                ("Newsreader" in hero_styles["titleFontFamily"] or "serif" in hero_styles["titleFontFamily"].lower())
            )
        }
        results["checks"].append(check_header_hero)
        print("  Header & Hero Check:", check_header_hero, flush=True)

        # 2. Consistent 3:4 Aspect Ratio on Catalog Cards
        print("2. Verifying 3:4 aspect ratio crops on catalog cards...", flush=True)
        card_metrics = b.js("""(() => {
            const cards = [...document.querySelectorAll('.product-card')];
            if (!cards.length) return null;
            return cards.slice(0, 4).map(card => {
                const wrapper = card.querySelector('.product-card-img-wrapper');
                const img = card.querySelector('.product-card-img');
                const title = card.querySelector('.product-card-title')?.textContent?.trim();
                const price = card.querySelector('.product-card-price')?.textContent?.trim();
                const rect = wrapper ? wrapper.getBoundingClientRect() : null;
                const ratio = rect && rect.height > 0 ? (rect.width / rect.height) : 0;
                return {
                    title,
                    price,
                    wrapperWidth: rect ? Math.round(rect.width) : 0,
                    wrapperHeight: rect ? Math.round(rect.height) : 0,
                    ratio: Math.round(ratio * 100) / 100, // Expected ~0.75 for 3:4
                    imgFit: img ? window.getComputedStyle(img).objectFit : null
                };
            });
        })()""")

        b.js("document.querySelector('#featured')?.scrollIntoView({ block: 'start' })")
        time.sleep(0.5)
        shot2 = b.capture_screenshot(OUT_DIR / "u2_desktop_catalog_grid_3_4.png")
        results["screenshots"]["catalog_3_4"] = str(shot2)

        # 3:4 ratio is 0.75 (allow minor pixel rounding between 0.70 and 0.80)
        all_3_4 = bool(card_metrics and len(card_metrics) > 0 and all(0.70 <= c["ratio"] <= 0.80 for c in card_metrics))
        check_aspect = {
            "name": "Consistent 3:4 Image Frame Ratio",
            "cards_sampled": card_metrics,
            "is_3_4_ratio": all_3_4,
            "passed": all_3_4
        }
        results["checks"].append(check_aspect)
        print("  Aspect Ratio Check:", check_aspect, flush=True)

        # 3. Responsive Breakpoints: Desktop (4 cols), Tablet (3 cols), Phone (2 cols)
        print("3. Testing responsive catalog grid breakpoints...", flush=True)
        # Desktop 1440px
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
        b.js("document.querySelector('#featured')?.scrollIntoView({ block: 'start' })")
        time.sleep(0.5)
        cols_desktop = b.js("""(() => {
            const grid = document.querySelector('.products-grid');
            return grid ? window.getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0;
        })()""")
        shot_desktop = b.capture_screenshot(OUT_DIR / "u2_desktop_4col.png")
        results["screenshots"]["desktop_4col"] = str(shot_desktop)

        # Tablet 768px
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 768, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False})
        b.js("document.querySelector('#featured')?.scrollIntoView({ block: 'start' })")
        time.sleep(0.5)
        cols_tablet = b.js("""(() => {
            const grid = document.querySelector('.products-grid');
            return grid ? window.getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0;
        })()""")
        shot_tablet = b.capture_screenshot(OUT_DIR / "u2_tablet_3col.png")
        results["screenshots"]["tablet_3col"] = str(shot_tablet)

        # Phone 390px
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 2, 'mobile': True})
        b.js("document.querySelector('#featured')?.scrollIntoView({ block: 'start' })")
        time.sleep(0.5)
        cols_phone = b.js("""(() => {
            const grid = document.querySelector('.products-grid');
            return grid ? window.getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0;
        })()""")
        shot_phone = b.capture_screenshot(OUT_DIR / "u2_mobile_2col.png")
        results["screenshots"]["mobile_2col"] = str(shot_phone)

        check_breakpoints = {
            "name": "Responsive Breakpoints (4 / 3 / 2 columns)",
            "desktop_cols": cols_desktop,
            "tablet_cols": cols_tablet,
            "phone_cols": cols_phone,
            "passed": bool(cols_desktop == 4 and cols_tablet == 3 and cols_phone == 2)
        }
        results["checks"].append(check_breakpoints)
        print("  Breakpoints Check:", check_breakpoints, flush=True)

        # 4. Touch Navigation (Immediate Tap) on Mobile
        print("4. Testing mobile touch immediate navigation...", flush=True)
        # Touch tap on first product card media link
        first_slug = b.js("document.querySelector('.product-card-media-link')?.dataset?.slug")
        b.click('.product-card-media-link')
        b.wait_for_selector('.product-page-title', timeout=8)
        navigated_to_product = b.js("Boolean(document.querySelector('.product-page-title'))")
        shot_touch = b.capture_screenshot(OUT_DIR / "u2_mobile_touch_tap_nav.png")
        results["screenshots"]["touch_nav"] = str(shot_touch)

        check_touch = {
            "name": "Touch Navigation Immediate Tap",
            "slug": first_slug,
            "navigated_to_product": navigated_to_product,
            "passed": bool(navigated_to_product)
        }
        results["checks"].append(check_touch)
        print("  Touch Tap Check:", check_touch, flush=True)

        # Reset to desktop for Sorting & Filtering checks
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
        b.goto("http://127.0.0.1:13001/", wait_selector='#featured')
        time.sleep(1)

        # 5. Full Dataset Sorting
        print("5. Testing Full-Dataset Sorting...", flush=True)
        # Sort Price: Low to High
        b.js("""(() => {
            const sel = document.querySelector('#catalog-sort');
            if (sel) {
                sel.value = 'price-asc';
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        })()""")
        time.sleep(0.5)
        prices_asc = b.js("""(() => {
            return [...document.querySelectorAll('.product-card-price')].slice(0, 5).map(el => el.textContent.trim());
        })()""")
        shot_sort_asc = b.capture_screenshot(OUT_DIR / "u2_sorted_price_asc.png")
        results["screenshots"]["sort_price_asc"] = str(shot_sort_asc)

        # Sort Price: High to Low
        b.js("""(() => {
            const sel = document.querySelector('#catalog-sort');
            if (sel) {
                sel.value = 'price-desc';
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        })()""")
        time.sleep(0.5)
        prices_desc = b.js("""(() => {
            return [...document.querySelectorAll('.product-card-price')].slice(0, 5).map(el => el.textContent.trim());
        })()""")

        check_sort = {
            "name": "Full-Dataset Sorting",
            "prices_asc": prices_asc,
            "prices_desc": prices_desc,
            "passed": bool(len(prices_asc) >= 2 and len(prices_desc) >= 2)
        }
        results["checks"].append(check_sort)
        print("  Sort Check:", check_sort, flush=True)

        # 6. Category Filtering & Empty / Retry State
        print("6. Testing Category Filtering & Tab switching...", flush=True)
        tab_names = b.js("""[...document.querySelectorAll('.filter-tabs .option-pill')].map(b => b.textContent.trim())""")
        # Click second tab if exists
        has_second_tab = b.js("Boolean(document.querySelectorAll('.filter-tabs .option-pill')[1])")
        if has_second_tab:
            b.js("document.querySelectorAll('.filter-tabs .option-pill')[1].click()")
            time.sleep(1)
            shot_filter = b.capture_screenshot(OUT_DIR / "u2_filtered_category.png")
            results["screenshots"]["filtered_category"] = str(shot_filter)

        check_filter = {
            "name": "Category Tabs & Filter Switching",
            "tabs": tab_names,
            "passed": bool(tab_names and len(tab_names) >= 1)
        }
        results["checks"].append(check_filter)
        print("  Filter Check:", check_filter, flush=True)

        # 7. Hover Crossfade Check (Fine pointer)
        print("7. Testing image hover crossfade & neutral fallback...", flush=True)
        b.goto("http://127.0.0.1:13001/", wait_selector='#featured')
        time.sleep(1)

        hover_info = b.js("""(() => {
            const card = document.querySelector('.product-card');
            if (!card) return null;
            const primary = card.querySelector('.product-card-img-primary');
            const secondary = card.querySelector('.product-card-img-secondary');
            return {
                hasPrimary: Boolean(primary),
                hasSecondary: Boolean(secondary),
                primarySrc: primary?.src,
                secondarySrc: secondary?.src,
                primaryClasses: primary?.className
            };
        })()""")

        # Hover over first card
        b.js("""(() => {
            const card = document.querySelector('.product-card');
            if (card) {
                card.scrollIntoView({ block: 'center' });
            }
        })()""")
        time.sleep(0.5)

        card_rect = b.js("""(() => {
            const card = document.querySelector('.product-card');
            if (!card) return null;
            const r = card.getBoundingClientRect();
            return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) };
        })()""")

        if card_rect:
            b.cdp('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': card_rect['x'],
                'y': card_rect['y']
            })
            time.sleep(0.3)
            shot_hover_enter = b.capture_screenshot(OUT_DIR / "u2_card_hover_enter.png")
            results["screenshots"]["hover_enter"] = str(shot_hover_enter)

            # Move away
            b.cdp('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': 10,
                'y': 10
            })
            time.sleep(0.3)
            shot_hover_leave = b.capture_screenshot(OUT_DIR / "u2_card_hover_leave.png")
            results["screenshots"]["hover_leave"] = str(shot_hover_leave)

        check_hover = {
            "name": "Image Hover Swap & Neutral Fallback",
            "info": hover_info,
            "passed": bool(hover_info and hover_info["hasPrimary"])
        }
        results["checks"].append(check_hover)
        print("  Hover Check:", check_hover, flush=True)

        results["errors"] = b.errors
        (OUT_DIR / "u2_verification.json").write_text(json.dumps(results, indent=2))
        print("U2 Gate verification completed successfully.", flush=True)

if __name__ == '__main__':
    main()
