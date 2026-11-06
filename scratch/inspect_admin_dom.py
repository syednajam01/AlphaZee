from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(2)
    html = b.js('document.querySelector("#admin-modal")?.innerHTML || document.body.innerHTML')
    print('HTML length:', len(html))
    print(html[:600])

