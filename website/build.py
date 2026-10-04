"""Allowlisted static build. Never copies repository documentation/evidence."""
from pathlib import Path
import hashlib
import html
import json
import re
import base64
from seo import metadata, video_section, graph, BASE, AUTHOR

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'website'
OUT = SITE / 'dist'
E = html.escape


def layer_diagram():
    return '<figure class="file-flow"><div class="flow-row"><span>AGENTS.md</span> → <span>Assigned TASKS.json row</span> → <span>scopeRef + relevant rules</span></div><div class="flow-row"><span>Authorized implementation</span> → <span>Actual evidence / conditional ADR</span> → <span>Task update + history</span></div><figcaption>Read instructions and current task before work; write evidence and update the canonical task afterward. Arrows describe information flow, not an automatic executor.</figcaption></figure>'


def header():
    return '<a class="skip" href="#main">Skip to content</a><header class="header"><a class="brand" href="/">MDAAI</a><span class="header-note">Repository documentation</span><div class="tools"><button class="search-open" type="button">Search <kbd>⌘ K</kbd></button><button class="theme" type="button" aria-label="Switch color theme">◐</button><button class="menu" type="button" aria-label="Toggle documentation navigation" aria-expanded="false" aria-controls="docs-nav">☰</button></div></header>'


def footer():
    return '<footer class="footer"><p>MDAAI · Repository operating protocol</p><section class="tejl" aria-label="Website creation and TEJL contact"><span>WEB made by</span><a href="https://tejl.hr/" aria-label="TEJL — tejl.hr"><img src="/assets/tejl-logo.svg" width="74" height="38" alt="TEJL"></a><a href="https://tejl.hr/">tejl.hr</a><a href="https://tejl.com/">tejl.com</a><a href="tel:+385****1079">+385 99 836 1079</a></section></footer>'


def shell(title, description, body, cls='', route=None):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · MDAAI</title><meta name="description" content="{E(description)}">{metadata(title, description, route)}<meta name="color-scheme" content="light dark"><link rel="icon" href="/assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css"><link rel="stylesheet" href="/assets/publication.css"><script src="/assets/app.js" defer></script></head><body class="{cls}">{header()}{body}{footer()}<dialog id="search-dialog" aria-labelledby="search-title"><div class="search-heading"><h2 id="search-title">Search documentation</h2><button id="search-close" type="button" aria-label="Close search">×</button></div><label for="search-input">Find a file, relationship or task rule</label><input id="search-input" type="search" autocomplete="off" placeholder="Try TASKS.json or supersession"><p id="search-status" role="status" aria-live="polite">Search runs locally. No query leaves your browser.</p><div id="search-results"></div><small>↑ ↓ move · Enter open · Esc close</small></dialog></body></html>'''



def load_content():
    pages = json.loads((SITE / 'content.json').read_text())
    provenance = json.loads((SITE / 'provenance.json').read_text())
    if hashlib.sha256((SITE / 'content.json').read_bytes()).hexdigest() != provenance['contentSha256']:
        raise ValueError('Reviewed content changed: source review and provenance refresh required')
    references = {s for p in pages for s in p['sources']}
    if references != set(provenance['sourceReferences']):
        raise ValueError('Source-reference coverage drift')
    for source, digest in provenance['sourceReferences'].items():
        if '..' in source or '/Users/' in source or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('Unsafe logical source reference')
    for asset, digest in provenance['assets'].items():
        path = (SITE / asset).resolve()
        if not path.is_relative_to((SITE / 'assets').resolve()) or path.is_symlink():
            raise ValueError('Unsafe asset path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Reviewed asset changed: ' + asset)
    for page in pages:
        if not re.fullmatch('[a-z0-9-]+', page['slug']):
            raise ValueError('unsafe slug')
        if not re.fullmatch(r'/(?:[a-z0-9-]+/)*', page['route']):
            raise ValueError('unsafe route')
    return pages


def build():
    pages = load_content()
    # Only owned disposable build output is replaced; source/history remain intact.
    if OUT.is_symlink():
        raise ValueError('output symlink refused')
    import shutil
    if OUT.exists():
        for item in OUT.rglob('*'):
            if item.is_symlink():
                raise ValueError('output symlink refused')
        shutil.rmtree(OUT)
    OUT.mkdir()
    assets = OUT / 'assets'
    assets.mkdir(exist_ok=True)
    # Explicit assets only, no recursive repository copy.
    for asset in json.loads((SITE / 'provenance.json').read_text())['assets']:
        destination = OUT / asset
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((SITE / asset).read_bytes())
    routes = {p['slug']: p['route'] for p in pages}
    search = []
    nav = ''
    previous_group = None
    for page in pages:
        if page['group'] != previous_group:
            nav += f'<p class="nav-group">{E(page["group"])}</p>'
            previous_group = page['group']
        nav += f'<a href="{page["route"]}">{E("What it is" if page["route"] == "/" else page["title"])}</a>'
    for i, page in enumerate(pages):
        url = page['route']
        current_nav = nav.replace(f'href="{url}"', f'href="{url}" aria-current="page"')
        sections = ''
        toc = ''
        for section in page['sections']:
            anchor = section['id']
            if not re.fullmatch('[a-z0-9-]+', anchor):
                raise ValueError('unsafe anchor')
            toc += f'<a href="#{anchor}">{E(section["title"])}</a>'
            sections += f'<section id="{anchor}"><h2><a class="heading-anchor" href="#{anchor}">{E(section["title"])}</a></h2><p>{E(section["text"])}</p>'
            if section.get('diagram'):
                sections += layer_diagram()
            if anchor == 'file-map':
                sections += '<div class="file-map-grid">'
            if section.get('code'):
                sections += f'<div class="code-block"><div class="code-top"><span>{E(section["language"])}</span><button class="copy" type="button">Copy</button></div><pre><code>{E(section["code"])}</code></pre><span class="copy-status" role="status"></span></div>'
            if section.get('table'):
                table = section['table']
                file_links = dict(section.get('links', [])) if anchor == 'file-map' else {}
                def cell(value):
                    if value in file_links:
                        fragment = file_links[value].split('#', 1)[1]
                        return '<td><a href="#' + fragment + '"><code>' + E(value) + '</code></a></td>'
                    return '<td>' + E(value) + '</td>'
                sections += '<div class="table-scroll" role="region" aria-label="' + E(section['title']) + ' table" tabindex="0"><table><thead><tr>' + ''.join('<th scope="col">' + E(h) + '</th>' for h in table['headers']) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(cell(c) for c in row) + '</tr>' for row in table['rows']) + '</tbody></table></div>'
            if anchor == 'file-map':
                sections += '</div>'
            for label, target in ([] if anchor == 'file-map' else section.get('links', [])):
                slug, _, fragment = target.partition('#')
                href = routes[slug] + ('#' + fragment if fragment else '')
                sections += f'<a class="inline-link" href="{href}">{E(label)} →</a>'
            sections += '</section>'
            search.append({'title': page['title'], 'heading': section['title'], 'text': section['text'] + ' ' + section.get('code', '') + ' ' + ' '.join(' '.join(row) for row in section.get('table', {}).get('rows', [])), 'url': url + '#' + anchor})
        pagination = '<nav class="pagination" aria-label="Adjacent pages">'
        for label, idx in [('← Previous', i-1), ('Next →', i+1)]:
            if 0 <= idx < len(pages):
                p = pages[idx]
                pagination += f'<a href="{p["route"]}"><small>{label}</small>{E(p["title"])}</a>'
        pagination += '</nav>'
        source_note = '<details class="source-note"><summary>Source references</summary><p>Based on original contracts and templates. These are source locations, not installed-file claims. No private source archives are served.</p><ul>' + ''.join(f'<li><code>{E(s.replace('../MDAAI-2-0/', 'MDAAI 2.0: ').replace('../MDAAI-MONOREPO/repo-template/', 'First-generation template: '))}</code></li>' for s in page['sources']) + '</ul></details>'
        author = f'<p class="source-note">By <span>{AUTHOR}</span> · <a href="https://github.com/Eris-Margeta/mdaai">Repository</a></p>'
        video = video_section(page['videoIntro']) if url == '/' else ''
        if video:
            toc += '<a href="#explainer">Video explainer</a>'
        body = f'<div class="docs-layout"><aside id="docs-nav"><nav aria-label="Documentation">{current_nav}</nav></aside><main id="main" class="article" tabindex="-1"><h1>{E(page["title"])}</h1><p class="lede">{E(page["description"])}</p>{author}{sections}{video}{source_note}{pagination}</main><aside class="toc"><nav aria-label="On this page"><p>On this page</p>{toc}</nav></aside></div>'
        target = OUT / page['route'].strip('/')
        target.mkdir(parents=True, exist_ok=True)
        (target / 'index.html').write_text(shell(page['title'], page['description'], body, 'docs', url))
    (assets / 'search.json').write_text(json.dumps(search, ensure_ascii=False))
    (OUT / '404.html').write_text(shell('Page not found', 'This route is not part of the documentation.', '<main id="main" class="not-found"><h1>Page not found</h1><p>The page may have moved, or the address may be incorrect.</p><a class="button primary" href="/">Go to documentation →</a></main>'))
    (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{BASE}{p["route"]}</loc></url>' for p in pages) + '</urlset>')
    (OUT / 'site.webmanifest').write_text(json.dumps({'name': 'MDAAI Documentation', 'short_name': 'MDAAI', 'start_url': '/', 'display': 'standalone', 'background_color': '#f7f6f2', 'theme_color': '#0b5146', 'icons': [{'src': '/assets/icon-192.png', 'sizes': '192x192', 'type': 'image/png'}, {'src': '/assets/icon-512.png', 'sizes': '512x512', 'type': 'image/png'}]}))
    hashes = []
    for file in OUT.rglob('*.html'):
        for data in re.findall(r'<script type="application/ld\+json">(.*?)</script>', file.read_text(), re.S):
            hashes.append("'sha256-" + base64.b64encode(hashlib.sha256(data.encode()).digest()).decode() + "'")
    csp = "default-src 'self'; script-src 'self' " + ' '.join(hashes) + "; style-src 'self'; img-src 'self'; media-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    (SITE / 'csp-header.conf').write_text('add_header Content-Security-Policy "' + csp + '" always;\n')
    expected = {'index.html', '404.html', 'robots.txt', 'sitemap.xml', 'site.webmanifest', 'assets/search.json'} | {(p['route'].strip('/') + '/index.html').lstrip('/') for p in pages} | set(json.loads((SITE / 'provenance.json').read_text())['assets'])
    for file in OUT.rglob('*'):
        if file.is_file() and str(file.relative_to(OUT)) not in expected:
            raise ValueError('Unexpected production output; inspect and remove explicitly: ' + str(file))
    print(f'Built {len(pages)} documentation pages, separate 404 and {len(search)} searchable sections.')


if __name__ == '__main__':
    build()
