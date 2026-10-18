import sys, time
from pathlib import Path
sys.path.insert(0, '.local/frontend-redesign')
from browser_util import RedesignBrowser

with RedesignBrowser('.local/frontend-redesign/run_u0_baseline') as b:
    b.goto('http://127.0.0.1:13001')
    time.sleep(2)
    b.js('document.querySelector("#featured").scrollIntoView()')
    time.sleep(1)
    b.capture_screenshot('.local/frontend-redesign/run_u0_baseline/u0_lab_products_grid_before.png')
    b.click('.product-card')
    time.sleep(1)
    b.capture_screenshot('.local/frontend-redesign/run_u0_baseline/u0_lab_product_modal_actual_before.png')

print("Product grid and modal screenshots saved.")
