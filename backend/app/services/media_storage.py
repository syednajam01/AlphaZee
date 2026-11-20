"""Bounded validation and generated filesystem paths for public catalog media."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 250_000_000

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

from app.config import settings
from app.services.owner_catalog import CatalogError

IMAGE_LIMIT = 100 * 1024 * 1024
VIDEO_LIMIT = 250 * 1024 * 1024
BODY_LIMIT = VIDEO_LIMIT + 10 * 1024 * 1024
PIXEL_LIMIT = 150_000_000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP', 'HEIF', 'TIFF', 'DNG', 'MPO'}
ALLOWED_FORMATS_BY_EXT = {
    '.jpg': {'JPEG', 'MPO', 'HEIF'},
    '.jpeg': {'JPEG', 'MPO', 'HEIF'},
    '.png': {'PNG'},
    '.webp': {'WEBP'},
    '.heic': {'HEIF', 'JPEG'},
    '.heif': {'HEIF', 'JPEG'},
    '.dng': {'TIFF', 'DNG'},
}
MAX_WEB_DIM = 4096

TYPES = {
    '.jpg': ('image/jpeg', 'JPEG'),
    '.jpeg': ('image/jpeg', 'JPEG'),
    '.png': ('image/png', 'PNG'),
    '.webp': ('image/webp', 'WEBP'),
    '.heic': ('image/heic', 'HEIF'),
    '.heif': ('image/heif', 'HEIF'),
    '.dng': ('image/x-adobe-dng', ('TIFF', 'DNG')),
    '.mp4': ('video/mp4', ('h264', 'hevc', 'av1', 'vp9', 'dvhe', 'dvh1', 'mpeg4')),
    '.mov': ('video/quicktime', ('h264', 'hevc', 'mov', 'prores', 'dnxhd', 'dvhe', 'dvh1', 'mjpeg')),
    '.webm': ('video/webm', ('vp8', 'vp9', 'av1')),
}

CONTENT_TYPE_ALIASES = {
    '.jpg': {'image/jpeg', 'image/pjpeg', 'image/heic', 'image/heif', 'application/octet-stream'},
    '.jpeg': {'image/jpeg', 'image/pjpeg', 'image/heic', 'image/heif', 'application/octet-stream'},
    '.png': {'image/png', 'application/octet-stream'},
    '.webp': {'image/webp', 'application/octet-stream'},
    '.heic': {'image/heic', 'image/heif', 'image/jpeg', 'application/octet-stream'},
    '.heif': {'image/heif', 'image/heic', 'image/jpeg', 'application/octet-stream'},
    '.dng': {'image/x-adobe-dng', 'image/dng', 'image/tiff', 'application/octet-stream'},
    '.mp4': {'video/mp4', 'video/x-m4v', 'video/quicktime', 'application/octet-stream'},
    '.mov': {'video/quicktime', 'video/mp4', 'video/x-m4v', 'application/octet-stream'},
    '.webm': {'video/webm', 'video/x-matroska', 'application/octet-stream'},
}


def low_priority_cmd(command: list[str]) -> list[str]:
    """Prefix CPU/IO intensive tasks with lowest scheduling priority on POSIX."""
    if os.name != 'nt':
        prefix = []
        if shutil.which('nice'):
            prefix.extend(['nice', '-n', '19'])
        if shutil.which('ionice'):
            prefix.extend(['ionice', '-c', '3'])
        return prefix + command
    return command


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


VARIANT_SPECS = {
    'thumb': {'max_dim': 300, 'quality': 80},
    'card': {'max_dim': 800, 'quality': 82},
    'stage': {'max_dim': 1600, 'quality': 84},
    'full': {'max_dim': 1600, 'quality': 84},
    'zoom': {'max_dim': 2560, 'quality': 86},
}


def variants_dir():
    root = settings.catalog_media_root.expanduser().resolve()
    vdir = root / 'variants'
    if vdir.is_symlink():
        raise RuntimeError('Media directories must not be symlinks')
    vdir.mkdir(exist_ok=True)
    if vdir.resolve().parent != root:
        raise RuntimeError('Unsafe media directory')
    return vdir


def variant_path(key, variant):
    if variant not in VARIANT_SPECS:
        raise CatalogError('invalid_variant', 'Invalid image variant requested', 400)
    stem = Path(key).stem
    if not re.fullmatch(r'[a-f0-9]{32}', stem):
        raise CatalogError('invalid_storage_key', 'Invalid media key', 404)
    vdir = variants_dir()
    path = vdir / f'{stem}_{variant}.webp'
    if path.is_symlink() or path.resolve().parent != vdir:
        raise CatalogError('invalid_storage_key', 'Unsafe media path', 404)
    return path


def ensure_image_variant(key, variant):
    target = variant_path(key, variant)
    if target.is_file():
        return target
    src = object_path(key)
    if not src.is_file():
        raise CatalogError('media_not_found', 'Master media file not found', 404)
    spec = VARIANT_SPECS[variant]
    max_dim = spec['max_dim']
    quality = spec['quality']
    vdir = variants_dir()
    tmp = vdir / f'{target.stem}_{os.getpid()}_{uuid.uuid4().hex[:6]}.tmp'
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(src) as img:
                img.load()
                clean = ImageOps.exif_transpose(img)
                if clean.mode in ('RGBA', 'LA') or (clean.mode == 'P' and 'transparency' in clean.info):
                    clean = clean.convert('RGBA')
                else:
                    clean = clean.convert('RGB')
                w, h = clean.size
                if max(w, h) > max_dim:
                    clean.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                clean.save(tmp, format='WEBP', quality=quality, method=6)
                os.replace(tmp, target)
                return target
    except Exception as e:
        tmp.unlink(missing_ok=True)
        if isinstance(e, CatalogError):
            raise
        raise CatalogError('variant_generation_failed', f'Could not generate image variant: {e}', 500) from e


def generate_all_variants(key):
    ext = Path(key).suffix.lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        for variant in VARIANT_SPECS:
            try:
                ensure_image_variant(key, variant)
            except Exception:
                pass


def delete_variants(key):
    stem = Path(key).stem
    if not re.fullmatch(r'[a-f0-9]{32}', stem):
        return
    vdir = variants_dir()
    for variant in VARIANT_SPECS:
        vfile = vdir / f'{stem}_{variant}.webp'
        if vfile.is_file():
            vfile.unlink(missing_ok=True)


def extract_video_poster(video_path: Path, poster_path: Path, max_dim: int = 1600) -> bool:
    """Extract a representative frame from video as high-quality JPEG poster."""
    for timestamp in ('0.0', '0.5'):
        cmd = low_priority_cmd([
            'ffmpeg', '-y', '-v', 'error', '-nostdin',
            '-i', str(video_path),
            '-ss', timestamp,
            '-map', '0:v:0',
            '-dn', '-sn',
            '-vframes', '1',
            '-vf', f'scale=min({max_dim}\\,iw):-2:force_original_aspect_ratio=decrease,out_color_matrix=bt709,format=yuv420p',
            '-f', 'image2',
            '-c:v', 'mjpeg',
            str(poster_path)
        ])
        try:
            kwargs = {}
            if os.name == 'nt':
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            subprocess.run(
                cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=settings.media_probe_timeout, check=True, **kwargs
            )
            if poster_path.is_file() and poster_path.stat().st_size > 0:
                return True
        except Exception:
            continue
    return False


def upload_type(filename, declared_type):
    # Filename is a display label, never a storage path. Reject path/control input.
    if not filename or len(filename) > 200 or re.search(r'[\\/\x00-\x1f\x7f]', filename):
        raise CatalogError('invalid_filename', 'Use a simple filename without paths')
    extension = Path(filename).suffix.lower()
    if extension not in TYPES:
        raise CatalogError('unsupported_media', 'Upload JPEG, PNG, WebP, HEIC, ProRAW DNG, MP4, MOV, or WebM')
    allowed = CONTENT_TYPE_ALIASES.get(extension, {TYPES[extension][0]})
    if declared_type and declared_type not in allowed and declared_type != 'application/octet-stream':
        raise CatalogError('unsupported_media', 'Upload with a matching content type')
    kind = 'image' if extension not in {'.mp4', '.webm', '.mov'} else 'video'
    return kind, extension, IMAGE_LIMIT if kind == 'image' else VIDEO_LIMIT


def _probe(command, timeout):
    try:
        kwargs = {}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=True, **kwargs)
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
                warnings.simplefilter('ignore', Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    detected_format = image.format
                    allowed_for_ext = ALLOWED_FORMATS_BY_EXT.get(extension, ALLOWED_IMAGE_FORMATS)
                    if detected_format not in allowed_for_ext or image.width * image.height > PIXEL_LIMIT:
                        raise CatalogError('invalid_image', f'Image content/type must match and stay under {PIXEL_LIMIT // 1_000_000} megapixels')
                    if getattr(image, 'n_frames', 1) != 1:
                        raise CatalogError('invalid_image', 'Animated images are not supported')
                    image.verify()
                with Image.open(path) as image:
                    image.load()
                    clean = ImageOps.exif_transpose(image)
                    if max(clean.width, clean.height) > MAX_WEB_DIM:
                        clean.thumbnail((MAX_WEB_DIM, MAX_WEB_DIM), Image.Resampling.LANCZOS)
                    width, height = clean.size

                    if detected_format == 'PNG':
                        if clean.mode not in ('RGB', 'RGBA'):
                            clean = clean.convert('RGBA' if 'transparency' in clean.info else 'RGB')
                        save_format = 'PNG'
                        out_extension = '.png'
                        out_content_type = 'image/png'
                        save_kwargs = {}
                    elif detected_format == 'WEBP':
                        if clean.mode not in ('RGB', 'RGBA'):
                            clean = clean.convert('RGBA' if 'transparency' in clean.info else 'RGB')
                        save_format = 'WEBP'
                        out_extension = '.webp'
                        out_content_type = 'image/webp'
                        save_kwargs = {'quality': 92, 'method': 6}
                    else:
                        clean = clean.convert('RGB')
                        save_format = 'JPEG'
                        out_extension = '.jpg'
                        out_content_type = 'image/jpeg'
                        save_kwargs = {'quality': 95}

                    clean.info.clear()
                    normalized = path.with_suffix('.clean')
                    try:
                        clean.save(normalized, format=save_format, **save_kwargs)
                        if normalized.stat().st_size > IMAGE_LIMIT:
                            raise CatalogError('media_too_large', f'Validated image exceeds {IMAGE_LIMIT // (1024 * 1024)} MiB', 413)
                        os.replace(normalized, path)
                    finally:
                        normalized.unlink(missing_ok=True)
            duration_ms = None
            extension = out_extension
            content_type = out_content_type
        else:
            output = _probe(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                '-format_whitelist', 'mov,mp4,matroska,webm', '-show_format', '-show_streams', '-of', 'json', str(path)], settings.media_probe_timeout)
            data = json.loads(output)
            streams = data.get('streams', [])
            video_streams = [s for s in streams if s.get('codec_type') == 'video']
            if not video_streams:
                raise CatalogError('invalid_video', 'Provide at least one valid video stream')

            # Pick primary video stream (highest resolution)
            stream = max(video_streams, key=lambda s: int(s.get('width', 0)) * int(s.get('height', 0)))
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']

            codec = stream.get('codec_name', '').lower()
            expected_codecs = expected if isinstance(expected, tuple) else (expected,)
            valid_codecs = {'h264', 'hevc', 'mov', 'prores', 'dnxhd', 'dvhe', 'dvh1', 'vp8', 'vp9', 'av1', 'mjpeg', 'mpeg4'}
            if codec not in expected_codecs and codec not in valid_codecs:
                raise CatalogError('invalid_video', 'Container and codec must match the chosen file type')

            with path.open('rb') as source: header = source.read(4096)
            if extension == '.webm' and b'\x42\x82\x84webm' not in header:
                raise CatalogError('invalid_video', 'Expected a WebM container')
            if extension in ('.mp4', '.mov') and not any(k in header[:64] for k in (b'ftyp', b'moov', b'wide', b'mdat', b'free', b'skip')):
                raise CatalogError('invalid_video', 'Expected an MP4 or QuickTime MOV container with supported brand')

            width, height = int(stream.get('width', 0)), int(stream.get('height', 0))
            duration = float(data.get('format', {}).get('duration') or stream.get('duration') or 0)
            if width <= 0 or height <= 0 or width * height > PIXEL_LIMIT or not math.isfinite(duration) or not 0 < duration <= 120:
                raise CatalogError('invalid_video', f'Video must be at most 120 seconds and {PIXEL_LIMIT // 1_000_000} megapixels')

            pix_fmt = stream.get('pix_fmt', '')
            color_primaries = stream.get('color_primaries', '')
            color_space = stream.get('color_space', '')
            color_trc = stream.get('color_trc', '')
            is_hdr = '10' in pix_fmt or color_primaries in ('bt2020',) or color_space in ('bt2020nc', 'bt2020c') or 'arib' in color_trc or 'smpte2084' in color_trc
            is_oversized = (width > 1920 or height > 1920)
            needs_transcode = (extension == '.mov') or (codec in ('hevc', 'prores', 'dvhe', 'dvh1')) or is_hdr or is_oversized

            if needs_transcode:
                normalized = path.with_suffix('.transcoded.mp4')
                video_idx = stream.get('index', 0)
                transcode_cmd = low_priority_cmd([
                    'ffmpeg', '-y', '-v', 'error', '-nostdin', '-threads', '2',
                    '-protocol_whitelist', 'file,pipe',
                    '-i', str(path),
                    '-map', f'0:{video_idx}',
                ])
                if audio_streams:
                    audio_idx = audio_streams[0].get('index', 1)
                    transcode_cmd.extend(['-map', f'0:{audio_idx}'])
                transcode_cmd.extend(['-dn', '-sn'])
                transcode_cmd.extend([
                    '-vf', "scale='min(1920,iw)':-2:force_original_aspect_ratio=decrease,out_color_matrix=bt709,format=yuv420p",
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                    '-c:a', 'aac', '-b:a', '128k',
                    '-movflags', '+faststart',
                    str(normalized)
                ])
                try:
                    _probe(transcode_cmd, max(settings.media_decode_timeout, 120))
                    if normalized.stat().st_size > VIDEO_LIMIT:
                        raise CatalogError('media_too_large', f'Transcoded video exceeds {VIDEO_LIMIT // (1024 * 1024)} MiB', 413)
                    os.replace(normalized, path)
                    extension = '.mp4'
                    content_type = 'video/mp4'
                    reprobe_out = _probe(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], settings.media_probe_timeout)
                    reprobe_data = json.loads(reprobe_out)
                    v_stream = [s for s in reprobe_data.get('streams', []) if s.get('codec_type') == 'video'][0]
                    width, height = int(v_stream['width']), int(v_stream['height'])
                    duration = float(reprobe_data.get('format', {}).get('duration') or v_stream.get('duration') or duration)
                finally:
                    normalized.unlink(missing_ok=True)
            else:
                _probe(low_priority_cmd(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-threads', '2',
                                         '-protocol_whitelist', 'file,pipe',
                                         '-format_whitelist', 'mov,mp4,matroska,webm',
                                         '-i', str(path), '-map', f"0:{stream.get('index', 0)}", '-f', 'null', '-']), settings.media_decode_timeout)
                content_type = TYPES[extension][0]
                if isinstance(content_type, tuple):
                    content_type = content_type[0]

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
