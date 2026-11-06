import sys, time
from pathlib import Path
sys.path.insert(0, ".local/frontend-redesign")
from browser_util import RedesignBrowser

with RedesignBrowser(Path(".local/tmp")) as b:
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(1)
    res = b.js("""(() => {
        return fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:13001'},
            body: JSON.stringify({username: 'syed123', password: 'Password123!'})
        }).then(r => r.status);
    })()""")
    print("Login fetch status on 13001:", res)
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(2)
    sidebar_visible = b.js("window.getComputedStyle(document.querySelector('#admin-sidebar')).display !== 'none'")
    tab_text = b.js("document.querySelector('.admin-tab-btn.active')?.innerText")
    content_header = b.js("document.querySelector('#admin-tab-content h2, #admin-tab-content h3')?.innerText")
    print(f"Logged in: {sidebar_visible}, Active tab: {tab_text}, Header: {content_header}")

