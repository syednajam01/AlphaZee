"""Actual HTTP/video/durability verification, confined to compose.media-check.yml."""
import argparse
from datetime import datetime, timezone
import hashlib
import http.cookiejar
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from sqlalchemy.engine import make_url
from app.config import settings
from app.database import SessionLocal
from app.services.owners import provision_owner

ORIGIN = 'http://127.0.0.1:13003'
BASE = 'http://127.0.0.1:8000/api/v1'
USERNAME = 'sample_m3_owner'
PASSWORD = 'SAMPLE-m3-isolated-password-2026'
ROOT = Path('/var/lib/alphazee/catalog-media')
MANIFEST = ROOT / 'verification' / 'manifest.json'


def guard():
    url = make_url(settings.database_url)
    if settings.app_env != 'test' or url.database not in {'alphazee_m3_media_test', 'alphazee_m3_restore_media_test'} or url.host != 'db' or settings.checkout_enabled or settings.catalog_media_root.resolve() != ROOT:
        raise RuntimeError('Refusing verification outside the isolated M3 Compose target')


class Client:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = None

    def call(self, path, payload=None, data=None, headers=None, expected=200):
        request_headers = {'Origin': ORIGIN, **(headers or {})}
        if payload is not None:
            data = json.dumps(payload).encode()
            request_headers['Content-Type'] = 'application/json'
        if self.csrf: request_headers['X-CSRF-Token'] = self.csrf
        request = urllib.request.Request(BASE + path, data=data, headers=request_headers)
        try: response = self.opener.open(request, timeout=90)
        except urllib.error.HTTPError as error: response = error
        with response:
            body = response.read()
            if response.status != expected:
                raise AssertionError(f'{path}: expected {expected}, got {response.status}: {body[:600]!r}')
            return json.loads(body) if response.headers.get_content_type() == 'application/json' else body

    def login(self):
        self.csrf = self.call('/auth/login', {'username': USERNAME, 'password': PASSWORD})['csrf_token']

    def upload(self, name, data, mime, expected=201):
        boundary = 'alphazeeM3VerifiedBoundary'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
        return self.call('/admin/media', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}, expected=expected)


def make_video(path, codec, duration='2', extension='mp4'):
    command = ['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'color=c=blue:s=64x48:r=5', '-t', duration,
               '-an', '-c:v', codec, '-threads', '2', '-pix_fmt', 'yuv420p']
    if extension == 'mp4': command += ['-movflags', '+faststart']
    subprocess.run(command + ['-y', str(path)], check=True, timeout=30, capture_output=True)
    return path.read_bytes()


def prepare():
    if MANIFEST.exists(): raise RuntimeError('Verification already prepared; use --check after a restart')
    with SessionLocal() as db:
        provision_owner(db, USERNAME, PASSWORD)
        db.commit()
    client = Client(); client.login()
    checks = ['isolated_owner_login']
    image = io.BytesIO(); Image.new('RGB', (64, 48), 'navy').save(image, 'PNG')
    poster = client.upload('SAMPLE-poster.png', image.getvalue(), 'image/png')
    assets = [poster]
    with tempfile.TemporaryDirectory(prefix='alphazee-m3-video-') as directory:
        path = Path(directory)
        for extension, codec in [('mp4', 'libx264'), ('webm', 'libvpx'), ('webm', 'libvpx-vp9')]:
            raw = make_video(path / ('sample-' + codec + '.' + extension), codec, extension=extension)
            asset = client.upload('SAMPLE-' + codec + '.' + extension, raw, 'video/' + extension)
            assert asset['kind'] == 'video' and asset['duration_ms'] == 2000
            assert client.call(asset['url'].removeprefix('/api/v1')) == raw
            assert client.call(asset['url'].removeprefix('/api/v1'), headers={'Range': 'bytes=0-31'}, expected=206) == raw[:32]
            assets.append(asset); checks.append('decoded_' + codec + '_and_http_range')
        wrong = make_video(path / 'wrong.mp4', 'mpeg4')
        client.upload('SAMPLE-wrong-codec.mp4', wrong, 'video/mp4', expected=422); checks.append('unsupported_codec_rejected')
        long = make_video(path / 'long.mp4', 'libx264', duration='121')
        client.upload('SAMPLE-too-long.mp4', long, 'video/mp4', expected=422); checks.append('duration_over_120_seconds_rejected')
        raw = make_video(path / 'truncated.mp4', 'libx264')
        client.upload('SAMPLE-corrupt.mp4', raw[:len(raw)//2], 'video/mp4', expected=422); checks.append('truncated_payload_rejected')
        client.upload('SAMPLE-video.webm', raw, 'video/webm', expected=422); checks.append('container_extension_mismatch_rejected')
    mp4 = assets[1]
    client.call(f"/admin/media/{mp4['id']}/poster", {'expected_version': 1, 'poster_id': poster['id']})
    client.call(f"/admin/media/{poster['id']}/delete", {'expected_version': 1}, expected=409)
    checks.append('poster_reference_blocks_deletion')
    collection = client.call('/admin/collections', {'name': 'SAMPLE M3', 'slug': 'sample-m3'}, expected=201)
    product = client.call('/admin/products', {'title': 'SAMPLE Media', 'slug': 'sample-m3', 'description': 'SAMPLE durable managed media',
        'collection_id': collection['id'], 'is_hero': True, 'variants': [{'sku': 'SAMPLE-M3', 'is_active': True, 'price_minor': 12345}]}, expected=201)
    attached = client.call(f"/admin/media/products/{product['id']}", {'expected_version': 1, 'items': [
        {'asset_id': poster['id'], 'role': 'primary', 'alt_text': 'Sample primary'},
        {'asset_id': mp4['id'], 'role': 'hero_video'}, {'asset_id': mp4['id'], 'role': 'gallery'}]})
    assert attached['hero_poster_url'] == poster['url']
    published = client.call(f"/admin/products/{product['id']}/publish", {'expected_version': 2})
    client.call(f"/admin/media/{mp4['id']}/poster", {'expected_version': 2, 'poster_id': None}, expected=409)
    client.call(f"/admin/media/{mp4['id']}/delete", {'expected_version': 2}, expected=409)
    checks += ['ready_media_allows_publication', 'published_gallery_requires_poster', 'hero_video_shared_reference_blocks_deletion']
    assert client.call('/storefront/capabilities')['checkout_enabled'] is False
    checks.append('checkout_stays_disabled')
    MANIFEST.parent.mkdir(exist_ok=True)
    manifest = {'phase': 'M3', 'prepared_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
                'assets': [{k: a[k] for k in ('id', 'url', 'checksum', 'byte_size')} for a in assets],
                'product_id': product['id'], 'product_edit_version': published['edit_version'],
                'database': 'alphazee_m3_media_test', 'storage': str(ROOT), 'development_modified': False}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n')
    Path('/evidence/runtime-prepared.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'checks_passed': len(checks), 'sample_assets': len(assets), 'normal_data_touched': False}))


def check(label):
    manifest = json.loads(MANIFEST.read_text())
    client = Client(); client.login()
    for asset in manifest['assets']:
        raw = client.call(asset['url'].removeprefix('/api/v1'))
        assert len(raw) == asset['byte_size'] and hashlib.sha256(raw).hexdigest() == asset['checksum']
        assert client.call(f"/admin/media/{asset['id']}")['state'] == 'ready'
    product = client.call('/admin/products/' + manifest['product_id'])
    assert product['status'] == 'published' and product['edit_version'] == manifest['product_edit_version']
    assert client.call('/storefront/capabilities')['checkout_enabled'] is False
    result = {'phase': 'M3', 'check': label, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'owner_login_survives': True, 'managed_asset_count': len(manifest['assets']), 'all_bytes_and_checksums_match': True,
              'product_and_associations_survive': True, 'checkout_enabled': False, 'development_modified': False}
    Path('/evidence/' + label + '.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    guard()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--check', choices=['restart', 'recreate', 'restore'])
    parser.add_argument('--serve', action='store_true', help='Start a temporary isolated API for restored-volume verification')
    parser.add_argument('--browser-owner', help='Provision a unique SAMPLE-only browser owner using a password on stdin')
    args = parser.parse_args()
    if args.browser_owner:
        import re
        if not re.fullmatch(r'sample_m4_[a-f0-9]{8}', args.browser_owner): raise RuntimeError('Invalid SAMPLE browser username')
        with SessionLocal() as db:
            provision_owner(db, args.browser_owner, sys.stdin.read().strip()); db.commit()
        print('Isolated SAMPLE browser owner provisioned.')
        raise SystemExit(0)
    process = None
    try:
        if args.serve:
            import time
            process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 30
            while True:
                try:
                    urllib.request.urlopen(BASE + '/ready', timeout=2).close(); break
                except Exception:
                    if time.monotonic() > deadline: raise RuntimeError('Temporary isolated API failed readiness')
                    time.sleep(.2)
        if args.prepare: prepare()
        elif args.check: check(args.check)
        else: parser.error('Choose --prepare or --check')
    finally:
        if process is not None: process.terminate(); process.wait(timeout=10)
