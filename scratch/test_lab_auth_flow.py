import subprocess, json, time, sys
from pathlib import Path

username = "sample_m8_a0000001"
password = "AcceptancePassword123!"

sys.path.insert(0, ".local/frontend-redesign")
from browser_util import RedesignBrowser

with RedesignBrowser(Path(".local/tmp")) as b:
    b.goto("http://127.0.0.1:13001/admin")
    time.sleep(1)
    login_res = b.js(f"""(() => {{
        return fetch('/api/v1/auth/login', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:13001'}},
            body: JSON.stringify({{username: '{username}', password: '{password}'}})
        }}).then(r => r.json());
    }})()""")
    print("Login response:", login_res)
    b.goto("http://127.0.0.1:13001/admin", wait_selector="#admin-modal")
    time.sleep(2)
    title = b.js("document.title")
    buttons = b.js("[...document.querySelectorAll('button[data-tab]')].map(el => el.getAttribute('data-tab'))")
    active_tab = b.js("document.querySelector('button[data-tab].active')?.getAttribute('data-tab')")
    print(f"Title: {title}")
    print(f"Buttons found: {buttons}")
    print(f"Active tab: {active_tab}")
