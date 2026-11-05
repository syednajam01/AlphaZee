import sys, time
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser('.local/test_sticky_bar') as b:
    b.set_viewport(390, 844, mobile=True)
    b.goto('http://localhost:13000/products/temporary-media-preview-20261105', wait_selector='#btn-add-to-cart')
    time.sleep(1.2)
    
    btn_top_before = b.js("document.querySelector('#btn-add-to-cart').getBoundingClientRect().top")
    print("btn-add-to-cart top before scroll:", btn_top_before)
    
    # Scroll down
    b.js("window.scrollTo(0, 1600)")
    time.sleep(0.5)
    
    btn_top_after = b.js("document.querySelector('#btn-add-to-cart').getBoundingClientRect().top")
    print("btn-add-to-cart top after scroll:", btn_top_after)
    
    is_visible = b.js("document.querySelector('#mobile-purchase-bar')?.classList?.contains('is-visible')")
    print("is-visible class:", is_visible)
    
    # Let's inspect mobile purchase bar styles
    classes = b.js("document.querySelector('#mobile-purchase-bar')?.className")
    display = b.js("window.getComputedStyle(document.querySelector('#mobile-purchase-bar')).display")
    transform = b.js("window.getComputedStyle(document.querySelector('#mobile-purchase-bar')).transform")
    print("Classes:", classes, "Display:", display, "Transform:", transform)

