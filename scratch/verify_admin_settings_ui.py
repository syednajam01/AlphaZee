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
    print("1. Opening /admin on 1440x950 desktop...", flush=True)
    b.set_viewport(1440, 950)
    b.goto('http://localhost:13000/admin')
    time.sleep(2)

    # 1. Login
    print("2. Authenticating as owner...", flush=True)
    login_res = b.js("""(async () => {
        try {
            const res = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Origin': 'http://localhost:13000'},
                body: JSON.stringify({username: 'owner_vf7_b71d91e8', password: 'OwnerPass123_b71d91e8'})
            });
            return { status: res.status, data: await res.json() };
        } catch (e) {
            return { error: String(e) };
        }
    })()""")
    print("Login status:", login_res.get('status'))

    b.goto('http://localhost:13000/admin')
    time.sleep(2)

    # Click Store Settings in sidebar nav
    print("3. Navigating to Store Settings...", flush=True)
    b.js("""(() => {
        const btn = Array.from(document.querySelectorAll('button, a')).find(el => el.textContent.includes('Store Settings') || el.dataset?.tab === 'settings');
        if (btn) btn.click();
    })()""")
    time.sleep(2)

    # Wait for Store Settings container
    b.wait_for_selector('#form-storefront-settings', timeout=10)
    print("4. Storefront settings form loaded.")

    res_sf = b.js("""(() => {
        const hpColTitle = document.querySelector('#input-hp-col-title')?.value;
        const hpColSub = document.querySelector('#input-hp-col-subtitle')?.value;
        const hpProdTitle = document.querySelector('#input-hp-prod-title')?.value;
        const hpProdSub = document.querySelector('#input-hp-prod-subtitle')?.value;
        const btnSave = document.querySelector('#btn-save-hp-headings');
        const mockupCol = document.querySelector('#mockup-hp-col-title')?.textContent;
        return {
            hpColTitle, hpColSub,
            hpProdTitle, hpProdSub,
            btnSavePresent: !!btnSave,
            mockupCol
        };
    })()""")
    print("Storefront Tab Checks:", json.dumps(res_sf, indent=2))
    assert res_sf['btnSavePresent'], "Save button missing on Storefront Headings card!"
    assert res_sf['hpColTitle'] == 'Shop by collection', f"Unexpected hpColTitle: {res_sf['hpColTitle']}"
    save_and_copy(b, "verified_admin_settings_storefront_headings_desktop.png")

    # Switch to FAQ & Support tab
    print("5. Switching to FAQ & Support tab...", flush=True)
    b.js("""(() => {
        const faqTab = Array.from(document.querySelectorAll('.settings-tab-btn, [data-tab="faq"]')).find(el => el.dataset?.tab === 'faq' || el.textContent.includes('FAQ'));
        if (faqTab) faqTab.click();
    })()""")
    time.sleep(2)

    b.wait_for_selector('#input-faq-section-title', timeout=10)
    res_faq = b.js("""(() => {
        const faqTitle = document.querySelector('#input-faq-section-title')?.value;
        const faqSub = document.querySelector('#input-faq-section-subtitle')?.value;
        const btnSave = document.querySelector('#btn-save-faq-headings');
        const mockupFaq = document.querySelector('#mockup-faq-title')?.textContent;
        return {
            faqTitle, faqSub,
            btnSavePresent: !!btnSave,
            mockupFaq
        };
    })()""")
    print("FAQ Tab Checks:", json.dumps(res_faq, indent=2))
    assert res_faq['btnSavePresent'], "Save button missing on FAQ Headings card!"
    assert res_faq['faqTitle'] == 'Before you order', f"Unexpected faqTitle: {res_faq['faqTitle']}"
    save_and_copy(b, "verified_admin_settings_faq_headings_desktop.png")

    # Mobile Viewport 390x844 on FAQ tab
    print("6. Capturing mobile view 390x844 on FAQ tab...", flush=True)
    b.set_viewport(390, 844)
    time.sleep(1)
    save_and_copy(b, "verified_admin_settings_faq_headings_mobile.png")

print("Admin console UI verification complete and certified!", flush=True)
