import sys, time
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser('.local/test_inspect_main') as b:
    b.goto('http://localhost:13000/products/temporary-media-preview-20261105')
    time.sleep(2.0)
    main_html = b.js("document.querySelector('#main-content')?.innerHTML")
    print("Main content length:", len(main_html) if main_html else 0)
    print("Main content snippet:", main_html[:500] if main_html else "NONE")
    # Also check window.location.pathname
    path = b.js("window.location.pathname")
    print("Path in browser:", path)

