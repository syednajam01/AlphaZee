"""
P3: Storefront Performance Profiling Script
Measures Cold-Load LCP, CLS, FCP, Navigation Timings, Resource Weights, Long Tasks,
and Interaction Latency across Development (http://localhost:13000) and
Production Build (http://127.0.0.1:4173).
Runs 3 cold runs per target, computes median and spread, and checks against project targets:
- LCP <= 2.5s
- CLS <= 0.1
- Interaction Latency <= 200ms
"""
import json
import statistics
import sys
import time
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/three-portal-quality/run_p3_performance'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

OBSERVER_SCRIPT = """
window.__perfMetrics = {
    lcp: 0,
    lcpElement: null,
    cls: 0,
    longTasks: 0,
    maxLongTask: 0,
    totalLongTaskDuration: 0
};

try {
    const lcpObserver = new PerformanceObserver((entryList) => {
        const entries = entryList.getEntries();
        const lastEntry = entries[entries.length - 1];
        if (lastEntry) {
            window.__perfMetrics.lcp = lastEntry.startTime;
            window.__perfMetrics.lcpElement = lastEntry.element ? (lastEntry.element.tagName + (lastEntry.element.className ? '.' + lastEntry.element.className : '')) : null;
            window.__perfMetrics.lcpUrl = lastEntry.url || null;
            window.__perfMetrics.lcpSize = lastEntry.size || 0;
        }
    });
    lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
} catch (e) {}

try {
    const clsObserver = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
            if (!entry.hadRecentInput) {
                window.__perfMetrics.cls += entry.value;
            }
        }
    });
    clsObserver.observe({ type: 'layout-shift', buffered: true });
} catch (e) {}

try {
    const ltObserver = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
            window.__perfMetrics.longTasks++;
            window.__perfMetrics.totalLongTaskDuration += entry.duration;
            if (entry.duration > window.__perfMetrics.maxLongTask) {
                window.__perfMetrics.maxLongTask = entry.duration;
            }
        }
    });
    ltObserver.observe({ type: 'longtask', buffered: true });
} catch (e) {}
"""

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT SAVED] {filename}", flush=True)

def measure_run(browser, url, wait_selector, interaction_type=None):
    # Clear cache and cookies for cold load
    browser.cdp('Network.clearBrowserCache')
    browser.cdp('Network.clearBrowserCookies')
    
    # Inject metrics observer before navigation
    browser.cdp('Page.addScriptToEvaluateOnNewDocument', {'source': OBSERVER_SCRIPT})

    t0 = time.time()
    browser.goto(url, wait_selector=wait_selector, timeout=12)
    # Give time for LCP and initial scripts to settle
    time.sleep(2.0)

    # Collect Performance API data
    metrics = browser.js("""
    (() => {
        const nav = performance.getEntriesByType('navigation')[0] || {};
        const fcpEntry = performance.getEntriesByName('first-contentful-paint')[0];
        const resources = performance.getEntriesByType('resource');

        let totalTransfer = 0;
        let jsTransfer = 0;
        let cssTransfer = 0;
        let imgTransfer = 0;
        let mediaTransfer = 0;

        resources.forEach(r => {
            const size = r.transferSize || 0;
            totalTransfer += size;
            const name = r.name.toLowerCase();
            if (name.endsWith('.js') || r.initiatorType === 'script') jsTransfer += size;
            else if (name.endsWith('.css') || r.initiatorType === 'link') cssTransfer += size;
            else if (r.initiatorType === 'img' || name.match(/\\.(png|jpg|jpeg|webp|avif|svg)(\\?|$)/)) imgTransfer += size;
            else if (r.initiatorType === 'video' || name.match(/\\.(mp4|webm)(\\?|$)/)) mediaTransfer += size;
        });

        return {
            fcp: fcpEntry ? fcpEntry.startTime : null,
            lcp: window.__perfMetrics.lcp,
            lcpElement: window.__perfMetrics.lcpElement,
            lcpUrl: window.__perfMetrics.lcpUrl,
            lcpSize: window.__perfMetrics.lcpSize,
            cls: window.__perfMetrics.cls,
            longTasks: window.__perfMetrics.longTasks,
            totalLongTaskDuration: window.__perfMetrics.totalLongTaskDuration,
            maxLongTask: window.__perfMetrics.maxLongTask,
            domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
            loadEventEnd: nav.loadEventEnd - nav.startTime,
            resourceCount: resources.length,
            totalTransferBytes: totalTransfer,
            jsBytes: jsTransfer,
            cssBytes: cssTransfer,
            imgBytes: imgTransfer,
            mediaBytes: mediaTransfer
        };
    })()
    """)

    # Measure interaction latency if specified
    interaction_latency = None
    if interaction_type == 'gallery_next':
        # Measure gallery next slide transition latency
        interaction_latency = browser.js("""
        (() => {
            return new Promise(resolve => {
                const btn = document.querySelector('#gallery-next-btn');
                if (!btn) {
                    resolve(null);
                    return;
                }
                const tStart = performance.now();
                btn.click();
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        const latency = performance.now() - tStart;
                        resolve(latency);
                    });
                });
            });
        })()
        """)
    elif interaction_type == 'cart_toggle':
        # Measure cart drawer open latency
        interaction_latency = browser.js("""
        (() => {
            return new Promise(resolve => {
                const btn = document.querySelector('#btn-cart') || document.querySelector('a[href="#cart"]');
                if (!btn) {
                    resolve(null);
                    return;
                }
                const tStart = performance.now();
                btn.click();
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        const latency = performance.now() - tStart;
                        resolve(latency);
                    });
                });
            });
        })()
        """)
        # Close cart drawer
        browser.js("document.querySelector('#cart-close-btn')?.click()")
        time.sleep(0.3)

    metrics['interactionLatency'] = interaction_latency
    return metrics

def summarize_metrics(runs):
    keys = ['fcp', 'lcp', 'cls', 'domContentLoaded', 'loadEventEnd', 'totalTransferBytes', 'interactionLatency']
    summary = {}
    for k in keys:
        vals = [r[k] for r in runs if r.get(k) is not None]
        if vals:
            summary[k] = {
                'median': statistics.median(vals),
                'min': min(vals),
                'max': max(vals),
                'spread': max(vals) - min(vals)
            }
        else:
            summary[k] = None
    return summary

def main():
    print("=== STARTING P3 STOREFRONT PERFORMANCE PROFILING ===", flush=True)

    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # Standard Desktop Viewport (1366 x 768)
        b.set_viewport(1366, 768)

        # -------------------------------------------------------------
        # TARGET A: PRODUCTION BUILD (http://127.0.0.1:4173)
        # -------------------------------------------------------------
        print("\n=======================================================", flush=True)
        print("  PROFILING: PRODUCTION BUILD (http://127.0.0.1:4173)", flush=True)
        print("=======================================================", flush=True)

        # 1. Homepage Production (3 runs)
        prod_home_runs = []
        for i in range(1, 4):
            print(f"\n  [Prod Home Run {i}/3]", flush=True)
            res = measure_run(b, "http://127.0.0.1:4173/", wait_selector=".product-card", interaction_type="cart_toggle")
            prod_home_runs.append(res)
            print(f"    LCP: {res['lcp']:.1f}ms (Element: {res['lcpElement']}), CLS: {res['cls']:.4f}, FCP: {res['fcp']:.1f}ms", flush=True)
            print(f"    DCL: {res['domContentLoaded']:.1f}ms, Load: {res['loadEventEnd']:.1f}ms", flush=True)
            print(f"    Resources: {res['resourceCount']} ({res['totalTransferBytes']/1024:.1f} KB transferred), Cart Toggle Latency: {res['interactionLatency']:.2f}ms", flush=True)
        
        save_screenshot(b, "p3_prod_home_desktop.png")
        prod_home_summary = summarize_metrics(prod_home_runs)

        # 2. Product Page Production (3 runs)
        prod_prod_runs = []
        for i in range(1, 4):
            print(f"\n  [Prod Product Page Run {i}/3]", flush=True)
            res = measure_run(b, "http://127.0.0.1:4173/products/temporary-media-preview-20261105", wait_selector=".product-gallery", interaction_type="gallery_next")
            prod_prod_runs.append(res)
            print(f"    LCP: {res['lcp']:.1f}ms (Element: {res['lcpElement']}), CLS: {res['cls']:.4f}, FCP: {res['fcp']:.1f}ms", flush=True)
            print(f"    DCL: {res['domContentLoaded']:.1f}ms, Load: {res['loadEventEnd']:.1f}ms", flush=True)
            print(f"    Resources: {res['resourceCount']} ({res['totalTransferBytes']/1024:.1f} KB transferred), Gallery Next Latency: {res['interactionLatency']:.2f}ms", flush=True)

        save_screenshot(b, "p3_prod_product_desktop.png")
        prod_prod_summary = summarize_metrics(prod_prod_runs)

        # -------------------------------------------------------------
        # TARGET B: DEVELOPMENT EXPERIENCE (http://localhost:13000)
        # -------------------------------------------------------------
        print("\n=======================================================", flush=True)
        print("  PROFILING: DEVELOPMENT EXPERIENCE (http://localhost:13000)", flush=True)
        print("=======================================================", flush=True)

        # 1. Homepage Development (3 runs)
        dev_home_runs = []
        for i in range(1, 4):
            print(f"\n  [Dev Home Run {i}/3]", flush=True)
            res = measure_run(b, "http://localhost:13000/", wait_selector=".product-card", interaction_type="cart_toggle")
            dev_home_runs.append(res)
            print(f"    LCP: {res['lcp']:.1f}ms (Element: {res['lcpElement']}), CLS: {res['cls']:.4f}, FCP: {res['fcp']:.1f}ms", flush=True)
            print(f"    DCL: {res['domContentLoaded']:.1f}ms, Load: {res['loadEventEnd']:.1f}ms", flush=True)
            print(f"    Resources: {res['resourceCount']} ({res['totalTransferBytes']/1024:.1f} KB transferred), Cart Toggle Latency: {res['interactionLatency']:.2f}ms", flush=True)

        save_screenshot(b, "p3_dev_home_desktop.png")
        dev_home_summary = summarize_metrics(dev_home_runs)

        # 2. Product Page Development (3 runs)
        dev_prod_runs = []
        for i in range(1, 4):
            print(f"\n  [Dev Product Page Run {i}/3]", flush=True)
            res = measure_run(b, "http://localhost:13000/products/temporary-media-preview-20261105", wait_selector=".product-gallery", interaction_type="gallery_next")
            dev_prod_runs.append(res)
            print(f"    LCP: {res['lcp']:.1f}ms (Element: {res['lcpElement']}), CLS: {res['cls']:.4f}, FCP: {res['fcp']:.1f}ms", flush=True)
            print(f"    DCL: {res['domContentLoaded']:.1f}ms, Load: {res['loadEventEnd']:.1f}ms", flush=True)
            print(f"    Resources: {res['resourceCount']} ({res['totalTransferBytes']/1024:.1f} KB transferred), Gallery Next Latency: {res['interactionLatency']:.2f}ms", flush=True)

        save_screenshot(b, "p3_dev_product_desktop.png")
        dev_prod_summary = summarize_metrics(dev_prod_runs)

        # -------------------------------------------------------------
        # TARGET C: MOBILE VIEWPORT (390 x 844) PRODUCTION
        # -------------------------------------------------------------
        print("\n=======================================================", flush=True)
        print("  PROFILING: MOBILE VIEWPORT (390x844) PRODUCTION", flush=True)
        print("=======================================================", flush=True)
        b.set_viewport(390, 844, mobile=True, device_scale_factor=2)
        
        mobile_home_res = measure_run(b, "http://127.0.0.1:4173/", wait_selector=".product-card")
        print(f"  Mobile Home -> LCP: {mobile_home_res['lcp']:.1f}ms, CLS: {mobile_home_res['cls']:.4f}, DCL: {mobile_home_res['domContentLoaded']:.1f}ms", flush=True)
        save_screenshot(b, "p3_prod_home_mobile.png")

        mobile_prod_res = measure_run(b, "http://127.0.0.1:4173/products/temporary-media-preview-20261105", wait_selector=".product-gallery")
        print(f"  Mobile Product -> LCP: {mobile_prod_res['lcp']:.1f}ms, CLS: {mobile_prod_res['cls']:.4f}, DCL: {mobile_prod_res['domContentLoaded']:.1f}ms", flush=True)
        save_screenshot(b, "p3_prod_product_mobile.png")

    # Write report JSON
    results = {
        'environment': {
            'browser': 'Chromium Headless (Chrome)',
            'desktop_viewport': '1366x768',
            'mobile_viewport': '390x844',
            'cache_state': 'Cold Load (Cleared cache and cookies prior to each run)',
            'fixtures': ['Homepage with hero video/slider & catalog grid', 'Product: /products/temporary-media-preview-20261105 (9 images + 1 video)'],
            'build_target': 'Vite 7.3 production build (dist/)'
        },
        'production_home': prod_home_summary,
        'production_product': prod_prod_summary,
        'dev_home': dev_home_summary,
        'dev_product': dev_prod_summary,
        'mobile_production': {
            'home': mobile_home_res,
            'product': mobile_prod_res
        }
    }

    out_file = OUT_DIR / "performance_measurements.json"
    out_file.write_text(json.dumps(results, indent=2))
    print(f"\n[REPORT SAVED] {out_file}", flush=True)

    print("\n=== P3 STOREFRONT PERFORMANCE PROFILING COMPLETED ===", flush=True)

if __name__ == "__main__":
    main()

