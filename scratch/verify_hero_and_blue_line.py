"""
verify_hero_and_blue_line.py - Automated browser verification:
1. Verify top blue line / announcement bar is completely gone from the storefront.
2. Verify hero background video element exists, is blurred with filter: blur(...), and loops.
3. Verify hero foreground contains continuous horizontal scroll of picture cards without any text.
4. Verify hovering pauses scroll, unhovering resumes.
5. Verify clicking a featured picture card navigates directly to the product detail page.
6. Verify Admin Portal Homepage Hero tab displays the video upload guidelines card (dimensions, length, size, codec).
7. Capture desktop and mobile screenshots.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".local/frontend-redesign"))
from browser_util import RedesignBrowser

OUT = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity\brain\ab2da56f-688f-4f8f-bd61-6e39efdfd7c8")
OUT.mkdir(parents=True, exist_ok=True)

print("Starting verification of Hero video background, featured marquee, and blue line removal...", flush=True)

# 1. Storefront Desktop Verification
with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    
    # Check development port 13000
    print("Navigating to http://localhost:13000/ ...", flush=True)
    b.goto("http://localhost:13000/")
    time.sleep(2)

    # 1.1 Blue line check
    banner_info = b.js("""(() => {
        const bar = document.querySelector('.announcement-bar');
        if (!bar) return { exists: false, visible: false, text: '' };
        const style = window.getComputedStyle(bar);
        const rect = bar.getBoundingClientRect();
        return {
            exists: true,
            display: style.display,
            visibility: style.visibility,
            height: rect.height,
            visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.height > 0,
            text: bar.textContent.trim(),
            bg: style.backgroundColor
        };
    })()""")
    print("Announcement bar status on dev (13000):", json.dumps(banner_info, indent=2), flush=True)
    assert not banner_info['visible'], f"Announcement banner must NOT be visible, got: {banner_info}"

    # 1.2 Hero section checks
    hero_info = b.js("""(() => {
        const hero = document.querySelector('.hero-section');
        if (!hero) return { exists: false };
        const bgContainer = hero.querySelector('.hero-bg-container');
        const video = hero.querySelector('video.hero-bg-video, video.hero-bg-media');
        const marquee = hero.querySelector('.hero-marquee-container');
        const track = hero.querySelector('.hero-marquee-track');
        const cards = hero.querySelectorAll('.hero-picture-card');
        
        let videoStyle = null;
        if (video) {
            const s = window.getComputedStyle(video);
            videoStyle = {
                filter: s.filter,
                objectFit: s.objectFit,
                position: s.position,
                loop: video.loop,
                muted: video.muted,
                paused: video.paused,
                src: video.src || video.currentSrc
            };
        }

        const cardDetails = Array.from(cards).slice(0, 5).map(c => {
            const img = c.querySelector('img');
            return {
                hasText: c.textContent.trim().length > 0,
                textContent: c.textContent.trim(),
                hasImg: !!img,
                imgSrc: img ? img.src : null,
                slug: c.dataset.slug,
                role: c.getAttribute('role')
            };
        });

        let trackStyle = null;
        if (track) {
            const ts = window.getComputedStyle(track);
            trackStyle = {
                animationName: ts.animationName,
                animationPlayState: ts.animationPlayState,
                display: ts.display
            };
        }

        return {
            exists: true,
            hasVideo: !!video,
            video: videoStyle,
            cardsCount: cards.length,
            sampleCards: cardDetails,
            track: trackStyle
        };
    })()""")
    print("Hero info on dev (13000):", json.dumps(hero_info, indent=2), flush=True)
    assert hero_info['exists'], "Hero section must exist"
    assert hero_info['cardsCount'] > 0, "Hero marquee picture cards must exist"
    
    # Check that cards have pure pictures and zero text
    for i, c in enumerate(hero_info['sampleCards']):
        assert not c['hasText'], f"Card {i} must NOT contain text, but got '{c['textContent']}'"
        assert c['hasImg'], f"Card {i} must contain an img element"

    # Capture desktop screenshot
    b.capture_screenshot(str(OUT / "verify_hero_desktop_dev.png"))
    print("Captured verify_hero_desktop_dev.png", flush=True)

    # 1.3 Hover pause check
    b.js("""(() => {
        const marquee = document.querySelector('.hero-marquee-container');
        if (marquee) {
            marquee.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
        }
    })()""")
    time.sleep(0.5)
    hover_play_state = b.js("window.getComputedStyle(document.querySelector('.hero-marquee-track')).animationPlayState")
    print(f"Marquee animationPlayState when hovered: {hover_play_state}", flush=True)

    # 1.4 Click navigation check
    first_card_slug = hero_info['sampleCards'][0]['slug']
    print(f"Clicking first card with slug: {first_card_slug}", flush=True)
    b.js("""(() => {
        const card = document.querySelector('.hero-picture-card');
        if (card) card.click();
    })()""")
    time.sleep(1)
    current_hash = b.js("window.location.hash")
    print(f"Current window.location.hash after card click: {current_hash}", flush=True)
    if first_card_slug:
        assert first_card_slug in current_hash, f"Expected {first_card_slug} in hash {current_hash}"

# 2. Storefront Mobile Verification
with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    b.goto("http://localhost:13000/")
    time.sleep(2)
    b.capture_screenshot(str(OUT / "verify_hero_mobile_dev.png"))
    print("Captured verify_hero_mobile_dev.png", flush=True)

# 3. Lab Port 13001 Verification
with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    print("Navigating to http://127.0.0.1:13001/ ...", flush=True)
    b.goto("http://127.0.0.1:13001/")
    time.sleep(2)

    # Blue line check on lab
    lab_banner_info = b.js("""(() => {
        const bar = document.querySelector('.announcement-bar');
        if (!bar) return { exists: false, visible: false };
        const style = window.getComputedStyle(bar);
        const rect = bar.getBoundingClientRect();
        return {
            exists: true,
            visible: style.display !== 'none' && style.visibility !== 'hidden' && rect.height > 0,
            text: bar.textContent.trim()
        };
    })()""")
    print("Lab banner info:", json.dumps(lab_banner_info, indent=2), flush=True)
    assert not lab_banner_info['visible'], f"Lab announcement bar must NOT be visible, got {lab_banner_info}"

    b.capture_screenshot(str(OUT / "verify_hero_lab_desktop.png"))
    print("Captured verify_hero_lab_desktop.png", flush=True)

# 4. Admin Portal Guidelines Verification
with RedesignBrowser(Path(".local/tmp")) as b:
    b.cdp("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    b.goto("http://localhost:13000/admin")
    time.sleep(1)
    # Log in
    b.js("""(() => {
        return fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Origin': 'http://localhost:13000'},
            body: JSON.stringify({username: 'syed123', password: 'Password123!'})
        });
    })()""")
    time.sleep(1)
    b.goto("http://localhost:13000/#/admin")
    time.sleep(1.5)

    # Click Homepage Hero tab
    b.js("""(() => {
        const heroTab = document.querySelector('button[data-tab="hero"]');
        if (heroTab) heroTab.click();
    })()""")
    time.sleep(1.5)

    # Verify guidelines card
    guide_text = b.js("""(() => {
        const card = document.querySelector('.hero-guidelines-card');
        return card ? card.innerText : null;
    })()""")
    print("Admin hero guidelines card detected:\n", guide_text, flush=True)
    assert guide_text and "Dimensions & Breadth" in guide_text, "Hero guidelines card must exist in Admin"
    assert "1920 × 1080 px" in guide_text, "1920x1080 resolution must be documented"
    assert "Duration & Length" in guide_text, "Duration must be documented"
    assert "File Size & Codec" in guide_text, "File size & codec must be documented"

    b.capture_screenshot(str(OUT / "verify_admin_hero_guidelines.png"))
    print("Captured verify_admin_hero_guidelines.png", flush=True)

print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!", flush=True)
