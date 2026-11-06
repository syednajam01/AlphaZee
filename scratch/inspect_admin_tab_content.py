from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(2)
    tab_content = b.js('document.querySelector("#admin-tab-content")?.innerHTML || "none"')
    print('Tab content length:', len(tab_content))
    print(tab_content[:800])

