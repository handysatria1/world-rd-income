"""Source-parsing checks for official income and governance inputs."""
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from income_data import governance_estimate_observations


class GovernanceEstimateTests(unittest.TestCase):
    def test_reads_exact_years_and_preserves_missing_values_with_cell_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wgi.xlsx'
            book = Workbook()
            sheet = book.active
            sheet.title = 'ge'
            sheet.append(['ID variable', 'Economy (name)', 'Economy (code)', 'Region', 'Income classification',
                          'Year', 'Governance dimension', 'Number of sources', 'Governance estimate (approx. -2.5 to +2.5)'])
            sheet.append(['AAAge1999', 'Alpha', 'AAA', 'Region', 'High income', 1999, 'ge', 2, -0.2])
            sheet.append(['AAAge2000', 'Alpha', 'AAA', 'Region', 'High income', 2000, 'ge', 2, -0.5])
            sheet.append(['AAAge2025', 'Alpha', 'AAA', 'Region', 'High income', 2025, 'ge', 1, '..'])
            book.save(path)

            metadata, observations = governance_estimate_observations(path)

        self.assertEqual(metadata['lastupdated'], '2026 WGI edition')
        self.assertEqual([row['date'] for row in observations], ['2000', '2025'])
        self.assertEqual(observations[0]['value'], -0.5)
        self.assertIsNone(observations[1]['value'])
        self.assertEqual(observations[0]['_source_record'], 'ge!I3')
        self.assertEqual(observations[1]['_source_record'], 'ge!I4')
        self.assertEqual(observations[0]['_source_country_code'], 'AAA')
        self.assertEqual(observations[0]['indicator']['id'], 'GOV_WGI_GE.EST')


if __name__ == '__main__':
    unittest.main()
