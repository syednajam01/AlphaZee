from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)
    
    fields = b.js("""(() => {
        const form = document.querySelector('#admin-auth-form');
        if (!form) return { hasForm: false };
        const inputs = Array.from(form.querySelectorAll('input')).map(i => ({ id: i.id, name: i.name, type: i.type }));
        const buttons = Array.from(form.querySelectorAll('button')).map(b => ({ id: b.id, type: b.type, text: b.innerText }));
        return { hasForm: true, inputs, buttons };
    })()""")
    print('Form fields:', fields)

