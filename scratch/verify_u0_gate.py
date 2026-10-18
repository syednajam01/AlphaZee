"""Verify U0 Gate: Capture updated screens and check tokens/controls."""
import json
import subprocess
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-redesign/run_u0_baseline'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Verifying U0 Gate...")
    with RedesignBrowser(OUT_DIR) as b:
        # 1. Desktop Check (1440x1000)
        b.cdp('Emulation.setDeviceMetricsOverride', {
            'width': 1440,
            'height': 1000,
            'deviceScaleFactor': 1,
            'mobile': False
        })
        b.goto('http://localhost:13000')
        time.sleep(2)
        b.capture_screenshot(OUT_DIR / "u0_desktop_home_after_tokens.png")

        # Check font families and tokens via computed style
        body_font = b.js("window.getComputedStyle(document.body).fontFamily")
        bg_color = b.js("window.getComputedStyle(document.body).backgroundColor")
        text_color = b.js("window.getComputedStyle(document.body).color")

        print("Computed body styles:")
        print("  Font family:", body_font)
        print("  Background color:", bg_color)
        print("  Text color:", text_color)

        # 2. Mobile Check (390x844)
        b.cdp('Emulation.setDeviceMetricsOverride', {
            'width': 390,
            'height': 844,
            'deviceScaleFactor': 2,
            'mobile': True
        })
        b.goto('http://localhost:13000')
        time.sleep(2)
        b.capture_screenshot(OUT_DIR / "u0_mobile_home_after_tokens.png")

        # Open cart drawer to check typography & buttons
        b.click('#btn-cart')
        time.sleep(1)
        b.capture_screenshot(OUT_DIR / "u0_mobile_cart_after_tokens.png")

        results = {
            "body_font": body_font,
            "bg_color": bg_color,
            "text_color": text_color,
            "desktop_screenshot": str(OUT_DIR / "u0_desktop_home_after_tokens.png"),
            "mobile_screenshot": str(OUT_DIR / "u0_mobile_home_after_tokens.png"),
            "cart_screenshot": str(OUT_DIR / "u0_mobile_cart_after_tokens.png")
        }
        (OUT_DIR / "u0_verification.json").write_text(json.dumps(results, indent=2))
        print("U0 Gate verification completed successfully.")

if __name__ == '__main__':
    main()
