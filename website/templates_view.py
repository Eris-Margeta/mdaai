"""Escaped catalog presentation; no fetched instruction is executed."""
from html import escape as E
from templates_feed import REPOSITORY


def cycle(content):
    steps = ''.join(f'<li><span class="cycle-number">{i:02}</span><span>{E(step)}</span></li>' for i, step in enumerate(content['steps'], 1))
    return f'<section id="template-cycle" class="template-cycle" aria-labelledby="cycle-title"><p class="cycle-eyebrow">PROTOCOL → PRACTICE → PROGRESS</p><h2 id="cycle-title">{E(content["title"])}</h2><p>{E(content["text"])}</p><ol class="cycle-steps">{steps}</ol><p class="cycle-note">{E(content["note"])}</p><a class="cycle-link" href="/templates/"><span>{E(content["link"])}</span><span class="direction-icon" aria-hidden="true">→</span></a></section>'


def gallery(lock, catalog, content, include=False):
    base = f'https://github.com/{REPOSITORY}/blob/{lock["revision"]}/'
    result = '<div class="catalog-toolbar"><div><label for="template-search">Find a template</label><input id="template-search" type="search" placeholder="Name, workflow or file" aria-controls="template-grid" autocomplete="off"></div><p id="template-status" role="status" aria-live="polite">' + str(len(catalog['templates'])) + ' templates</p></div><div class="template-grid" id="template-grid">'
    index = 0
    for template in catalog['templates']:
        tid = E(template['id'])
        canonical = 'https://github.com/' + E(template['source']['repository'])
        search = E(' '.join([template['title'], template['description'], template['templateVersion'], template['license']] + [f['path'] for f in template['files']]), quote=True)
        result += f'<article class="template-card template-family-{tid}" data-template-search="{search}" aria-labelledby="{tid}-title"><p class="template-label">{E(template["templateVersion"])} · {E(template["license"])}</p><h3 id="{tid}-title">{E(template["title"])}</h3><p class="template-description">{E(template["description"])}</p><p class="template-status">Review before adoption</p><div class="template-actions"><a class="button primary" href="{canonical}">View template<span class="direction-icon" aria-hidden="true">↗</span></a><a href="{base + E(template["entrypoint"])}">Read entry instructions<span class="direction-icon" aria-hidden="true">↗</span></a></div><details class="template-inventory"><summary>Inspect {len(template["files"])} files and source details</summary><dl class="template-facts"><dt>Template version</dt><dd>{E(template["templateVersion"])}</dd><dt>Historical source label</dt><dd>{E(template["protocol"]["identity"])}</dd><dt>Canonical source</dt><dd>{E(template["source"]["repository"])} @ <code>{E(template["source"]["revision"])}</code></dd><dt>License</dt><dd>{E(template["license"])} — retain inherited notices; see license scopes below.</dd><dt>Adoption status</dt><dd>Review before adoption · complete: false</dd></dl><ul>'
        for file in template['files']:
            result += f'<li><span class="file-role">{E(file["role"])}</span><a href="{base + E(file["path"])}"><code>{E(file["path"])}</code></a><small>{file["size"]:,} bytes</small>'
            if include:
                result += f'<span><a href="/template-files/{index:03}.html">Read text</a> · <a href="/template-files/{index:03}.txt" download>Download text</a></span>'
            result += '</li>'
            index += 1
        result += '</ul></details></article>'
    result += '</div><p id="template-empty" hidden>No templates match. Try a broader word or clear the search.</p>'
    result += '<div class="catalog-contribute"><div><h3>Have a template to contribute?</h3><p>Propose a listing through a pull request to the GitHub index. Review is required before a template is featured.</p></div><a class="button" href="https://github.com/' + REPOSITORY + '/blob/main/CONTRIBUTING.md">Submit a template<span class="direction-icon" aria-hidden="true">↗</span></a><a href="https://github.com/' + REPOSITORY + '/pulls">Catalog pull requests</a></div>'
    result += '<details class="catalog-audit"><summary>Catalog pin, provenance and license scopes</summary><p class="catalog-pin">Reviewed catalog commit <a href="' + base + 'templates.json"><code>' + E(lock['revision']) + '</code></a> · ' + str(lock['fileCount']) + ' files</p><p>' + E(content['included'] if include else content['remote']) + '</p><p><a href="' + base + 'export-manifest.json">Export provenance</a> · <a href="' + base + 'LICENSE-NOTICES.md">License scopes</a> · <a href="' + base + 'tests/known-source-link-gaps.json">Known source link gaps</a></p></details>'
    return result
