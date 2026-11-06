from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)
    
    info = b.js("""(() => {
        const isAuthForm = !!document.querySelector('#admin-auth-form');
        const tabs = Array.from(document.querySelectorAll('button[data-tab]')).map(el => el.getAttribute('data-tab'));
        const activeTab = document.querySelector('.admin-tab-btn.active, .admin-tab-btn[aria-selected="true"]')?.getAttribute('data-tab');
        const h2 = document.querySelector('#admin-tab-content h2, #admin-tab-content h3')?.innerText;
        return { isAuthForm, tabs, activeTab, h2 };
    })()""")
    print('Admin page status:', info)

