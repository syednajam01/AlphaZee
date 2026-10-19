"""MM2 Browser Verification Script for AlphaZee Admin Media & Collections.
Executes all acceptance workflows through Chrome/CDP on checkout lab (http://127.0.0.1:13001).
"""
import io
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

OUT_DIR = ROOT / '.local/admin-media/mm2'
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
    
    # 1. Front image (Blue, 600x800)
    front_path = tmp_dir / 'test_front_coat.png'
    Image.new('RGB', (600, 800), '#1A365D').save(front_path, format='PNG')
    
    # 2. Hover / back image (Amber, 600x800)
    hover_path = tmp_dir / 'test_hover_coat.png'
    Image.new('RGB', (600, 800), '#92400E').save(hover_path, format='PNG')
    
    # 3. Gallery image (Green, 600x800)
    gallery_path = tmp_dir / 'test_gallery_detail.png'
    Image.new('RGB', (600, 800), '#166534').save(gallery_path, format='PNG')

    # 4. Poster image (Slate, 640x360)
    poster_path = tmp_dir / 'test_video_poster.png'
    Image.new('RGB', (640, 360), '#334155').save(poster_path, format='PNG')

    # 5. Invalid file (text file)
    invalid_path = tmp_dir / 'invalid_script.exe'
    invalid_path.write_bytes(b'NOT AN IMAGE OR VIDEO')

    return front_path, hover_path, gallery_path, poster_path, invalid_path

def generate_lab_video():
    print("Generating real 2-second MP4 video in lab container...", flush=True)
    run_lab_cmd(['exec', 'api', 'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=indigo:s=320x240:d=2',
                 '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '/tmp/test_clip_mm2.mp4'])
    
    local_video_path = ROOT / '.local/admin-media/test_assets/test_hero_clip.mp4'
    local_video_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = LAB_COMPOSE + ['exec', '-T', 'api', 'cat', '/tmp/test_clip_mm2.mp4']
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, check=True)
    local_video_path.write_bytes(res.stdout)
    print(f"Local video ready: {local_video_path} ({len(res.stdout)} bytes)", flush=True)
    return local_video_path

def wait_for_status(b, expected_text, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        text = b.js("document.querySelector('#catalog-status')?.textContent || ''")
        if expected_text.lower() in text.lower():
            return text
        time.sleep(0.2)
    current = b.js("document.querySelector('#catalog-status')?.textContent || ''")
    raise TimeoutError(f"Expected status '{expected_text}' not reached within {timeout}s (current: '{current}')")

def main():
    print("=" * 70, flush=True)
    print("STARTING MM2 ADMIN MEDIA & COLLECTIONS BROWSER VERIFICATION", flush=True)
    print("=" * 70, flush=True)

    front_img, hover_img, gallery_img, poster_img, invalid_file = create_test_images()
    video_file = generate_lab_video()

    with RedesignBrowser(OUT_DIR) as b:
        b.set_viewport(1440, 960)

        def save_and_copy(filename):
            local_path = OUT_DIR / filename
            b.capture_screenshot(str(local_path))
            print(f"  [SCREENSHOT] {filename}", flush=True)
            if BRAIN_ARTIFACTS.exists():
                dest = BRAIN_ARTIFACTS / filename
                shutil.copy2(local_path, dest)

        # Step 1: Provision lab owner & log in
        print("\n1. Provisioning lab owner & logging in...", flush=True)
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
        print("Login response:", login_res.get('username', login_res), "CSRF:", bool(csrf_token), flush=True)

        b.goto(f"{ORIGIN}/admin", wait_selector='#btn-admin-logout')
        b.js("window.confirm = () => true;")
        time.sleep(1.2)
        save_and_copy("mm2_01_admin_logged_in.png")

        # Helper to upload asset via API inside browser session
        def upload_asset_via_browser(file_path, mime_type):
            filename = file_path.name
            file_bytes = file_path.read_bytes()
            import base64
            encoded = base64.b64encode(file_bytes).decode('ascii')
            res = b.js(f"""(() => {{
                const byteCharacters = atob({json.dumps(encoded)});
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {{
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }}
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], {{ type: {json.dumps(mime_type)} }});
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

        print("\nUploading test assets into library...", flush=True)
        uploaded_front = upload_asset_via_browser(front_img, 'image/png')
        uploaded_hover = upload_asset_via_browser(hover_img, 'image/png')
        uploaded_gallery = upload_asset_via_browser(gallery_img, 'image/png')
        uploaded_poster = upload_asset_via_browser(poster_img, 'image/png')
        uploaded_video = upload_asset_via_browser(video_file, 'video/mp4')
        print(f"Uploaded 4 images + 1 video. Video ID: {uploaded_video['id']}", flush=True)

        # Step 2: Collections Workflow - Create "Winter Collection"
        col_name = f"Winter Collection {token}"
        col_slug = f"winter-collection-{token}"
        print(f"\n2. Navigating to Collections tab & creating '{col_name}'...", flush=True)
        b.click('.admin-tab-btn[data-tab="collections"]')
        b.wait_for_selector('#catalog-new-collection', timeout=10)
        time.sleep(0.5)
        b.click('#catalog-new-collection')
        b.wait_for_selector('#catalog-collection-form', timeout=10)

        b.js(f"""(() => {{
            const form = document.querySelector('#catalog-collection-form');
            form.querySelector('[name="name"]').value = {json.dumps(col_name)};
            form.querySelector('[name="slug"]').value = {json.dumps(col_slug)};
            form.querySelector('[name="description"]').value = 'Architectural heavy drape collection for winter.';
            form.querySelector('[name="is_active"]').checked = true;
            form.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.3)
        b.click('#catalog-save-collection')
        st = wait_for_status(b, 'Collection saved.')
        print("Collection saved status:", st, flush=True)
        time.sleep(0.5)
        save_and_copy("mm2_02_winter_collection_created.png")

        # Step 3: Inside Winter Collection -> "Create product here"
        print(f"\n3. Testing 'Create product here' inside '{col_name}'...", flush=True)
        b.js(f"""(() => {{
            const cards = [...document.querySelectorAll('.catalog-card')];
            const target = cards.find(c => c.textContent.includes({json.dumps(col_name)}));
            target.querySelector('[data-edit-collection]').click();
        }})()""")
        b.wait_for_selector('#catalog-col-create-prod', timeout=10)
        time.sleep(0.5)

        has_create_prod = b.js("Boolean(document.querySelector('#catalog-col-create-prod'))")
        assert has_create_prod, "Missing #catalog-col-create-prod button in collection editor!"
        
        b.click('#catalog-col-create-prod')
        b.wait_for_selector('#catalog-product-form', timeout=10)
        time.sleep(0.5)

        current_col_val = b.js("document.querySelector('#catalog-product-form [name=\"collection_id\"]')?.value || ''")
        print(f"Pre-selected collection ID in new product: {current_col_val}", flush=True)
        assert current_col_val != '', "Collection ID was not pre-populated!"

        b.click('#catalog-add-variant')
        time.sleep(0.4)

        coat_sku = f"WWO-{token}"
        coat_slug = f"winter-wool-overcoat-{token}"
        b.js(f"""(() => {{
            const form = document.querySelector('#catalog-product-form');
            form.querySelector('[name="title"]').value = 'Winter Wool Overcoat';
            form.querySelector('[name="slug"]').value = {json.dumps(coat_slug)};
            form.querySelector('[name="description"]').value = 'Double-faced structured wool coat.';
            const variantRow = document.querySelector('.catalog-variant');
            if (variantRow) {{
                variantRow.querySelector('[name="sku"]').value = {json.dumps(coat_sku)};
                variantRow.querySelector('[name="price"]').value = '18500';
                variantRow.querySelector('[name="variant_active"]').checked = true;
            }}
            form.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.5)
        b.click('#catalog-save-product')
        st = wait_for_status(b, 'Product')
        print("Product save status:", st, flush=True)
        save_and_copy("mm2_03_product_created_in_collection.png")

        # Step 4: Create Unassigned Draft Product
        print("\n4. Creating unassigned draft product...", flush=True)
        b.click('.admin-tab-btn[data-tab="products"]')
        b.wait_for_selector('#catalog-new-product', timeout=10)
        time.sleep(0.5)
        b.click('#catalog-new-product')
        b.wait_for_selector('#catalog-product-form', timeout=10)
        time.sleep(0.5)

        b.click('#catalog-add-variant')
        time.sleep(0.4)

        beanie_title = f"Unassigned Cashmere Beanie {token}"
        beanie_slug = f"unassigned-cashmere-beanie-{token}"
        beanie_sku = f"UCB-{token}"
        b.js(f"""(() => {{
            const form = document.querySelector('#catalog-product-form');
            form.querySelector('[name="title"]').value = {json.dumps(beanie_title)};
            form.querySelector('[name="slug"]').value = {json.dumps(beanie_slug)};
            form.querySelector('[name="description"]').value = 'Ribbed pure cashmere.';
            form.querySelector('[name="collection_id"]').value = '';
            const variantRow = document.querySelector('.catalog-variant');
            if (variantRow) {{
                variantRow.querySelector('[name="sku"]').value = {json.dumps(beanie_sku)};
                variantRow.querySelector('[name="price"]').value = '4500';
                variantRow.querySelector('[name="variant_active"]').checked = true;
            }}
            form.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.5)
        b.click('#catalog-save-product')
        wait_for_status(b, 'Product')
        print("Unassigned product saved.", flush=True)

        # Step 5: Assign unassigned product to Winter Collection via "Add existing product"
        print(f"\n5. Assigning unassigned product to '{col_name}'...", flush=True)
        b.click('.admin-tab-btn[data-tab="collections"]')
        b.wait_for_selector('[data-edit-collection]', timeout=10)
        time.sleep(0.5)
        b.js(f"""(() => {{
            const cards = [...document.querySelectorAll('.catalog-card')];
            const target = cards.find(c => c.textContent.includes({json.dumps(col_name)}));
            target.querySelector('[data-edit-collection]').click();
        }})()""")
        b.wait_for_selector('#catalog-col-add-prod-select', timeout=10)
        time.sleep(0.5)

        add_options = b.js("""(() => {
            const select = document.querySelector('#catalog-col-add-prod-select');
            return [...select.options].map(o => ({ value: o.value, text: o.text }));
        })()""")
        print("Available unassigned products:", [o['text'] for o in add_options], flush=True)
        target_opt = next((o for o in add_options if beanie_title in o['text']), None)
        assert target_opt is not None, f"{beanie_title} not found in add selector!"

        b.js(f"""(() => {{
            const select = document.querySelector('#catalog-col-add-prod-select');
            select.value = {json.dumps(target_opt['value'])};
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.3)
        b.click('#catalog-col-add-prod-btn')
        st = wait_for_status(b, 'added to collection')
        print("Add to collection status:", st, flush=True)

        member_count = b.js("document.querySelectorAll('.collection-member-item').length")
        print(f"Collection member count after add: {member_count}", flush=True)
        assert member_count >= 2, f"Expected at least 2 members, got {member_count}"
        save_and_copy("mm2_04_member_products_added.png")

        # Step 6: Move product out of collection (Unassign)
        print("\n6. Moving product out of collection (Unassign)...", flush=True)
        b.js(f"""(() => {{
            const items = [...document.querySelectorAll('.collection-member-item')];
            const beanieItem = items.find(i => i.textContent.includes({json.dumps(beanie_title)}));
            const moveSelect = beanieItem.querySelector('select[data-move-target]');
            moveSelect.value = '__unassign__';
            moveSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
            beanieItem.querySelector('button[data-move-member-prod]').click();
        }})()""")
        st = wait_for_status(b, 'moved successfully')
        print("Move member status:", st, flush=True)

        member_count = b.js("document.querySelectorAll('.collection-member-item').length")
        print(f"Collection member count after move: {member_count}", flush=True)
        assert member_count == 1, f"Expected 1 member remaining, got {member_count}"
        save_and_copy("mm2_05_member_product_moved.png")

        # Step 7: Product Media Roles (Front, Hover, Gallery, Video Poster)
        print("\n7. Setting Card Front, Card Hover, Gallery, and Video Poster...", flush=True)
        b.click('.admin-tab-btn[data-tab="products"]')
        b.wait_for_selector('[data-edit-product]', timeout=10)
        time.sleep(0.5)
        b.js(f"""(() => {{
            const rows = [...document.querySelectorAll('.catalog-card')];
            const coatRow = rows.find(r => r.textContent.includes('Winter Wool Overcoat'));
            coatRow.querySelector('[data-edit-product]').click();
        }})()""")
        b.wait_for_selector('#catalog-product-form', timeout=10)
        time.sleep(0.5)

        # Attach video clip and gallery image first
        b.js(f"""(() => {{
            const picker = document.querySelector('#catalog-attach-asset');
            picker.value = {json.dumps(uploaded_video['id'])};
            const roleSelect = document.querySelector('#catalog-attach-role');
            roleSelect.value = 'gallery';
            document.querySelector('#catalog-attach').click();
        }})()""")
        time.sleep(0.8)

        b.js(f"""(() => {{
            const picker = document.querySelector('#catalog-attach-asset');
            picker.value = {json.dumps(uploaded_gallery['id'])};
            const roleSelect = document.querySelector('#catalog-attach-role');
            roleSelect.value = 'gallery';
            document.querySelector('#catalog-attach').click();
        }})()""")
        time.sleep(0.8)

        # Set Card Front Image selector
        b.js(f"""(() => {{
            const frontSelect = document.querySelector('#catalog-select-front');
            frontSelect.value = {json.dumps(uploaded_front['id'])};
            frontSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.8)

        # Set Card Hover Image selector
        b.js(f"""(() => {{
            const hoverSelect = document.querySelector('#catalog-select-hover');
            hoverSelect.value = {json.dumps(uploaded_hover['id'])};
            hoverSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.8)

        # Set Video Poster directly on the video card
        vid_id = uploaded_video['id']
        b.js(f"""(() => {{
            const vidSelect = document.querySelector('select[name="video_poster_id"][data-video-asset="{vid_id}"]');
            vidSelect.value = {json.dumps(uploaded_poster['id'])};
            vidSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.3)
        b.click(f'button[data-save-video-poster="{vid_id}"]')
        st = wait_for_status(b, 'Video poster saved')
        print("Video poster save status:", st, flush=True)

        # Save product
        b.click('#catalog-save-product')
        st = wait_for_status(b, 'Product')
        print("Product saved status:", st, flush=True)

        # Reload product editor to confirm persistence across reload!
        print("Reloading product editor to verify persistence...", flush=True)
        b.click('#catalog-reload-product')
        time.sleep(1.5)

        persisted_front = b.js("document.querySelector('#catalog-select-front')?.value || ''")
        persisted_hover = b.js("document.querySelector('#catalog-select-hover')?.value || ''")
        front_thumb_src = b.js("document.querySelector('#card-front-thumb img')?.src || ''")
        hover_thumb_src = b.js("document.querySelector('#card-hover-thumb img')?.src || ''")

        print(f"Persisted Front ID: {persisted_front} (expected {uploaded_front['id']})", flush=True)
        print(f"Persisted Hover ID: {persisted_hover} (expected {uploaded_hover['id']})", flush=True)
        assert persisted_front == uploaded_front['id'], "Front image was not persisted!"
        assert persisted_hover == uploaded_hover['id'], "Hover image was not persisted!"
        assert front_thumb_src != '', "Front thumbnail image not displayed!"
        assert hover_thumb_src != '', "Hover thumbnail image not displayed!"

        save_and_copy("mm2_07_product_media_roles_persisted.png")

        # Publish the product so the collection has an active published product
        print("Publishing product...", flush=True)
        b.click('#catalog-publish')
        st = wait_for_status(b, 'published')
        print("Product publish status:", st, flush=True)
        print("\n8. Testing Homepage Hero Playlist Editor...", flush=True)
        b.click('.admin-tab-btn[data-tab="hero"]')
        b.wait_for_selector('#catalog-new-hero-slide', timeout=10)
        time.sleep(0.5)

        # Slide 1: Video slide
        b.click('#catalog-new-hero-slide')
        b.wait_for_selector('#catalog-hero-form', timeout=10)
        time.sleep(0.5)
        b.js(f"""(() => {{
            const form = document.querySelector('#catalog-hero-form');
            form.querySelector('[name="title"]').value = 'Winter Outerwear 2026';
            form.querySelector('[name="benefit"]').value = 'Heavyweight wool overcoats and structured drapes.';
            form.querySelector('[name="video_asset_id"]').value = {json.dumps(uploaded_video['id'])};
            form.querySelector('[name="poster_asset_id"]').value = {json.dumps(uploaded_poster['id'])};
            form.querySelector('[name="is_enabled"]').checked = true;
            form.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.3)
        b.click('#catalog-save-hero-slide')
        st = wait_for_status(b, 'Hero slide')
        print("Hero slide 1 status:", st, flush=True)

        # Slide 2: Image slide
        b.click('#catalog-new-hero-slide')
        b.wait_for_selector('#catalog-hero-form', timeout=10)
        time.sleep(0.5)
        b.js(f"""(() => {{
            const form = document.querySelector('#catalog-hero-form');
            form.querySelector('[name="title"]').value = 'Curated Daily Silhouettes';
            form.querySelector('[name="benefit"]').value = 'Fine cashmere beanies and architectural essentials.';
            form.querySelector('[name="image_asset_id"]').value = {json.dumps(uploaded_gallery['id'])};
            form.querySelector('[name="is_enabled"]').checked = true;
            form.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }})()""")
        time.sleep(0.3)
        b.click('#catalog-save-hero-slide')
        st = wait_for_status(b, 'Hero slide')
        print("Hero slide 2 status:", st, flush=True)

        slide_count = b.js("document.querySelectorAll('.hero-slide-card').length")
        print(f"Hero slide count: {slide_count}", flush=True)
        assert slide_count >= 2, f"Expected at least 2 slides, got {slide_count}"

        # Reorder slides (move down slide 1)
        print("Testing slide reordering...", flush=True)
        b.click('button[data-slide-down="0"]')
        st = wait_for_status(b, 'reordered')
        print("Reorder status:", st, flush=True)

        # Toggle slide enable/disable
        print("Testing slide enable toggle...", flush=True)
        b.click('button[data-slide-toggle]')
        st = wait_for_status(b, 'Slide')
        print("Toggle status:", st, flush=True)

        save_and_copy("mm2_08_hero_playlist_editor.png")

        # Step 9: Collection Deactivation Warning
        print("\n9. Testing Collection Deactivation Warning...", flush=True)
        b.js("window.confirm = () => true;")
        b.click('.admin-tab-btn[data-tab="collections"]')
        b.wait_for_selector('[data-edit-collection]', timeout=10)
        time.sleep(0.5)
        b.js(f"""(() => {{
            const cards = [...document.querySelectorAll('.catalog-card')];
            const target = cards.find(c => c.textContent.includes({json.dumps(col_name)}));
            target.querySelector('[data-edit-collection]').click();
        }})()""")
        b.wait_for_selector('#catalog-col-is-active', timeout=10)
        time.sleep(0.5)

        # Deactivate collection active checkbox and observe warning display
        warning_display = b.js("""(() => {
            const checkbox = document.querySelector('#catalog-col-is-active');
            checkbox.checked = false;
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            const warning = document.querySelector('#catalog-col-deactivation-warning');
            return window.getComputedStyle(warning).display;
        })()""")
        print(f"Deactivation warning display: {warning_display}", flush=True)
        assert warning_display == 'block', f"Expected deactivation warning display: block, got {warning_display}"
        save_and_copy("mm2_09_collection_deactivation_warning.png")

    print("\n" + "=" * 70, flush=True)
    print("MM2 BROWSER ACCEPTANCE VERIFICATION COMPLETED SUCCESSFULLY", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
