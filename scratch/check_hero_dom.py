from pathlib import Path
import sys, time
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser
with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/')
    time.sleep(3)
    res = b.js("""(() => {
        const h = document.querySelector('.hero-section');
        if (!h) return 'NO HERO';
        const v = h.querySelector('video');
        const m = h.querySelector('.hero-marquee-container');
        const c = h.querySelectorAll('.hero-picture-card');
        return {
            classes: h.className,
            video: v ? v.outerHTML : null,
            marquee: m ? m.outerHTML.slice(0, 300) : null,
            cardsCount: c.length,
            innerSample: h.innerHTML.slice(0, 400)
        };
    })()""")
    print('Hero DOM:', res)
