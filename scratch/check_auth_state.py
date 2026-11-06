from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(3)

    state = b.js("""(() => {
        const authForm = document.querySelector('#admin-auth-form');
        const overview = document.querySelector('.admin-financial-overview');
        const viewTitle = document.querySelector('#admin-view-title')?.innerText;
        return { hasAuthForm: !!authForm, hasOverview: !!overview, viewTitle };
    })()""")
    print('State after 3s load:', state)

