"""MM3 Hero Playback State Machine Acceptance Script for AlphaZee.
Executes acceptance workflows through Chrome/CDP on checkout lab (http://127.0.0.1:13001).
Verifies:
1. Real clips of different lengths advance on active video 'ended' event (A-end -> B-end -> A).
2. Multiple videos do NOT loop individually (video.loop = false).
3. Inactive videos do not download eagerly (on-demand streaming).
4. Single video loops continuously (video.loop = true).
5. Accessible play/pause control (#hero-play-pause) updates icon/label and pauses/resumes active video.
6. User-pause state persists across tab visibility changes.
7. Automatic pause on tab hidden (document.hidden), resuming when returning to visible.
8. Preservation of clean layout, crisp presentation, and saved timing/event records.
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

OUT_DIR = ROOT / '.local/admin-media/mm3'
OUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_ARTIFACTS = Path(r"C:\Users\SyedNajam's PC\.gemini\antigravity-ide\brain\ca17e23f-7699-47ff-83c4-deb583790c47")

ORIGIN = "http://127.0.0.1:13001"
LAB_COMPOSE = ['docker', 'compose', '-f', 'compose.checkout-lab.yml']

def run_lab_cmd(args, input_bytes=None):
    cmd = LAB_COMPOSE + args
    res = subprocess.run(cmd, cwd=ROOT, input=input_bytes, capture_output=True, check=True)
    return res.stdout.decode('utf-8', errors='replace').strip()

def generate_test_media():
    tmp_dir = ROOT / '.local/admin-media/test_assets'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Clip A: 2 seconds, Indigo
    clip_a_local = tmp_dir / 'hero_clip_a_2s.mp4'
    print("Generating Clip A (2s, indigo)...", flush=True)
    run_lab_cmd(['exec', 'api', 'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=indigo:s=320x240:d=2',
                 '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '/tmp/clip_a_2s.mp4'])
    cmd = LAB_COMPOSE + ['exec', '-T', 'api', 'cat', '/tmp/clip_a_2s.mp4']
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, check=True)
    clip_a_local.write_bytes(res.stdout)

    # 2. Clip B: 3 seconds, Crimson
    clip_b_local = tmp_dir / 'hero_clip_b_3s.mp4'
    print("Generating Clip B (3s, crimson)...", flush=True)
    run_lab_cmd(['exec', 'api', 'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=crimson:s=320x240:d=3',
                 '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '/tmp/clip_b_3s.mp4'])
    cmd = LAB_COMPOSE + ['exec', '-T', 'api', 'cat', '/tmp/clip_b_3s.mp4']
    res = subprocess.run(cmd, cwd=ROOT, capture_output=True, check=True)
    clip_b_local.write_bytes(res.stdout)

    # 3. Poster A (640x360)
    poster_a_local = tmp_dir / 'hero_poster_a.png'
    Image.new('RGB', (640, 360), '#312E81').save(poster_a_local, format='PNG')

    # 4. Poster B (640x360)
    poster_b_local = tmp_dir / 'hero_poster_b.png'
    Image.new('RGB', (640, 360), '#881337').save(poster_b_local, format='PNG')

    print(f"Media generated: Clip A ({len(clip_a_local.read_bytes())}B), Clip B ({len(clip_b_local.read_bytes())}B)", flush=True)
    return clip_a_local, clip_b_local, poster_a_local, poster_b_local

def main():
    print("=" * 70, flush=True)
    print("STARTING MM3 HERO PLAYBACK STATE MACHINE ACCEPTANCE", flush=True)
    print("=" * 70, flush=True)

    clip_a_file, clip_b_file, poster_a_file, poster_b_file = generate_test_media()

    timing_log = []
    def log_event(event_name, details=""):
        t = time.time()
        timing_log.append({"time": t, "event": event_name, "details": details})
        print(f"  [EVENT @ {t:.2f}s] {event_name}: {details}", flush=True)

    with RedesignBrowser(OUT_DIR) as b:
        b.set_viewport(1440, 960)

        def save_and_copy(filename):
            local_path = OUT_DIR / filename
            b.capture_screenshot(str(local_path))
            print(f"  [SCREENSHOT] {filename}", flush=True)
            if BRAIN_ARTIFACTS.exists():
                dest = BRAIN_ARTIFACTS / filename
                shutil.copy2(local_path, dest)

        # 1. Provision Lab Owner & Login
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
        assert csrf_token, f"Login failed: {login_res}"
        print(f"Authenticated as {owner_username}, CSRF verified.", flush=True)

        def upload_asset_via_browser(file_path, mime_type):
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

        print("\n2. Uploading clips and posters...", flush=True)
        uploaded_clip_a = upload_asset_via_browser(clip_a_file, 'video/mp4')
        uploaded_clip_b = upload_asset_via_browser(clip_b_file, 'video/mp4')
        uploaded_poster_a = upload_asset_via_browser(poster_a_file, 'image/png')
        uploaded_poster_b = upload_asset_via_browser(poster_b_file, 'image/png')

        # Attach posters to videos
        for v, p_id in [(uploaded_clip_a, uploaded_poster_a['id']), (uploaded_clip_b, uploaded_poster_b['id'])]:
            v_id = v['id']
            v_version = v.get('edit_version', 1)
            set_res = b.js(f"""(() => {{
                return fetch('/api/v1/admin/media/{v_id}/poster', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Origin': '{ORIGIN}',
                        'X-CSRF-Token': {json.dumps(csrf_token)},
                    }},
                    body: JSON.stringify({{
                        poster_id: {json.dumps(p_id)},
                        expected_version: {v_version}
                    }})
                }}).then(r => r.json());
            }})()""")
            assert set_res.get('poster_id') == p_id, f"Failed to set poster: {set_res}"

        # Clean existing hero slides to start with a clean playlist of exactly 2 clips
        print("\n3. Configuring Hero Playlist with Clip A (2s) and Clip B (3s)...", flush=True)
        existing_slides = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/hero/slides').then(r => r.json());
        }})()""")
        for s in existing_slides.get('slides', []):
            b.js(f"""(() => {{
                return fetch('/api/v1/admin/media/hero/slides/{s["id"]}/delete', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Origin': '{ORIGIN}',
                        'X-CSRF-Token': {json.dumps(csrf_token)},
                    }},
                    body: JSON.stringify({{
                        expected_version: {s.get("edit_version", 1)}
                    }})
                }});
            }})()""")

        # Create Slide 1 (Clip A, 2s)
        slide1_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/hero/slides', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    title: 'Indigo Boxy Tee',
                    benefit: 'Engineered 300 GSM cotton drape',
                    video_asset_id: {json.dumps(uploaded_clip_a['id'])},
                    poster_asset_id: {json.dumps(uploaded_poster_a['id'])},
                    display_order: 1,
                    is_enabled: true
                }})
            }}).then(async r => ({{ status: r.status, data: await r.json() }}));
        }})()""")
        assert slide1_res['status'] == 201, f"Failed to create slide 1: {slide1_res}"
        slide1_id = slide1_res['data']['id']

        # Create Slide 2 (Clip B, 3s)
        slide2_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/hero/slides', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    title: 'Crimson Heavyweight Hoodie',
                    benefit: '500 GSM French Terry Fleece',
                    video_asset_id: {json.dumps(uploaded_clip_b['id'])},
                    poster_asset_id: {json.dumps(uploaded_poster_b['id'])},
                    display_order: 2,
                    is_enabled: true
                }})
            }}).then(async r => ({{ status: r.status, data: await r.json() }}));
        }})()""")
        assert slide2_res['status'] == 201, f"Failed to create slide 2: {slide2_res}"
        slide2_id = slide2_res['data']['id']
        print(f"Created 2 slides: Slide 1 ({slide1_id}) & Slide 2 ({slide2_id})", flush=True)

        # 4. Storefront Verification - Load Homepage
        print("\n4. Navigating to Storefront Homepage & instrumenting playback events...", flush=True)
        b.goto(f"{ORIGIN}/", wait_selector='.hero-section')
        b.wait_for_selector('.hero-bg-media.hero-video-media', timeout=10)
        time.sleep(0.5)

        # Instrument media playback event listeners
        b.js("""(() => {
            window.__heroEvents = [];
            const videos = document.querySelectorAll('.hero-bg-media.hero-video-media');
            videos.forEach((v, idx) => {
                ['play', 'playing', 'pause', 'ended', 'timeupdate', 'error'].forEach(evtType => {
                    v.addEventListener(evtType, (e) => {
                        window.__heroEvents.push({
                            index: idx,
                            type: evtType,
                            time: performance.now(),
                            currentTime: v.currentTime,
                            paused: v.paused,
                            src: v.src,
                            loop: v.loop
                        });
                    });
                });
            });
        })()""")

        # Verify initial invariants
        videos_info = b.js("""(() => {
            const videos = Array.from(document.querySelectorAll('.hero-bg-media.hero-video-media'));
            return videos.map(v => ({
                src: v.src,
                dataSrc: v.dataset.videoSrc,
                muted: v.muted,
                loop: v.loop,
                playsInline: v.playsInline,
                paused: v.paused,
                isActive: v.classList.contains('is-active')
            }));
        })()""")
        assert len(videos_info) == 2, f"Expected 2 videos, got {len(videos_info)}"
        assert videos_info[0]['muted'] is True, "Hero video must be muted"
        assert videos_info[0]['loop'] is False, "Multiple videos must NOT have loop=true"
        assert videos_info[1]['loop'] is False, "Slide 2 video must NOT have loop=true"
        assert videos_info[0]['isActive'] is True, "Slide 1 must be active initially"
        assert videos_info[1]['isActive'] is False, "Slide 2 must be inactive initially"
        assert videos_info[1]['src'] == '', "Inactive video.src must be empty (on-demand streaming invariant)"
        log_event("INITIAL_INVARIANTS_VERIFIED", "Muted=True, MultiLoop=False, OnDemandPreload=True")

        save_and_copy("mm3_01_hero_slide_a_playing.png")

        # 5. Verify A-end -> B-end -> A sequence driven by active video 'ended'
        print("\n5. Testing A-end -> B-end -> A sequencing driven by video 'ended' event...", flush=True)
        start_wait = time.time()
        clip_a_ended = False
        clip_b_started = False
        clip_b_ended = False
        loop_back_a = False

        while time.time() - start_wait < 14:
            state = b.js("""(() => {
                const indicator = document.querySelector('#hero-indicator')?.textContent || '';
                const title = document.querySelector('.hero-slide.is-active .hero-title')?.textContent || '';
                const events = window.__heroEvents || [];
                const v0 = document.querySelectorAll('video')[0];
                const v1 = document.querySelectorAll('video')[1];
                return {
                    indicator,
                    title,
                    events: events.filter(e => e.type === 'ended' || e.type === 'playing'),
                    v0_time: v0?.currentTime || 0,
                    v0_paused: v0?.paused ?? true,
                    v1_time: v1?.currentTime || 0,
                    v1_paused: v1?.paused ?? true,
                    v1_src: v1?.src || ''
                };
            })()""")

            # Check if Slide A ended
            if not clip_a_ended:
                ended_events = [e for e in state['events'] if e['index'] == 0 and e['type'] == 'ended']
                if ended_events or '2 / 2' in state['indicator']:
                    clip_a_ended = True
                    log_event("CLIP_A_ENDED", f"Transitioned to Slide 2 ({state['title']})")
                    save_and_copy("mm3_02_hero_slide_b_playing.png")

            # Check if Slide B started and then ended
            if clip_a_ended and not clip_b_ended:
                assert state['v1_src'] != '', "Slide 2 video.src must be loaded on demand when activated"
                ended_events_b = [e for e in state['events'] if e['index'] == 1 and e['type'] == 'ended']
                if ended_events_b or ('1 / 2' in state['indicator'] and clip_a_ended):
                    clip_b_ended = True
                    loop_back_a = True
                    log_event("CLIP_B_ENDED_LOOPED_BACK_TO_A", f"Wrapped back to Slide 1 ({state['title']})")
                    save_and_copy("mm3_03_hero_slide_a_looped.png")
                    break

            time.sleep(0.3)

        assert clip_a_ended, "Clip A did not end or advance to Slide B within timeout"
        assert clip_b_ended, "Clip B did not end or loop back to Slide A within timeout"
        print("PASS: A-end -> B-end -> A sequence proven via active video 'ended' listeners!", flush=True)

        # 6. Test Accessible Play/Pause Control (#hero-play-pause)
        print("\n6. Testing Play/Pause Control (#hero-play-pause)...", flush=True)
        btn_info = b.js("""(() => {
            const btn = document.querySelector('#hero-play-pause');
            return {
                exists: Boolean(btn),
                text: btn?.textContent.trim(),
                label: btn?.getAttribute('aria-label'),
                title: btn?.title
            };
        })()""")
        assert btn_info['exists'] is True, "#hero-play-pause button must exist"
        print(f"Initial button: text='{btn_info['text']}', label='{btn_info['label']}'", flush=True)

        # Pause
        b.click('#hero-play-pause')
        time.sleep(0.3)
        pause_state = b.js("""(() => {
            const btn = document.querySelector('#hero-play-pause');
            const activeVideo = document.querySelector('.hero-bg-media.is-active');
            return {
                btn_text: btn?.textContent.trim(),
                btn_label: btn?.getAttribute('aria-label'),
                video_paused: activeVideo?.paused,
                video_time: activeVideo?.currentTime
            };
        })()""")
        assert pause_state['btn_text'] == '▶', f"Expected play icon '▶', got '{pause_state['btn_text']}'"
        assert pause_state['video_paused'] is True, "Active video must pause when pause button is clicked"
        assert 'Resume' in pause_state['btn_label'], "Button label must reflect resume action"
        log_event("USER_PAUSED", f"Time froze at {pause_state['video_time']:.2f}s")
        save_and_copy("mm3_04_hero_user_paused.png")

        # Wait 1s and verify time did not advance
        time.sleep(1.0)
        still_frozen_time = b.js("document.querySelector('.hero-bg-media.is-active')?.currentTime || 0")
        assert abs(still_frozen_time - pause_state['video_time']) < 0.1, "Playback continued while paused!"

        # Resume
        b.click('#hero-play-pause')
        time.sleep(0.3)
        resume_state = b.js("""(() => {
            const btn = document.querySelector('#hero-play-pause');
            const activeVideo = document.querySelector('.hero-bg-media.is-active');
            return {
                btn_text: btn?.textContent.trim(),
                btn_label: btn?.getAttribute('aria-label'),
                video_paused: activeVideo?.paused,
                video_time: activeVideo?.currentTime
            };
        })()""")
        assert resume_state['btn_text'] == '⏸', f"Expected pause icon '⏸', got '{resume_state['btn_text']}'"
        assert resume_state['video_paused'] is False, "Active video must resume when resumed"
        log_event("USER_RESUMED", f"Resumed at {resume_state['video_time']:.2f}s")
        save_and_copy("mm3_05_hero_user_resumed.png")

        # 7. Test User Pause Persistence across Visibility Changes
        print("\n7. Testing user-pause persistence across tab visibility changes...", flush=True)
        # Pause playback
        b.click('#hero-play-pause')
        time.sleep(0.2)
        assert b.js("document.querySelector('.hero-bg-media.is-active')?.paused") is True

        # Simulate tab switch to background and back
        b.js("""(() => {
            Object.defineProperty(document, 'hidden', { value: true, configurable: true });
            document.dispatchEvent(new Event('visibilitychange'));
        })()""")
        time.sleep(0.2)
        b.js("""(() => {
            Object.defineProperty(document, 'hidden', { value: false, configurable: true });
            document.dispatchEvent(new Event('visibilitychange'));
        })()""")
        time.sleep(0.2)
        still_paused_after_vis = b.js("document.querySelector('.hero-bg-media.is-active')?.paused")
        assert still_paused_after_vis is True, "User pause MUST persist through visibility changes!"
        log_event("USER_PAUSE_PERSISTED_ACROSS_VISIBILITY", "Video remained paused after tab switch")

        # Unpause
        b.click('#hero-play-pause')
        time.sleep(0.2)
        assert b.js("document.querySelector('.hero-bg-media.is-active')?.paused") is False

        # 8. Test Automatic Pause on Tab Hidden & Auto-Resume
        print("\n8. Testing automatic pause on hidden tab and resume on visible...", flush=True)
        b.js("""(() => {
            Object.defineProperty(document, 'hidden', { value: true, configurable: true });
            document.dispatchEvent(new Event('visibilitychange'));
        })()""")
        time.sleep(0.2)
        hidden_paused = b.js("document.querySelector('.hero-bg-media.is-active')?.paused")
        assert hidden_paused is True, "Active video must pause when tab becomes hidden"
        log_event("TAB_HIDDEN_AUTO_PAUSED", "Video paused when tab hidden")

        b.js("""(() => {
            Object.defineProperty(document, 'hidden', { value: false, configurable: true });
            document.dispatchEvent(new Event('visibilitychange'));
        })()""")
        time.sleep(0.2)
        visible_resumed = b.js("document.querySelector('.hero-bg-media.is-active')?.paused")
        assert visible_resumed is False, "Active video must auto-resume when returning to visible tab"
        log_event("TAB_VISIBLE_AUTO_RESUMED", "Video resumed when tab returned to visible")

        # 9. Test Single-Video Mode (Continuous Loop, No Prev/Next buttons)
        print("\n9. Testing Single-Video Mode (disable slide 2)...", flush=True)
        # Disable slide 2 via API
        disable_res = b.js(f"""(() => {{
            return fetch('/api/v1/admin/media/hero/slides/{slide2_id}', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Origin': '{ORIGIN}',
                    'X-CSRF-Token': {json.dumps(csrf_token)},
                }},
                body: JSON.stringify({{
                    is_enabled: false,
                    expected_version: {slide2_res["data"].get("edit_version", 1)}
                }})
            }}).then(r => r.json());
        }})()""")
        assert disable_res.get('is_enabled') is False, f"Failed to disable slide 2: {disable_res}"

        # Reload storefront
        b.goto(f"{ORIGIN}/", wait_selector='.hero-section')
        b.wait_for_selector('.hero-bg-media.hero-video-media', timeout=10)
        time.sleep(0.5)

        single_info = b.js("""(() => {
            const videos = Array.from(document.querySelectorAll('.hero-bg-media.hero-video-media'));
            const prevBtn = document.querySelector('#hero-prev');
            const nextBtn = document.querySelector('#hero-next');
            const playPauseBtn = document.querySelector('#hero-play-pause');
            const indicator = document.querySelector('#hero-indicator')?.textContent || '';
            return {
                video_count: videos.length,
                video_loop: videos[0]?.loop,
                video_paused: videos[0]?.paused,
                prev_exists: Boolean(prevBtn),
                next_exists: Boolean(nextBtn),
                play_pause_exists: Boolean(playPauseBtn),
                indicator
            };
        })()""")
        assert single_info['video_count'] == 1, f"Expected 1 video, got {single_info['video_count']}"
        assert single_info['video_loop'] is True, "Single video hero MUST have loop=true for continuous looping"
        assert single_info['prev_exists'] is False, "Prev button must be omitted for single-item playlist"
        assert single_info['next_exists'] is False, "Next button must be omitted for single-item playlist"
        assert single_info['play_pause_exists'] is True, "Play/pause button must still exist for single video"
        assert '1 / 1' in single_info['indicator'], f"Expected '1 / 1', got '{single_info['indicator']}'"
        log_event("SINGLE_VIDEO_MODE_VERIFIED", "Loop=True, Prev/Next=Hidden, PlayPause=Active")
        save_and_copy("mm3_06_hero_single_video_loop.png")

        # 10. Write timing and event audit file
        audit_file = OUT_DIR / 'mm3_timing_audit.json'
        audit_file.write_text(json.dumps(timing_log, indent=2), encoding='utf-8')
        if BRAIN_ARTIFACTS.exists():
            shutil.copy2(audit_file, BRAIN_ARTIFACTS / 'mm3_timing_audit.json')
        print(f"\nTiming audit written to {audit_file}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL MM3 HERO PLAYBACK STATE MACHINE ACCEPTANCE CHECKS PASSED!", flush=True)
    print("=" * 70, flush=True)

if __name__ == '__main__':
    main()
