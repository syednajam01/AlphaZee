import sys, time
from pathlib import Path
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.goto('http://127.0.0.1:13001/admin')
    time.sleep(1)
    b.js("""(() => {
        return fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:13001'},
            body: JSON.stringify({username: 'sample_m8_a0000001', password: 'AcceptancePassword123!'})
        });
    })()""")
    b.goto('http://127.0.0.1:13001/admin', wait_selector='#admin-modal')
    time.sleep(1.5)
    b.js("document.querySelector(\"button[data-tab='products']\")?.click()")
    time.sleep(1.5)
    text = b.js("document.querySelector('#admin-body-area, #admin-tab-content')?.innerText")
    print('Products tab text:')
    print(text[:400] if text else 'None')

