from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    diag = b.js("""(() => {
        return {
            u: !!document.querySelector('#admin-username'),
            p: !!document.querySelector('#admin-password'),
            f: !!document.querySelector('#admin-auth-form'),
            forms: Array.from(document.querySelectorAll('form')).map(f => f.id)
        };
    })()""")
    print('Diag:', diag)

