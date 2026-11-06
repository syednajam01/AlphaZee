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
        const f = c ? c.querySelector('form') : null;
        return {
            hasForm: !!f,
            formId: f ? f.id : null,
            formClasses: f ? f.className : null,
            formHTML: f ? f.outerHTML.slice(0, 400) : null
        };
    })()""")
    print('Form inside #admin-tab-content:\n', info)

