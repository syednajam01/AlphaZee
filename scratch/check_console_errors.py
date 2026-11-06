from pathlib import Path
import sys, time
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

with RedesignBrowser(Path('.local/tmp')) as b:
    b.cdp('Log.enable')
    b.cdp('Runtime.enable')
    
    logs = []
    
    b.goto('http://localhost:13000/admin')
    time.sleep(3)
    
    # Check evaluate
    res = b.cdp('Runtime.evaluate', {'expression': 'window.__errors || []'})
    print('Eval res:', res)
    
    # Check document title and app innerHTML
    title = b.js('document.title')
    app_html = b.js('document.getElementById("app")?.innerHTML')
    print('Title:', title)
    print('App HTML length:', len(app_html) if app_html else 0)
    if app_html:
        print(app_html[:400])

