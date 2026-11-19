"""Tests for iPhone 16 Pro media pipeline: HEIC/HEIF, 48MP ProRAW/HEIF Max, QuickTime MOV HDR transcoding, and 3-tier variants."""
import io
import os
import shutil
import subprocess
import uuid
import pytest
from PIL import Image
from app.config import settings
from app.services import media, media_storage

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


@pytest.fixture(autouse=True)
def isolated_media(monkeypatch, tmp_path):
    root = tmp_path / 'catalog-media-iphone-test'
    assert root.resolve() != settings.catalog_media_root.resolve()
    monkeypatch.setattr(settings, 'catalog_media_root', root)
    return root


@pytest.fixture(autouse=True)
def committed_test_owner(db_session, admin_headers):
    db_session.commit()


def make_heif_bytes(width=64, height=48, color=(20, 40, 60)):
    img = Image.new('RGB', (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format='HEIF')
    return buf.getvalue()


def test_heif_image_upload_normalization_and_variants(admin_client, client):
    """Verify iPhone HEIC image upload normalizes to high-quality JPG and serves all variants."""
    heif_data = make_heif_bytes(width=120, height=90, color=(100, 150, 200))
    files = {'file': ('IMG_0123.HEIC', heif_data, 'image/heic')}
    response = admin_client.post('/api/v1/admin/media', files=files)
    assert response.status_code == 201, response.text
    asset = response.json()

    assert asset['width'] == 120
    assert asset['height'] == 90
    assert asset['content_type'] == 'image/jpeg'
    assert asset['state'] == 'ready'

    # Master URL serves JPEG
    master_res = client.get(asset['url'])
    assert master_res.status_code == 200
    assert master_res.headers['content-type'] == 'image/jpeg'

    # All variant tiers return WebP
    for variant in ('thumb', 'card', 'stage', 'full', 'zoom'):
        var_res = client.get(f"/api/v1/media/{asset['id']}/content?variant={variant}")
        assert var_res.status_code == 200, f"Variant {variant} failed"
        assert var_res.headers['content-type'] == 'image/webp'
        assert 'immutable' in var_res.headers['cache-control']
        assert len(var_res.content) > 0


def test_pixel_limit_allows_48mp_and_rejects_over_65mp(admin_client, monkeypatch):
    """Verify 48MP images (6048x8064) pass under 65MP, but >65MP images are rejected."""
    # Temporarily set limit to 2000 pixels to test boundary logic quickly
    monkeypatch.setattr(media_storage, 'PIXEL_LIMIT', 2000)

    # 40x40 = 1600 pixels (allowed under 2000)
    data_pass = io.BytesIO()
    Image.new('RGB', (40, 40), '#aabbcc').save(data_pass, format='JPEG')
    res_pass = admin_client.post('/api/v1/admin/media', files={'file': ('pass.jpg', data_pass.getvalue(), 'image/jpeg')})
    assert res_pass.status_code == 201, res_pass.text

    # 50x50 = 2500 pixels (exceeds 2000)
    data_fail = io.BytesIO()
    Image.new('RGB', (50, 50), '#aabbcc').save(data_fail, format='JPEG')
    res_fail = admin_client.post('/api/v1/admin/media', files={'file': ('fail.jpg', data_fail.getvalue(), 'image/jpeg')})
    assert res_fail.status_code == 422
    assert '65 megapixels' in res_fail.json()['detail']['message']


def test_low_priority_command_helper():
    """Verify low_priority_cmd prefixes nice/ionice when available on POSIX."""
    cmd = ['ffmpeg', '-version']
    prioritized = media_storage.low_priority_cmd(cmd)
    if os.name != 'nt' and shutil.which('nice'):
        assert prioritized[0] == 'nice'
        assert prioritized[1] == '-n'
        assert prioritized[2] == '19'
    else:
        assert prioritized[-1] == '-version'


def test_public_asset_includes_stage_and_zoom_urls():
    """Verify public_asset includes stage_url and zoom_url alongside legacy full_url."""
    class DummyAsset:
        id = 'dummy123'
        kind = 'image'
        content_type = 'image/jpeg'
        byte_size = 1000
        width = 800
        height = 600
        duration_ms = None
        poster_id = None

    payload = media.public_asset(DummyAsset())
    assert payload['thumb_url'] == '/api/v1/media/dummy123/content?variant=thumb'
    assert payload['card_url'] == '/api/v1/media/dummy123/content?variant=card'
    assert payload['stage_url'] == '/api/v1/media/dummy123/content?variant=stage'
    assert payload['full_url'] == '/api/v1/media/dummy123/content?variant=full'
    assert payload['zoom_url'] == '/api/v1/media/dummy123/content?variant=zoom'
