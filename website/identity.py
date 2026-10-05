"""MDAAI identity: stdlib build helpers; offline, opt-in asset regeneration.

Build integration: emit_manifest(OUT). Copy only files in inventory['assets']
through the reviewed provenance allowlist. Normal imports need Python stdlib only.
Regenerate: Python + Pillow==12.1.0, `python3 -B website/identity.py --generate`.
Pinned, embedded DejaVu Serif fonts avoid host font dependencies. The approved
native cover plate is aspect-fitted deterministically, never replaced by a new animal.
Generation does not change the approved guardian cover or source SVGs.
"""
from pathlib import Path
import html
import json

SITE = Path(__file__).resolve().parent
ASSET_ROOT = 'assets/identity'
VERSION = 'v3'
THEME_DARK = '#161b21'
THEME_LIGHT = '#f8f9fa'
COVER_SHA256 = 'fee7149b09f5fdc922646a1356026af2bc0747dc586aa579b4842d977d82f22d'
ROUTES = {
    '/': ('mdaai', 'MDAAI', 'A protocol for AI-assisted development'),
    '/repository-structure/': ('structure', 'Repository structure', 'Contracts, tasks and evidence'),
    '/how-files-work-together/': ('connections', 'How files work together', 'Instructions to evidence'),
    '/task-lifecycle/': ('lifecycle', 'Task lifecycle', 'Assigned work to verified completion'),
    '/mdaai-1/': ('mdaai-1', 'First-generation template', ''),
    '/mdaai-2/': ('mdaai-2', 'MDAAI 2.0 template', ''),
    '/templates/': ('templates', 'Templates', 'Reviewed repository starting points'),
}


def social_assets(route):
    """Fail closed on an unreviewed route; no silent home-art fallback."""
    if route == '/paper/':
        # Explicit editorial reuse of approved protocol artwork, not a new cover.
        assets = social_assets('/')
        assets['alt'] = 'MDAAI paper — approved engraved guardian protocol artwork, E.M.K.'
        return assets
    slug, title, subtitle = ROUTES[route]
    prefix = '/' + ASSET_ROOT + '/' + VERSION + '-' + slug + '-'
    return {'static': prefix + 'og-static.png', 'animated': prefix + 'og-animated.gif',
            'large': prefix + 'twitter-large.png', 'summary': prefix + 'twitter-summary.png',
            'alt': title + (' — ' + subtitle if route == '/' else ' — MDAAI protocol documentation') + '; engraved guardian artwork, E.M.K.'}


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
            'description': 'MDAAI is a protocol for governing AI-assisted development. Choose and configure a template to apply it.',
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
    inventory.update({n: e for n, e in previous['assets'].items() if not n.startswith(('v1-', 'v2-', 'v3-'))})
    approved = Image.open(cover).convert('RGB')
    assert approved.size == (1000, 1300)
    plate = approved.crop((270, 405, 735, 1060))
    paper = approved.getpixel((20, 20))
    burgundy = approved.getpixel((20, 100))

    font_hashes = {'DejaVuSerif.ttf': '107244956e9962b9e96faccdc551825e0ae0898ae13737133e1b921a2fd35ffa',
                   'DejaVuSerif-Bold.ttf': 'c3753f2ed6bc673f15846dc45addbeb3b9c872f32fb18fd53a21f1bef1ed7676'}
    for name, digest in font_hashes.items():
        assert hashlib.sha256((SITE / 'fonts' / name).read_bytes()).hexdigest() == digest, 'Pinned font changed'

    def font(size, bold=False):
        return ImageFont.truetype(str(SITE / 'fonts' / ('DejaVuSerif-Bold.ttf' if bold else 'DejaVuSerif.ttf')), size=size)

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

    layouts = {}

    def card(route, width, height, phase=11):
        _, title, subtitle = ROUTES[route]
        home = route == '/'
        square = width == height
        image = Image.new('RGB', (width, height), paper)
        d = ImageDraw.Draw(image)
        margin = 36 if square else 60
        top, bottom = (28, 240) if square else (36, 245)
        d.rectangle((0, top, width, bottom), fill=burgundy)
        tokens, boxes = [], []

        def typeset(text, face, y, max_width):
            wrapped = lines(text, d, face, max_width)
            ascent, descent = face.getmetrics()
            advance = ascent + descent + 5
            for i, line in enumerate(wrapped):
                box = d.textbbox((0, 0), line, font=face)
                x0, y0 = margin, y + i * advance
                # Offset full glyph bounds, including ascenders and descenders.
                x, baseline = x0 - box[0], y0 - box[1]
                actual = d.textbbox((x, baseline), line, font=face)
                assert actual[0] >= margin and actual[2] <= width - margin
                assert actual[1] >= top and actual[3] <= bottom - 12
                d.text((x, baseline), line, font=face, fill=paper)
                boxes.append(list(actual))
            tokens.append(text)
            return y + len(wrapped) * advance

        if not home and 'MDAAI' not in title:
            typeset('MDAAI', font(22 if square else 26), top + 16, width - margin * 2)
        title_top = top + (32 if home else 60)
        fs = (72 if square else 86) if home else (43 if square else 60)
        while True:
            face = font(fs, bold=True)
            wrapped = lines(title, d, face, width - margin * 2)
            ascent, descent = face.getmetrics()
            reserved = (72 if square else 60) if home else 0
            if title_top + len(wrapped) * (ascent + descent + 5) + reserved <= bottom - 12:
                break
            fs -= 1
            assert fs >= 30
        end = typeset(title, face, title_top, width - margin * 2)
        if home:
            typeset(subtitle, font(22 if square else 32), end + 2, width - margin * 2)
        stamp = plate.copy()
        stamp.thumbnail((240, height - bottom - 66) if square else (380, height - bottom - 66), Image.Resampling.LANCZOS)
        x, y = (width - stamp.width) // 2, bottom + 18
        assert y + stamp.height <= height - 42 and x >= margin and x + stamp.width <= width - margin
        # The alternate reveals only the engraving, never text or decorative ticks.
        # Every frame remains a complete readable cover; the first is 85% visible.
        if phase < 11:
            stamp = Image.blend(Image.new('RGB', stamp.size, paper), stamp, .85 + .15 * phase / 11)
        image.paste(stamp, (x, y))
        face = font(18 if square else 22)
        box = d.textbbox((0, 0), 'E.M.K.', font=face)
        author_y = height - 26 - (box[3] - box[1])
        d.text((margin - box[0], author_y - box[1]), 'E.M.K.', font=face, fill='#202321')
        tokens.append('E.M.K.')
        assert sum(token.count('MDAAI') for token in tokens) == 1
        layouts[f'{route}:{width}x{height}'] = {'text': tokens, 'textBounds': boxes,
                                              'artBounds': [x, y, x + stamp.width, y + stamp.height],
                                              'safeMargin': margin}
        return image

    for route in ROUTES:
        assets = social_assets(route)
        for key,w,h in [('static',1200,630),('large',1200,600),('summary',600,600)]:
            record(Path(assets[key]).name,card(route,w,h),'image/png',key,format='PNG',compress_level=9)
        palette = card(route,1200,630).quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
        frames = [card(route,1200,630,phase=i).quantize(palette=palette,dither=Image.Dither.NONE) for i in range(12)]
        record(Path(assets['animated']).name,frames[0],'image/gif','animated alternate',format='GIF',save_all=True,append_images=frames[1:],duration=[90] * 11 + [2500],loop=0,disposal=1,optimize=False)
    document = {'version':VERSION,'generator':{'pillow':'12.1.0','font':'Embedded DejaVu Serif regular/bold; unmodified, licensed in licenses/DejaVu-fonts.txt',
                'fontSha256':font_hashes,'svgSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'algorithm':'Approved engraving aspect-fit; measured full-glyph serif typography; no duplicated labels; engraving-only reveal'},
                'layouts':layouts,'coverSha256':COVER_SHA256,'assets':inventory,'routes':{route:social_assets(route) for route in ROUTES},
                'limitations':['Animated GIF is an engraving-reveal alternate; platform playback and crawler cache behavior are not verified locally.',
                               'Installation, offline and update acceptance require the separately integrated service worker and browser tests.']}
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
