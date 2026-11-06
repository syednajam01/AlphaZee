from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://localhost:13000/admin')
    time.sleep(3)

    login_action = b.js("""(async () => {
        const u = document.querySelector('#admin-username');
        const p = document.querySelector('#admin-password');
        const btn = document.querySelector('#admin-login-submit');
        if (!u || !p || !btn) return { error: 'elements not found' };
        u.value = 'syed123';
        p.value = 'Password123!';
        btn.click();
        return { clicked: true };
    })()""")
    print('Login action:', login_action)
    time.sleep(3)

    state_after = b.js("""(() => {
        const hasAuth = !!document.querySelector('#admin-auth-form');
        const err = document.querySelector('#admin-login-error')?.innerText;
        const cards = document.querySelectorAll('.admin-financial-overview div').length;
        const viewTitle = document.querySelector('#admin-view-title')?.innerText;
        return { hasAuth, err, cards, viewTitle };
    })()""")
    print('State after login:\n', state_after)

