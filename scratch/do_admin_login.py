from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    res = b.js("""(() => {
        const u = document.querySelector('#admin-username');
        const p = document.querySelector('#admin-password');
        const f = document.querySelector('#admin-auth-form');
        if (!u || !p || !f) return 'Form not found';
        u.value = 'syed123';
        p.value = 'Password123!';
        f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        return 'Submitted';
    })()""")
    print('Submit trigger:', res)
    time.sleep(3)
    
    status = b.js("""(() => {
        const err = document.querySelector('#admin-login-error')?.textContent;
        const form = !!document.querySelector('#admin-auth-form');
        const h2 = document.querySelector('#admin-tab-content h2, #admin-tab-content h3')?.innerText;
        const title = document.title;
        return { err, formStillThere: form, h2, title };
    })()""")
    print('After 3s:', status)

