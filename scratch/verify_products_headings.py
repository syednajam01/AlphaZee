import sys, time, shutil, json
from pathlib import Path

ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT / '.local/frontend-redesign'))
from browser_util import RedesignBrowser

OUT_DIR = ROOT / 'scratch'
ARTIFACT_DIR = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\e0e456e1-e4cb-4fd8-a8d5-475bb70698e3")

def save_and_copy(b, filename):
    local_path = OUT_DIR / filename
    b.capture_screenshot(str(local_path))
    if ARTIFACT_DIR.exists():
        shutil.copy2(local_path, ARTIFACT_DIR / filename)
    print(f"Captured & copied: {filename}", flush=True)

with RedesignBrowser(ROOT / '.local/tmp') as b:
    print("1. Opening browser and authenticating as admin...", flush=True)
    b.set_viewport(1440, 900)
    b.goto('http://localhost:13000/admin')
    time.sleep(1)

    # Login
    b.js("""(async () => {
        await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Origin': 'http://localhost:13000'},
            body: JSON.stringify({username: 'owner_vf7_b71d91e8', password: 'OwnerPass123_b71d91e8'})
        });
    })()""")
    time.sleep(1)

    # Direct navigation to Products workspace
    print("2. Navigating to /admin/products...", flush=True)
    b.goto('http://localhost:13000/admin/products')
    time.sleep(2)

    # Verify Products workspace loaded with headings toggle
    has_toggle = False
    for _ in range(15):
        if b.js("!!document.querySelector('#btn-toggle-prod-headings')"):
            has_toggle = True
            break
        time.sleep(0.5)

    print(f"Has Products Page Headings toggle button: {has_toggle}", flush=True)
    assert has_toggle, "Page Headings toggle button #btn-toggle-prod-headings not found!"

    # Click toggle button to open headings studio
    print("3. Opening Storefront Page Headings studio...", flush=True)
    b.js("document.querySelector('#btn-toggle-prod-headings')?.click()")
    time.sleep(1.5)

    studio_rendered = b.js("!!document.querySelector('#prod-headings-studio')")
    print(f"Studio card rendered: {studio_rendered}", flush=True)
    assert studio_rendered, "Studio card #prod-headings-studio did not render!"

    # Update title and subtitle
    print("4. Editing title and subtitle with live preview verification...", flush=True)
    b.js("""(() => {
        const titleInput = document.querySelector('#input-prod-headings-title');
        const subtitleInput = document.querySelector('#input-prod-headings-subtitle');
        if (titleInput) {
            titleInput.value = 'Signature Wardrobe';
            titleInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (subtitleInput) {
            subtitleInput.value = 'Curated essentials engineered with timeless cuts and everyday luxury.';
            subtitleInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
    })()""")
    time.sleep(1)

    # Check live preview
    preview_data = b.js("""(() => {
        return {
            title: document.querySelector('#preview-prod-title')?.textContent?.trim(),
            subtitle: document.querySelector('#preview-prod-subtitle')?.textContent?.trim(),
            counterTitle: document.querySelector('#prod-title-counter')?.textContent?.trim(),
            counterSub: document.querySelector('#prod-subtitle-counter')?.textContent?.trim()
        };
    })()""")
    print("Live preview data:", preview_data, flush=True)
    assert preview_data['title'] == 'Signature Wardrobe', f"Title mismatch: {preview_data}"
    assert 'timeless cuts' in preview_data['subtitle'], f"Subtitle mismatch: {preview_data}"

    # Click Save Headings
    print("5. Clicking Save Headings...", flush=True)
    b.js("document.querySelector('#btn-save-prod-headings')?.click()")
    time.sleep(2.5)

    alert_text = b.js("document.querySelector('#prod-headings-alert')?.textContent")
    print("Save alert message:", alert_text, flush=True)

    # Check desktop overflow
    desktop_overflow = b.js("document.documentElement.scrollWidth > window.innerWidth")
    print("Admin desktop horizontal overflow:", desktop_overflow, flush=True)
    assert not desktop_overflow
    save_and_copy(b, 'admin_products_headings_desktop.png')

    # Mobile Admin Check
    print("6. Checking Admin on Mobile (390x844)...", flush=True)
    b.set_viewport(390, 844)
    time.sleep(1)
    mobile_overflow = b.js("document.documentElement.scrollWidth > window.innerWidth")
    print("Admin mobile horizontal overflow:", mobile_overflow, flush=True)
    assert not mobile_overflow
    save_and_copy(b, 'admin_products_headings_mobile.png')

    # Storefront Catalog Desktop Check
    print("7. Navigating to Storefront Catalog (/products) on Desktop...", flush=True)
    b.set_viewport(1440, 900)
    b.goto('http://localhost:13000/products')
    time.sleep(2)

    # Poll until hydrated with custom title
    for _ in range(20):
        t = b.js("document.querySelector('h1.section-title')?.textContent?.trim()")
        if t == 'Signature Wardrobe':
            break
        time.sleep(0.5)

    storefront_desktop = b.js("""(() => {
        const h1 = document.querySelector('h1.section-title')?.textContent?.trim() || '';
        const p = document.querySelector('.section-subtitle')?.textContent?.trim() || '';
        const crumb = document.querySelector('.product-breadcrumb-current')?.textContent?.trim() || '';
        const title = document.title;
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return { h1, p, crumb, title, hasHorizScroll };
    })()""")

    print("Storefront desktop data:", json.dumps(storefront_desktop, indent=2), flush=True)
    assert storefront_desktop['h1'] == 'Signature Wardrobe', f"Storefront H1 mismatch: {storefront_desktop}"
    assert 'timeless cuts' in storefront_desktop['p'], f"Storefront subtitle mismatch: {storefront_desktop}"
    assert storefront_desktop['crumb'] == 'Signature Wardrobe', f"Storefront breadcrumb mismatch: {storefront_desktop}"
    assert 'Signature Wardrobe' in storefront_desktop['title'], f"Storefront doc title mismatch: {storefront_desktop}"
    assert not storefront_desktop['hasHorizScroll'], "Storefront desktop has horizontal overflow!"
    save_and_copy(b, 'storefront_products_headings_desktop.png')

    # Storefront Catalog Mobile Check
    print("8. Checking Storefront Catalog on Mobile (390x844)...", flush=True)
    b.set_viewport(390, 844)
    time.sleep(1.5)

    for _ in range(15):
        t = b.js("document.querySelector('h1.section-title')?.textContent?.trim()")
        if t == 'Signature Wardrobe':
            break
        time.sleep(0.5)

    storefront_mobile = b.js("""(() => {
        const h1 = document.querySelector('h1.section-title')?.textContent?.trim() || '';
        const p = document.querySelector('.section-subtitle')?.textContent?.trim() || '';
        const crumb = document.querySelector('.product-breadcrumb-current')?.textContent?.trim() || '';
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return { h1, p, crumb, hasHorizScroll };
    })()""")
    print("Storefront mobile data:", json.dumps(storefront_mobile, indent=2), flush=True)
    assert storefront_mobile['h1'] == 'Signature Wardrobe', f"Storefront mobile H1 mismatch: {storefront_mobile}"
    assert not storefront_mobile['hasHorizScroll'], "Storefront mobile has horizontal overflow!"
    save_and_copy(b, 'storefront_products_headings_mobile.png')

    print("\nALL 4 BROWSER ACCEPTANCE GATES PASSED PERFECTLY!", flush=True)
