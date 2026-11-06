from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    with open('scratch/page_dump.html', 'w', encoding='utf-8') as f:
        f.write(b.js('document.body.innerHTML'))
    print('Dumped HTML to scratch/page_dump.html')

