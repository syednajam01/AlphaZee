"""Bounded validation and generated filesystem paths for public catalog media."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from app.config import settings
from app.services.owner_catalog import CatalogError

IMAGE_LIMIT = 10 * 1024 * 1024
VIDEO_LIMIT = 100 * 1024 * 1024
BODY_LIMIT = VIDEO_LIMIT + 1024 * 1024
PIXEL_LIMIT = 40_000_000
TYPES = {'.jpg': ('image/jpeg', 'JPEG'), '.jpeg': ('image/jpeg', 'JPEG'),
         '.png': ('image/png', 'PNG'), '.webp': ('image/webp', 'WEBP'),
         '.mp4': ('video/mp4', 'h264'), '.webm': ('video/webm', ('vp8', 'vp9'))}


def paths():
    root = settings.catalog_media_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in ('staging', 'objects'):
        directory = root / name
        if directory.is_symlink():
            raise RuntimeError('Media directories must not be symlinks')
        directory.mkdir(exist_ok=True)
        if directory.resolve().parent != root:
            raise RuntimeError('Unsafe media directory')
    return root / 'staging', root / 'objects'


def object_path(key):
    if not re.fullmatch(r'[a-f0-9]{32}\.(jpg|png|webp|mp4|webm)', key):
        raise CatalogError('invalid_storage_key', 'Invalid media key', 404)
    _, objects = paths()
    path = objects / key
    if path.is_symlink() or path.resolve().parent != objects:
        raise CatalogError('invalid_storage_key', 'Unsafe media path', 404)
    return path


def upload_type(filename, declared_type):
    # Filename is a display label, never a storage path. Reject path/control input.
    if not filename or len(filename) > 200 or re.search(r'[\\/\x00-\x1f\x7f]', filename):
        raise CatalogError('invalid_filename', 'Use a simple filename without paths')
    extension = Path(filename).suffix.lower()
    if extension not in TYPES or declared_type != TYPES[extension][0]:
        raise CatalogError('unsupported_media', 'Upload JPEG, PNG, WebP, H.264 MP4 or VP8/VP9 WebM with the correct content type')
    kind = 'image' if extension not in {'.mp4', '.webm'} else 'video'
    return kind, extension, IMAGE_LIMIT if kind == 'image' else VIDEO_LIMIT


def _probe(command, timeout):
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=True,
                                **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
        return result.stdout
    except FileNotFoundError:
        raise CatalogError('video_validator_unavailable', 'Video validation requires ffmpeg and ffprobe. Use the Docker API.', 503) from None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        raise CatalogError('invalid_video', 'Video could not be safely decoded within the processing limit') from None


def validate(path: Path, kind, extension):
    content_type, expected = TYPES[extension]
    try:
        if kind == 'image':
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    if image.format != expected or image.width * image.height > PIXEL_LIMIT:
                        raise CatalogError('invalid_image', 'Image content/type must match and stay under 40 megapixels')
                    if getattr(image, 'n_frames', 1) != 1:
                        raise CatalogError('invalid_image', 'Animated images are not supported')
                    image.verify()
                with Image.open(path) as image:
                    image.load()
                    clean = ImageOps.exif_transpose(image)
                    width, height = clean.size
                    if expected == 'JPEG': clean = clean.convert('RGB')
                    clean.info.clear()
                    normalized = path.with_suffix('.clean')
                    try:
                        clean.save(normalized, format=expected)
                        if normalized.stat().st_size > IMAGE_LIMIT:
                            raise CatalogError('media_too_large', 'Validated image exceeds 10 MiB', 413)
                        os.replace(normalized, path)
                    finally:
                        normalized.unlink(missing_ok=True)
            duration_ms = None
            extension = '.jpg' if extension == '.jpeg' else extension
        else:
            output = _probe(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                '-format_whitelist', 'mov,matroska,webm', '-show_format', '-show_streams', '-of', 'json', str(path)], settings.media_probe_timeout)
            data = json.loads(output)
            streams = data.get('streams', [])
            video = [s for s in streams if s.get('codec_type') == 'video']
            formats = data.get('format', {}).get('format_name', '').split(',')
            if len(video) != 1 or len(streams) > 2 or any(s.get('codec_type') not in {'video', 'audio'} for s in streams):
                raise CatalogError('invalid_video', 'Provide one video stream with optional audio')
            stream = video[0]
            codec = stream.get('codec_name')
            if (extension == '.mp4' and (codec != 'h264' or 'mp4' not in formats)) or (extension == '.webm' and (codec not in expected or 'webm' not in formats)):
                raise CatalogError('invalid_video', 'Container and codec must match the chosen file type')
            # WebM is a restricted Matroska container: require its EBML document type.
            with path.open('rb') as source: header = source.read(4096)
            if extension == '.webm' and b'\x42\x82\x84webm' not in header:
                raise CatalogError('invalid_video', 'Expected a WebM container')
            if extension == '.mp4' and (header[4:8] != b'ftyp' or header[8:12] not in {
                    b'isom', b'iso2', b'iso3', b'iso4', b'iso5', b'iso6', b'avc1', b'mp41', b'mp42', b'M4V ', b'dash', b'cmfc', b'cmfs'}):
                raise CatalogError('invalid_video', 'Expected an MP4 container with a supported file-type brand')
            width, height = int(stream['width']), int(stream['height'])
            duration = float(data['format']['duration'])
            if width <= 0 or height <= 0 or width * height > PIXEL_LIMIT or not math.isfinite(duration) or not 0 < duration <= 120:
                raise CatalogError('invalid_video', 'Video must be at most 120 seconds and 40 megapixels')
            # Probe alone accepts corrupt/truncated payloads. Decode all frames, bounded.
            _probe(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-threads', '2', '-protocol_whitelist', 'file,pipe',
                    '-format_whitelist', 'mov,matroska,webm', '-i', str(path), '-map', '0:v:0', '-f', 'null', '-'], settings.media_decode_timeout)
            duration_ms = max(1, math.ceil(duration * 1000))
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''): digest.update(chunk)
        return dict(kind=kind, content_type=content_type, width=width, height=height,
                    duration_ms=duration_ms, checksum=digest.hexdigest(), byte_size=path.stat().st_size), extension
    except CatalogError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, KeyError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise CatalogError('invalid_media', 'Media is corrupt, oversized or does not match its declared type') from None
