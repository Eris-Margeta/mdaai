"""Canonical metadata for the curated publication; no ranking promises."""
import html
import json

BASE = 'https://www.mdaai.internet.technology'
AUTHOR = 'Eris Margeta Kurdali'
IMAGE = BASE + '/assets/og.png'
ALT = 'MDAAI — repository-based operating protocol; contracts, tasks and evidence'


def graph(title, description, route):
    person = {'@type': 'Person', '@id': BASE + '/#author', 'name': AUTHOR}
    site = {'@type': 'WebSite', '@id': BASE + '/#website', 'url': BASE + '/', 'name': 'MDAAI', 'inLanguage': 'en', 'author': {'@id': person['@id']}}
    page = {'@type': 'WebPage' if route == '/' else 'TechArticle', '@id': BASE + route + '#page', 'url': BASE + route, 'name': title + ' · MDAAI', 'description': description, 'inLanguage': 'en', 'isPartOf': {'@id': site['@id']}, 'author': {'@id': person['@id']}, 'breadcrumb': {'@id': BASE + route + '#breadcrumb'}}
    items = [{'@type': 'ListItem', 'position': 1, 'name': 'MDAAI', 'item': BASE + '/'}]
    if route != '/':
        items.append({'@type': 'ListItem', 'position': 2, 'name': title, 'item': BASE + route})
    breadcrumbs = {'@type': 'BreadcrumbList', '@id': BASE + route + '#breadcrumb', 'itemListElement': items}
    objects = [person, site, page, breadcrumbs]
    if route == '/':
        video = {'@type': 'VideoObject', '@id': BASE + '/#explainer', 'name': 'MDAAI: original and 2.0', 'description': 'A technical file-map explainer showing the original MDAAI template, the MDAAI 2.0 portable core, file relationships and evidence-backed task completion.', 'thumbnailUrl': BASE + '/assets/media/thumbnail.png', 'contentUrl': BASE + '/assets/media/mdaai-original-and-2.mp4', 'duration': 'PT1M31.3S', 'uploadDate': '2026-10-04', 'inLanguage': 'en', 'creator': {'@id': person['@id']}, 'isPartOf': {'@id': page['@id']}}
        objects.append(video)
        page['video'] = {'@id': video['@id']}
    return {'@context': 'https://schema.org', '@graph': objects}


def metadata(title, description, route):
    if route is None:
        return '<meta name="robots" content="noindex,follow">'
    escape = html.escape
    url = BASE + route
    data = json.dumps(graph(title, description, route), ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return f'''<link rel="canonical" href="{url}"><meta name="author" content="{AUTHOR}"><meta property="og:type" content="{'website' if route == '/' else 'article'}"><meta property="og:site_name" content="MDAAI"><meta property="og:locale" content="en_US"><meta property="og:title" content="{escape(title)} · MDAAI"><meta property="og:description" content="{escape(description)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{IMAGE}"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{ALT}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)} · MDAAI"><meta name="twitter:description" content="{escape(description)}"><meta name="twitter:image" content="{IMAGE}"><meta name="twitter:image:alt" content="{ALT}"><link rel="manifest" href="/site.webmanifest"><script type="application/ld+json">{data}</script>'''


def video_section():
    return '''<section id="explainer"><h2><a class="heading-anchor" href="#explainer">MDAAI in 91 seconds</a></h2><p>A technical overview of the original template and MDAAI 2.0. The endpoint example is illustrative, not a product implementation claim.</p><video controls preload="metadata" playsinline width="1080" height="1080" poster="/assets/media/thumbnail.png" class="explainer-video" aria-label="MDAAI original and 2.0 technical explainer"><source src="/assets/media/mdaai-original-and-2.mp4" type="video/mp4"><track kind="captions" src="/assets/media/mdaai-original-and-2.vtt" srclang="en" label="English" default>Your browser does not support HTML video. <a href="/assets/media/mdaai-original-and-2.mp4">Download the explainer</a>.</video><p>English narration and captions · 1080 × 1080 · 1 min 31.3 sec. <a href="/assets/media/mdaai-original-and-2.srt">Download captions (SRT)</a>.</p></section>'''
