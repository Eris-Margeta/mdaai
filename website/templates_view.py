"""Escaped catalog presentation; no fetched instruction is executed."""
from html import escape as E
from templates_feed import REPOSITORY


def cycle(content):
    steps = ''.join(f'<li><span class="cycle-number">{i:02}</span><span>{E(step)}</span></li>' for i, step in enumerate(content['steps'], 1))
    return f'<section id="template-cycle" class="template-cycle" aria-labelledby="cycle-title"><p class="cycle-eyebrow">PROTOCOL → PRACTICE → PROGRESS</p><h2 id="cycle-title">{E(content["title"])}</h2><p>{E(content["text"])}</p><ol class="cycle-steps">{steps}</ol><p class="cycle-note">{E(content["note"])}</p><a class="cycle-link" href="/templates/">{E(content["link"])} <span aria-hidden="true">↗</span></a></section>'


def gallery(lock, catalog, content, include=False):
    base = f'https://github.com/{REPOSITORY}/blob/{lock["revision"]}/'
    result = '<p class="catalog-pin">Reviewed catalog commit <a href="' + base + 'templates.json"><code>' + E(lock['revision']) + '</code></a> · ' + str(lock['fileCount']) + ' files</p>'
    result += '<p>' + E(content['included'] if include else content['remote']) + '</p>'
    result += '<p><a href="' + base + 'export-manifest.json">Export provenance</a> · <a href="' + base + 'LICENSE-NOTICES.md">License scopes</a> · <a href="' + base + 'tests/known-source-link-gaps.json">Known source link gaps</a></p>'
    index = 0
    for template in catalog['templates']:
        result += f'<article class="template-card template-family-{E(template["id"])}" aria-labelledby="{E(template["id"])}-title"><h3 id="{E(template["id"])}-title">{E(template["title"])}</h3><p>{E(template["description"])}</p><dl class="template-facts"><dt>Template version</dt><dd>{E(template["templateVersion"])}</dd><dt>Protocol identity</dt><dd>{E(template["protocol"]["identity"])}</dd><dt>Canonical source</dt><dd>{E(template["source"]["repository"])} @ <code>{E(template["source"]["revision"])}</code></dd><dt>License</dt><dd>{E(template["license"])}</dd><dt>Adoption status</dt><dd>Review before adoption · complete: false</dd></dl><p><a href="https://github.com/{E(template["source"]["repository"])}">Canonical template repository ↗</a> · <a href="{base + E(template["entrypoint"])}">Read the entry point on GitHub <span aria-hidden="true">↗</span></a></p><details class="template-inventory"><summary>Inspect {len(template["files"])} files and their roles</summary><ul>'
        for file in template['files']:
            result += f'<li><span class="file-role">{E(file["role"])}</span><a href="{base + E(file["path"])}"><code>{E(file["path"])}</code></a><small>{file["size"]:,} bytes</small>'
            if include:
                result += f'<span><a href="/template-files/{index:03}.html">Read text</a> · <a href="/template-files/{index:03}.txt" download>Download text</a></span>'
            result += '</li>'
            index += 1
        result += '</ul></details></article>'
    return result
