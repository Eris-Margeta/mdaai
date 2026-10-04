"""Canonical metadata for the curated publication; no ranking promises."""
import html
import json
from identity import icon_metadata, social_assets

BASE = 'https://www.mdaai.internet.technology'
AUTHOR = 'Eris Margeta Kurdali'


def graph(title, description, route):
    person = {'@type': 'Person', '@id': BASE + '/#author', 'name': AUTHOR}
    studio = {'@type': 'Organization', '@id': 'https://tejl.hr/#organization', 'name': 'TEJL Studio', 'url': 'https://tejl.hr/', 'sameAs': ['https://tejl.com/']}
    brand = {'@type': 'Brand', '@id': BASE + '/#brand', 'name': 'MDAAI', 'url': BASE + '/', 'logo': BASE + '/assets/identity/icon-512.png'}
    site = {'@type': 'WebSite', '@id': BASE + '/#website', 'url': BASE + '/', 'name': 'MDAAI', 'inLanguage': 'en', 'author': {'@id': person['@id']}, 'publisher': {'@id': person['@id']}, 'about': {'@id': brand['@id']}, 'creator': {'@id': studio['@id']}, 'maintainer': {'@id': studio['@id']}}
    page = {'@type': 'WebPage' if route == '/' else 'TechArticle', '@id': BASE + route + '#page', 'url': BASE + route, 'name': title + ' · MDAAI', 'description': description, 'inLanguage': 'en', 'isPartOf': {'@id': site['@id']}, 'author': {'@id': person['@id']}, 'breadcrumb': {'@id': BASE + route + '#breadcrumb'}}
    items = [{'@type': 'ListItem', 'position': 1, 'name': 'MDAAI', 'item': BASE + '/'}]
    if route != '/':
        items.append({'@type': 'ListItem', 'position': 2, 'name': title, 'item': BASE + route})
    breadcrumbs = {'@type': 'BreadcrumbList', '@id': BASE + route + '#breadcrumb', 'itemListElement': items}
    objects = [person, studio, brand, site, page, breadcrumbs]
    if route == '/':
        video = {'@type': 'VideoObject', '@id': BASE + '/#explainer', 'name': 'MDAAI: original and 2.0', 'description': 'A technical file-map explainer showing the original MDAAI template, the MDAAI 2.0 portable core, file relationships and evidence-backed task completion.', 'thumbnailUrl': BASE + '/assets/media/thumbnail.png', 'contentUrl': BASE + '/assets/media/mdaai-original-and-2.mp4', 'duration': 'PT1M31.3S', 'uploadDate': '2026-10-04', 'inLanguage': 'en', 'creator': {'@id': person['@id']}, 'isPartOf': {'@id': page['@id']}}
        objects.append(video)
        page['video'] = {'@id': video['@id']}
    return {'@context': 'https://schema.org', '@graph': objects}


def metadata(title, description, route):
    if route is None:
        return '<meta name="robots" content="noindex,follow">' + icon_metadata()
    escape = html.escape
    url = BASE + route
    assets = social_assets(route)
    data = json.dumps(graph(title, description, route), ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    tags = [f'<link rel="canonical" href="{url}">', f'<meta name="author" content="{AUTHOR}">']
    def meta(key, value, property=False):
        attribute = 'property' if property else 'name'
        tags.append(f'<meta {attribute}="{key}" content="{escape(str(value), quote=True)}">')
    for key, value in [('og:type', 'website' if route == '/' else 'article'), ('og:site_name', 'MDAAI'), ('og:locale', 'en_US'), ('og:title', title + ' · MDAAI'), ('og:description', description), ('og:url', url)]:
        meta(key, value, True)
    # Ordered OG records: reliable PNG first, correctly typed GIF alternate second.
    for variant, mime, alt in [('static', 'image/png', assets['alt']), ('animated', 'image/gif', assets['alt'] + ' — animated alternate; platform playback varies')]:
        for key, value in [('og:image', BASE + assets[variant]), ('og:image:secure_url', BASE + assets[variant]), ('og:image:type', mime), ('og:image:width', '1200'), ('og:image:height', '630'), ('og:image:alt', alt)]:
            meta(key, value, True)
    for key, value in [('twitter:card', 'summary_large_image'), ('twitter:title', title + ' · MDAAI'), ('twitter:description', description), ('twitter:image', BASE + assets['large']), ('twitter:image:alt', assets['alt'])]:
        meta(key, value)
    tags.append(icon_metadata())
    tags.append(f'<script type="application/ld+json">{data}</script>')
    return ''.join(tags)


def video_section(intro):
    return f'''<section id="explainer"><p>A technical overview of the original template and MDAAI 2.0. The endpoint example is illustrative, not a product implementation claim.</p><h2><a class="heading-anchor" href="#explainer">{html.escape(intro['heading'])}</a></h2><p>{html.escape(intro['supportingLine'])}</p><video controls preload="metadata" playsinline width="1080" height="1080" poster="/assets/media/thumbnail.png" class="explainer-video" aria-label="MDAAI original and 2.0 technical explainer"><source src="/assets/media/mdaai-original-and-2.mp4" type="video/mp4"><track kind="captions" src="/assets/media/mdaai-original-and-2.vtt" srclang="en" label="English" default>Your browser does not support HTML video. <a href="/assets/media/mdaai-original-and-2.mp4">Download the explainer</a>.</video><p>English narration and captions · 1080 × 1080 · 1 min 31.3 sec. <a href="/assets/media/mdaai-original-and-2.srt">Download captions (SRT)</a>.</p></section>'''
