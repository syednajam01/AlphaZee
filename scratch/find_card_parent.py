from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    info = b.js("""(() => {
        const card = document.querySelector('.admin-login-card');
        return {
            hasCard: !!card,
            parentTag: card ? card.parentElement.tagName : null,
            parentId: card ? card.parentElement.id : null,
            parentClass: card ? card.parentElement.className : null,
            parentParentId: card ? card.parentElement.parentElement?.id : null
        };
    })()""")
    print('Card parent info:\n', info)

