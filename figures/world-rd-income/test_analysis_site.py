"""Check publication of the exact frozen study, with no source refresh."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from analysis_site import ROOT, SNAPSHOT, build_analysis_site


class StudyPublicationTests(unittest.TestCase):
    def test_frozen_payload_and_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            published = build_analysis_site(destination)
            payload = json.loads((destination / 'analysis/2026-11-11/study.json').read_text('utf-8'))
            self.assertEqual(len(payload['countries']), 83)
            self.assertEqual(len(payload['pairs']), 120)
            self.assertEqual(len(payload['manufacturing']), 19)
            self.assertEqual(len(payload['correlations']), 36)
            self.assertEqual(payload['snapshot']['government_effectiveness']['unit'], 'estimate')
            self.assertTrue(any(float(r['gov_effect']) < 0 for r in payload['countries'] if r['gov_effect']))
            self.assertTrue(all(r['gdp_year'] == '2022' for r in payload['countries']))
            self.assertTrue(all(float(r['absolute_rd_gap']) <= .15 and float(r['relative_rd_gap']) <= .10 for r in payload['pairs']))
            self.assertEqual(len(published), len(set(published)))
            with ZipFile(SNAPSHOT / 'Global_RD_Income_Study.zip') as archive:
                for name in payload['downloads']:
                    self.assertEqual((destination / 'analysis/2026-11-11' / name).read_bytes(), archive.read(name))
            for name in published:
                self.assertTrue((destination / name).is_file(), name)
            self.assertEqual(hashlib.sha256((destination / 'analysis/2026-11-11/Global_RD_Income_Study.zip').read_bytes()).hexdigest(), payload['snapshot']['sha256'])
            self.assertIn('analysis.html', (ROOT / 'dashboard.js').read_text('utf-8'))


if __name__ == '__main__':
    unittest.main()
