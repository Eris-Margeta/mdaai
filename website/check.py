"""Website-focused artifact, route, schema and disclosure regressions."""
import contextlib
import hashlib
from html.parser import HTMLParser
import tempfile
import shutil
import struct
import copy
import xml.etree.ElementTree as ET
from unittest.mock import patch
from urllib.parse import urljoin
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import unittest
from urllib.parse import urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build
from identity import social_assets
import serve


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.links = []
        self.headings = []
        self.elements = []
        self.text = text
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.elements.append((tag, a))
        if 'id' in a:
            self.ids.append(a['id'])
        if tag in ('a', 'link') and 'href' in a:
            self.links.append(a['href'])
        if tag in ('img', 'script', 'source', 'track') and 'src' in a:
            self.links.append(a['src'])
        if 'poster' in a:
            self.links.append(a['poster'])
        if tag == 'h1':
            self.headings.append(tag)
        if tag == 'script' and 'src' not in a and a.get('type') != 'application/ld+json':
            raise AssertionError('Inline script forbidden')
        if any(key.startswith('on') for key in a):
            raise AssertionError('Inline handler forbidden')


class WebsiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = Path.home() / '.hermes/cache/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='mdaai-check-', dir=scratch)
        cls.addClassCleanup(cls.temp.cleanup)
        site = Path(cls.temp.name) / 'website'
        shutil.copytree(HERE, site, ignore=shutil.ignore_patterns('dist', '__pycache__', '.template-cache'))
        cls.patches = [patch.object(build, 'SITE', site), patch.object(build, 'OUT', site / 'dist'), patch.object(serve, 'ROOT', site / 'dist')]
        for mock in cls.patches:
            mock.start()
            cls.addClassCleanup(mock.stop)
        build.build()
        cls.pages = json.loads((site / 'content.json').read_text())
        cls.documents = {}
        for file in build.OUT.rglob('*.html'):
            route = '/' + str(file.relative_to(build.OUT)).replace('index.html', '')
            cls.documents[route] = Document(file.read_text())

    def test_all_routes_anchors_assets(self):
        for route, doc in self.documents.items():
            self.assertEqual(len(doc.headings), 1, route)
            self.assertEqual(len(set(doc.ids)), len(doc.ids), route)
            for href in doc.links:
                url = urlsplit(href)
                if url.scheme or url.netloc:
                    self.assertIn(url.scheme, ('https', 'tel'))
                    continue
                target = urlsplit(urljoin(route, href)).path
                if target in self.documents:
                    if url.fragment:
                        self.assertIn(url.fragment, self.documents[target].ids, href)
                else:
                    self.assertTrue((build.OUT / target.lstrip('/')).is_file(), href)

    def test_search_schema_and_all_sections(self):
        entries = json.loads((build.OUT / 'assets/search.json').read_text())
        expected = sum(len(p['sections']) for p in self.pages)
        self.assertEqual(len(entries), expected)
        self.assertEqual(len({e['url'] for e in entries}), expected)
        for entry in entries:
            self.assertEqual(set(entry), {'title','heading','text','url'})
            url = urlsplit(entry['url'])
            self.assertIn(url.path, self.documents)
            self.assertIn(url.fragment, self.documents[url.path].ids)

    def test_portable_provenance_and_drift_fail_closed(self):
        provenance = json.loads((build.SITE / 'provenance.json').read_text())
        self.assertEqual(set(provenance['sourceReferences']), {s for p in self.pages for s in p['sources']})
        for asset, digest in provenance['assets'].items():
            self.assertEqual(hashlib.sha256((build.OUT / asset).read_bytes()).hexdigest(), digest)
        with tempfile.TemporaryDirectory(prefix='drift-', dir=Path(self.temp.name)) as temp:
            site = Path(temp) / 'website'
            shutil.copytree(build.SITE, site)
            with patch.object(build, 'SITE', site):
                content = site / 'content.json'
                original = content.read_bytes()
                content.write_bytes(original + b' ')
                with self.assertRaisesRegex(ValueError, 'Reviewed content changed'):
                    build.load_content()
                content.write_bytes(original)
                for name in provenance['assets']:
                    with self.subTest(asset=name):
                        asset = site / name
                        original_asset = asset.read_bytes()
                        asset.write_bytes(original_asset + b'drift')
                        with self.assertRaisesRegex(ValueError, 'Reviewed asset changed'):
                            build.load_content()
                        asset.write_bytes(original_asset)
                build.load_content()

    def test_no_private_assets_or_machine_paths(self):
        provenance = json.loads((build.SITE / 'provenance.json').read_text())
        expected = {'404.html', 'robots.txt', 'sitemap.xml', 'site.webmanifest', 'assets/search.json', 'offline.html', 'service-worker.js'} | set(provenance['assets']) | {(p['route'].strip('/') + '/index.html').lstrip('/') for p in self.pages}
        files = {str(p.relative_to(build.OUT)) for p in build.OUT.rglob('*') if p.is_file()}
        self.assertEqual(files, expected)
        for file in build.OUT.rglob('*'):
            if not file.is_file():
                continue
            self.assertFalse(file.is_symlink())
            if file.suffix in ('.png', '.webp', '.jpg', '.mp4', '.gif', '.ico'):
                continue
            text = file.read_text()
            for pattern in (r'/Users/', r'/private/', r'file://', r'BEGIN [A-Z ]*PRIVATE KEY', r'\bsk-[A-Za-z0-9]{20,}', r'\b[A-Fa-f0-9]{64}\b', r'source-pins', r'sourcearchives', r'\.hermes/', r'\.git/'):
                self.assertIsNone(re.search(pattern, text), (file.name, pattern))
        for name in ('evidence', 'PROJECT-INTERNAL', 'provenance.json', 'source-pins.json'):
            self.assertFalse((build.OUT / name).exists())

    def test_template_panel_order_and_header(self):
        home = self.documents['/'].text
        self.assertRegex(home, r'</video><p>English narration.*?</p></section><section id="template-cycle"')
        self.assertIn('Having difficulty reading? Watch the 91-second overview.', home)
        self.assertIn('Narration and captions offer another way to explore the two template families.', home)
        for route, doc in self.documents.items():
            if route == '/offline.html':
                continue
            links = [a for t, a in doc.elements if t == 'a' and a.get('class') == 'templates-repo']
            self.assertEqual(len(links), 1)
            self.assertEqual(links[0]['href'], '/templates/')
            self.assertIn('>TEMPLATES</a>', doc.text)
            github = [a for t, a in doc.elements if t == 'a' and a.get('class') == 'templates-repo github-repo']
            self.assertEqual(len(github), 1)
            self.assertEqual(github[0]['href'], 'https://github.com/Eris-Margeta/mdaai')
            self.assertIn('external', github[0]['aria-label'])
        gallery = self.documents['/templates/'].text
        lock, catalog, files = build.load_catalog(build.SITE)
        for path, file in files.items():
            self.assertIn('/blob/' + lock['revision'] + '/' + path, gallery)
            self.assertIn(file['role'], gallery)
        self.assertNotIn('/template-files/', gallery)
        self.assertIn('complete: false', gallery)
        self.assertIn('not missing export files', gallery)

    def test_content_is_escaped(self):
        self.assertEqual(build.E('<script>"&'), '&lt;script&gt;&quot;&amp;')
        js = (build.OUT / 'assets/app.js').read_text()
        self.assertNotIn('innerHTML', js)
        self.assertNotIn('eval(', js)
        self.assertIn('textContent', js)

    def test_homepage_is_mdaai_documentation(self):
        self.assertEqual(len(self.pages), 7)
        self.assertEqual({p['route'] for p in self.pages}, {'/', '/repository-structure/', '/how-files-work-together/', '/task-lifecycle/', '/mdaai-1/', '/mdaai-2/', '/templates/'})
        home = (build.OUT / 'index.html').read_text()
        self.assertIn('<h1>MDAAI</h1>', home)
        self.assertIn('MDAAI is a protocol for governing AI-assisted development.', home)
        self.assertIn('Project Elaboration owns scope and sequence', home)

    def test_rejected_content_is_not_served(self):
        text = '\n'.join(f.read_text() for f in build.OUT.rglob('*') if f.is_file() and f.suffix not in ('.png', '.webp', '.jpg', '.mp4', '.gif', '.ico'))
        for rejected in ('hermes --', 'HermesSol', 'Hermes Agent', 'native_p95_regression', '564 tests', 'Year-long governance', 'python3 -B website/', '/docs/quickstart/', '/evolution/', 'industry-first', 'self-declared breakthrough'):
            self.assertNotIn(rejected, text)
        self.assertEqual(len(list(build.OUT.rglob('*.html'))), 9)

    def test_core_inventory_and_section_links(self):
        structure = next(p for p in self.pages if p['slug'] == 'structure')
        section = structure['sections'][0]
        core = {'AGENTS.md'} | {'PROJECT-INTERNAL/GOVERNANCE/' + n + '.md' for n in ('AUTHORITY', 'ENGINEERING', 'EVIDENCE', 'REASONING', 'RECORDS')} | {'PROJECT-INTERNAL/MANAGEMENT/PROJECT-ELABORATION.md', 'PROJECT-INTERNAL/MANAGEMENT/TASKS.json'}
        listed = {r[0] for r in section['table']['rows']}
        self.assertTrue(core <= listed)
        for path in core:
            self.assertIn('MDAAI 2.0: ' + path, structure['sources'])
        links = dict(section['links'])
        self.assertEqual(set(links), core)
        doc = self.documents['/repository-structure/']
        for path, target in links.items():
            self.assertIn('#' + target.split('#')[1], doc.links, path)
        css = (build.OUT / 'assets/style.css').read_text()
        self.assertIn('.file-map-grid{display:grid', css)
        self.assertIn('.table-scroll{overflow:auto', css)

    def test_sample_registries_structurally_match_documented_schema(self):
        # Local structural checks only; the original validator is tested separately.
        examples = [json.loads(s['code']) for p in self.pages for s in p['sections'] if s.get('language') in ('Illustrative TASKS.json', 'Fresh registry — source adoption schema')]
        self.assertEqual(len(examples), 2)
        for registry in examples:
            self.assertEqual(set(registry), {'schemaVersion', 'taskPrefix', 'tasks'})
            self.assertEqual(registry['schemaVersion'], 1)
            self.assertRegex(registry['taskPrefix'], r'^[A-Z][A-Z0-9]*$')
            self.assertIsInstance(registry['tasks'], list)
            ids = [t['id'] for t in registry['tasks']]
            self.assertEqual(len(ids), len(set(ids)))
            for task in registry['tasks']:
                self.assertEqual(set(task), {'id', 'title', 'owner', 'state', 'disposition', 'scopeRef', 'acceptance', 'dependencies', 'evidence', 'blocker', 'next', 'history'})
                self.assertRegex(task['id'], '^' + registry['taskPrefix'] + r'-[0-9]{3}$')
                self.assertEqual(task['state'], 'active')
                self.assertEqual(task['disposition'], 'current')
                self.assertEqual(task['scopeRef'], 'PROJECT-INTERNAL/MANAGEMENT/PROJECT-ELABORATION.md')
                for field in ('title', 'owner', 'next'):
                    self.assertTrue(isinstance(task[field], str) and task[field].strip())
                self.assertTrue(task['acceptance'])
                self.assertTrue(all(isinstance(x, str) and x.strip() for x in task['acceptance']))
                self.assertEqual(task['dependencies'], [])
                self.assertEqual(task['evidence'], [])
                self.assertIsNone(task['blocker'])
                self.assertEqual(len(task['history']), 1)
                history = task['history'][0]
                self.assertEqual(set(history), {'at', 'state', 'disposition', 'reason'})
                from datetime import date
                date.fromisoformat(history['at'])
                self.assertEqual(history['state'], task['state'])
                self.assertEqual(history['disposition'], task['disposition'])
                self.assertTrue(history['reason'].strip())
        self.assertEqual(sorted(len(x['tasks']) for x in examples), [0, 1])

    def test_generations_and_adoption_boundary(self):
        routes = {p['route']: p for p in self.pages}
        original = json.dumps(routes['/mdaai-1/'])
        successor = json.dumps(routes['/mdaai-2/'])
        for term in ('WORK-ORDERS/registry.json', 'work-order-template.md', 'CORRECTIVE/CWO-', 'ADR-NNN', 'Version 1.7', 'not a pristine', 'CHECKPOINTS/CP-', 'KNOWLEDGE/AGENTS.md', '.template/agent-rules.yaml', 'reconcile this contradiction'):
            self.assertIn(term, original)
        for term in ('no routine per-edit WO', 'fresh registry', 'not the portable adoption inventory', 'Completed/void records', 'rollback'):
            self.assertIn(term, successor)

    def test_search_finds_files_relationships_and_task(self):
        entries = json.loads((build.OUT / 'assets/search.json').read_text())
        for term, route in [('TASKS.json', '/repository-structure/'), ('scopeRef', '/how-files-work-together/'), ('APP-001', '/task-lifecycle/'), ('CWO-', '/mdaai-1/'), ('taskPrefix', '/mdaai-2/')]:
            self.assertTrue(any(urlsplit(e['url']).path == route and term.lower() in e['text'].lower() for e in entries), (term, route))
        self.assertEqual({urlsplit(e['url']).path for e in entries}, {p['route'] for p in self.pages})

    def test_retained_accessibility_and_clipboard_guards(self):
        js = (build.OUT / 'assets/app.js').read_text()
        for term in ('dialog.showModal()', "returnFocus.focus()", 'ArrowDown', '1500', 'Copy unavailable. Select the code and copy manually.'):
            self.assertIn(term, js)
        for f in build.OUT.rglob('*.html'):
            text = f.read_text()
            if f.name == 'offline.html':
                self.assertIn('MDAAI is offline', text)
                self.assertIn('Return to MDAAI documentation', text)
                continue
            for term in ('Skip to content', 'aria-labelledby="search-title"', 'WEB made by', '/assets/tejl/tejl-logo-off-white.svg', '/assets/tejl/tejl-logo-off-black.svg', 'Web studio contact:'):
                self.assertIn(term, text)

    def test_metadata_schema_and_canonical_routes(self):
        base = 'https://www.mdaai.internet.technology'
        author = 'Eris Margeta Kurdali'
        titles, descriptions = [], []
        for page in self.pages:
            route = page['route']
            doc = self.documents[route]
            with self.subTest(route=route):
                metas = {}
                for tag, attrs in doc.elements:
                    if tag == 'meta' and ('name' in attrs or 'property' in attrs):
                        key = attrs.get('name', attrs.get('property'))
                        if key.startswith('og:image') or key == 'theme-color':
                            metas.setdefault(key, attrs.get('content'))
                        else:
                            self.assertNotIn(key, metas)
                            metas[key] = attrs.get('content')
                title = build.page_title(page['title'], route)
                self.assertIn('<title>' + build.E(title) + '</title>', doc.text)
                self.assertEqual(title.count('MDAAI'), 1)
                titles.append(title)
                descriptions.append(metas['description'])
                expected = {'author': author, 'description': page['description'], 'og:title': title, 'twitter:title': title, 'og:description': page['description'], 'twitter:description': page['description'], 'og:url': base + route, 'og:type': 'website' if route in ('/', '/templates/') else 'article', 'og:site_name': 'MDAAI', 'og:locale': 'en_US', 'og:image': base + social_assets(route)['static'], 'twitter:image': base + social_assets(route)['large'], 'og:image:type': 'image/png', 'og:image:width': '1200', 'og:image:height': '630', 'twitter:card': 'summary_large_image'}
                for key, value in expected.items():
                    self.assertEqual(metas[key], value, key)
                self.assertTrue(metas['og:image:alt'].strip())
                self.assertEqual(metas['twitter:image:alt'], metas['og:image:alt'])
                self.assertIn('By <span>' + author + '</span>', doc.text)
                self.assertEqual([a['href'] for t, a in doc.elements if t == 'link' and a.get('rel') == 'canonical'], [base + route])
                blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc.text, re.S)
                self.assertEqual(len(blocks), 1)
                graph = json.loads(blocks[0])
                self.assertEqual(graph['@context'], 'https://schema.org')
                nodes = graph['@graph']
                by_id = {n['@id']: n for n in nodes}
                self.assertEqual(len(by_id), len(nodes))
                self.assertEqual({n['@type'] for n in nodes}, {'Person', 'Organization', 'Brand', 'WebSite', 'BreadcrumbList', 'CollectionPage' if route == '/templates/' else 'WebPage' if route == '/' else 'TechArticle'} | ({'VideoObject'} if route == '/' else {'ItemList'} if route == '/templates/' else set()))
                def refs(value):
                    if isinstance(value, dict):
                        if set(value) == {'@id'}:
                            self.assertIn(value['@id'], by_id)
                        for child in value.values():
                            refs(child)
                    elif isinstance(value, list):
                        for child in value:
                            refs(child)
                refs(graph)
                self.assertEqual(by_id[base + '/#author']['name'], author)
                node = by_id[base + route + '#page']
                self.assertEqual(node['url'], base + route)
                self.assertEqual(node['name'], title)
                self.assertEqual(node['description'], page['description'])
                self.assertEqual(node['author'], {'@id': base + '/#author'})
                self.assertEqual(node['isPartOf'], {'@id': base + '/#website'})
                crumbs = by_id[base + route + '#breadcrumb']['itemListElement']
                self.assertEqual([x['position'] for x in crumbs], list(range(1, len(crumbs) + 1)))
                self.assertEqual(crumbs[0], {'@type': 'ListItem', 'position': 1, 'name': 'MDAAI', 'item': base + '/'})
                self.assertEqual(len(crumbs), 1 if route == '/' else 2)
                self.assertEqual(crumbs[-1]['item'], base + route)
                if route != '/':
                    self.assertEqual(crumbs[-1]['name'], page['title'])
                if route == '/templates/':
                    _, catalog, _ = build.load_catalog(build.SITE)
                    listing = by_id[base + route + '#templates']
                    self.assertEqual(node['mainEntity'], {'@id': listing['@id']})
                    self.assertEqual(listing['@type'], 'ItemList')
                    self.assertEqual(listing['itemListElement'], [
                        {'@type': 'ListItem', 'position': i, 'name': t['title'],
                         'url': 'https://github.com/' + t['source']['repository']}
                        for i, t in enumerate(catalog['templates'], 1)])
                    self.assertNotIn('Product', {n['@type'] for n in nodes})
                videos = [n for n in nodes if n['@type'] == 'VideoObject']
                self.assertEqual(len(videos), int(route == '/'))
                if videos:
                    video = videos[0]
                    self.assertEqual(node['video'], {'@id': video['@id']})
                    self.assertEqual(video['creator'], {'@id': base + '/#author'})
                    self.assertEqual(video['isPartOf'], {'@id': node['@id']})
                    self.assertEqual(video['duration'], 'PT1M31.3S')
                    from datetime import datetime
                    self.assertEqual(datetime.fromisoformat(video['uploadDate']).date().isoformat(), '2026-10-04')
                    if 'T' in video['uploadDate']:
                        self.assertIsNotNone(datetime.fromisoformat(video['uploadDate']).tzinfo)
                    for key, suffix in [('contentUrl', '.mp4'), ('thumbnailUrl', '.png')]:
                        self.assertTrue(video[key].startswith(base + '/assets/media/'))
                        path = build.OUT / urlsplit(video[key]).path.lstrip('/')
                        self.assertEqual(path.suffix, suffix)
                        self.assertTrue(path.is_file())
        self.assertEqual(len(set(titles)), 7)
        self.assertEqual(len(set(descriptions)), 7)
        not_found = self.documents['/404.html']
        self.assertIn(('meta', {'name': 'robots', 'content': 'noindex,follow'}), not_found.elements)
        self.assertFalse(any(t == 'link' and a.get('rel') == 'canonical' for t, a in not_found.elements))
        self.assertNotIn('application/ld+json', not_found.text)

    def test_owner_video_intro_immediately_precedes_video(self):
        home = self.documents['/'].text
        match = re.search(r'<section id="explainer">(.*?)</section>', home, re.S)
        self.assertIsNotNone(match)
        assert match is not None
        section = match.group(1)
        expected = '<h2><a class="heading-anchor" href="#explainer">Having difficulty reading? Watch the 91-second overview.</a></h2><p>Narration and captions offer another way to explore the two template families.</p><video '
        self.assertIn(expected, section)
        self.assertTrue(section.startswith(expected))
        intro = next(p for p in self.pages if p['route'] == '/').get('videoIntro')
        self.assertEqual(intro, {'heading': 'Having difficulty reading? Watch the 91-second overview.', 'supportingLine': 'Narration and captions offer another way to explore the two template families.'})
        for route, doc in self.documents.items():
            if route != '/':
                self.assertNotIn('Having difficulty reading? Watch the 91-second overview.', doc.text)

    def test_images_video_captions_and_manifest(self):
        def png_size(path):
            data = path.read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(data[8:16], b'\x00\x00\x00\rIHDR')
            return struct.unpack('>II', data[16:24])
        self.assertEqual(png_size(build.OUT / 'assets/og.png'), (1200, 630))
        self.assertEqual(png_size(build.OUT / 'assets/media/thumbnail.png'), (1080, 1080))
        for route, doc in self.documents.items():
            videos = [a for t, a in doc.elements if t == 'video']
            self.assertEqual(len(videos), int(route == '/'))
            if videos:
                self.assertIn('controls', videos[0])
                self.assertIn('playsinline', videos[0])
                self.assertEqual(videos[0]['preload'], 'metadata')
                self.assertTrue(videos[0]['aria-label'])
                tracks = [a for t, a in doc.elements if t == 'track']
                self.assertEqual(len(tracks), 1)
                self.assertEqual(tracks[0]['kind'], 'captions')
                self.assertEqual(tracks[0]['srclang'], 'en')
                self.assertIn('default', tracks[0])
                vtt = (build.OUT / tracks[0]['src'].lstrip('/')).read_text()
                self.assertTrue(vtt.startswith('WEBVTT'))
                cues = re.findall(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})', vtt)
                self.assertTrue(cues)
                last = 0
                for start, end in cues:
                    def seconds(value):
                        h, m, s = value.split(':')
                        return int(h) * 3600 + int(m) * 60 + float(s)
                    self.assertGreaterEqual(seconds(start), last)
                    self.assertGreater(seconds(end), seconds(start))
                    last = seconds(end)
                self.assertLessEqual(last, 91.4)
        mp4 = (build.OUT / 'assets/media/mdaai-original-and-2.mp4').read_bytes()
        self.assertEqual(mp4[4:8], b'ftyp')
        self.assertGreater(len(mp4), 100000)
        self.assertIn('-->', (build.OUT / 'assets/media/mdaai-original-and-2.srt').read_text())
        manifest = json.loads((build.OUT / 'site.webmanifest').read_text())
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual(manifest['display'], 'standalone')
        for icon in manifest['icons']:
            width, height = map(int, icon['sizes'].split('x'))
            self.assertEqual(icon['type'], 'image/png')
            self.assertEqual(png_size(build.OUT / icon['src'].lstrip('/')), (width, height))
        self.assertEqual({i['sizes'] for i in manifest['icons']}, {'192x192', '512x512'})

    def test_sitemap_robots_and_inline_script_policy(self):
        base = 'https://www.mdaai.internet.technology'
        root = ET.fromstring((build.OUT / 'sitemap.xml').read_text())
        locations = [n.text for n in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(set(locations), {base + p['route'] for p in self.pages})
        self.assertEqual(len(locations), 7)
        self.assertEqual((build.OUT / 'robots.txt').read_text(), 'User-agent: *\nAllow: /\nSitemap: ' + base + '/sitemap.xml\n')
        for html in ('<script>alert(1)</script>', '<button onclick="evil()">x</button>', '<img onerror="evil()">'):
            with self.assertRaises(AssertionError):
                Document(html)
        Document('<script type="application/ld+json">{"@context":"https://schema.org"}</script>')
        import base64
        csp = (build.SITE / 'csp-header.conf').read_text()
        self.assertNotIn("'unsafe-inline'", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertIn("media-src 'self'", csp)
        for doc in self.documents.values():
            for data in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc.text, re.S):
                digest = base64.b64encode(hashlib.sha256(data.encode()).digest()).decode()
                self.assertIn("'sha256-" + digest + "'", csp)

    def test_http_routes_and_genuine_404(self):
        from functools import partial
        server = serve.ThreadingHTTPServer(('127.0.0.1',0),partial(serve.Handler,directory=str(build.OUT)))
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            for route in self.documents:
                with urlopen(base + route) as response:
                    self.assertEqual(response.status,200)
                    self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
            with urlopen(base + '/task-lifecycle') as response:
                self.assertTrue(response.url.endswith('/task-lifecycle/'))
            for route in ('/missing/','/README.md','/assets/','/docs/','/docs/quickstart/','/onion-governance/','/%2e%2e/README.md'):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(base + route)
                self.assertEqual(caught.exception.code,404)
                self.assertIn(b'Page not found',caught.exception.read())
                caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main(verbosity=2)
