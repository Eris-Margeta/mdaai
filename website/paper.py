"""Approved final preprint metadata and explicit PDF publication allowlist."""
from pathlib import Path
import hashlib
import html
import json

DATA = Path(__file__).with_name('paper.json')


def load(site=None):
    root = Path(site) if site is not None else DATA.parent
    data = json.loads((root / 'paper.json').read_text())
    expected = {'assets/paper/mdaai-paper-soft.pdf'}
    if {item['path'] for item in data['files']} != expected or len(data['files']) != 1:
        raise ValueError('Paper asset allowlist drift')
    for item in data['files']:
        path = root / item['path']
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Approved paper asset drift')
    return data


def downloads(site=None, home=False):
    data = load(site)
    soft = data['files'][0]
    primary = '<a class="button primary" href="/' + soft['path'] + '" download>Download paper (PDF)</a>'
    note = '<p>Three pages · Preprint / documentary design paper · ' + html.escape(data['author']) + ' · Published ' + data['datePublished'] + '. Soft edition: simulated print finish, not a genuine scan.</p>'
    if home:
        return '<section id="paper"><h2><a class="heading-anchor" href="#paper">Read the paper</a></h2><p>' + html.escape(data['title']) + '</p>' + primary + '<p><a href="/paper/">Abstract and author →</a></p>' + note + '</section>'
    return '<div class="paper-downloads">' + primary + '</div>' + note


def article(base):
    data = load()
    affiliation = {'@type': 'Organization', 'name': data['affiliation'], 'url': 'https://tejl.hr/', 'sameAs': ['https://tejl.com/']}
    return {'@type': 'ScholarlyArticle', '@id': base + '/paper/#article', 'url': base + '/paper/', 'mainEntityOfPage': base + '/paper/',
            'name': data['title'], 'headline': data['title'], 'abstract': data['abstract'], 'description': data['abstract'],
            'author': {'@type': 'Person', 'name': data['author'], 'email': data['email'], 'affiliation': affiliation},
            'datePublished': data['datePublished'], 'dateModified': data['dateModified'], 'inLanguage': 'en', 'keywords': data['keywords'],
            'encoding': [{'@type': 'MediaObject', 'name': 'Paper PDF', 'encodingFormat': 'application/pdf', 'contentUrl': base + '/' + item['path'], 'contentSize': str(item['bytes']) + ' bytes'} for item in data['files']]}


def citations(base):
    data = load()
    soft = data['files'][0]
    values = {'citation_title': data['title'], 'citation_author': data['author'], 'citation_publication_date': data['datePublished'].replace('-', '/'), 'citation_pdf_url': base + '/' + soft['path']}
    return ''.join('<meta name="' + key + '" content="' + html.escape(value, quote=True) + '">' for key, value in values.items())
