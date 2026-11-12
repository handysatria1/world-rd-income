import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from release_downloads import prepare, verify


class ReleaseDownloadTests(unittest.TestCase):
    def fixture(self, root):
        site, assets = root / 'site', root / 'downloads'
        site.mkdir()
        (site / 'index.html').write_text('<main><a href="world-rd-income.zip" download>Research ZIP</a><a href="./book.xlsx">Excel</a><a href="table.csv">CSV</a><a href="small.csv">Small</a><script src="app.js"></script></main>', encoding='utf-8')
        for name in ['world-rd-income.zip', 'book.xlsx', 'table.csv', 'payload.json', 'partition.json.gz', 'app.js']:
            (site / name).write_bytes(b'unchanged bytes' * 8)
        (site / 'small.csv').write_bytes(b'few')
        return site, assets

    def test_downloads_move_but_runtime_and_small_files_stay(self):
        with tempfile.TemporaryDirectory() as folder:
            site, assets = self.fixture(Path(folder))
            manifest = prepare(site, assets, 'owner/project', 'data-123', threshold=100)
            self.assertEqual(set(manifest['files']), {'world-rd-income.zip', 'book.xlsx', 'table.csv'})
            for name in ['payload.json', 'partition.json.gz', 'app.js', 'small.csv']:
                self.assertTrue((site / name).is_file())
            self.assertIn('https://github.com/owner/project/releases/download/data-123/book.xlsx', (site / 'index.html').read_text('utf-8'))
            self.assertEqual(json.loads((site / 'downloads_manifest.json').read_text('utf-8')), manifest)
            self.assertEqual(verify(site, assets, manifest)['verification'], 'passed')

    def test_identical_existing_asset_is_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            site, assets = self.fixture(Path(folder))
            body = (site / 'world-rd-income.zip').read_bytes()
            reuse = {'world-rd-income.zip': {'size': len(body), 'digest': 'sha256:' + hashlib.sha256(body).hexdigest(),
                     'browser_download_url': 'https://github.com/owner/project/releases/download/old-snapshot/world-rd-income.zip'}}
            manifest = prepare(site, assets, 'owner/project', 'new-data', threshold=100, reuse=reuse)
            self.assertTrue(manifest['files']['world-rd-income.zip']['reused_existing_asset'])
            self.assertEqual(manifest['files']['world-rd-income.zip']['release_tag'], 'old-snapshot')

    def test_mismatched_existing_file_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            site, assets = self.fixture(Path(folder))
            manifest = prepare(site, assets, 'owner/project', 'new-data', threshold=100,
                               reuse={'world-rd-income.zip': {'size': 1, 'digest': 'sha256:wrong'}})
            self.assertFalse(manifest['files']['world-rd-income.zip']['reused_existing_asset'])

    def test_tampered_download_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            site, assets = self.fixture(Path(folder))
            manifest = prepare(site, assets, 'owner/project', 'data-123', threshold=100)
            (assets / 'book.xlsx').write_bytes(b'tampered')
            with self.assertRaises(AssertionError):
                verify(site, assets, manifest)

    def test_assets_must_be_outside_website(self):
        with tempfile.TemporaryDirectory() as folder:
            site, _ = self.fixture(Path(folder))
            with self.assertRaises(ValueError):
                prepare(site, site / 'downloads', 'owner/project', 'data-123', threshold=100)

    def test_html_line_endings_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            site, assets = self.fixture(Path(folder))
            body = b'<main>\r\n<a href="book.xlsx">Download</a>\r\n<script>const data={value:1};</script>\r\n</main>'
            (site / 'index.html').write_bytes(body)
            prepare(site, assets, 'owner/project', 'data-123', threshold=100)
            result = (site / 'index.html').read_bytes()
            self.assertEqual(result.count(b'\r\n'), body.count(b'\r\n'))
            self.assertIn(b'<script>const data={value:1};</script>', result)

    def test_absolute_links_to_own_pages_downloads_are_rewritten(self):
        with tempfile.TemporaryDirectory() as folder:
            site, assets = self.fixture(Path(folder))
            (site / 'sources.html').write_text('<a href="https://owner.github.io/project/book.xlsx">Excel</a><a href="https://elsewhere.example/book.xlsx">Unrelated</a>', encoding='utf-8')
            prepare(site, assets, 'owner/project', 'data-123', threshold=100)
            text = (site / 'sources.html').read_text('utf-8')
            self.assertIn('https://github.com/owner/project/releases/download/data-123/book.xlsx', text)
            self.assertIn('https://elsewhere.example/book.xlsx', text)


if __name__ == '__main__':
    unittest.main()
