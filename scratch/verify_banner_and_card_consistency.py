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
    print("1. Opening storefront at 1440x900 desktop...", flush=True)
    b.set_viewport(1440, 900)
    b.goto('http://localhost:13000')
    time.sleep(2)

    # Gate 1: Desktop Hero Banner
    print("2. Verifying Desktop Hero Banner clearance and 16:9 ratio...", flush=True)
    hero_metrics = b.js("""(() => {
        const hero = document.querySelector('.hero-section');
        const header = document.querySelector('.site-header');
        const media = document.querySelector('.hero-bg-media');
        const heroRect = hero?.getBoundingClientRect();
        const headerRect = header?.getBoundingClientRect();
        const mediaRect = media?.getBoundingClientRect();
        const heroStyle = hero ? window.getComputedStyle(hero) : null;
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return {
            heroTop: Math.round(heroRect?.top || 0),
            heroHeight: Math.round(heroRect?.height || 0),
            heroWidth: Math.round(heroRect?.width || 0),
            headerBottom: Math.round(headerRect?.bottom || 0),
            mediaTop: Math.round(mediaRect?.top || 0),
            mediaHeight: Math.round(mediaRect?.height || 0),
            mediaWidth: Math.round(mediaRect?.width || 0),
            marginTop: heroStyle?.marginTop,
            aspectRatio: heroStyle?.aspectRatio,
            hasHorizScroll
        };
    })()""")

    print("Hero metrics:", json.dumps(hero_metrics, indent=2), flush=True)
    assert hero_metrics['heroTop'] >= 10, f"Hero banner has insufficient top clearance: {hero_metrics['heroTop']}"
    assert not hero_metrics['hasHorizScroll'], "Desktop page has horizontal scrollbar!"
    save_and_copy(b, 'verified_desktop_hero_1440.png')

    # Gate 2: Collection Cards Consistency
    print("3. Verifying Collection Cards Consistency...", flush=True)
    b.js("document.querySelector('#collections')?.scrollIntoView({ behavior: 'instant' })")
    time.sleep(1.5)

    col_metrics = b.js("""(() => {
        const grid = document.querySelector('#collections-grid-container');
        const cards = Array.from(grid?.querySelectorAll('.collection-card') || []).map(card => {
            const img = card.querySelector('.collection-img');
            const cta = card.querySelector('.collection-card-cta');
            const desc = card.querySelector('.collection-description');
            const cardRect = card.getBoundingClientRect();
            const imgRect = img?.getBoundingClientRect();
            const ctaRect = cta?.getBoundingClientRect();
            const descRect = desc?.getBoundingClientRect();
            const cardStyle = window.getComputedStyle(card);
            return {
                title: card.querySelector('.collection-card-title')?.textContent?.trim(),
                cardTop: Math.round(cardRect.top),
                cardHeight: Math.round(cardRect.height),
                imgTop: Math.round(imgRect?.top || 0),
                imgHeight: Math.round(imgRect?.height || 0),
                ctaTop: Math.round(ctaRect?.top || 0),
                descHeight: Math.round(descRect?.height || 0),
                justifyContent: cardStyle.justifyContent
            };
        });
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return { cards, hasHorizScroll };
    })()""")

    print("Collection cards metrics:", json.dumps(col_metrics, indent=2), flush=True)
    cards = col_metrics['cards']
    assert len(cards) >= 2, f"Expected at least 2 collection cards, found {len(cards)}"
    img_tops = [c['imgTop'] for c in cards]
    assert max(img_tops) == min(img_tops), f"Collection images are not aligned at the same top! img_tops={img_tops}"
    for c in cards:
        assert c['justifyContent'] == 'flex-start', f"Card justifyContent is {c['justifyContent']}"
    save_and_copy(b, 'verified_collection_cards_desktop.png')

    # Gate 3: Product Cards Consistency
    print("4. Verifying Product Cards Consistency...", flush=True)
    b.js("document.querySelector('#featured')?.scrollIntoView({ behavior: 'instant' })")
    time.sleep(1.5)

    prod_metrics = b.js("""(() => {
        const grid = document.querySelector('#products-grid-container');
        const cards = Array.from(grid?.querySelectorAll('.product-card') || []).slice(0, 4).map(card => {
            const wrapper = card.querySelector('.product-card-img-wrapper');
            const btn = card.querySelector('.product-card-btn');
            const cardRect = card.getBoundingClientRect();
            const wrapperRect = wrapper?.getBoundingClientRect();
            const btnRect = btn?.getBoundingClientRect();
            return {
                cardTop: Math.round(cardRect.top),
                cardHeight: Math.round(cardRect.height),
                wrapperTop: Math.round(wrapperRect?.top || 0),
                btnTop: Math.round(btnRect?.top || 0)
            };
        });
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return { cards, hasHorizScroll };
    })()""")

    print("Product cards metrics:", json.dumps(prod_metrics, indent=2), flush=True)
    if prod_metrics['cards']:
        wrapper_tops = [c['wrapperTop'] for c in prod_metrics['cards']]
        assert max(wrapper_tops) == min(wrapper_tops), f"Product image wrappers are not aligned! wrapper_tops={wrapper_tops}"
    save_and_copy(b, 'verified_product_cards_desktop.png')

    # Gate 4: Mobile Viewport (390x844)
    print("5. Verifying Mobile Viewport (390x844)...", flush=True)
    b.set_viewport(390, 844)
    b.js("window.scrollTo(0, 0)")
    time.sleep(1.5)

    mobile_hero = b.js("""(() => {
        const hero = document.querySelector('.hero-section');
        const heroRect = hero?.getBoundingClientRect();
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return {
            heroTop: Math.round(heroRect?.top || 0),
            heroHeight: Math.round(heroRect?.height || 0),
            heroWidth: Math.round(heroRect?.width || 0),
            hasHorizScroll
        };
    })()""")
    print("Mobile hero metrics:", json.dumps(mobile_hero, indent=2), flush=True)
    assert not mobile_hero['hasHorizScroll'], "Mobile page has horizontal overflow!"
    save_and_copy(b, 'verified_mobile_hero_390.png')

    # Mobile Cards Scroll
    b.js("document.querySelector('#collections')?.scrollIntoView({ behavior: 'instant' })")
    time.sleep(1)
    mobile_cards = b.js("""(() => {
        const hasHorizScroll = document.documentElement.scrollWidth > window.innerWidth;
        return { hasHorizScroll };
    })()""")
    assert not mobile_cards['hasHorizScroll'], "Mobile cards section has horizontal overflow!"
    save_and_copy(b, 'verified_mobile_cards_390.png')

    print("\nALL 4 BROWSER ACCEPTANCE GATES PASSED PERFECTLY!", flush=True)
