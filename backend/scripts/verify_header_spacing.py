import json
import os
import pathlib
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser_driver import Browser

def test_header_spacing():
    artifacts = pathlib.Path("C:/Users/SyedNajam's PC/.gemini/antigravity/brain/e0e456e1-e4cb-4fd8-a8d5-475bb70698e3")
    
    print("--- Starting Browser Verification for Header Spacing & Banner Alignment ---")
    with Browser(artifacts) as b:
        # 1. Desktop Test (1440x900)
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
        b.goto('http://localhost:13000/')
        b.expect('document.querySelector(".hero-section")', 'Hero section rendered')
        time.sleep(0.5)
        
        # Check initial expanded state
        expanded_stats = b.js('''(() => {
            const header = document.querySelector('.site-header');
            const panel = document.querySelector('.site-header .header-panel');
            const hero = document.querySelector('.hero-section');
            const hb = header ? header.getBoundingClientRect() : null;
            const pb = panel ? panel.getBoundingClientRect() : null;
            const hrb = hero ? hero.getBoundingClientRect() : null;
            return {
                navState: header?.dataset.navState,
                headerHeight: hb ? hb.height : 0,
                pillTop: pb ? pb.top : 0,
                pillBottom: pb ? pb.bottom : 0,
                pillHeight: pb ? pb.height : 0,
                heroTop: hrb ? hrb.top : 0,
                airGap: (hrb && pb) ? (hrb.top - pb.bottom) : 0
            };
        })()''')
        print("Desktop Initial (Expanded):", json.dumps(expanded_stats, indent=2))
        
        # Save screenshot of expanded desktop
        res = b.cdp('Page.captureScreenshot', {'format': 'png'})
        import base64
        with open(artifacts / "verified_desktop_expanded_air_gap.png", "wb") as f:
            f.write(base64.b64decode(res['data']))
        print("Saved verified_desktop_expanded_air_gap.png")

        # Wait for idle countdown (2.5s) to trigger compact mode
        time.sleep(3.0)
        compact_stats = b.js('''(() => {
            const header = document.querySelector('.site-header');
            const logo = document.querySelector('.site-header #header-logo-slot');
            const hero = document.querySelector('.hero-section');
            const hb = header ? header.getBoundingClientRect() : null;
            const lb = logo ? logo.getBoundingClientRect() : null;
            const hrb = hero ? hero.getBoundingClientRect() : null;
            return {
                navState: header?.dataset.navState,
                headerHeight: hb ? hb.height : 0,
                logoTop: lb ? lb.top : 0,
                logoHeight: lb ? lb.height : 0,
                heroTop: hrb ? hrb.top : 0,
                whiteLineThickness: hrb ? hrb.top : 0
            };
        })()''')
        print("Desktop Idle/Collapsed (Compact):", json.dumps(compact_stats, indent=2))
        
        res_compact = b.cdp('Page.captureScreenshot', {'format': 'png'})
        with open(artifacts / "verified_desktop_compact_half_line.png", "wb") as f:
            f.write(base64.b64decode(res_compact['data']))
        print("Saved verified_desktop_compact_half_line.png")

        # 2. Mobile Viewport Test (390x844 iPhone 16)
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 390, 'height': 844, 'deviceScaleFactor': 3, 'mobile': True})
        b.goto('http://localhost:13000/')
        b.expect('document.querySelector(".hero-section")', 'Mobile hero section rendered')
        time.sleep(0.5)
        
        mobile_expanded = b.js('''(() => {
            const header = document.querySelector('.site-header');
            const panel = document.querySelector('.site-header .header-panel');
            const hero = document.querySelector('.hero-section');
            const pb = panel ? panel.getBoundingClientRect() : null;
            const hrb = hero ? hero.getBoundingClientRect() : null;
            return {
                navState: header?.dataset.navState,
                pillBottom: pb ? pb.bottom : 0,
                heroTop: hrb ? hrb.top : 0,
                airGap: (hrb && pb) ? (hrb.top - pb.bottom) : 0,
                hasHorizScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth
            };
        })()''')
        print("Mobile Initial (Expanded):", json.dumps(mobile_expanded, indent=2))
        
        res_mobile_exp = b.cdp('Page.captureScreenshot', {'format': 'png'})
        with open(artifacts / "verified_mobile_expanded_air_gap.png", "wb") as f:
            f.write(base64.b64decode(res_mobile_exp['data']))
        print("Saved verified_mobile_expanded_air_gap.png")

        time.sleep(3.0)
        mobile_compact = b.js('''(() => {
            const header = document.querySelector('.site-header');
            const hero = document.querySelector('.hero-section');
            const hrb = hero ? hero.getBoundingClientRect() : null;
            return {
                navState: header?.dataset.navState,
                heroTop: hrb ? hrb.top : 0,
                whiteLineThickness: hrb ? hrb.top : 0,
                hasHorizScroll: document.documentElement.scrollWidth > document.documentElement.clientWidth
            };
        })()''')
        print("Mobile Idle/Collapsed (Compact):", json.dumps(mobile_compact, indent=2))

        res_mobile_comp = b.cdp('Page.captureScreenshot', {'format': 'png'})
        with open(artifacts / "verified_mobile_compact_half_line.png", "wb") as f:
            f.write(base64.b64decode(res_mobile_comp['data']))
        print("Saved verified_mobile_compact_half_line.png")

        # 3. Subpage Test (/collections)
        b.cdp('Emulation.setDeviceMetricsOverride', {'width': 1440, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
        b.goto('http://localhost:13000/collections')
        b.expect('document.querySelector(".collections-page-container")', 'Collections container rendered')
        time.sleep(0.5)
        collections_stats = b.js('''(() => {
            const container = document.querySelector('.collections-page-container');
            const cb = container ? container.getBoundingClientRect() : null;
            return {
                hasContainer: Boolean(container),
                containerTop: cb ? cb.top : 0
            };
        })()''')
        print("Subpage (/collections):", json.dumps(collections_stats, indent=2))

        print("--- ALL BROWSER CHECKS COMPLETED ---")

if __name__ == "__main__":
    test_header_spacing()

