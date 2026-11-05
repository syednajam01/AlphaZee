import sys, time
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser('.local/test_check_err') as b:
    b.goto('http://127.0.0.1:13001/products/vf5-raw-indigo-denim', wait_selector='#btn-add-to-cart')
    time.sleep(1.0)
    b.js('document.querySelector(\'.option-chip[data-option-size="34"]\').click()')
    time.sleep(0.3)
    b.click('#btn-add-to-cart')
    time.sleep(0.5)
    b.click('#btn-checkout')
    time.sleep(0.8)
    b.js("""
        document.querySelector('#input-customer-name').value = 'Zainab Ahmed';
        document.querySelector('#input-customer-phone').value = '03001234567';
        document.querySelector('#input-shipping-address-1').value = 'Street 5, Phase 6';
        document.querySelector('#input-shipping-city').value = 'Karachi';
        document.querySelector('#input-shipping-province').value = 'Sindh';
    """)
    time.sleep(0.3)
    # 1st click calculates quote
    b.click('#btn-place-order')
    time.sleep(1.0)
    btn_text1 = b.js("document.querySelector('#btn-place-order')?.textContent")
    err1 = b.js("document.querySelector('#checkout-error-banner')?.innerText")
    print("After 1st click - button:", btn_text1, "banner:", err1)
    
    # 2nd click places order
    b.click('#btn-place-order')
    time.sleep(2.0)
    btn_text2 = b.js("document.querySelector('#btn-place-order')?.textContent")
    err2 = b.js("document.querySelector('#checkout-error-banner')?.innerText")
    body = b.js("document.querySelector('#checkout-body-content')?.innerText")
    print("After 2nd click - button:", btn_text2, "banner:", err2)
    print("Body content (first 300 chars):", body[:300] if body else None)

