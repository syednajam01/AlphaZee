import sys, time, shutil, json, subprocess, io
from pathlib import Path
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / 'scratch'
ARTIFACT_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\e0e456e1-e4cb-4fd8-a8d5-475bb70698e3")

# Clear login bucket before test run
subprocess.run([
    'docker', 'compose', 'exec', '-T', 'api', 'python', '-c',
    '''from app.database import SessionLocal; from app.models.auth import OwnerLoginBucket;
db = SessionLocal()
db.query(OwnerLoginBucket).delete()
db.commit()
db.close()'''
], capture_output=True)

def save_and_copy(b, filename):
    local_path = OUT_DIR / filename
    b.capture_screenshot(str(local_path))
    if ARTIFACT_DIR.exists():
        shutil.copy2(local_path, ARTIFACT_DIR / filename)
    print(f"Captured & copied: {filename}", flush=True)

# 1. Create realistic sample iPhone media files
sample_heic_path = OUT_DIR / 'iphone_16_pro_sample.heic'
heic_img = Image.new('RGB', (1200, 1600), color=(140, 45, 60))
heic_img.save(str(sample_heic_path), format='HEIF')
print(f"Created sample iPhone HEIC photo: {sample_heic_path} ({sample_heic_path.stat().st_size} bytes)")

sample_mov_path = OUT_DIR / 'iphone_16_pro_sample.mov'
if not sample_mov_path.exists():
    subprocess.run(['docker', 'compose', 'exec', '-T', 'api', 'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=indigo:s=1080x1920:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '/tmp/iphone_sample.mov'], check=True)
    subprocess.run(['docker', 'compose', 'cp', 'api:/tmp/iphone_sample.mov', str(sample_mov_path)], check=True)
print(f"Sample iPhone QuickTime MOV video ready: {sample_mov_path} ({sample_mov_path.stat().st_size} bytes)")

with RedesignBrowser(ROOT / '.local/tmp') as b:
    print("=== TEST SUITE: IPHONE 16 PRO MEDIA PIPELINE & VARIANTS ===", flush=True)

    # 1. Desktop Viewport & Login
    print("1. Opening desktop browser (1440x900) to /admin...", flush=True)
    b.set_viewport(1440, 900)
    b.goto('http://localhost:13000/admin')
    time.sleep(1)

    # Wait for API to be healthy
    for _ in range(20):
        h_res = b.js("(async () => { try { const r = await fetch('/api/v1/health'); return r.status; } catch { return 0; } })()")
        if h_res == 200:
            print("API is healthy!")
            break
        time.sleep(1)

    login_res = b.js("""(async () => {
        try {
            const res = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Origin': 'http://localhost:13000'},
                body: JSON.stringify({username: 'owner_vf7_b71d91e8', password: 'OwnerPass123_b71d91e8'})
            });
            const data = await res.json();
            return { ok: res.ok, status: res.status, csrf_token: data.csrf_token };
        } catch (e) {
            return { error: String(e) };
        }
    })()""")
    print("Login status:", login_res)
    csrf_token = login_res.get('csrf_token')
    assert csrf_token, f"Login failed: {login_res}"

    b.goto('http://localhost:13000/admin')
    time.sleep(1.5)

    # 2. Upload iPhone HEIC photo via API
    upload_heic_res = b.js(f"""(async () => {{
        const formData = new FormData();
        const blob = new Blob([new Uint8Array({list(sample_heic_path.read_bytes())})], {{ type: 'image/heic' }});
        formData.append('file', blob, 'iphone_16_pro_sample.heic');
        const res = await fetch('/api/v1/admin/media', {{
            method: 'POST',
            headers: {{ 'X-CSRF-Token': '{csrf_token}', 'Origin': 'http://localhost:13000' }},
            body: formData
        }});
        return {{ ok: res.ok, status: res.status, data: await res.json() }};
    }})()""")
    print("HEIC Upload response:", upload_heic_res.get('status'), upload_heic_res.get('ok'))
    assert upload_heic_res.get('ok'), f"HEIC upload failed: {upload_heic_res}"
    heic_asset = upload_heic_res['data']
    print("HEIC Asset:", heic_asset.get('id'), "kind:", heic_asset.get('kind'), "content_type:", heic_asset.get('content_type'))
    assert heic_asset['content_type'] == 'image/jpeg', "Master content_type should be image/jpeg"
    assert heic_asset['stage_url'], "Asset should include stage_url"
    assert heic_asset['zoom_url'], "Asset should include zoom_url"

    # 3. Upload iPhone MOV video via API
    upload_mov_res = b.js(f"""(async () => {{
        const formData = new FormData();
        const blob = new Blob([new Uint8Array({list(sample_mov_path.read_bytes())})], {{ type: 'video/quicktime' }});
        formData.append('file', blob, 'iphone_16_pro_sample.mov');
        const res = await fetch('/api/v1/admin/media', {{
            method: 'POST',
            headers: {{ 'X-CSRF-Token': '{csrf_token}', 'Origin': 'http://localhost:13000' }},
            body: formData
        }});
        return {{ ok: res.ok, status: res.status, data: await res.json() }};
    }})()""")
    print("MOV Upload response:", upload_mov_res.get('status'), upload_mov_res.get('ok'))
    assert upload_mov_res.get('ok'), f"MOV upload failed: {upload_mov_res}"
    mov_asset = upload_mov_res['data']
    print("MOV Asset:", mov_asset.get('id'), "kind:", mov_asset.get('kind'), "content_type:", mov_asset.get('content_type'), "poster_id:", mov_asset.get('poster_id'))
    assert mov_asset['content_type'] == 'video/mp4', "Master content_type should be normalized to video/mp4"
    assert mov_asset['poster_id'], "MOV video should have auto-extracted poster_id"

    # 4. Navigate to Admin Media Library tab
    b.js("""(() => {
        const tab = document.querySelector('button.admin-tab-btn[data-tab="media"]');
        if (tab) tab.click();
    })()""")
    time.sleep(2)
    b.wait_for_selector('.media-control-bar', timeout=10)

    # Verify zero scrollbars & horizontal scroll on desktop
    metrics_desktop = b.js("""(() => {
        return {
            windowWidth: window.innerWidth,
            docWidth: document.documentElement.clientWidth,
            hasHorizScroll: document.documentElement.scrollWidth > window.innerWidth,
            assetCardsCount: document.querySelectorAll('.media-asset-card, .media-thumb-box').length
        };
    })()""")
    print("Admin Media Desktop metrics:", metrics_desktop)
    assert not metrics_desktop['hasHorizScroll'], "Desktop admin media must not horizontally overflow"
    save_and_copy(b, 'verified_admin_media_library_desktop.png')

    # 5. Mobile Viewport (390x844)
    print("Switching to Mobile 390px viewport...", flush=True)
    b.set_viewport(390, 844)
    time.sleep(1.5)
    metrics_mobile = b.js("""(() => {
        return {
            windowWidth: window.innerWidth,
            docWidth: document.documentElement.clientWidth,
            hasHorizScroll: document.documentElement.scrollWidth > window.innerWidth
        };
    })()""")
    print("Admin Media Mobile metrics:", metrics_mobile)
    assert not metrics_mobile['hasHorizScroll'], "Mobile admin media must not horizontally overflow"
    save_and_copy(b, 'verified_admin_media_library_mobile.png')

    # 6. Storefront Product Page Gallery and Lightbox Zoom Verification
    print("6. Verifying Storefront Product Page Stage and Lightbox Zoom...", flush=True)
    b.set_viewport(1440, 900)
    # Navigate to first published product
    prod_slug = b.js("""(async () => {
        try {
            const res = await fetch('/api/v1/products');
            const data = await res.json();
            return (data.products && data.products[0]) ? data.products[0].slug : null;
        } catch { return null; }
    })()""")
    print("Found product slug:", prod_slug)
    if prod_slug:
        b.goto(f'http://localhost:13000/products/{prod_slug}')
    else:
        b.goto('http://localhost:13000/products')
    
    b.wait_for_selector('.product-gallery-media-wrapper img, .product-gallery-media-wrapper video', timeout=15)
    time.sleep(1)

    # Check gallery stage image src
    stage_metrics = b.js("""(() => {
        const img = document.querySelector('.product-gallery-img');
        return {
            exists: !!img,
            src: img ? img.src : null,
            hasStageVariant: img ? img.src.includes('variant=stage') : false,
            srcset: img ? img.srcset : null
        };
    })()""")
    print("Stage image metrics:", stage_metrics)
    assert stage_metrics['exists'], "Gallery stage image should exist"
    assert stage_metrics['hasStageVariant'], "Gallery stage image should request variant=stage"

    save_and_copy(b, 'verified_storefront_product_stage_desktop.png')

    # Open Lightbox Zoom
    b.js("""(() => {
        const zoomBtn = document.querySelector('#gallery-zoom-btn, .gallery-zoom-btn');
        if (zoomBtn) zoomBtn.click();
        else {
            const img = document.querySelector('.product-gallery-img');
            if (img) img.click();
        }
    })()""")
    time.sleep(1)

    lightbox_metrics = b.js("""(() => {
        const lb = document.querySelector('#gallery-lightbox, .gallery-lightbox');
        const lbImg = document.querySelector('.gallery-lightbox-img');
        return {
            isOpen: !!lb,
            imgSrc: lbImg ? lbImg.src : null,
            hasZoomVariant: lbImg ? lbImg.src.includes('variant=zoom') : false
        };
    })()""")
    print("Lightbox zoom metrics:", lightbox_metrics)
    assert lightbox_metrics['isOpen'], "Lightbox should open on zoom click"
    assert lightbox_metrics['hasZoomVariant'], "Lightbox image should request variant=zoom"

    save_and_copy(b, 'verified_storefront_product_lightbox_zoom_desktop.png')

    # Close Lightbox
    b.js("""(() => {
        const closeBtn = document.querySelector('#gallery-lightbox-close');
        if (closeBtn) closeBtn.click();
    })()""")
    time.sleep(0.5)

    # Check mobile product gallery at 390px
    b.set_viewport(390, 844)
    time.sleep(1)
    prod_mobile_metrics = b.js("""(() => {
        return {
            windowWidth: window.innerWidth,
            docWidth: document.documentElement.clientWidth,
            hasHorizScroll: document.documentElement.scrollWidth > window.innerWidth
        };
    })()""")
    print("Product page mobile metrics:", prod_mobile_metrics)
    assert not prod_mobile_metrics['hasHorizScroll'], "Product page on mobile must have zero horizontal scroll"
    save_and_copy(b, 'verified_storefront_product_stage_mobile.png')

    print("=== ALL IPHONE MEDIA PIPELINE BROWSER CHECKS PASSED SUCCESSFULLY ===", flush=True)
