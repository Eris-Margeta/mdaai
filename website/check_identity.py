"""Identity acceptance: source metadata by default; --dist verifies built output too.

No third-party runtime dependencies. --decode additionally exercises Pillow's real
image decoders, every animated frame, and the maskable safe circle.
"""
from pathlib import Path
import argparse
import hashlib
import json
from html.parser import HTMLParser
import struct
import zlib

SITE = Path(__file__).resolve().parent


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.meta = {}
        self.links = []
        self.structured = []
        self.in_json = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta':
            key = a.get('property', a.get('name'))
            self.meta.setdefault(key, []).append(a.get('content'))
        if tag == 'link':
            self.links.append(a)
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_json = False

    def handle_data(self, text):
        if self.in_json:
            self.structured.append(json.loads(text))


def check_identity(site=SITE, dist=None, decode=False):
    from identity import manifest, social_assets, ASSET_ROOT, COVER_SHA256, ROUTES, VERSION
    from seo import metadata, page_title, BASE, AUTHOR
    site = Path(site)
    pages = json.loads((site / 'content.json').read_text())
    assert len(pages) == 8, 'Seven documentation routes plus approved paper required'
    inventory = json.loads((site / 'assets/identity/inventory.json').read_text())
    required = {'favicon.ico', 'favicon-32.png', 'favicon.svg', 'apple-touch-icon.png',
                'icon-192.png', 'icon-512.png', 'icon-maskable-192.png', 'icon-maskable-512.png'}
    for page in pages:
        for variant, value in social_assets(page['route']).items():
            if variant != 'alt':
                required.add(value.removeprefix('/' + ASSET_ROOT + '/'))
    assert set(inventory['assets']) == required, 'Exact reviewed identity asset matrix required'
    assert len(required) == 36
    content = json.loads((site / 'content.json').read_text())
    assert {p['route']: p['title'] for p in content if p['route'] != '/paper/'} == {route: values[1] for route, values in ROUTES.items()}, 'Social titles must match actual published titles'
    assert social_assets('/paper/')['static'] == social_assets('/')['static'], 'Paper deliberately reuses approved protocol artwork'
    assert inventory['generator']['pillow'] == '12.1.0'
    assert inventory['version'] == 'v3'
    assert len(inventory['layouts']) == 21
    for key, layout in inventory['layouts'].items():
        width, height = map(int, key.rsplit(':', 1)[1].split('x'))
        tokens = layout['text']
        assert sum(token.count('MDAAI') for token in tokens) == 1, (key, tokens)
        assert tokens.count('E.M.K.') == 1
        assert not any('DOCUMENTATION' in token for token in tokens)
        if key.startswith('/:'):
            assert tokens == ['MDAAI', 'A protocol for AI-assisted development', 'E.M.K.']
        margin = layout['safeMargin']
        for x0, y0, x1, y1 in layout['textBounds'] + [layout['artBounds']]:
            assert margin <= x0 < x1 <= width - margin
            assert 0 < y0 < y1 < height
    for name, digest in inventory['generator']['fontSha256'].items():
        assert hashlib.sha256((site / 'fonts' / name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256((site / 'assets/brand/mdaai-guardian-cover.webp').read_bytes()).hexdigest() == COVER_SHA256, 'Approved cover changed'
    for name, entry in inventory['assets'].items():
        data = (site / ASSET_ROOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256'], name
        assert len(data) == entry['bytes'], name
        if entry['mime'] == 'image/png':
            assert data[:8] == b'\x89PNG\r\n\x1a\n', name
            assert list(struct.unpack('>II', data[16:24])) == entry['dimensions'], name
            offset = 8
            idat = b''
            while offset < len(data):
                length = struct.unpack('>I', data[offset:offset+4])[0]
                kind = data[offset+4:offset+8]
                payload = data[offset+8:offset+8+length]
                crc = struct.unpack('>I', data[offset+8+length:offset+12+length])[0]
                assert zlib.crc32(kind + payload) & 0xffffffff == crc, name
                if kind == b'IDAT':
                    idat += payload
                offset += length + 12
            assert zlib.decompress(idat), name
            assert len(data) < 350 * 1024, name
        elif entry['mime'] == 'image/gif':
            assert data[:6] == b'GIF89a' and data[-1:] == b';', name
            assert list(struct.unpack('<HH', data[6:10])) == [1200, 630], name
            assert entry['frames'] > 1 and len(data) < 5 * 1024 * 1024, name
            # Parse actual encoded GIF blocks, not byte-pattern frame guesses.
            offset = 13
            packed = data[10]
            if packed & 128:
                offset += 3 * (2 ** ((packed & 7) + 1))
            frames = 0
            def blocks(offset):
                total = 0
                while True:
                    size = data[offset]
                    offset += 1
                    if size == 0:
                        return offset, total
                    total += size
                    offset += size
                    assert offset <= len(data), name
            while data[offset] != 0x3b:
                tag = data[offset]
                offset += 1
                if tag == 0x21:
                    offset += 1  # extension label, followed by subblocks
                    offset, _ = blocks(offset)
                elif tag == 0x2c:
                    left, top, width, height, packed = struct.unpack('<HHHHB', data[offset:offset+9])
                    assert width and height and left + width <= 1200 and top + height <= 630, name
                    offset += 9
                    if packed & 128:
                        offset += 3 * (2 ** ((packed & 7) + 1))
                    assert 2 <= data[offset] <= 8, name  # GIF LZW code size
                    offset += 1
                    offset, compressed = blocks(offset)
                    assert compressed > 0, name
                    frames += 1
                else:
                    raise AssertionError((name, 'Unexpected GIF block', tag))
            assert frames == entry['frames'] and frames == 12, name
        elif entry['mime'] == 'image/x-icon':
            reserved, kind, count = struct.unpack('<HHH', data[:6])
            assert (reserved, kind, count) == (0, 1, 2)
            assert {tuple(data[6+16*i:8+16*i]) for i in range(count)} == {(16,16),(32,32)}
        elif entry['mime'] == 'image/svg+xml':
            import xml.etree.ElementTree as ET
            assert ET.fromstring(data).attrib['viewBox'] == '0 0 512 512'
        else:
            raise AssertionError('Unsupported asset MIME: ' + name)
        if dist:
            assert (Path(dist) / ASSET_ROOT / name).read_bytes() == data, 'Missing/stale output: ' + name
    images = set()
    for page in pages:
        route = page['route']
        selection = social_assets(route)
        assert set(selection) == {'static', 'animated', 'large', 'summary', 'alt'}
        for variant, dims, mime in [('static',[1200,630],'image/png'), ('animated',[1200,630],'image/gif'), ('large',[1200,600],'image/png'), ('summary',[600,600],'image/png')]:
            entry = inventory['assets'][selection[variant].removeprefix('/' + ASSET_ROOT + '/')]
            assert entry['dimensions'] == dims and entry['mime'] == mime
        images.add(selection['static'])
        if dist:
            text = (Path(dist) / route.strip('/') / 'index.html').read_text()
        else:
            text = metadata(page['title'], page['description'], route)
        h = Head(text)
        def one(key, value):
            assert h.meta.get(key) == [value], (route, key, h.meta.get(key), value)
        one('author', AUTHOR)
        one('og:url', BASE + route)
        one('og:site_name', 'MDAAI')
        one('og:locale', 'en_US')
        one('og:type', 'website' if route in ('/', '/templates/') else 'article')
        one('og:title', page_title(page['title'], route))
        one('og:description', page['description'])
        assert h.meta['og:image'] == [BASE + selection['static'], BASE + selection['animated']]
        assert h.meta['og:image:type'] == ['image/png', 'image/gif']
        assert h.meta['og:image:width'] == ['1200', '1200']
        assert h.meta['og:image:height'] == ['630', '630']
        assert h.meta['og:image:alt'] == [selection['alt'], selection['alt'] + ' — animated alternate; platform playback varies']
        one('twitter:card', 'summary_large_image')
        one('twitter:image', BASE + selection['large'])
        one('twitter:image:alt', selection['alt'])
        one('twitter:title', page_title(page['title'], route))
        one('twitter:description', page['description'])
        assert 'twitter:site' not in h.meta and 'twitter:creator' not in h.meta
        assert [x['href'] for x in h.links if x['rel'] == 'canonical'] == [BASE + route]
        check_icons(h)
        assert len(h.structured) == 1
        objects = h.structured[0]['@graph']
        by_id = {x['@id']: x for x in objects}
        assert len(by_id) == len(objects)
        person = by_id[BASE + '/#author']
        studio = by_id['https://tejl.hr/#organization']
        assert person['@type'] == 'Person' and person['name'] == AUTHOR
        assert studio['@type'] == 'Organization' and studio['name'] == 'TEJL Studio'
        assert studio['url'] == 'https://tejl.hr/' and studio['sameAs'] == ['https://tejl.com/']
        website = by_id[BASE + '/#website']
        assert website['author'] == {'@id': person['@id']}
        assert website['creator'] == website['maintainer'] == {'@id': studio['@id']}
        assert website['publisher'] != website['creator'], 'Client and studio must remain distinct'
        document = by_id[BASE + route + '#page']
        assert document['url'] == BASE + route and document['inLanguage'] == 'en'
        assert document['author'] == {'@id': person['@id']}
        assert document['isPartOf'] == {'@id': website['@id']}
        breadcrumbs = by_id[BASE + route + '#breadcrumb']['itemListElement']
        assert breadcrumbs[-1]['item'] == BASE + route
        def refs(value):
            if isinstance(value, dict):
                if set(value) == {'@id'}:
                    assert value['@id'] in by_id, value
                for v in value.values():
                    refs(v)
            elif isinstance(value, list):
                for v in value:
                    refs(v)
        refs(objects)
    assert len(images) == 7, 'Route-specific images required'
    for variant in ['static', 'animated', 'large', 'summary']:
        digests = {inventory['assets'][social_assets(p['route'])[variant].removeprefix('/' + ASSET_ROOT + '/')]['sha256'] for p in pages}
        assert len(digests) == 7, ('Route-specific artwork required', variant)
    for size in [192,512]:
        assert inventory['assets'][f'icon-{size}.png']['sha256'] != inventory['assets'][f'icon-maskable-{size}.png']['sha256'], 'Maskable artwork must be separately fitted'
    m = manifest()
    if dist:
        assert json.loads((Path(dist) / 'site.webmanifest').read_text()) == m
        error = Head((Path(dist) / '404.html').read_text())
        assert error.meta['robots'] == ['noindex,follow']
        check_icons(error)
    assert m['id'] == m['scope'] == m['start_url'] == '/'
    assert m['lang'] == 'en' and m['display'] == 'standalone'
    assert m['theme_color'] == '#161b21' and m['background_color'] == '#161b21'
    assert m['name'] and m['short_name'] and m['description']
    assert len(m['icons']) == 4
    assert {(x['sizes'], x['purpose']) for x in m['icons']} == {('192x192','any'),('512x512','any'),('192x192','maskable'),('512x512','maskable')}
    for icon in m['icons']:
        entry = inventory['assets'][icon['src'].removeprefix('/' + ASSET_ROOT + '/')]
        assert entry['mime'] == icon['type'] == 'image/png'
        assert icon['sizes'] == 'x'.join(map(str, entry['dimensions']))
    for shortcut in m['shortcuts']:
        assert shortcut['url'] in {x['route'] for x in pages}
    if decode:
        from PIL import Image, ImageChops
        for name, entry in inventory['assets'].items():
            if entry['mime'] == 'image/svg+xml':
                continue
            image = Image.open(site / ASSET_ROOT / name)
            image.load()
            assert image.format == {'image/png':'PNG','image/gif':'GIF','image/x-icon':'ICO'}[entry['mime']]
            if image.format == 'GIF':
                assert image.n_frames == entry['frames']
                frames = []
                stable = None
                for i in range(image.n_frames):
                    image.seek(i)
                    image.load()
                    assert image.size == (1200,630)
                    rgb = image.convert('RGB')
                    # Meaningful reveal is confined to the approved engraving.
                    # Text and the entire surrounding cover stay pixel-stable.
                    route = next(route for route in ROUTES if name == Path(social_assets(route)['animated']).name)
                    x0, y0, x1, y1 = inventory['layouts'][route + ':1200x630']['artBounds']
                    surround = rgb.copy()
                    surround.paste((0, 0, 0), (x0, y0, x1, y1))
                    if stable is None:
                        stable = surround.tobytes()
                    assert surround.tobytes() == stable, (name, 'Animation outside engraving')
                    assert image.info['duration'] == (2500 if i == 11 else 90)
                    frames.append(hashlib.sha256(rgb.tobytes()).hexdigest())
                assert len(set(frames)) > 1
            if name.startswith(VERSION + '-') and image.format == 'PNG':
                cover = Image.open(site / 'assets/brand/mdaai-guardian-cover.webp').convert('RGB')
                rgb = image.convert('RGB')
                assert rgb.getpixel((0, 0)) == cover.getpixel((20, 20)), (name, 'Ivory paper')
                assert rgb.getpixel((0, 100)) == cover.getpixel((20, 100)), (name, 'Burgundy band')
                square = image.width == image.height
                band_bottom = 240 if square else 245
                plate = cover.crop((270, 405, 735, 1060))
                plate.thumbnail((240, image.height - band_bottom - 66) if square else (380, image.height - band_bottom - 66), Image.Resampling.LANCZOS)
                x = (image.width - plate.width) // 2
                y = band_bottom + 18
                assert rgb.crop((x, y, x + plate.width, y + plate.height)).tobytes() == plate.tobytes(), (name, 'Approved plate must be intact and aspect-fitted')
            if 'maskable' in name:
                rgb = image.convert('RGB')
                w, h = rgb.size
                background = Image.new('RGB', rgb.size, '#161b21')
                pixels = ImageChops.difference(rgb, background).load()
                for y in range(h):
                    for x in range(w):
                        if any(pixels[x,y]):
                            assert (x-(w-1)/2)**2 + (y-(h-1)/2)**2 <= (w*.4)**2, (name,x,y)
            if name == 'apple-touch-icon.png' or 'maskable' in name:
                assert image.convert('RGBA').getchannel('A').getextrema() == (255,255)
    return {'routes': len(pages), 'assets': len(inventory['assets']), 'decoded': decode, 'built_output': bool(dist)}


def check_icons(head):
    from identity import ASSET_ROOT
    for filename, rel, sizes, mime in [('favicon.ico','icon','16x16 32x32','image/x-icon'),('favicon-32.png','icon','32x32','image/png'),('favicon.svg','icon','any','image/svg+xml'),('apple-touch-icon.png','apple-touch-icon','180x180',None)]:
        matches = [x for x in head.links if x.get('rel') == rel and x.get('href') == '/' + ASSET_ROOT + '/' + filename]
        assert len(matches) == 1 and matches[0]['sizes'] == sizes, filename
        if mime:
            assert matches[0]['type'] == mime
    assert [x['href'] for x in head.links if x.get('rel') == 'manifest'] == ['/site.webmanifest']
    assert head.meta['apple-mobile-web-app-capable'] == ['yes']
    assert head.meta['apple-mobile-web-app-title'] == ['MDAAI']
    assert '#161b21' in head.meta['theme-color']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path)
    parser.add_argument('--decode', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check_identity(dist=args.dist, decode=args.decode), sort_keys=True))
