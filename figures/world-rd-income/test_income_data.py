"""Source-parsing checks for official income and governance inputs."""
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from income_data import governance_estimate_observations
from income_sources import wdi_archive_url
from wdi_bulk import load_wdi_observations


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


class WdiBulkTests(unittest.TestCase):
    def test_discovers_the_dated_archive_from_the_catalog_page(self):
        body = (b'<a href="https://datacatalogfiles.worldbank.org/ddh-published/0037712/'
                b'DR0095335/WDI_CSV_2026_10_08.zip">CSV file</a>')
        self.assertEqual(wdi_archive_url(body),
                         'https://datacatalogfiles.worldbank.org/ddh-published/0037712/'
                         'DR0095335/WDI_CSV_2026_10_08.zip')

    def test_reads_requested_indicators_in_one_pass_and_preserves_missing_year_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wdi.zip'
            with ZipFile(path, 'w') as archive:
                archive.writestr('WDI/WDICSV.csv',
                                 'Country Name,Country Code,Indicator Name,Indicator Code,2000,2001\n'
                                 'Alpha,AAA,Population,SP.POP.TOTL,10,\n'
                                 'Alpha,AAA,R&D,GB.XPD.RSDV.GD.ZS,1.5,1.7\n')

            observations = load_wdi_observations(path, {'SP.POP.TOTL', 'GB.XPD.RSDV.GD.ZS'}, 2000, 2001)

        self.assertEqual(observations['SP.POP.TOTL'][0]['value'], 10)
        self.assertIsNone(observations['SP.POP.TOTL'][1]['value'])
        self.assertEqual(observations['SP.POP.TOTL'][0]['date'], '2000')
        self.assertEqual(observations['SP.POP.TOTL'][0]['_source_country_code'], 'AAA')
        self.assertEqual(observations['SP.POP.TOTL'][0]['_country_match'], 'iso3')
        self.assertEqual(observations['GB.XPD.RSDV.GD.ZS'][0]['_source_record'],
                         'WDI/WDICSV.csv:row 3, column 5 (2000)')

    def test_observed_year_filter_keeps_country_level_missing_values_only_in_reported_years(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'hci.zip'
            with ZipFile(path, 'w') as archive:
                archive.writestr('HCIData.csv',
                                 'Country Name,Country Code,Indicator Name,Indicator Code,2010,2011,2012\n'
                                 'Alpha,AAA,Human Capital Index,HD.HCI.OVRL,0.5,,0.6\n'
                                 'Beta,BBB,Human Capital Index,HD.HCI.OVRL,, ,\n')

            observations = load_wdi_observations(path, {'HD.HCI.OVRL'}, 2010, 2012,
                                                member_name='HCIData.csv', observed_only_years=True)

        self.assertEqual([row['date'] for row in observations['HD.HCI.OVRL']], ['2010', '2012', '2010', '2012'])
        self.assertEqual([row['value'] for row in observations['HD.HCI.OVRL']], [0.5, 0.6, None, None])


if __name__ == '__main__':
    unittest.main()
