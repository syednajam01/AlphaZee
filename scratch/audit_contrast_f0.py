"""Audit text/background colors and contrast ratios across storefront."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-repairs/run_20261105_reproduce'

JS_CONTRAST_AUDIT = """
(() => {
    function parseRgb(colorStr) {
        if (!colorStr) return null;
        const match = colorStr.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/);
        if (!match) return null;
        return {
            r: parseInt(match[1], 10),
            g: parseInt(match[2], 10),
            b: parseInt(match[3], 10),
            a: match[4] !== undefined ? parseFloat(match[4]) : 1.0
        };
    }

    function getLuminance(rgb) {
        const a = [rgb.r, rgb.g, rgb.b].map(v => {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
    }

    function getContrast(rgb1, rgb2) {
        const l1 = getLuminance(rgb1);
        const l2 = getLuminance(rgb2);
        const lighter = Math.max(l1, l2);
        const darker = Math.min(l1, l2);
        return (lighter + 0.05) / (darker + 0.05);
    }

    function getEffectiveBg(el) {
        let cur = el;
        while (cur && cur !== document.documentElement) {
            const cs = window.getComputedStyle(cur);
            const bg = parseRgb(cs.backgroundColor);
            if (bg && bg.a > 0.8) {
                return bg;
            }
            cur = cur.parentElement;
        }
        return { r: 247, g: 247, b: 242, a: 1 }; // Default #F7F7F2
    }

    const elementsToCheck = [
        // Header
        '.announcement-bar, .proto-banner, .prototype-announcement',
        'header a, .header-nav a',
        '#btn-cart',
        '#btn-mobile-menu',
        // Hero
        '.hero-section',
        '.hero-badge',
        '.hero-title',
        '.hero-desc',
        '.hero-price-tag',
        '.hero-cta-btn',
        '.hero-section .btn-secondary',
        '.hero-ctrl-btn',
        '.hero-slide-indicator',
        // Product Page
        '.product-breadcrumb a',
        '.product-breadcrumb-current',
        '.product-page-title',
        '.product-page-price',
        '.product-page-badge',
        '.product-stock-status',
        '.product-gallery-thumb',
        '.gallery-nav-btn',
        '.gallery-zoom-btn',
        '.gallery-counter',
        '.option-label',
        '.option-pill',
        '.quantity-btn',
        '.quantity-input',
        '.btn-add-to-cart, #add-to-cart-btn',
        '.product-detail-fact h3',
        '.product-detail-fact p',
        '.product-unavailable-title',
        '.product-unavailable-desc'
    ];

    const results = [];
    elementsToCheck.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            const cs = window.getComputedStyle(el);
            const text = (el.textContent || '').trim().slice(0, 40);
            const fg = parseRgb(cs.color);
            const bg = getEffectiveBg(el);
            if (!fg || !bg) return;
            const ratio = getContrast(fg, bg);
            const fontSize = parseFloat(cs.fontSize);
            const isBold = parseInt(cs.fontWeight, 10) >= 600 || cs.fontWeight === 'bold';
            const isLarge = fontSize >= 24 || (fontSize >= 18.5 && isBold);
            const required = isLarge ? 3.0 : 4.5;
            const passes = ratio >= required;

            results.push({
                selector: sel,
                tag: el.tagName,
                text: text,
                fg: cs.color,
                bg: `rgb(${bg.r}, ${bg.g}, ${bg.b})`,
                fontSize: cs.fontSize,
                fontWeight: cs.fontWeight,
                contrastRatio: Math.round(ratio * 100) / 100,
                requiredRatio: required,
                passes: passes
            });
        });
    });

    return results;
})()
"""

def main():
    report = {}
    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # Check Home
        b.goto("http://localhost:13000/")
        b.wait_for_selector(".hero-section", timeout=10)
        import time; time.sleep(2)
        home_audit = b.js(JS_CONTRAST_AUDIT)
        report["home"] = home_audit

        # Check Product Page
        b.goto("http://localhost:13000/products/temporary-media-preview-20261105")
        b.wait_for_selector(".product-page-title", timeout=10)
        time.sleep(1)
        product_audit = b.js(JS_CONTRAST_AUDIT)
        report["product"] = product_audit

    out_file = OUT_DIR / "contrast_audit_raw.json"
    out_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Contrast audit saved to {out_file}", flush=True)

    # Print failures
    print("\n--- CONTRAST FAILURES ---")
    for page, items in report.items():
        failures = [it for it in items if not it["passes"]]
        print(f"\n{page.upper()} Failures ({len(failures)}):")
        for f in failures:
            print(f"  [{f['selector']}] '{f['text']}': ratio {f['contrastRatio']}:1 (needed {f['requiredRatio']}:1) fg={f['fg']} bg={f['bg']}")

if __name__ == '__main__':
    main()

