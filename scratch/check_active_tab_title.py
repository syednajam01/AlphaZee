from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    info = b.js("""(() => {
        const title = document.querySelector('#admin-view-title')?.innerText;
        const activeBtn = document.querySelector('.admin-tab-btn[aria-selected="true"], .admin-tab-btn.active');
        const activeTab = activeBtn?.dataset?.tab;
        const contentText = document.querySelector('#admin-tab-content')?.innerText.slice(0, 200);
        return { title, activeTab, contentText };
    })()""")
    print('Tab Info:', info)

