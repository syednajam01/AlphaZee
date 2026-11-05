"""
P2: Browser Verification for Storefront Transactions, Trust & Recovery (Lab on 13001).
Verifies:
1. Complete Cash on Delivery (COD) purchase flow in lab.
2. Order Reference and Private Access Code generation.
3. Order Tracking lookup by Order Number + Access Code.
4. Complete Online Bank Transfer flow in lab.
5. Cart Drawer item removal, quantity adjustment, and empty bag recovery.
"""
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/three-portal-quality/run_p2_transactions'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

def save_screenshot(browser, filename):
    local_path = OUT_DIR / filename
    browser.capture_screenshot(str(local_path))
    if BRAIN_DIR.exists():
        shutil.copy2(local_path, BRAIN_DIR / filename)
    print(f"  [SCREENSHOT SAVED] {filename}", flush=True)

def main():
    print("=== STARTING P2 STOREFRONT TRANSACTION & TRUST VERIFICATION ===", flush=True)

    with RedesignBrowser(OUT_DIR / "browser_data") as b:
        # 1. Desktop Viewport (1366 x 768)
        b.set_viewport(1366, 768)

        # =========================================================
        # JOURNEY 1: CASH ON DELIVERY (COD) in Lab (13001)
        # =========================================================
        print("\n--- Journey 1: Cash on Delivery (COD) in Lab ---", flush=True)
        b.goto("http://127.0.0.1:13001/products/vf5-raw-indigo-denim", wait_selector="#btn-add-to-cart")
        time.sleep(1.2)

        # Select available size 34
        print("  Selecting size 34...", flush=True)
        b.js("""
        (() => {
            const chip = document.querySelector('.option-chip[data-option-size="34"]');
            if (chip) chip.click();
        })()
        """)
        time.sleep(0.5)

        # Add to cart
        print("  Adding to shopping bag...", flush=True)
        b.click("#btn-add-to-cart")
        time.sleep(0.8)
        save_screenshot(b, "p2_desktop_cart_drawer_item.png")

        # Open checkout
        print("  Proceeding to checkout...", flush=True)
        b.click("#btn-checkout")
        time.sleep(1.0)
        save_screenshot(b, "p2_desktop_checkout_modal_opened.png")

        # Fill valid shipping form fields
        print("  Filling shipping address...", flush=True)
        b.js("""
        (() => {
            document.querySelector('#input-customer-name').value = 'Zainab Ahmed';
            document.querySelector('#input-customer-phone').value = '03001234567';
            document.querySelector('#input-customer-email').value = 'zainab@example.com';
            document.querySelector('#input-shipping-address-1').value = 'House 14-B, Street 5, Phase 6, DHA';
            document.querySelector('#input-shipping-city').value = 'Karachi';
            document.querySelector('#input-shipping-province').value = 'Sindh';
            document.querySelector('#input-shipping-postal').value = '75500';
            
            // Ensure COD is selected
            const codRadio = document.querySelector('input[name="payment_method"][value="cod"]');
            if (codRadio) {
                codRadio.checked = true;
                codRadio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        })()
        """)
        time.sleep(0.5)
        save_screenshot(b, "p2_desktop_checkout_form_filled_cod.png")

        # Click Place Order (first click calculates quote and confirms)
        print("  Submitting order quote...", flush=True)
        b.click("#btn-place-order")
        time.sleep(1.0)
        
        quote_text = b.js("document.querySelector('#btn-place-order')?.textContent?.trim()")
        print(f"  Button after quote calculation: {quote_text}", flush=True)
        save_screenshot(b, "p2_desktop_checkout_quote_confirmed.png")

        # Second click places order with confirmed quote
        print("  Confirming order placement...", flush=True)
        b.click("#btn-place-order")
        
        # Wait for order confirmation to render
        b.wait_for_selector("#checkout-access-code", timeout=12)
        time.sleep(0.6)

        # Verify confirmation screen
        cod_order_num = b.js("document.querySelector('#checkout-body-content')?.innerText?.match(/Order #(AZ-[A-Za-z0-9-]+)/)?.[1]")
        cod_access_code = b.js("document.querySelector('#checkout-access-code')?.textContent?.trim()")
        print(f"  COD Order Placed! Order Number: {cod_order_num}, Access Code: {cod_access_code}", flush=True)
        assert cod_order_num, "COD Order Number was not found on confirmation screen"
        assert cod_access_code, "Private Access Code was not found on confirmation screen"
        save_screenshot(b, "p2_desktop_checkout_cod_confirmed.png")

        # Close checkout
        b.click("#checkout-close-btn")
        time.sleep(0.5)

        # =========================================================
        # ORDER TRACKING LOOKUP (Using COD Order + Access Code)
        # =========================================================
        print("\n--- Order Tracking Verification ---", flush=True)
        b.click("a[href='#track']")
        time.sleep(0.8)
        save_screenshot(b, "p2_desktop_tracking_modal_opened.png")

        print(f"  Looking up order {cod_order_num}...", flush=True)
        b.js(f"""
        (() => {{
            document.querySelector('#tracking-order-num').value = '{cod_order_num}';
            document.querySelector('#tracking-code').value = '{cod_access_code}';
        }})()
        """)
        time.sleep(0.3)
        b.click("#btn-search-order")
        
        b.wait_for_selector("#tracking-results-area div", timeout=10)
        time.sleep(0.8)

        tracked_found = b.js(f"document.querySelector('#tracking-results-area')?.innerText?.includes('{cod_order_num}')")
        print(f"  Tracked Order Number matches in UI: {tracked_found}", flush=True)
        assert tracked_found, f"Order {cod_order_num} was not found in tracking results"
        save_screenshot(b, "p2_desktop_tracking_details_loaded.png")

        b.click("#tracking-close-btn")
        time.sleep(0.5)

        # =========================================================
        # JOURNEY 2: ONLINE BANK TRANSFER in Lab (13001)
        # =========================================================
        print("\n--- Journey 2: Online Bank Transfer in Lab ---", flush=True)
        # Navigate back to product and add to cart
        b.goto("http://127.0.0.1:13001/products/vf5-raw-indigo-denim", wait_selector="#btn-add-to-cart")
        time.sleep(1.2)

        # Select size 34
        b.js("""
        (() => {
            const chip = document.querySelector('.option-chip[data-option-size="34"]');
            if (chip) chip.click();
        })()
        """)
        time.sleep(0.4)
        b.click("#btn-add-to-cart")
        time.sleep(0.8)
        b.click("#btn-checkout")
        time.sleep(1.0)

        # Fill shipping info and select Bank Transfer
        print("  Filling shipping address and selecting Bank Transfer...", flush=True)
        b.js("""
        (() => {
            document.querySelector('#input-customer-name').value = 'Bilal Khan';
            document.querySelector('#input-customer-phone').value = '03219876543';
            document.querySelector('#input-customer-email').value = 'bilal@example.com';
            document.querySelector('#input-shipping-address-1').value = 'Apartment 402, Royal Residency, Gulshan';
            document.querySelector('#input-shipping-city').value = 'Karachi';
            document.querySelector('#input-shipping-province').value = 'Sindh';
            
            // Select Bank Transfer radio
            const bankRadio = document.querySelector('input[name="payment_method"][value="bank_transfer"]');
            if (bankRadio) {
                bankRadio.checked = true;
                bankRadio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        })()
        """)
        time.sleep(0.5)
        save_screenshot(b, "p2_desktop_checkout_form_filled_bank.png")

        # Submit quote
        print("  Submitting quote for bank transfer...", flush=True)
        b.click("#btn-place-order")
        time.sleep(1.0)

        # Confirm order
        print("  Confirming bank transfer order placement...", flush=True)
        b.click("#btn-place-order")
        
        b.wait_for_selector("#checkout-access-code", timeout=12)
        time.sleep(0.6)

        bank_order_num = b.js("document.querySelector('#checkout-body-content')?.innerText?.match(/Order #(AZ-[A-Za-z0-9-]+)/)?.[1]")
        bank_access_code = b.js("document.querySelector('#checkout-access-code')?.textContent?.trim()")
        print(f"  Bank Order Placed! Order Number: {bank_order_num}, Access Code: {bank_access_code}", flush=True)
        assert bank_order_num, "Bank Order Number was not found"
        assert bank_access_code, "Bank Access Code was not found"
        save_screenshot(b, "p2_desktop_checkout_bank_confirmed.png")

        b.click("#checkout-close-btn")
        time.sleep(0.5)

        # =========================================================
        # CART DRAWER QUANTITY ADJUSTMENT & REMOVAL
        # =========================================================
        print("\n--- Cart Drawer Adjustment & Removal ---", flush=True)
        # Add item again
        b.goto("http://127.0.0.1:13001/products/vf5-raw-indigo-denim", wait_selector="#btn-add-to-cart")
        time.sleep(1.2)
        b.js("""
        (() => {
            const chip = document.querySelector('.option-chip[data-option-size="34"]');
            if (chip) chip.click();
        })()
        """)
        time.sleep(0.4)
        b.click("#btn-add-to-cart")
        time.sleep(0.8)

        # Increase qty
        print("  Incrementing quantity...", flush=True)
        b.click(".btn-qty-inc")
        time.sleep(0.5)
        qty_num = b.js("document.querySelector('.cart-qty-num')?.textContent?.trim()")
        print(f"  Quantity after increment: {qty_num}", flush=True)
        assert qty_num == "2", f"Expected qty 2, got {qty_num}"
        save_screenshot(b, "p2_desktop_cart_qty_incremented.png")

        # Remove item
        print("  Removing item from cart...", flush=True)
        b.click(".btn-remove-item")
        time.sleep(0.5)
        is_empty = b.js("Boolean(document.querySelector('.drawer-empty-state'))")
        print(f"  Cart is empty state: {is_empty}", flush=True)
        assert is_empty, "Cart did not show empty state after item removal"
        save_screenshot(b, "p2_desktop_cart_empty_state.png")

        b.click("#cart-close-btn")
        time.sleep(0.5)

    print("\n=== P2 STOREFRONT TRANSACTION & TRUST VERIFICATION COMPLETED (100% PASS) ===", flush=True)

if __name__ == "__main__":
    main()
