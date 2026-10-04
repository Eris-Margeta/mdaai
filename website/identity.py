"""MDAAI identity: stdlib build helpers; offline, opt-in asset regeneration.

Build integration: emit_manifest(OUT). Copy only files in inventory['assets']
through the reviewed provenance allowlist. Normal imports need Python stdlib only.
Regenerate: Python + Pillow==12.1.0, `python3 -B website/identity.py --generate`.
Pillow's embedded default Aileron font avoids host font dependencies. The approved
SVG path geometry is sampled deterministically, not replaced by a text monogram.
Generation does not change the approved guardian cover or source SVGs.
"""
from pathlib import Path
import html
import json

SITE = Path(__file__).resolve().parent
ASSET_ROOT = 'assets/identity'
VERSION = 'v1'
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
            'alt': 'MDAAI coiled guardian emblem — ' + title + '; ' + subtitle}


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
    import io
    import re
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

    def contours(path):
        tokens = re.findall(r'[MCLZ]|-?\d+(?:\.\d+)?', path)
        result, points = [], []
        pos, current = 0, (0, 0)
        while pos < len(tokens):
            command = tokens[pos]
            pos += 1
            if command in ['M', 'L']:
                current = (float(tokens[pos]), float(tokens[pos+1]))
                pos += 2
                points.append(current)
            elif command == 'C':
                values = list(map(float, tokens[pos:pos+6]))
                pos += 6
                a, b, c = current, tuple(values[:2]), tuple(values[2:4])
                end = tuple(values[4:])
                for step in range(1, 33):
                    t = step / 32
                    u = 1-t
                    points.append(tuple(u**3*a[k] + 3*u*u*t*b[k] + 3*u*t*t*c[k] + t**3*end[k] for k in [0,1]))
                current = end
            elif command == 'Z':
                result.append(points)
                points = []
            else:
                raise ValueError('Unsupported source path command')
        assert not points
        return result

    # Source geometry is preserved: exterior paths union; subsequent contours are holes.
    mask = Image.new('L', (2048,2048))
    draw = ImageDraw.Draw(mask)
    for path in paths:
        for index, polygon in enumerate(contours(path)):
            draw.polygon([(round(x*4), round(y*4)) for x,y in polygon], fill=255 if index == 0 else 0)

    def mark(size):
        stamp = Image.new('RGBA', (size,size), '#ecf0f4')
        stamp.putalpha(mask.resize((size,size), Image.Resampling.LANCZOS))
        return stamp

    def record(name, image, mime, purpose, **options):
        target = output / name
        image.save(target, **options)
        data = target.read_bytes()
        inventory[name] = {'mime': mime, 'dimensions': list(image.size), 'bytes': len(data),
                           'sha256': hashlib.sha256(data).hexdigest(), 'purpose': purpose,
                           'alpha': image.mode == 'RGBA', 'backdrop': THEME_DARK}
        if mime == 'image/gif':
            inventory[name]['frames'] = Image.open(target).n_frames

    for size, name, purpose in [(32,'favicon-32.png','browser'),(180,'apple-touch-icon.png','apple'),
                                (192,'icon-192.png','any'),(512,'icon-512.png','any'),
                                (192,'icon-maskable-192.png','maskable'),(512,'icon-maskable-512.png','maskable')]:
        image = Image.new('RGB', (size,size), THEME_DARK)
        # Maskable fits a central circle, including antialiasing; not a square inset.
        extent = round(size*(.70 if purpose == 'maskable' else .89))
        stamp = mark(extent)
        offset = (size-extent)//2
        image.paste(stamp,(offset,offset),stamp)
        record(name,image,'image/png',purpose,format='PNG',optimize=False,compress_level=9)
    ico = Image.new('RGBA',(64,64),THEME_DARK)
    stamp = mark(58)
    ico.alpha_composite(stamp,(3,3))
    record('favicon.ico',ico,'image/x-icon','browser',format='ICO',sizes=[(16,16),(32,32)])
    inventory['favicon.ico']['dimensions'] = [32, 32]
    inventory['favicon.ico']['frames'] = [[16,16], [32,32]]
    svg = source.read_text().replace('fill="#fff"','fill="#20262c"')
    svg = svg.replace('<path d=', '<style>@media(prefers-color-scheme:dark){svg{fill:#ecf0f4}}</style><path d=',1)
    (output / 'favicon.svg').write_text(svg)
    data = (output / 'favicon.svg').read_bytes()
    inventory['favicon.svg'] = {'mime':'image/svg+xml','dimensions':[512,512],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'purpose':'browser','alpha':True,'backdrop':'transparent'}

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
        slug,title,subtitle = ROUTES[route]
        square = width == height
        image = Image.new('RGB',(width,height),THEME_DARK)
        d = ImageDraw.Draw(image)
        margin = 56 if square else 72
        # Restrained grid references repository relationships, not a product UI.
        for x in range(0,width,60):
            d.line((x,0,x,height),fill='#1d242c')
        for y in range(0,height,60):
            d.line((0,y,width,y),fill='#1d242c')
        d.rectangle((margin,margin,width-margin,margin+3), fill='#9bcbea')
        d.text((margin,margin+25),'MDAAI  /  DOCUMENTATION',font=font(22 if square else 24),fill='#9bcbea')
        if square:
            size = 136
            stamp = mark(size)
            image.paste(stamp,(margin,124),stamp)
            top,width_text,fs = 287,width-2*margin,40
        else:
            size = 278
            stamp = mark(size)
            image.paste(stamp,(width-margin-size,158),stamp)
            top,width_text,fs = 171,700,54
        face = font(fs)
        wrapped = lines(title,d,face,width_text)
        for index,line in enumerate(wrapped):
            d.text((margin,top+index*(fs+10)),line,font=face,fill='#ecf0f4')
        subtop = top + len(wrapped)*(fs+10) + 22
        for index,line in enumerate(lines(subtitle,d,font(22 if square else 27),width_text)):
            d.text((margin,subtop+index*33),line,font=font(22 if square else 27),fill='#b5c0cb')
        if not square:
            flow_y = height-142
            for index,label in enumerate(['CONTRACTS','TASKS','EVIDENCE']):
                x = margin+index*228
                d.rounded_rectangle((x,flow_y,x+198,flow_y+48),radius=5,fill='#293542',outline='#3a4653')
                d.text((x+18,flow_y+14),label,font=font(18),fill='#ecf0f4')
                if index < 2:
                    d.line((x+204,flow_y+24,x+222,flow_y+24),fill='#9bcbea',width=2)
            # One bounded evidence-flow pulse; title/emblem never morph or disappear.
            x = margin+int((phase/11)*652)
            d.ellipse((x-4,flow_y+58,x+4,flow_y+66),fill='#9bcbea')
        d.text((margin,height-54),'mdaai.internet.technology',font=font(18),fill='#b5c0cb')
        d.text((width-margin-30,height-54),f'{list(ROUTES).index(route)+1:02}',font=font(18),fill='#9bcbea')
        return image

    for route in ROUTES:
        assets = social_assets(route)
        for key,w,h in [('static',1200,630),('large',1200,600),('summary',600,600)]:
            record(Path(assets[key]).name,card(route,w,h),'image/png',key,format='PNG',compress_level=9)
        frames = [card(route,1200,630,phase=i).quantize(colors=128,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE) for i in range(12)]
        record(Path(assets['animated']).name,frames[0],'image/gif','animated alternate',format='GIF',save_all=True,append_images=frames[1:],duration=140,loop=0,disposal=1,optimize=False)
    document = {'version':VERSION,'generator':{'pillow':'12.1.0','font':'Pillow embedded Aileron default','svgSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'algorithm':'SVG cubic contours sampled at 32 steps; 4x source mask; Lanczos fit; deterministic flat cards'},'coverSha256':COVER_SHA256,'assets':inventory,'routes':{route:social_assets(route) for route in ROUTES},'limitations':['Animated GIF is an alternate; platform playback and crawler cache behavior are not verified locally.','Installation, offline and update acceptance require the separately integrated service worker and browser tests.']}
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
