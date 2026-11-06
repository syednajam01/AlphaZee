from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)
    
    res = b.js("""(async () => {
        const u = document.querySelector('#admin-username');
        const p = document.querySelector('#admin-password');
        const btn = document.querySelector('#admin-login-submit');
        if (!u || !p || !btn) return { error: 'elements missing' };
        u.value = 'syed123';
        p.value = 'Password123!';
        btn.click();
        await new Promise(r => setTimeout(r, 2000));
        const err = document.querySelector('#admin-login-error')?.textContent;
        const loggedIn = !document.querySelector('#admin-auth-form');
        return { err, loggedIn, url: window.location.href };
    })()""")
    print('Login result:', res)

