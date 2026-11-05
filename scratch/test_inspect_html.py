import sys, time
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser('.local/test_inspect_html') as b:
    b.goto('http://localhost:13000/products/temporary-media-preview-20261105', wait_selector='#main-content')
    time.sleep(1.5)
    html = b.js("document.querySelector('#app')?.innerHTML")
    print("HTML length:", len(html) if html else 0)
    print("HTML snippet:", html[:500] if html else "NONE")
    # Check if unavailable screen was shown
    is_unavail = b.js("Boolean(document.querySelector('.product-unavailable-view'))")
    title = b.js("document.querySelector('.product-page-title, .product-unavailable-title')?.textContent")
    print("is_unavail:", is_unavail)
    print("Title found:", title)

