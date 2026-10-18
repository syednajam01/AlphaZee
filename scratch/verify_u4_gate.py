"""Verify Phase U4 Gate: Cart Drawer, 2-Column Checkout, Field Validation, Lab COD & Bank Journeys, Access Code, and Order Tracking Stepper."""
import json
import time
from pathlib import Path
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/frontend-redesign/run_u4_checkout'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("Verifying Phase U4 Gate on http://127.0.0.1:13001 ...", flush=True)
    results = {
        "checks": [],
        "screenshots": {},
        "errors": []
    }

    with RedesignBrowser(OUT_DIR) as b:
        # 1. Cart Drawer Empty State, Accessibility & Escape Dismiss
        print("1. Testing Cart Drawer Empty State, Accessibility & Escape Dismiss...", flush=True)
        b.set_viewport(1440, 900)
        b.goto("http://127.0.0.1:13001/", wait_selector='#btn-cart')
        time.sleep(1)

        # Clear cart and refresh
        b.js("localStorage.clear(); sessionStorage.clear();")
        b.goto("http://127.0.0.1:13001/", wait_selector='#btn-cart')
        time.sleep(1)

        # Click cart button (with focus so opener is tracked)
        b.js("const btn = document.querySelector('#btn-cart'); if (btn) { btn.focus(); btn.click(); }")
        time.sleep(0.5)

        cart_empty_state = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const backdrop = document.querySelector('#cart-drawer-backdrop');
            const emptyTitle = drawer ? drawer.querySelector('.drawer-empty-title') : null;
            const exploreBtn = drawer ? drawer.querySelector('#btn-cart-explore') : null;
            const closeBtn = drawer ? drawer.querySelector('#cart-close-btn') : null;
            const isOpen = drawer ? drawer.classList.contains('is-open') : false;

            return {
                isOpen,
                drawerOpenedNotHidden: drawer ? !drawer.hidden : false,
                emptyTitleText: emptyTitle ? emptyTitle.textContent.trim() : null,
                hasExploreBtn: Boolean(exploreBtn),
                hasCloseBtn: Boolean(closeBtn),
            };
        })()""")

        shot1 = b.capture_screenshot(OUT_DIR / "u4_empty_cart_drawer.png")
        results["screenshots"]["empty_cart_drawer"] = str(shot1)

        # Test Escape key dismiss and focus restoration
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Escape', 'code': 'Escape'})
        b.cdp('Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Escape', 'code': 'Escape'})
        time.sleep(0.5)

        escape_check = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const active = document.activeElement;
            return {
                isClosed: drawer ? !drawer.classList.contains('is-open') : false,
                drawerClosedHidden: drawer ? drawer.hidden : false,
                focusRestoredToCartBtn: active ? active.id === 'btn-cart' : false,
            };
        })()""")

        check1 = {
            "name": "Cart Drawer Empty State & Escape Dismiss",
            "metrics": { **cart_empty_state, **escape_check },
            "passed": bool(
                cart_empty_state["isOpen"] and
                cart_empty_state["drawerOpenedNotHidden"] and
                cart_empty_state["hasExploreBtn"] and
                escape_check["isClosed"] and
                escape_check["drawerClosedHidden"] and
                escape_check["focusRestoredToCartBtn"]
            )
        }
        results["checks"].append(check1)
        print("  Check 1:", check1, flush=True)

        # 2. Add Item to Cart & 3:4 Thumbnail & Stepper
        print("2. Testing Add Item to Cart, 3:4 Thumbnail & Stepper Controls...", flush=True)
        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector='#btn-add-to-cart')
        time.sleep(1.5)

        # Select option chip if available
        b.js("""(() => {
            const chip = document.querySelector('.product-option-chip[data-size]');
            if (chip) chip.click();
        })()""")
        time.sleep(0.5)

        # Click Add to Cart
        b.click('#btn-add-to-cart')
        time.sleep(1)

        cart_item_info = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const item = drawer ? drawer.querySelector('.cart-item') : null;
            const img = item ? item.querySelector('.cart-item-img') : null;
            const price = item ? item.querySelector('.cart-item-price') : null;
            const subtotal = drawer ? drawer.querySelector('#cart-subtotal') : null;
            const incBtn = item ? item.querySelector('.btn-qty-inc') : null;
            const decBtn = item ? item.querySelector('.btn-qty-dec') : null;
            const qtyNum = item ? item.querySelector('.cart-qty-num') : null;
            const checkoutBtn = drawer ? drawer.querySelector('#btn-checkout') : null;

            const imgRect = img ? img.getBoundingClientRect() : null;
            const imgRatio = imgRect && imgRect.height > 0 ? (imgRect.width / imgRect.height) : 0;

            return {
                hasItem: Boolean(item),
                imgWidth: imgRect ? Math.round(imgRect.width) : 0,
                imgHeight: imgRect ? Math.round(imgRect.height) : 0,
                imgRatio: Number(imgRatio.toFixed(2)),
                priceText: price ? price.textContent.trim() : null,
                priceTabular: price ? price.classList.contains('price-tabular') : false,
                subtotalText: subtotal ? subtotal.textContent.trim() : null,
                subtotalTabular: subtotal ? subtotal.classList.contains('price-tabular') : false,
                qty: qtyNum ? qtyNum.textContent.trim() : null,
                checkoutDisabled: checkoutBtn ? checkoutBtn.disabled : true
            };
        })()""")

        # Increment quantity
        b.click('.btn-qty-inc')
        time.sleep(0.5)

        cart_item_incremented = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const qtyNum = drawer ? drawer.querySelector('.cart-qty-num') : null;
            const subtotal = drawer ? drawer.querySelector('#cart-subtotal') : null;
            return {
                newQty: qtyNum ? qtyNum.textContent.trim() : null,
                newSubtotal: subtotal ? subtotal.textContent.trim() : null,
            };
        })()""")

        shot2 = b.capture_screenshot(OUT_DIR / "u4_cart_drawer_with_item.png")
        results["screenshots"]["cart_drawer_item"] = str(shot2)

        check2 = {
            "name": "Cart Item 3:4 Thumbnail & Stepper",
            "metrics": { **cart_item_info, **cart_item_incremented },
            "passed": bool(
                cart_item_info["hasItem"] and
                cart_item_info["imgRatio"] >= 0.70 and cart_item_info["imgRatio"] <= 0.80 and
                cart_item_info["priceTabular"] and
                cart_item_info["subtotalTabular"] and
                cart_item_incremented["newQty"] == '2' and
                not cart_item_info["checkoutDisabled"]
            )
        }
        results["checks"].append(check2)
        print("  Check 2:", check2, flush=True)

        # 3. Checkout Modal 2-Column Responsive Layout
        print("3. Testing Checkout View 2-Column Desktop Layout & Autocomplete...", flush=True)
        b.click('#btn-checkout')
        time.sleep(1)

        checkout_layout = b.js("""(() => {
            const modal = document.querySelector('#checkout-modal');
            const form = modal ? modal.querySelector('#checkout-form') : null;
            const colMain = modal ? modal.querySelector('.checkout-col-main') : null;
            const colSummary = modal ? modal.querySelector('.checkout-col-summary') : null;
            const itemsList = modal ? modal.querySelector('#checkout-items-list') : null;

            const nameInput = modal ? modal.querySelector('#input-customer-name') : null;
            const phoneInput = modal ? modal.querySelector('#input-customer-phone') : null;
            const addressInput = modal ? modal.querySelector('#input-shipping-address-1') : null;
            const cityInput = modal ? modal.querySelector('#input-shipping-city') : null;
            const provinceInput = modal ? modal.querySelector('#input-shipping-province') : null;
            const postalInput = modal ? modal.querySelector('#input-shipping-postal') : null;

            const mainRect = colMain ? colMain.getBoundingClientRect() : null;
            const summaryRect = colSummary ? colSummary.getBoundingClientRect() : null;
            const totalW = mainRect && summaryRect ? (mainRect.width + summaryRect.width) : 0;
            const mainPct = totalW > 0 ? Math.round((mainRect.width / totalW) * 100) : 0;
            const summaryPct = totalW > 0 ? Math.round((summaryRect.width / totalW) * 100) : 0;

            return {
                isModalOpen: modal ? modal.classList.contains('is-open') : false,
                hasLayoutGrid: form ? form.classList.contains('checkout-layout-grid') : false,
                mainPct,
                summaryPct,
                hasItemsInSummary: itemsList ? itemsList.children.length > 0 : false,
                nameAutocomplete: nameInput ? nameInput.getAttribute('autocomplete') : null,
                phoneAutocomplete: phoneInput ? phoneInput.getAttribute('autocomplete') : null,
                addressAutocomplete: addressInput ? addressInput.getAttribute('autocomplete') : null,
                cityAutocomplete: cityInput ? cityInput.getAttribute('autocomplete') : null,
                provinceAutocomplete: provinceInput ? provinceInput.getAttribute('autocomplete') : null,
                postalAutocomplete: postalInput ? postalInput.getAttribute('autocomplete') : null,
            };
        })()""")

        shot3 = b.capture_screenshot(OUT_DIR / "u4_desktop_checkout_layout.png")
        results["screenshots"]["desktop_checkout_layout"] = str(shot3)

        check3 = {
            "name": "Desktop 2-Column Layout & HTML5 Autocomplete",
            "metrics": checkout_layout,
            "passed": bool(
                checkout_layout["isModalOpen"] and
                checkout_layout["hasLayoutGrid"] and
                checkout_layout["mainPct"] >= 50 and checkout_layout["mainPct"] <= 65 and
                checkout_layout["hasItemsInSummary"] and
                checkout_layout["nameAutocomplete"] == "name" and
                checkout_layout["phoneAutocomplete"] == "tel" and
                checkout_layout["addressAutocomplete"] == "street-address" and
                checkout_layout["cityAutocomplete"] == "address-level2" and
                checkout_layout["provinceAutocomplete"] == "address-level1" and
                checkout_layout["postalAutocomplete"] == "postal-code"
            )
        }
        results["checks"].append(check3)
        print("  Check 3:", check3, flush=True)

        # 4. Inline Field Validation & Error Banner
        print("4. Testing Inline Field Validation & Error Banner...", flush=True)
        # Attempt submission without entering required fields
        b.click('#btn-place-order')
        time.sleep(0.5)

        validation_state = b.js("""(() => {
            const banner = document.querySelector('#checkout-error-banner');
            const nameInput = document.querySelector('#input-customer-name');
            const phoneInput = document.querySelector('#input-customer-phone');
            const addressInput = document.querySelector('#input-shipping-address-1');
            const cityInput = document.querySelector('#input-shipping-city');
            const provinceInput = document.querySelector('#input-shipping-province');

            const errName = document.querySelector('#error-customer-name');
            const errPhone = document.querySelector('#error-customer-phone');
            const errAddr = document.querySelector('#error-shipping-address-1');

            return {
                bannerVisible: banner ? window.getComputedStyle(banner).display !== 'none' : false,
                bannerText: banner ? banner.textContent.trim() : null,
                nameInvalid: nameInput ? nameInput.getAttribute('aria-invalid') === 'true' : false,
                phoneInvalid: phoneInput ? phoneInput.getAttribute('aria-invalid') === 'true' : false,
                addressInvalid: addressInput ? addressInput.getAttribute('aria-invalid') === 'true' : false,
                cityInvalid: cityInput ? cityInput.getAttribute('aria-invalid') === 'true' : false,
                provinceInvalid: provinceInput ? provinceInput.getAttribute('aria-invalid') === 'true' : false,
                errNameVisible: errName ? window.getComputedStyle(errName).display !== 'none' : false,
                errPhoneVisible: errPhone ? window.getComputedStyle(errPhone).display !== 'none' : false,
                errAddrVisible: errAddr ? window.getComputedStyle(errAddr).display !== 'none' : false,
            };
        })()""")

        shot4 = b.capture_screenshot(OUT_DIR / "u4_checkout_inline_validation.png")
        results["screenshots"]["inline_validation"] = str(shot4)

        check4 = {
            "name": "Checkout Inline Validation & Error Banner",
            "metrics": validation_state,
            "passed": bool(
                validation_state["bannerVisible"] and
                validation_state["nameInvalid"] and
                validation_state["phoneInvalid"] and
                validation_state["addressInvalid"] and
                validation_state["errNameVisible"] and
                validation_state["errPhoneVisible"]
            )
        }
        results["checks"].append(check4)
        print("  Check 4:", check4, flush=True)

        # 5. Lab COD Order Placement & Confirmation with Private Access Code
        print("5. Testing Lab COD Order Placement & Confirmation View...", flush=True)
        # Fill valid details
        b.js("""(() => {
            document.querySelector('#input-customer-name').value = 'Ayesha Malik';
            document.querySelector('#input-customer-name').dispatchEvent(new Event('input'));

            document.querySelector('#input-customer-phone').value = '0300-7654321';
            document.querySelector('#input-customer-phone').dispatchEvent(new Event('input'));

            document.querySelector('#input-customer-email').value = 'ayesha@example.com';

            document.querySelector('#input-shipping-address-1').value = 'House 12, Street 4, Sector F-7/2';
            document.querySelector('#input-shipping-address-1').dispatchEvent(new Event('input'));

            document.querySelector('#input-shipping-city').value = 'Islamabad';
            document.querySelector('#input-shipping-city').dispatchEvent(new Event('input'));

            document.querySelector('#input-shipping-province').value = 'Federal Capital';
            document.querySelector('#input-shipping-province').dispatchEvent(new Event('input'));

            document.querySelector('#input-shipping-postal').value = '44000';

            // Ensure COD is selected
            const codRadio = document.querySelector('input[name="payment_method"][value="cod"]');
            if (codRadio) {
                codRadio.checked = true;
                codRadio.dispatchEvent(new Event('change'));
            }
        })()""")
        time.sleep(0.5)

        # Submit order
        b.click('#btn-place-order')
        time.sleep(2)

        cod_confirmation = b.js("""(() => {
            const modal = document.querySelector('#checkout-modal');
            const headline = modal ? modal.querySelector('h2') : null;
            const orderNumEl = modal ? modal.querySelector('#checkout-body-content') : null;
            const accessCodeEl = modal ? modal.querySelector('#checkout-access-code') : null;
            const copyBtn = modal ? modal.querySelector('#btn-copy-access-code') : null;
            const finishBtn = modal ? modal.querySelector('#btn-finish-checkout') : null;
            const badge = modal ? modal.querySelector('#checkout-badge') : null;

            return {
                headlineText: headline ? headline.textContent.trim() : null,
                badgeText: badge ? badge.textContent.trim() : null,
                accessCode: accessCodeEl ? accessCodeEl.textContent.trim() : null,
                hasCopyBtn: Boolean(copyBtn),
                hasFinishBtn: Boolean(finishBtn),
                bodyText: orderNumEl ? orderNumEl.textContent : ''
            };
        })()""")

        shot5 = b.capture_screenshot(OUT_DIR / "u4_cod_order_confirmation.png")
        results["screenshots"]["cod_order_confirmation"] = str(shot5)

        # Extract order number from confirmation
        import re
        order_match = re.search(r'Order #(AZ-[A-Z0-9-]+)', cod_confirmation.get("bodyText", ""))
        order_number = order_match.group(1) if order_match else None
        access_code = cod_confirmation.get("accessCode")

        # Test copy button click
        b.click('#btn-copy-access-code')
        time.sleep(0.5)
        copy_btn_state = b.js("""(() => {
            const btn = document.querySelector('#btn-copy-access-code');
            const feedback = document.querySelector('#copy-code-feedback');
            return {
                btnText: btn ? btn.textContent.trim() : null,
                feedbackVisible: feedback ? window.getComputedStyle(feedback).display !== 'none' : false
            };
        })()""")

        check5 = {
            "name": "Lab COD Order Placement & Access Code",
            "orderNumber": order_number,
            "accessCode": access_code,
            "metrics": { **cod_confirmation, **copy_btn_state },
            "passed": bool(
                cod_confirmation["headlineText"] == "Thank You for Your Order!" and
                cod_confirmation["badgeText"] == "Order Placed" and
                order_number and
                access_code and
                copy_btn_state["btnText"] == "Copied!" and
                copy_btn_state["feedbackVisible"]
            )
        }
        results["checks"].append(check5)
        print("  Check 5:", check5, flush=True)

        # 6. Order Tracking Lookup & 4-Step Progress Stepper
        print("6. Testing Order Tracking Lookup & 4-Step Status Stepper...", flush=True)
        # Close checkout modal
        b.click('#btn-finish-checkout')
        time.sleep(0.5)

        # Open tracking modal
        b.goto("http://127.0.0.1:13001/", wait_selector='#nav-track-order')
        time.sleep(1)
        b.click('#nav-track-order')
        time.sleep(0.5)

        # Enter order number and access code
        b.js(f"""(() => {{
            document.querySelector('#tracking-order-num').value = {json.dumps(order_number)};
            document.querySelector('#tracking-code').value = {json.dumps(access_code)};
        }})()""")
        time.sleep(0.5)

        # Click lookup order
        b.click('#btn-search-order')
        time.sleep(1.5)

        tracking_state = b.js("""(() => {
            const modal = document.querySelector('#tracking-modal');
            const results = modal ? modal.querySelector('#tracking-results-area') : null;
            const stepper = results ? results.querySelector('.tracking-stepper') : null;
            const steps = stepper ? [...stepper.querySelectorAll('.tracking-step')] : [];

            return {
                isResultsVisible: results ? window.getComputedStyle(results).display !== 'none' : false,
                hasStepper: Boolean(stepper),
                stepsCount: steps.length,
                step0DoneOrActive: steps[0] ? (steps[0].classList.contains('is-done') || steps[0].classList.contains('is-active')) : false,
                orderNumText: results ? results.querySelector('h2, div[style*="font-weight: 800"]')?.textContent : null,
            };
        })()""")

        shot6 = b.capture_screenshot(OUT_DIR / "u4_order_tracking_stepper.png")
        results["screenshots"]["order_tracking_stepper"] = str(shot6)

        check6 = {
            "name": "Order Tracking Lookup & 4-Step Stepper",
            "metrics": tracking_state,
            "passed": bool(
                tracking_state["isResultsVisible"] and
                tracking_state["hasStepper"] and
                tracking_state["stepsCount"] == 4 and
                tracking_state["step0DoneOrActive"]
            )
        }
        results["checks"].append(check6)
        print("  Check 6:", check6, flush=True)

        # 7. Lab Bank Transfer Journey & Payment Instructions
        print("7. Testing Lab Bank Transfer Journey & Instructions...", flush=True)
        # Close tracking modal
        b.click('#tracking-close-btn')
        time.sleep(0.5)

        # Navigate to product page and add to cart
        b.goto("http://127.0.0.1:13001/products/sample-m8-0d535c70", wait_selector='#btn-add-to-cart')
        time.sleep(1)
        b.click('#btn-add-to-cart')
        time.sleep(1)

        # Open checkout
        b.click('#btn-checkout')
        time.sleep(1)

        # Select Bank Transfer radio
        b.js("""(() => {
            const radBank = document.querySelector('input[name="payment_method"][value="bank_transfer"]');
            if (radBank) {
                radBank.checked = true;
                radBank.dispatchEvent(new Event('change'));
            }
        })()""")
        time.sleep(0.5)

        # Check bank card highlight
        bank_selection = b.js("""(() => {
            const cardBank = document.querySelector('#label-method-bank');
            const cardCod = document.querySelector('#label-method-cod');
            return {
                bankSelected: cardBank ? cardBank.classList.contains('is-selected') : false,
                codSelected: cardCod ? cardCod.classList.contains('is-selected') : true
            };
        })()""")

        # Fill shipping details
        b.js("""(() => {
            document.querySelector('#input-customer-name').value = 'Bilal Tariq';
            document.querySelector('#input-customer-name').dispatchEvent(new Event('input'));

            document.querySelector('#input-customer-phone').value = '0321-9876543';
            document.querySelector('#input-customer-phone').dispatchEvent(new Event('input'));

            document.querySelector('#input-shipping-address-1').value = 'Apartment 5A, Clifton Block 4';
            document.querySelector('#input-shipping-address-1').dispatchEvent(new Event('input'));

            document.querySelector('#input-shipping-city').value = 'Karachi';
            document.querySelector('#input-shipping-city').dispatchEvent(new Event('input'));

            document.querySelector('#input-shipping-province').value = 'Sindh';
            document.querySelector('#input-shipping-province').dispatchEvent(new Event('input'));
        })()""")
        time.sleep(0.5)

        # Place bank transfer order
        b.click('#btn-place-order')
        time.sleep(2)

        bank_confirmation = b.js("""(() => {
            const modal = document.querySelector('#checkout-modal');
            const body = modal ? modal.querySelector('#checkout-body-content') : null;
            const bankBox = body ? body.querySelector('div[style*="#F0FDF4"], div[style*="#FFFBEB"]') : null;
            const receiptForm = modal ? modal.querySelector('#receipt-upload-form') : null;
            const receiptInput = modal ? modal.querySelector('#receipt-url-input') : null;

            return {
                hasConfirmationBody: Boolean(body),
                hasBankBox: Boolean(bankBox),
                hasReceiptForm: Boolean(receiptForm),
                hasReceiptInput: Boolean(receiptInput),
                bankBoxText: bankBox ? bankBox.textContent : ''
            };
        })()""")

        shot7 = b.capture_screenshot(OUT_DIR / "u4_bank_transfer_instructions.png")
        results["screenshots"]["bank_transfer_instructions"] = str(shot7)

        check7 = {
            "name": "Lab Bank Transfer Journey & Instructions",
            "metrics": { **bank_selection, **bank_confirmation },
            "passed": bool(
                bank_selection["bankSelected"] and
                not bank_selection["codSelected"] and
                bank_confirmation["hasBankBox"] and
                ("Bank Transfer" in bank_confirmation["bankBoxText"] or "supplier confirmation" in bank_confirmation["bankBoxText"])
            )
        }
        results["checks"].append(check7)
        print("  Check 7:", check7, flush=True)

        results["errors"] = b.errors

    out_json = OUT_DIR / "u4_verification.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nVerification finished! Report written to {out_json}")
    all_passed = all(c["passed"] for c in results["checks"])
    print(f"Overall Status: {'ALL CHECKS PASSED (7/7)' if all_passed else 'SOME CHECKS FAILED'}")
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
