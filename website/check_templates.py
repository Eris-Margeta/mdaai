"""Offline adversarial import fixtures, cache atomicity and optional output checks."""
import gzip
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import templates_feed as feed
import build


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mdaai-feed-')
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name).resolve() / 'website'
        self.site.mkdir()
        for name in ('templates.lock.json', 'templates.catalog.json'):
            shutil.copyfile(feed.SITE / name, self.site / name)
        self.lock, self.catalog, self.files = feed.load_catalog(self.site)
        self.root = 'mdaai-templates-' + self.lock['revision']
        self.path = 'templates/mdaai-1/a.txt'
        self.data = b'<script>alert("not executable")</script>'
        self.small_files = {self.path: {'sha256': feed.sha(self.data), 'size': len(self.data)}}

    def archive(self, members=None):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for name, data, kind in members or [(self.root + '/' + self.path, self.data, tarfile.REGTYPE)]:
                item = tarfile.TarInfo(name)
                item.type = kind
                item.size = len(data) if kind == tarfile.REGTYPE else 0
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    item.linkname = '../../escape'
                archive.addfile(item, io.BytesIO(data) if kind == tarfile.REGTYPE else None)
        return gzip.compress(stream.getvalue())

    def test_reviewed_inventory(self):
        self.assertEqual(len(self.files), 105)
        self.assertEqual([len(t['files']) for t in self.catalog['templates']], [89, 16])
        self.assertEqual(feed.sha((self.site / 'templates.catalog.json').read_bytes()), self.lock['manifestSha256'])

    def test_retired_provider_pointer_rejected(self):
        catalog = json.loads((self.site / "templates.catalog.json").read_text())
        catalog["templates"][0]["files"][0]["path"] = "templates/mdaai-1/cLaUdE.Md"
        raw = json.dumps(catalog).encode()
        (self.site / "templates.catalog.json").write_bytes(raw)
        self.lock["manifestSha256"] = feed.sha(raw)
        (self.site / "templates.lock.json").write_text(json.dumps(self.lock))
        with self.assertRaisesRegex(ValueError, "Retired agent pointer"):
            feed.load_catalog(self.site)

    def test_safe_archive_and_admin_files(self):
        data = self.archive([(self.root + '/' + self.path, self.data, tarfile.REGTYPE), (self.root + '/README.md', b'ignored', tarfile.REGTYPE)])
        self.assertEqual(feed.archive_payloads(data, self.lock, self.small_files), {self.path: self.data})

    def test_unsafe_paths(self):
        for path in ('/absolute', '../escape', 'a/../b', 'a/./b', 'a//b', 'a\\b', 'a\x00b', 'a/%2e%2e/b', 'a/\uff0e\uff0e/b', 'a/\u202eb', 'a/e\u0301', 'a/é', 'C:/x', 'a./b'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                feed.safe_path(path)

    def test_unsafe_members_even_outside_payload(self):
        good = (self.root + '/' + self.path, self.data, tarfile.REGTYPE)
        for name in ('/absolute', self.root + '/../escape', self.root + '/a\\b', self.root + '/a\x00b', self.root + '/\uff0e\uff0e/x', self.root + '/a/./b', 'wrong-root/file'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                feed.archive_payloads(self.archive([good, (name, b'bad', tarfile.REGTYPE)]), self.lock, self.small_files)
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                feed.archive_payloads(self.archive([good, (self.root + '/admin', b'', kind)]), self.lock, self.small_files)

    def test_duplicate_members(self):
        member = (self.root + '/' + self.path, self.data, tarfile.REGTYPE)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            feed.archive_payloads(self.archive([member, member]), self.lock, self.small_files)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            feed.archive_payloads(self.archive([member, (member[0].upper(), self.data, tarfile.REGTYPE)]), self.lock, self.small_files)

    def test_hash_size_and_missing(self):
        for files in ({self.path: {'sha256': '0' * 64, 'size': len(self.data)}}, {self.path: {'sha256': feed.sha(self.data), 'size': 0}}, {self.path + 'missing': next(iter(self.small_files.values()))}):
            with self.assertRaises(ValueError):
                feed.archive_payloads(self.archive(), self.lock, files)

    def test_all_resource_caps(self):
        archive = self.archive()
        for name, value in [('MAX_COMPRESSED', len(archive)-1), ('MAX_EXPANDED', 10), ('MAX_FILE', 1), ('MAX_MEMBERS', 0)]:
            with self.subTest(cap=name), patch.object(feed, name, value), self.assertRaises(ValueError):
                feed.archive_payloads(archive, self.lock, self.small_files)
        with patch.object(feed, 'MAX_PAYLOADS', 92), self.assertRaises(ValueError):
            feed.load_catalog(self.site)

    def test_pin_and_manifest_fail_closed(self):
        raw = (self.site / 'templates.catalog.json').read_bytes()
        (self.site / 'templates.catalog.json').write_bytes(raw + b' ')
        with self.assertRaisesRegex(ValueError, 'digest'):
            feed.load_catalog(self.site)
        (self.site / 'templates.catalog.json').write_bytes(raw)
        self.lock['revision'] = 'main'
        (self.site / 'templates.lock.json').write_text(json.dumps(self.lock))
        with self.assertRaises(ValueError):
            feed.load_catalog(self.site)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            feed.decode('{"x":1,"x":2}')

    def test_url_allowlist_before_network(self):
        with patch.object(feed.subprocess, 'run') as run:
            for url in ('http://github.com/x', 'https://evil.example/x', 'https://github.com/Eris-Margeta/mdaai-templates/archive/main.tar.gz'):
                with self.assertRaises(ValueError):
                    feed.fetch(url, set(feed.urls(self.lock)), 1024)
            run.assert_not_called()

    def test_redirect_rejected_before_following(self):
        import subprocess
        calls = []
        def response(args, **kwargs):
            calls.append(args[-1])
            Path(args[args.index('--output')+1]).write_bytes(b'redirect')
            Path(args[args.index('--dump-header')+1]).write_text('HTTP/2 302\nlocation: https://evil.example/archive\n')
            return subprocess.CompletedProcess(args, 0, '302', '')
        manifest, archive, codeload = feed.urls(self.lock)
        with patch.object(feed.subprocess, 'run', side_effect=response), self.assertRaisesRegex(ValueError, 'Unapproved'):
            feed.fetch(archive, {archive, codeload}, 1024)
        self.assertEqual(calls, [archive])

    def test_catalog_duplicates_and_outside_paths(self):
        for bad in ('duplicate', 'outside'):
            catalog = json.loads((self.site / 'templates.catalog.json').read_bytes())
            if bad == 'duplicate':
                catalog['templates'][0]['files'].append(catalog['templates'][0]['files'][0])
            else:
                catalog['templates'][0]['files'][0]['path'] = 'assets/index.html'
            raw = json.dumps(catalog).encode()
            lock = dict(self.lock, manifestSha256=feed.sha(raw))
            (self.site / 'templates.catalog.json').write_bytes(raw)
            (self.site / 'templates.lock.json').write_text(json.dumps(lock))
            with self.assertRaises(ValueError):
                feed.load_catalog(self.site)
            shutil.copyfile(feed.SITE / 'templates.catalog.json', self.site / 'templates.catalog.json')

    def test_atomic_failure_preserves_last_good(self):
        # Synthetic content is confined to this offline fixture; the real remote
        # import is separately verified by the explicit sync command.
        payloads = {p: self.data for p in self.files}
        files = {p: dict(f, size=len(self.data), sha256=feed.sha(self.data)) for p, f in self.files.items()}
        manifest = (self.site / 'templates.catalog.json').read_bytes()
        with patch.object(feed, 'load_catalog', return_value=(self.lock, self.catalog, files)), patch.object(feed, 'archive_payloads', return_value=payloads):
            feed.sync(self.site, lambda url, allowed, limit: manifest)
            pointer = self.site / '.template-cache/current.json'
            before = pointer.read_bytes()
            for failure in ('network', 'manifest', 'archive', 'activation'):
                with self.subTest(failure=failure):
                    if failure == 'network':
                        def downloader(*args):
                            raise ValueError('network failure')
                        with self.assertRaises(ValueError):
                            feed.sync(self.site, downloader)
                    elif failure == 'manifest':
                        with self.assertRaises(ValueError):
                            feed.sync(self.site, lambda *args: b'bad digest')
                    elif failure == 'archive':
                        with patch.object(feed, 'archive_payloads', side_effect=ValueError('bad archive')), self.assertRaises(ValueError):
                            feed.sync(self.site, lambda *args: manifest)
                    else:
                        with patch.object(feed.os, 'replace', side_effect=OSError('activation failure')), self.assertRaises(OSError):
                            feed.sync(self.site, lambda *args: manifest)
                    self.assertEqual(pointer.read_bytes(), before)
                    self.assertEqual(feed.read_cache(self.site), payloads)
            stage = self.site / '.template-cache' / json.loads(before)['generation']
            first = stage / '000.txt'
            first.write_bytes(b'corruption')
            with self.assertRaises(ValueError):
                feed.read_cache(self.site)
            first.unlink()
            first.symlink_to(stage / '001.txt')
            with self.assertRaises(ValueError):
                feed.read_cache(self.site)

    def test_optional_output_is_escaped_and_isolated(self):
        out = self.site / 'out'
        out.mkdir()
        (out / 'index.html').write_text('untouched')
        expected = feed.emit_payloads(out, {self.path: self.data})
        self.assertEqual(expected, {'template-files/000.txt', 'template-files/000.html'})
        self.assertEqual((out / 'index.html').read_text(), 'untouched')
        self.assertEqual((out / 'template-files/000.txt').read_bytes(), self.data)
        preview = (out / 'template-files/000.html').read_text()
        self.assertNotIn('<script>', preview)
        self.assertIn('&lt;script&gt;', preview)
        self.assertIn('noindex', preview)

    def test_default_build_cannot_download_or_read_cache(self):
        out = self.site / 'dist'
        with patch.object(build, 'OUT', out), patch.object(feed, 'fetch', side_effect=AssertionError('network forbidden')), patch.object(build, 'read_cache', side_effect=AssertionError('cache forbidden')), patch.object(build, 'SITE', feed.SITE):
            build.build()
        self.assertFalse((out / 'template-files').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
