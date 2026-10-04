"""Approved cover derivatives only; never modifies the source plate.
Run: uv run --python 3.13.14 --with Pillow==12.1.0 python -B website/cover.py
Normal build helpers use stdlib only. Regeneration requires pinned Pillow.
"""
from pathlib import Path
import hashlib
import html
import io
import json
import math
import re

SITE = Path(__file__).resolve().parent
MASTER = SITE / 'assets/brand/mdaai-guardian-cover.webp'
MASTER_SHA256 = 'fee7149b09f5fdc922646a1356026af2bc0747dc586aa579b4842d977d82f22d'
ROOT = SITE / 'assets/cover'
WIDTHS = (280, 360, 560, 720, 1000)
SIZES = '(max-width: 1000px) min(272px, calc(100vw - 48px)), min(352px, calc(45.945946vw - 142.891892px))'


def inventory():
    return json.loads((ROOT / 'inventory.json').read_text())


def image_html(alt):
    assets = inventory()['assets']
    src = next(a['path'] for a in assets if a['width'] == 360)
    srcset = ', '.join('/' + a['path'] + ' ' + str(a['width']) + 'w' for a in assets)
    return (f'<img src="/{src}" srcset="{srcset}" sizes="{SIZES}" '
            f'width="1000" height="1300" loading="eager" fetchpriority="high" '
            f'alt="{html.escape(alt, quote=True)}">')


def generate():
    from PIL import Image, ImageChops, ImageStat, ImageDraw, __version__, features
    if __version__ != '12.1.0':
        raise RuntimeError('Regeneration requires Pillow==12.1.0')
    source = MASTER.read_bytes()
    if hashlib.sha256(source).hexdigest() != MASTER_SHA256:
        raise RuntimeError('Approved master digest mismatch')
    with Image.open(io.BytesIO(source)) as opened:
        if opened.size != (1000, 1300):
            raise RuntimeError('Approved master dimensions mismatch')
        master = opened.convert('RGB')
    ROOT.mkdir(parents=True, exist_ok=True)
    assets = []
    sheet = Image.new('RGB', (1500, 760), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, width in enumerate(WIDTHS):
        reference = master.resize((width, width * 13 // 10), Image.Resampling.LANCZOS) if width != 1000 else master.copy()
        output = io.BytesIO()
        reference.save(output, 'JPEG', quality=95, subsampling=0, optimize=True, progressive=True)
        data = output.getvalue()
        sha = hashlib.sha256(data).hexdigest()
        name = f'v1-guardian-{width}-{sha[:16]}.jpg'
        (ROOT / name).write_bytes(data)
        decoded = Image.open(io.BytesIO(data)); decoded.load()
        if decoded.size != reference.size or not decoded.info.get('progressive'):
            raise RuntimeError('Invalid progressive derivative')
        # Stuffed entropy bytes cannot contain unescaped FF DA/C2 markers.
        scans = len(re.findall(b'\xff\xda', data))
        if b'\xff\xc2' not in data or scans < 2:
            raise RuntimeError('Missing SOF2 or multiple scans')
        mse = sum(ImageStat.Stat(ImageChops.difference(reference, decoded)).rms[i] ** 2 for i in range(3)) / 3
        psnr = 10 * math.log10(255 ** 2 / mse) if mse else None
        assets.append({'path': 'assets/cover/' + name, 'sha256': sha, 'bytes': len(data), 'width': width, 'height': reference.height, 'sof': 'SOF2', 'sos_scans': scans, 'psnr_db': round(psnr, 3) if psnr else None})
        x = index * 300
        draw.text((x + 6, 6), f'{width}px Q95 4:4:4 / {len(data):,} bytes', fill='black')
        # Compare at identical display size; no enhancement, sharpening or recoloring.
        sheet.paste(reference.resize((272,354), Image.Resampling.LANCZOS), (x+6,30))
        sheet.paste(decoded.resize((272,354), Image.Resampling.LANCZOS), (x+6,400))
        draw.text((x+6,385), 'decoded JPEG (above: resized master)', fill='black')
    record = {'version': 1, 'master': {'path': 'assets/brand/mdaai-guardian-cover.webp', 'sha256': MASTER_SHA256, 'bytes': len(source), 'width': 1000, 'height': 1300}, 'generator': {'pillow': __version__, 'libjpeg': features.version_codec('jpg'), 'quality': 95, 'subsampling': '4:4:4', 'progressive': True, 'optimize': True, 'resample': 'LANCZOS'}, 'sizes': SIZES, 'assets': assets}
    (ROOT / 'inventory.json').write_text(json.dumps(record, indent=2) + '\n')
    evidence = SITE.parent / 'PROJECT-INTERNAL'
    evidence.mkdir(exist_ok=True)
    sheet.save(evidence / 'progressive-cover-contact-sheet.png')
    if MASTER.read_bytes() != source:
        raise RuntimeError('Master changed')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    generate()
