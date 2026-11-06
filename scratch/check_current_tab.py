from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    info = b.js("""(() => {
        const c = document.querySelector('#admin-tab-content');
        return {
            text: c ? c.innerText.slice(0, 300) : 'none',
            childTags: c ? Array.from(c.children).map(el => el.tagName + '.' + el.className) : []
        };
    })()""")
    print('Current tab content info:\n', info)

