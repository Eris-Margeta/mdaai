"""Release contracts for reviewed catalog, cumulative governance and runtime pin."""
from pathlib import Path
import json
import re
import unittest
import build
import templates_feed as feed

ROOT = build.ROOT


class ReleaseTests(unittest.TestCase):
    def test_exact_python_contract(self):
        version = (ROOT / '.python-version').read_text().strip()
        self.assertEqual(version, '3.13.14')
        lock, catalog, files = feed.load_catalog()
        import hashlib
        for template in catalog['templates']:
            pin = next(f for f in template['files'] if f['path'].endswith('/.python-version'))
            self.assertEqual(pin['sha256'], hashlib.sha256((version + '\n').encode()).hexdigest())
        docker = (ROOT / 'Dockerfile').read_text()
        self.assertIn('FROM python:' + version + '-alpine', docker)
        self.assertNotRegex(docker, r'python:3\.(?:12|13)-')
        for path in (ROOT / '.github/workflows').glob('*.y*ml'):
            text = path.read_text()
            if 'actions/setup-python' in text:
                self.assertIn("python-version-file: '.python-version'", text)
                self.assertNotRegex(text, r'python-version:\s*[\"\x27]?3\.')
        just = (ROOT / 'Justfile').read_text()
        self.assertIn('trim(read(".python-version"))', just)
        self.assertNotRegex(just, r'^    python3 -B website/', re.M)

    def test_no_claude_payload_or_active_website(self):
        lock, catalog, files = feed.load_catalog()
        for path in files:
            self.assertNotEqual(Path(path).name.casefold(), 'claude.md')
        for path in (ROOT / 'website/content.json', ROOT / 'README.md'):
            self.assertNotIn('claude.md', path.read_text().casefold())
        for path in build.OUT.rglob('*.html'):
            self.assertNotIn('claude.md', path.read_text().casefold())
        self.assertIn('For any agent system, point its entry instructions to the nearest AGENTS.md. Applicable parent and scoped governance files are cumulative.', (ROOT / 'README.md').read_text())

    def test_canonical_links_license_and_counts(self):
        lock, catalog, files = feed.load_catalog()
        text = (build.OUT / 'templates/index.html').read_text()
        self.assertIn(str(len(files)) + ' files', text)
        for template in catalog['templates']:
            self.assertIn('href="https://github.com/' + template['source']['repository'] + '"', text)
            self.assertIn(template['source']['revision'], text)
            self.assertIn(template['license'], text)
            self.assertIn(template['templateVersion'], text)

    def test_cover_dimensions_credit_and_placement(self):
        data = (ROOT / "website/assets/brand/mdaai-guardian-cover.webp").read_bytes()
        self.assertEqual(data[:4], b"RIFF")
        self.assertEqual(data[8:12], b"WEBP")
        self.assertEqual(data[12:16], b"VP8L")
        self.assertEqual(data[20], 0x2f)
        bits = int.from_bytes(data[21:25], "little")
        self.assertEqual(((bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1), (1000, 1300))
        import hashlib
        self.assertEqual(hashlib.sha256(data).hexdigest(), "fee7149b09f5fdc922646a1356026af2bc0747dc586aa579b4842d977d82f22d")
        html = (build.OUT / "index.html").read_text()
        self.assertIn("coiled mythical guardian and E.M.K. credit", html)
        self.assertLess(html.index("<h1>"), html.index("documentation-cover"))
        self.assertIn('class="homepage-intro"', html)
        import html as html_parser
        self.assertIn("inspired by o'reily's book covers", html_parser.unescape(html))
        self.assertEqual(html.count('<h1>'), 1)
        for page in build.OUT.rglob('index.html'):
            if page != build.OUT / 'index.html':
                self.assertNotIn('class="homepage-intro"', page.read_text())
        self.assertIn("Eris Margeta Kurdali", html)
        self.assertIn("AI-generated mythical guardian", html)
        self.assertNotIn("Iconographia Zoologica", html)

    def test_logo_variants_and_manual_theme(self):
        import xml.etree.ElementTree as ET
        for name, fill in [('logo-black.svg', '#000'), ('logo-white.svg', '#fff')]:
            raw = (ROOT / 'website/assets/brand' / name).read_text()
            ET.fromstring(raw)
            self.assertIn(fill, raw.lower())
            self.assertIn('/assets/brand/' + name, (build.OUT / 'index.html').read_text())
        css = (ROOT / 'website/assets/publication.css').read_text()
        self.assertIn('[data-theme="dark"] .logo-light{display:none}', css)
        self.assertIn('[data-theme="light"] .logo-dark{display:none}', css)


if __name__ == '__main__':
    unittest.main(verbosity=2)
