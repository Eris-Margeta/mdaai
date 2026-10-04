"""MDAAI identity: stdlib build helpers; offline, opt-in asset regeneration.

Build integration: emit_manifest(OUT). Copy only files in inventory['assets']
through the reviewed provenance allowlist. Normal imports need Python stdlib only.
Regenerate: Python + Pillow==12.1.0, `python3 -B website/identity.py --generate`.
Pillow's embedded default Aileron font avoids host font dependencies. The approved
native cover plate is aspect-fitted deterministically, never replaced by a new animal.
Generation does not change the approved guardian cover or source SVGs.
"""
from pathlib import Path
import html
import json

SITE = Path(__file__).resolve().parent
ASSET_ROOT = 'assets/identity'
VERSION = 'v2'
THEME_DARK = '#161b21'
THEME_LIGHT = '#f8f9fa'
COVER_SHA256 = 'fee7149b09f5fdc922646a1356026af2bc0747dc586aa579b4842d977d82f22d'
ROUTES = {
    '/': ('mdaai', 'MDAAI', 'Repository operating protocol'),
    '/repository-structure/': ('structure', 'Repository structure', 'Contracts, tasks and evidence'),
    '/how-files-work-together/': ('connections', 'How files work together', 'Instructions to evidence'),
    '/task-lifecycle/': ('lifecycle', 'Task lifecycle', 'Assigned work to verified completion'),
    '/mdaai-1/': ('mdaai-1', 'First-generation MDAAI', 'The original repository template'),
    '/mdaai-2/': ('mdaai-2', 'MDAAI 2.0', 'The portable core'),
    '/templates/': ('templates', 'Templates', 'Reviewed repository starting points'),
}


def social_assets(route):
    """Fail closed on an unreviewed route; no silent home-art fallback."""
    slug, title, subtitle = ROUTES[route]
    prefix = '/' + ASSET_ROOT + '/' + VERSION + '-' + slug + '-'
    return {'static': prefix + 'og-static.png', 'animated': prefix + 'og-animated.gif',
            'large': prefix + 'twitter-large.png', 'summary': prefix + 'twitter-summary.png',
            'alt': 'MDAAI engraved guardian book-cover artwork — ' + title + '; ' + subtitle}


def icon_metadata():
    """Every page including errors receives accurate native-icon declarations."""
    prefix = '/' + ASSET_ROOT + '/'
    links = []
    for name, rel, size, mime in [('favicon.ico', 'icon', '16x16 32x32', 'image/x-icon'),
                                  ('favicon-32.png', 'icon', '32x32', 'image/png'),
                                  ('favicon.svg', 'icon', 'any', 'image/svg+xml'),
                                  ('apple-touch-icon.png', 'apple-touch-icon', '180x180', 'image/png')]:
        links.append(f'<link rel="{rel}" href="{prefix}{name}" sizes="{size}" type="{mime}">')
    return ''.join(links) + '<link rel="manifest" href="/site.webmanifest" type="application/manifest+json">' + \
        '<meta name="theme-color" content="#f8f9fa" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#161b21" media="(prefers-color-scheme: dark)">' + \
        '<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="MDAAI"><meta name="apple-mobile-web-app-status-bar-style" content="default">'


def manifest():
    """Identity only: not an assertion that SW/install/offline gates passed."""
    icons = []
    for purpose in ['any', 'maskable']:
        for size in [192, 512]:
            name = ('icon-maskable-' if purpose == 'maskable' else 'icon-') + str(size) + '.png'
            icons.append({'src': '/' + ASSET_ROOT + '/' + name, 'sizes': f'{size}x{size}', 'type': 'image/png', 'purpose': purpose})
    return {'id': '/', 'name': 'MDAAI Documentation', 'short_name': 'MDAAI',
            'description': 'Repository operating protocol: contracts, tasks, evidence and reviewed templates.',
            'lang': 'en', 'start_url': '/', 'scope': '/', 'display': 'standalone',
            'theme_color': THEME_DARK, 'background_color': THEME_DARK,
            'icons': icons,
            'shortcuts': [{'name': 'Repository structure', 'short_name': 'Structure', 'url': '/repository-structure/'},
                          {'name': 'Task lifecycle', 'short_name': 'Tasks', 'url': '/task-lifecycle/'},
                          {'name': 'Templates', 'short_name': 'Templates', 'url': '/templates/'}]}


def emit_manifest(output):
    """Write deterministically to the caller-owned static build output."""
    destination = Path(output) / 'site.webmanifest'
    destination.write_text(json.dumps(manifest(), ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return 'site.webmanifest'


def generate_assets():
    """Developer-only generation; Pillow is deliberately imported lazily."""
    import hashlib
    import xml.etree.ElementTree as ET
    import PIL
    from PIL import Image, ImageDraw, ImageFont
    if PIL.__version__ != '12.1.0':
        raise RuntimeError('Regeneration requires Pillow==12.1.0')
    cover = SITE / 'assets/brand/mdaai-guardian-cover.webp'
    if hashlib.sha256(cover.read_bytes()).hexdigest() != COVER_SHA256:
        raise ValueError('Approved cover changed')
    source = SITE / 'assets/brand/logo-white.svg'
    root = ET.fromstring(source.read_bytes())
    assert root.attrib['viewBox'] == '0 0 512 512'
    paths = [p.attrib['d'] for p in root.findall('{http://www.w3.org/2000/svg}path')]
    output = SITE / ASSET_ROOT
    output.mkdir(parents=True, exist_ok=True)
    inventory = {}

    def record(name, image, mime, purpose, **options):
        target = output / name
        image.save(target, **options)
        data = target.read_bytes()
        inventory[name] = {'mime': mime, 'dimensions': list(image.size), 'bytes': len(data),
                           'sha256': hashlib.sha256(data).hexdigest(), 'purpose': purpose,
                           'alpha': image.mode == 'RGBA', 'backdrop': '#%02x%02x%02x' % paper}
        if mime == 'image/gif':
            inventory[name]['frames'] = Image.open(target).n_frames

    # Only social assets are regenerated; native icons remain immutable.
    previous = json.loads((output / 'inventory.json').read_text())
    inventory.update({n: e for n, e in previous['assets'].items() if not n.startswith(('v1-', 'v2-'))})
    approved = Image.open(cover).convert('RGB')
    assert approved.size == (1000, 1300)
    plate = approved.crop((270, 405, 735, 1060))
    paper = approved.getpixel((20, 20))
    burgundy = approved.getpixel((20, 100))

    def font(size):
        return ImageFont.load_default(size=size)

    def lines(text, draw, face, width):
        result, current = [], ''
        for word in text.split():
            trial = (current + ' ' + word).strip()
            if current and draw.textlength(trial,font=face) > width:
                result.append(current)
                current = word
            else:
                current = trial
        if current:
            result.append(current)
        return result

    def card(route, width, height, phase=0):
        slug, title, subtitle = ROUTES[route]
        square = width == height
        image = Image.new('RGB', (width, height), paper)
        d = ImageDraw.Draw(image)
        margin = 36 if square else 60
        band_top, band_bottom = (30, 225) if square else (36, 250)
        d.rectangle((0, band_top, width, band_bottom), fill=burgundy)
        d.text((margin, band_top + 18), 'MDAAI', font=font(38 if square else 44), fill=paper)
        fs = 40 if square else 58
        while True:
            face = font(fs)
            wrapped = lines(title, d, face, width - 2 * margin)
            if len(wrapped) <= 2 and all(d.textlength(t, font=face) <= width - 2 * margin for t in wrapped):
                break
            fs -= 1
            assert fs >= 24, 'Title cannot fit approved band'
        top = band_top + (72 if square else 83)
        for index, line in enumerate(wrapped):
            d.text((margin, top + index * (fs + 8)), line, font=face, fill=paper)
        assert top + len(wrapped) * (fs + 8) <= band_bottom - 8, 'Title clipping'
        stamp = plate.copy()
        stamp.thumbnail((225, 292) if square else (260, height - band_bottom - 90), Image.Resampling.LANCZOS)
        x = (width - stamp.width) // 2 if square else width - margin - stamp.width - 65
        image.paste(stamp, (x, band_bottom + 12))
        if not square:
            for index, line in enumerate(lines(subtitle, d, font(30), 620)):
                d.text((margin, band_bottom + 50 + index * 39), line, font=font(30), fill='#202321')
            d.text((margin, band_bottom + 154), 'MDAAI DOCUMENTATION', font=font(19), fill='#202321')
        footer = height - (52 if square else 64)
        d.line((margin, footer - 12, width - margin, footer - 12), fill='#555853', width=1)
        d.text((margin, footer), 'E.M.K.', font=font(25 if square else 28), fill='#202321')
        tick = margin + round(phase / 11 * 66)
        d.line((tick, height - 14, tick + 12, height - 14), fill=burgundy, width=2)
        return image

    for route in ROUTES:
        assets = social_assets(route)
        for key,w,h in [('static',1200,630),('large',1200,600),('summary',600,600)]:
            record(Path(assets[key]).name,card(route,w,h),'image/png',key,format='PNG',compress_level=9)
        frames = [card(route,1200,630,phase=i).quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE) for i in range(12)]
        record(Path(assets['animated']).name,frames[0],'image/gif','animated alternate',format='GIF',save_all=True,append_images=frames[1:],duration=140,loop=0,disposal=1,optimize=False)
    document = {'version':VERSION,'generator':{'pillow':'12.1.0','font':'Pillow embedded Aileron default','svgSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'algorithm':'Approved native cover plate crop (270,405,735,1060); aspect-fit Lanczos; ivory paper and burgundy measured title band; bounded footer tick'},'coverSha256':COVER_SHA256,'assets':inventory,'routes':{route:social_assets(route) for route in ROUTES},'limitations':['Animated GIF is an alternate; platform playback and crawler cache behavior are not verified locally.','Installation, offline and update acceptance require the separately integrated service worker and browser tests.']}
    (output / 'inventory.json').write_text(json.dumps(document,sort_keys=True,indent=2)+'\n')
    print(f'Generated {len(inventory)} identity assets; approved cover unchanged.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    if args.generate:
        generate_assets()
    else:
        print(json.dumps(manifest(),sort_keys=True,indent=2))
