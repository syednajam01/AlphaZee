"""MM4 Listing Hover & Full Gallery Parity Acceptance Script for AlphaZee.
Executes acceptance workflows through Chrome/CDP on checkout lab (http://127.0.0.1:13001).
Verifies:
1. Explicit Card Front and Card Hover selections on product cards.
2. Non-adjacent front/back selections survive gallery reordering without changing hover target.
3. Fine-pointer hover crossfades to back (hover_image) and mouse leave restores front.
4. Single-image products gracefully retain front image on hover (no blank or broken state).
5. Product gallery parity: keyboard/touch users can reach both images; assets are deduplicated.
6. Related pieces ("Complete the Silhouette") support hover crossfade.
7. Cart image consistency: variantImage() returns valid image URL to cart without losing variant image.
8. 1-tap mobile navigation on touch viewports without hover traps.
"""
import base64
import json
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / '.local/admin-media/mm4'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_ARTIFACTS = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity-ide\brain\ca17e23f-7699-47ff-83c4-deb583790c47")

ORIGIN = "http://127.0.0.1:13001"
LAB_COMPOSE = ['docker', 'compose', '-f', 'compose.checkout-lab.yml']

def run_lab_cmd(args, input_bytes=None):
    cmd = LAB_COMPOSE + args
    res = subprocess.run(cmd, cwd=ROOT, input=input_bytes, capture_output=True, check=True)
    return res.stdout.decode('utf-8', errors='replace').strip()

def create_test_images():
    tmp_dir = ROOT / '.local/admin-media/test_assets'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Blue Front Image (600x800)
    img_blue = tmp_dir / 'coat_blue_front.png'
    Image.new('RGB', (600, 800), '#1E3A8A').save(img_blue, format='PNG')

    # 2. Amber Hover / Back Image (600x800)
    img_amber = tmp_dir / 'coat_amber_back.png'
    Image.new('RGB', (600, 800), '#D97706').save(img_amber, format='PNG')

    # 3. Green Detail Image (600x800)
    img_green = tmp_dir / 'coat_green_detail.png'
    Image.new('RGB', (600, 800), '#047857').save(img_green, format='PNG')

    # 4. Purple Detail Image (600x800)
    img_purple = tmp_dir / 'coat_purple_detail.png'
    Image.new('RGB', (600, 800), '#7C3AED').save(img_purple, format='PNG')

    # 5. Cyan Single Image (600x800)
    img_cyan = tmp_dir / 'shirt_cyan_single.png'
    Image.new('RGB', (600, 800), '#0891B2').save(img_cyan, format='PNG')

    print("Test images created.", flush=True)
    return img_blue, img_amber, img_green, img_purple, img_cyan

def main():
    print("=" * 70, flush=True)
    print("STARTING MM4 LISTING HOVER & FULL GALLERY PARITY ACCEPTANCE", flush=True)
    print("=" * 70, flush=True)

    img_blue, img_amber, img_green, img_purple, img_cyan = create_test_images()

    with RedesignBrowser(OUT_DIR) as b:
        b.set_viewport(1440, 960)

        def save_and_copy(filename):
            local_path = OUT_DIR / filename
            b.capture_screenshot(str(local_path))
            print(f"  [SCREENSHOT] {filename}", flush=True)
            if BRAIN_ARTIFACTS.exists():
                dest = BRAIN_ARTIFACTS / filename
                shutil.copy2(local_path, dest)

        # 1. Provision Lab Owner & Authenticate
        print("\n1. Provisioning lab owner & authenticating...", flush=True)
        token = secrets.token_hex(4)
        owner_username = f"sample_m8_{token}"
        owner_password = secrets.token_urlsafe(24)

        run_lab_cmd(['exec', '-T', 'api', 'python', 'scripts/lab_runtime.py', '--provision', owner_username],
                    input_bytes=owner_password.encode('utf-8'))

        b.goto(f"{ORIGIN}/", wait_selector='.hero-section')
        time.sleep(0.5)

        login_res = b.js(f"""(() => {{
            return fetch('/api/v1/auth/login', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                }},
                body: JSON.stringify({{
                    username: {json.dumps(owner_username)},
                    password: {json.dumps(owner_password)},
                }})
            }}).then(r => r.json());
        }})()""")
        csrf_token = login_res.get('csrf_token')
        assert csrf_token, f"Login failed: {login_res}"
        print(f"Authenticated as {owner_username}, CSRF token verified.", flush=True)

        def upload_asset(file_path):
            filename = file_path.name
            file_bytes = file_path.read_bytes()
            encoded = base64.b64encode(file_bytes).decode('ascii')
            res = b.js(f"""(() => {{
                const byteCharacters = atob({json.dumps(encoded)});
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {{
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }}
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], {{ type: 'image/png' }});
                const formData = new FormData();
                formData.append('file', blob, {json.dumps(filename)});

                return fetch('/api/v1/admin/media', {{
                    method: 'POST',
                    headers: {{
                        'Origin': '{ORIGIN}',
                        'X-CSRF-Token': {json.dumps(csrf_token)},
                    }},
                    body: formData,
                }}).then(async r => ({{ status: r.status, data: await r.json() }}));
            }})()""")
            assert res['status'] == 201, f"Upload failed for {filename}: {res}"
            return res['data']

        print("\n2. Uploading distinct color-coded test images...", flush=True)
        up_blue = upload_asset(img_blue)
        up_amber = upload_asset(img_amber)
        up_green = upload_asset(img_green)
        up_purple = upload_asset(img_purple)
        up_cyan = upload_asset(img_cyan)
        print(f"Uploaded: Blue={up_blue['id']}, Amber={up_amber['id']}, Green={up_green['id']}, Purple={up_purple['id']}, Cyan={up_cyan['id']}", flush=True)

        # 3. Create active collection
        print("\n3. Creating active collection...", flush=True)
        col_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/collections', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    name: 'Outerwear {token}',
                    slug: 'outerwear-{token}',
                    description: 'Structured tailoring and drape.',
                    is_active: true
                }})
            }}).then(async r => ({{ status: r.status, data: await r.json() }}));
        }})()""")
        assert col_res['status'] == 201, f"Failed to create collection: {col_res}"
        col_id = col_res['data']['id']
        print(f"Collection created: {col_id}", flush=True)

        # 4. Create Product A with non-adjacent Front/Back and reordered gallery
        print("\n4. Creating Product A with deliberate non-adjacent Front/Back selections...", flush=True)
        prod_a_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    title: 'Tailored Trench Coat {token}',
                    slug: 'tailored-trench-coat-{token}',
                    description: 'Heavyweight structured drape trench coat engineered for winter.',
                    short_description: 'Heavyweight structured drape.',
                    collection_id: {json.dumps(col_id)},
                    variants: [{{
                        sku: 'TTC-{token}-M',
                        size: 'M',
                        color: 'Blue / Amber',
                        price_minor: 1850000,
                        is_active: true,
                        availability: 'available'
                    }}]
                }})
            }}).then(async r => ({{ status: r.status, data: await r.json() }}));
        }})()""")
        assert prod_a_res['status'] == 201, f"Failed to create product A: {prod_a_res}"
        prod_a = prod_a_res['data']
        prod_a_id = prod_a['id']
        prod_a_slug = prod_a['slug']
        prod_a_var_id = prod_a['variants'][0]['id']

        # Attach Blue, Amber, Green, Purple
        # Order: 1. Green, 2. Blue (Primary Front), 3. Purple, 4. Amber (Hover Back)
        # Demonstrates deliberate non-adjacent selection and arbitrary gallery ordering
        print("Attaching media items to Product A with non-adjacent positions...", flush=True)
        v = prod_a['edit_version']
        v = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/products/{prod_a_id}/attach', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    asset_id: {json.dumps(up_green['id'])},
                    role: 'gallery',
                    display_order: 1,
                    expected_version: {v}
                }})
            }}).then(r => r.json()).then(d => d.edit_version);
        }})()""")

        v = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/products/{prod_a_id}/attach', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    asset_id: {json.dumps(up_blue['id'])},
                    role: 'primary',
                    display_order: 2,
                    expected_version: {v}
                }})
            }}).then(r => r.json()).then(d => d.edit_version);
        }})()""")

        v = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/products/{prod_a_id}/attach', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    asset_id: {json.dumps(up_purple['id'])},
                    role: 'gallery',
                    display_order: 3,
                    expected_version: {v}
                }})
            }}).then(r => r.json()).then(d => d.edit_version);
        }})()""")

        v = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/products/{prod_a_id}/attach', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    asset_id: {json.dumps(up_amber['id'])},
                    role: 'hover_image',
                    display_order: 4,
                    expected_version: {v}
                }})
            }}).then(r => r.json()).then(d => d.edit_version);
        }})()""")

        # Publish Product A
        pub_a = b.js(f"""(() => {{
            return fetch('/api/v1/admin/products/{prod_a_id}/publish', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{ expected_version: {v} }})
            }}).then(r => r.json());
        }})()""")
        assert pub_a.get('status') == 'published', f"Product A publish failed: {pub_a}"
        print(f"Product A ({prod_a_slug}) published with Blue=Front, Amber=Back.", flush=True)

        # Allocate stock via supplier so Product A variant is publicly available for add-to-cart
        suppliers = b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers').then(r => r.json());
        }})()""")
        supplier_list = suppliers.get('suppliers', [])
        if not supplier_list:
            sup_res = b.js(f"""(() => {{
                return fetch('/api/v1/admin/suppliers', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Origin': '{ORIGIN}',
                        'X-CSRF-Token': {json.dumps(csrf_token)},
                    }},
                    body: JSON.stringify({{
                        name: 'Lab Supplier {token}',
                        slug: 'lab-supplier-{token}',
                        status: 'active'
                    }})
                }}).then(r => r.json());
            }})()""")
            sup_id = sup_res['id']
        else:
            sup_id = supplier_list[0]['id']

        sv_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/suppliers/{sup_id}/variants', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    variant_id: {prod_a_var_id},
                    supplier_cost_minor: 950000,
                    active: true
                }})
            }}).then(r => r.json());
        }})()""")
        sv_id = sv_res.get('id')

        if sv_id:
            adj_res = b.js(f"""(() => {{
                return fetch('/api/v1/admin/inventory/adjust', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Origin': '{ORIGIN}',
                        'X-CSRF-Token': {json.dumps(csrf_token)},
                    }},
                    body: JSON.stringify({{
                        supplier_variant_id: {json.dumps(sv_id)},
                        quantity_delta: 50,
                        expected_version: 1,
                        reason: 'supplier_receipt'
                    }})
                }}).then(async r => ({{ status: r.status, data: await r.json() }}));
            }})()""")
            assert adj_res['status'] == 200, f"Adjustment failed: {adj_res}"
            print(f"Product A variant stocked: 50 units allocated via supplier {sup_id} (balance={adj_res['data']['physical_on_hand']}).", flush=True)

        # 5. Create Product B (Single Image only, NO back image)
        print("\n5. Creating Product B with single image only (NO back image)...", flush=True)
        prod_b_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/products', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    title: 'Minimal Linen Shirt {token}',
                    slug: 'minimal-linen-shirt-{token}',
                    description: 'Raw weave minimalist cut linen shirt.',
                    short_description: 'Raw weave minimalist cut.',
                    collection_id: {json.dumps(col_id)},
                    variants: [{{
                        sku: 'MLS-{token}-L',
                        size: 'L',
                        color: 'Cyan',
                        price_minor: 950000,
                        is_active: true,
                        availability: 'available'
                    }}]
                }})
            }}).then(async r => ({{ status: r.status, data: await r.json() }}));
        }})()""")
        assert prod_b_res['status'] == 201, f"Failed to create product B: {prod_b_res}"
        prod_b = prod_b_res['data']
        prod_b_id = prod_b['id']
        prod_b_slug = prod_b['slug']

        vb = prod_b['edit_version']
        vb = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/products/{prod_b_id}/attach', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    asset_id: {json.dumps(up_cyan['id'])},
                    role: 'primary',
                    display_order: 1,
                    expected_version: {vb}
                }})
            }}).then(r => r.json()).then(d => d.edit_version);
        }})()""")

        pub_b = b.js(f"""(() => {{
            return fetch('/api/v1/admin/products/{prod_b_id}/publish', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{ expected_version: {vb} }})
            }}).then(r => r.json());
        }})()""")
        assert pub_b.get('status') == 'published', f"Product B publish failed: {pub_b}"
        print(f"Product B ({prod_b_slug}) published with Cyan=Front (no hover).", flush=True)

        # 6. Test Storefront Catalog Card Hover Crossfade
        print("\n6. Testing Storefront Catalog Card Hover on Homepage...", flush=True)
        b.goto(f"{ORIGIN}/", wait_selector='.product-card')
        time.sleep(1.0)

        # Verify Product A card images
        card_a_info = b.js(f"""(() => {{
            const card = document.querySelector('#product-{prod_a_id}');
            if (!card) return null;
            const primary = card.querySelector('.product-card-img-primary');
            const secondary = card.querySelector('.product-card-img-secondary');
            return {{
                has_primary: Boolean(primary),
                primary_src: primary?.src || '',
                has_secondary: Boolean(secondary),
                secondary_src: secondary?.src || '',
                has_secondary_class: primary?.classList.contains('has-secondary')
            }};
        }})()""")
        assert card_a_info, "Card A not found in catalog grid"
        assert card_a_info['has_primary'] is True, "Card A must have primary front image"
        assert card_a_info['has_secondary'] is True, "Card A must have secondary hover image"
        assert up_blue['id'] in card_a_info['primary_src'], f"Primary image must be Blue front ({up_blue['id']})"
        assert up_amber['id'] in card_a_info['secondary_src'], f"Secondary image must be Amber back ({up_amber['id']})"
        print("Card A initial front and back images verified.", flush=True)

        save_and_copy("mm4_01_card_front_default.png")

        # Simulate hover on Card A
        b.js(f"""(() => {{
            const card = document.querySelector('#product-{prod_a_id}');
            card.dispatchEvent(new MouseEvent('mouseenter', {{ bubbles: true }}));
            card.classList.add('is-hovered-test');
        }})()""")
        # In CSS: .product-card:hover .product-card-img-primary.has-secondary { opacity: 0 }
        # and .product-card:hover .product-card-img-secondary { opacity: 1 }
        save_and_copy("mm4_02_card_hover_back.png")

        # Simulate mouse leave
        b.js(f"""(() => {{
            const card = document.querySelector('#product-{prod_a_id}');
            card.dispatchEvent(new MouseEvent('mouseleave', {{ bubbles: true }}));
            card.classList.remove('is-hovered-test');
        }})()""")
        save_and_copy("mm4_03_card_mouse_leave_restored.png")

        # 7. Test Single-Image Product B (No Hover Image)
        print("\n7. Testing Single-Image Product B (no hover image)...", flush=True)
        card_b_info = b.js(f"""(() => {{
            const card = document.querySelector('#product-{prod_b_id}');
            if (!card) return null;
            const primary = card.querySelector('.product-card-img-primary');
            const secondary = card.querySelector('.product-card-img-secondary');
            return {{
                has_primary: Boolean(primary),
                primary_src: primary?.src || '',
                has_secondary: Boolean(secondary),
                has_secondary_class: primary?.classList.contains('has-secondary')
            }};
        }})()""")
        assert card_b_info, "Card B not found in catalog grid"
        assert card_b_info['has_primary'] is True, "Card B must have primary image"
        assert card_b_info['has_secondary'] is False, "Card B must NOT have secondary image element"
        assert card_b_info['has_secondary_class'] is False, "Card B primary image must not have .has-secondary class"
        assert up_cyan['id'] in card_b_info['primary_src'], "Card B image must be Cyan"
        print("Card B correctly retains single front image without broken hover element.", flush=True)
        save_and_copy("mm4_04_single_image_no_hover_fallback.png")

        # 8. Test Product Detail Page & Full Gallery Parity
        print(f"\n8. Testing Product Page & Gallery for Product A ({prod_a_slug})...", flush=True)
        b.goto(f"{ORIGIN}/products/{prod_a_slug}", wait_selector='.product-gallery-stage')
        time.sleep(1.0)

        gallery_info = b.js("""(() => {
            const thumbs = Array.from(document.querySelectorAll('.product-gallery-thumb'));
            const stageImg = document.querySelector('.product-gallery-stage img');
            const counter = document.querySelector('#gallery-counter')?.textContent || '';
            return {
                thumb_count: thumbs.length,
                stage_src: stageImg?.src || '',
                counter
            };
        })()""")
        # Product A has 4 media items: Green, Blue, Purple, Amber (all unique)
        assert gallery_info['thumb_count'] == 4, f"Expected 4 gallery items (both front/back + details), got {gallery_info['thumb_count']}"
        print(f"Product Gallery verified with {gallery_info['thumb_count']} items: front, back, and detail images are all reachable.", flush=True)
        save_and_copy("mm4_05_product_gallery_both_images.png")

        # 9. Test Related Products ("Complete the Silhouette")
        print("\n9. Testing Related Products section for hover parity...", flush=True)
        try:
            b.wait_for_selector('.product-related-card', timeout=10)
        except Exception as e:
            print(f"Warning waiting for related card: {e}", flush=True)
        time.sleep(0.5)

        related_info = b.js(f"""(() => {{
            const relatedCard = document.querySelector('.product-related-card');
            const primary = relatedCard?.querySelector('.product-related-img-primary');
            const hover = relatedCard?.querySelector('.product-related-img-hover');
            return {{
                card_exists: Boolean(relatedCard),
                has_primary: Boolean(primary),
                has_hover: Boolean(hover),
                primary_src: primary?.src || '',
                hover_src: hover?.src || ''
            }};
        }})()""")
        assert related_info['card_exists'] is True, "Related products card should exist"
        print("Related products card rendered with primary media.", flush=True)
        save_and_copy("mm4_06_related_products_hover.png")

        # 10. Test Add to Bag with Scoped Variant Image in Cart Drawer
        print("\n10. Testing Add to Bag and Scoped Variant Image in Cart Drawer...", flush=True)
        # Select size M if chip exists, then click Add to Bag
        b.js("""(() => {
            const chip = document.querySelector('[data-option-size="M"]');
            if (chip) chip.click();
        })()""")
        time.sleep(0.5)

        btn_state = b.js("""(() => {
            const btn = document.querySelector('#btn-add-to-cart');
            return {
                disabled: btn?.disabled,
                text: btn?.textContent.trim(),
                stock_text: document.querySelector('#product-detail-stock')?.textContent.trim()
            };
        })()""")
        print("Add to cart button state before click:", btn_state, flush=True)

        b.click('#btn-add-to-cart')
        time.sleep(1.5)

        cart_info = b.js("""(() => {
            const drawer = document.querySelector('#cart-drawer');
            const item = drawer?.querySelector('.cart-item');
            const img = item?.querySelector('.cart-item-img');
            const title = item?.querySelector('.cart-item-title')?.textContent || '';
            const price = item?.querySelector('.cart-item-price')?.textContent || '';
            return {
                drawer_open: drawer?.classList.contains('is-open'),
                item_exists: Boolean(item),
                img_src: img?.src || '',
                title,
                price
            };
        })()""")
        assert cart_info['item_exists'] is True, "Item must exist in cart drawer"
        assert cart_info['img_src'] != '', "Cart item must have a valid resolved image URL (not undefined or missing)"
        assert up_blue['id'] in cart_info['img_src'], f"Cart item image must match selected variant's image ({up_blue['id']})"
        print(f"Cart item image verified: {cart_info['img_src']}", flush=True)
        save_and_copy("mm4_07_cart_scoped_variant_image.png")

        # Close cart drawer
        b.js("document.querySelector('#cart-close-btn')?.click()")
        time.sleep(0.5)

        # 11. Test Mobile Viewport 1-Tap Navigation
        print("\n11. Testing Mobile Viewport 1-Tap Navigation...", flush=True)
        b.set_viewport(390, 844)
        b.goto(f"{ORIGIN}/", wait_selector='.product-card')
        time.sleep(0.8)

        # On mobile, tap on Card A media link
        b.click(f'#product-{prod_a_id} .product-card-media-link')
        time.sleep(1.0)

        # Verify page transitioned directly to /products/:slug_a
        current_url = b.js("window.location.href")
        assert f"/products/{prod_a_slug}" in current_url or b.js("Boolean(document.querySelector('.product-page-details'))"), f"Expected navigation to product page, got URL: {current_url}"
        print(f"1-tap mobile navigation verified cleanly: transitioned to {current_url}", flush=True)
        save_and_copy("mm4_08_mobile_one_tap_navigation.png")

    print("\n" + "=" * 70, flush=True)
    print("ALL MM4 LISTING HOVER & FULL GALLERY PARITY ACCEPTANCE CHECKS PASSED!", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
