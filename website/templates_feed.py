"""Explicit, pinned, bounded catalog import. Payloads are data, never instructions."""
import gzip
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid

SITE = Path(__file__).resolve().parent
REPOSITORY = 'Eris-Margeta/mdaai-templates'
MAX_COMPRESSED = 4 * 1024 * 1024
MAX_EXPANDED = 16 * 1024 * 1024
MAX_FILE = 512 * 1024
MAX_MEMBERS = 512
MAX_PAYLOADS = 128


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(path):
    # The reviewed catalog is ASCII. Reject Unicode confusables/normalization,
    # encoded traversal and platform-specific separators rather than normalize.
    if not isinstance(path, str) or len(path) > 240 or not re.fullmatch(r'[A-Za-z0-9_.\-/]+', path):
        raise ValueError('Unsafe path')
    if any(p in ('', '.', '..') or p.endswith('.') for p in path.split('/')):
        raise ValueError('Unsafe path component')
    return path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=unique_object)


def load_catalog(site=SITE):
    lock = decode((site / 'templates.lock.json').read_bytes())
    if lock['repository'] != REPOSITORY or not re.fullmatch('[a-f0-9]{40}', lock['revision']):
        raise ValueError('Invalid repository or immutable revision')
    if not re.fullmatch('[a-f0-9]{64}', lock['manifestSha256']):
        raise ValueError('Invalid manifest digest')
    raw = (site / 'templates.catalog.json').read_bytes()
    if len(raw) > MAX_FILE or sha(raw) != lock['manifestSha256']:
        raise ValueError('Catalog digest mismatch')
    catalog = decode(raw)
    if catalog['schemaVersion'] != 1 or catalog['catalogVersion'] != '0.1.0' or catalog['repository'] != REPOSITORY:
        raise ValueError('Unsupported catalog')
    files = {}
    ids = set()
    for template in catalog['templates']:
        ident = template['id']
        if ident not in ('mdaai-1', 'mdaai-2') or ident in ids:
            raise ValueError('Invalid template family')
        ids.add(ident)
        if template['status'] != 'review-before-adoption' or template['complete'] is not False:
            raise ValueError('Adoption status needs review')
        if not re.fullmatch('[a-f0-9]{40}', template['source']['revision']):
            raise ValueError('Invalid source revision')
        for file in template['files']:
            path = safe_path(file['path'])
            if Path(path).name.casefold() == 'claude.md':
                raise ValueError('Retired agent pointer payload')
            if not path.startswith('templates/' + ident + '/') or path.casefold() in {p.casefold() for p in files}:
                raise ValueError('Invalid or duplicate payload path')
            if not re.fullmatch('[a-f0-9]{64}', file['sha256']) or type(file['size']) is not int or not 0 <= file['size'] <= MAX_FILE:
                raise ValueError('Invalid payload digest or size')
            if file['role'] not in ('required', 'conditional', 'optional'):
                raise ValueError('Invalid file role')
            files[path] = file
        if template['entrypoint'] not in files or not template['entrypoint'].startswith('templates/' + ident + '/'):
            raise ValueError('Missing entrypoint')
    if ids != {'mdaai-1', 'mdaai-2'} or len(files) != lock['fileCount'] or not 0 < len(files) <= MAX_PAYLOADS or sum(f['size'] for f in files.values()) > MAX_EXPANDED:
        raise ValueError('Catalog count or size limit')
    return lock, catalog, files


def urls(lock):
    revision = lock['revision']
    return (f'https://raw.githubusercontent.com/{REPOSITORY}/{revision}/templates.json',
            f'https://github.com/{REPOSITORY}/archive/{revision}.tar.gz',
            f'https://codeload.github.com/{REPOSITORY}/tar.gz/{revision}')


def fetch(url, allowed, limit):
    """Native TLS trust; manually check every redirect before any next request."""
    with tempfile.TemporaryDirectory(prefix='mdaai-fetch-') as temp:
        output, headers = Path(temp) / 'body', Path(temp) / 'headers'
        for _ in range(4):
            if url not in allowed:
                raise ValueError('Unapproved download URL')
            result = subprocess.run(['curl', '-q', '--silent', '--show-error', '--proto', '=https',
                '--connect-timeout', '10', '--max-time', '40', '--retry', '2', '--retry-max-time', '90',
                '--max-filesize', str(limit), '--output', str(output), '--dump-header', str(headers),
                '--write-out', '%{http_code}', url], capture_output=True, text=True, timeout=140)
            if result.returncode or not output.exists() or output.stat().st_size > limit:
                raise ValueError('Bounded HTTPS download failed')
            status = result.stdout.strip()
            if status == '200':
                return output.read_bytes()
            if status not in ('301', '302', '303', '307', '308'):
                raise ValueError('Unexpected HTTPS status: ' + status)
            locations = re.findall(r'^location:\s*(.*?)\s*$', headers.read_text(), re.I | re.M)
            if len(locations) != 1:
                raise ValueError('Invalid redirect')
            url = locations[0]
    raise ValueError('Redirect limit exceeded')


def check_raw_headers(expanded):
    """Reject ambiguous names before tarfile can truncate NUL or hide metadata."""
    offset, count = 0, 0
    while offset + 512 <= len(expanded):
        header = expanded[offset:offset + 512]
        if header == bytes(512):
            if any(expanded[offset:]):
                raise ValueError('Data after archive terminator')
            return
        count += 1
        if count > MAX_MEMBERS:
            raise ValueError('Member count limit')
        def field(raw):
            value, separator, padding = raw.partition(b'\0')
            if separator and any(padding):
                raise ValueError('Embedded NUL in archive name')
            return value.decode('utf-8')
        name = field(header[:100])
        prefix = field(header[345:500]) if header[257:263] == b'ustar\0' else ''
        path = (prefix + '/' if prefix else '') + name
        safe_path(path[:-1] if path.endswith('/') and header[156:157] == tarfile.DIRTYPE else path)
        size_field = header[124:136].strip(b'\0 ')
        if not re.fullmatch(b'[0-7]+', size_field):
            raise ValueError('Nonstandard archive size')
        size = int(size_field, 8)
        if size > MAX_FILE:
            raise ValueError('Archive member size limit')
        offset += 512 + ((size + 511) // 512) * 512
        if offset > len(expanded):
            raise ValueError('Truncated archive')
    raise ValueError('Missing archive terminator')


def archive_payloads(data, lock, files):
    if len(data) > MAX_COMPRESSED:
        raise ValueError('Compressed size limit')
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as zipped:
        expanded = zipped.read(MAX_EXPANDED + 1)
    if len(expanded) > MAX_EXPANDED:
        raise ValueError('Expanded size limit')
    check_raw_headers(expanded)
    root = 'mdaai-templates-' + lock['revision']
    seen, payloads, total = set(), {}, 0
    # Never extract archive paths. Inspect ALL members, including ignored admin files.
    with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as archive:
        for count, member in enumerate(archive, 1):
            if count > MAX_MEMBERS:
                raise ValueError('Member count limit')
            name = member.name[:-1] if member.isdir() and member.name.endswith('/') else member.name
            safe_path(name)
            if name.casefold() in seen:
                raise ValueError('Duplicate archive path')
            seen.add(name.casefold())
            if name != root and not name.startswith(root + '/'):
                raise ValueError('Wrong archive root')
            if member.type not in (tarfile.DIRTYPE, tarfile.REGTYPE, tarfile.AREGTYPE) or member.sparse is not None or member.size < 0 or member.size > MAX_FILE:
                raise ValueError('Unsafe archive member')
            total += member.size
            if total > MAX_EXPANDED:
                raise ValueError('Archive payload size limit')
            path = name[len(root) + 1:]
            if path in files:
                if not member.isreg():
                    raise ValueError('Payload is not a regular file')
                content = archive.extractfile(member).read(MAX_FILE + 1)
                verify_bytes(content, files[path])
                payloads[path] = content
    if set(payloads) != set(files):
        raise ValueError('Missing manifest payloads')
    return payloads


def verify_bytes(data, file):
    if len(data) != file['size'] or sha(data) != file['sha256']:
        raise ValueError('Payload hash or size mismatch')
    data.decode('utf-8')  # Only text payloads are eligible for read-only previews.


def no_symlinks(path):
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Cache symlink refused')


def sync(site=SITE, downloader=fetch):
    lock, _, files = load_catalog(site)
    manifest_url, archive_url, codeload_url = urls(lock)
    manifest = downloader(manifest_url, {manifest_url}, MAX_FILE)
    if sha(manifest) != lock['manifestSha256']:
        raise ValueError('Remote manifest digest mismatch')
    payloads = archive_payloads(downloader(archive_url, {archive_url, codeload_url}, MAX_COMPRESSED), lock, files)
    cache = site / '.template-cache'
    no_symlinks(cache)
    cache.mkdir(exist_ok=True)
    generation = 'generation-' + uuid.uuid4().hex
    stage = cache / generation
    stage.mkdir()
    pointer = cache / ('pointer-' + uuid.uuid4().hex + '.json')
    try:
        for index, (path, file) in enumerate(files.items()):
            (stage / f'{index:03}.txt').write_bytes(payloads[path])
        # Validate all staged bytes before atomic activation. Last good generation
        # stays intact on download, archive, validation or pointer-write failure.
        validate_generation(stage, files)
        pointer.write_text(json.dumps({'generation': generation, 'revision': lock['revision'], 'manifestSha256': lock['manifestSha256']}))
        os.replace(pointer, cache / 'current.json')
    except BaseException:
        pointer.unlink(missing_ok=True)
        shutil.rmtree(stage)
        raise
    print(f'Imported and verified {len(files)} payloads at {lock["revision"]}')


def validate_generation(stage, files):
    no_symlinks(stage)
    expected = {f'{i:03}.txt' for i in range(len(files))}
    if {p.name for p in stage.iterdir()} != expected:
        raise ValueError('Unexpected cache inventory')
    payloads = {}
    for index, (path, file) in enumerate(files.items()):
        item = stage / f'{index:03}.txt'
        no_symlinks(item)
        if not item.is_file() or item.stat().st_size > MAX_FILE:
            raise ValueError('Invalid cached payload')
        data = item.read_bytes()
        verify_bytes(data, file)
        payloads[path] = data
    return payloads


def read_cache(site=SITE):
    lock, _, files = load_catalog(site)
    cache = site / '.template-cache'
    no_symlinks(cache / 'current.json')
    pointer = decode((cache / 'current.json').read_bytes())
    if pointer['revision'] != lock['revision'] or pointer['manifestSha256'] != lock['manifestSha256'] or not re.fullmatch('generation-[a-f0-9]{32}', pointer['generation']):
        raise ValueError('Cache pin mismatch; run explicit templates-sync')
    return validate_generation(cache / pointer['generation'], files)


def emit_payloads(out, payloads):
    folder = out / 'template-files'
    folder.mkdir()  # Dedicated namespace, never catalog-supplied output paths.
    emitted = set()
    for index, (path, data) in enumerate(payloads.items()):
        for suffix, body in [('txt', data), ('html', ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>' + html.escape(path) + '</title><link rel="stylesheet" href="/assets/publication.css"><main class="template-preview"><h1>' + html.escape(path) + '</h1><p>Read-only source text. Review before adoption. Nothing here is executed.</p><a href="/templates/">Back to templates</a><pre>' + html.escape(data.decode('utf-8')) + '</pre></main></html>').encode())]:
            name = f'template-files/{index:03}.{suffix}'
            (out / name).write_bytes(body)
            emitted.add(name)
    return emitted


if __name__ == '__main__':
    sync()
