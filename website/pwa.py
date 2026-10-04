"""Deterministic public PWA output. Call write_pwa(dist) after rendering all pages.

Parent integration: link /assets/pwa.js with defer on every page. Serve the root
worker with Cache-Control: no-cache and application/javascript (not immutable).
Identity/manifest/CSP and production headers remain parent-owned acceptance gates.
"""
from hashlib import sha256
from pathlib import Path
import json

OFFLINE = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MDAAI — Offline</title><body><main id="main"><h1>MDAAI is offline</h1><p>Previously opened documentation may still be available. This page has not been saved for offline reading.</p><p>Reconnect, then try this address again. No form submission has been sent.</p><a href="/">Return to MDAAI documentation</a></main></body></html>'''


def write_pwa(output):
    """Write a root-scoped worker and offline page; return content revision.

    Only public rendered HTML and essential local JS/CSS are eligible. Assets
    are cached lazily, never the video/identity media corpus. No output timestamps.
    """
    root = Path(output)
    assets = Path(__file__).parent / 'assets'
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    (root / 'assets/pwa.js').write_bytes((assets / 'pwa.js').read_bytes())
    (root / 'offline.html').write_text(OFFLINE, encoding='utf-8')
    eligible = sorted(p for p in root.rglob('*') if p.is_file() and
                      (p.suffix == '.html' or (p.suffix in ('.css', '.js') and 'assets' in p.relative_to(root).parts)) and
                      p.name != 'service-worker.js' and p.stat().st_size <= 512 * 1024)
    digest = sha256()
    urls = []
    for path in eligible:
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode() + b'\0' + path.read_bytes() + b'\0')
        urls.append('/' + (rel[:-10] if rel.endswith('index.html') else rel))
    template = (assets / 'service-worker.js').read_text(encoding='utf-8')
    digest.update(template.encode())
    revision = digest.hexdigest()[:24]
    (root / 'service-worker.js').write_text(template.replace('__REVISION__', revision).replace('__PUBLIC_URLS__', json.dumps(urls)), encoding='utf-8')
    return revision
