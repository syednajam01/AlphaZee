import sys, time
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser('.local/test_vf5') as b:
    b.goto('http://127.0.0.1:13001/products/vf5-raw-indigo-denim', wait_selector='#btn-add-to-cart')
    time.sleep(1.2)
    
    selected_sz = b.js("document.querySelector('#selected-size-name')?.textContent")
    btn_disabled = b.js("document.querySelector('#btn-add-to-cart')?.disabled")
    btn_text = b.js("document.querySelector('#btn-add-to-cart')?.textContent?.trim()")
    print("Initial selected size:", selected_sz)
    print("Button disabled:", btn_disabled)
    print("Button text:", btn_text)
    
    # Click button
    b.click("#btn-add-to-cart")
    time.sleep(0.4)
    
    prompt = b.js("""
    (() => {
        const el = document.querySelector('#size-selection-prompt');
        return {
            exists: Boolean(el),
            hidden: el ? el.hidden : null,
            display: el ? window.getComputedStyle(el).display : null,
            text: el ? el.textContent.trim() : null
        };
    })()
    """)
    print("Prompt details:", prompt)

