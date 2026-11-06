from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    ids = b.js("""(() => {
        return Array.from(document.querySelectorAll('[id]')).map(el => el.id);
    })()""")
    print('All IDs on page:\n', ids)

