import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    b.goto("http://localhost:13000/")
    
    # Wait for .hero-section to be populated
    start = time.time()
    loaded = False
    while time.time() - start < 8:
        state = b.js("""(() => {
            const h = document.querySelector('.hero-section');
            if (!h) return { ready: false, reason: 'no-hero' };
            const track = h.querySelector('.hero-marquee-track');
            const cards = h.querySelectorAll('.hero-picture-card');
            const video = h.querySelector('video');
            return {
                ready: cards.length > 0,
                cardsCount: cards.length,
                hasVideo: !!video,
                videoSrc: video ? video.src : null,
                innerPrefix: h.innerHTML.slice(0, 200)
            };
        })()""")
        if state and state.get('ready'):
            loaded = True
            print("Hero loaded successfully!", json.dumps(state, indent=2))
            break
        time.sleep(0.5)

    if not loaded:
        print("Hero did not load within 8s. Final state:", json.dumps(state, indent=2))
        logs = b.js("window.__console_logs || []")
        print("Console logs:", logs)

