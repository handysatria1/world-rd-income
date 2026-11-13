"""Exact-year tests for the country snapshot indicator joins."""
import unittest

from snapshot_indicators import build_snapshot_indicators


class SnapshotIndicatorTests(unittest.TestCase):
    def setUp(self):
        self.income = {
            'builtUTC': 'test-build',
            'countries': [
                {'iso': 'AAA', 'series': {
                    'humanCapitalIndex': {'2019': {'v': 0.7}, '2020': {'v': None}},
                    'bachelorAttainment': {'2020': {'v': 22}},
                    'researchers': {'2020': {'v': 4.5}},
                    'population': {'2020': {'v': 2_000_000}},
                }},
                {'iso': 'ES-PV', 'series': {
                    'researchersTotal': {'2020': {'v': 10, 'provenance': {'method': 'Reported Eustat FTE total'}}},
                    'population': {'2020': {'v': 2_000_000}},
                }},
            ],
        }
        self.broad = {
            'groups': [{'id': 'MHT'}, {'id': 'LMT'}, {'id': 'KIS'}],
            'rows': [{'iso': 'AAA', 'year': 2020, 'status': 'available', 'shares': [25, 30, 45]}],
        }
        self.industry = {'exports': [
            {'iso3': 'AAA', 'year': 2020, 'mht_exports_percent_manufactured': 31.4, 'status': 'reported'},
        ]}
        self.six_group = {
            'groups': [{'id': key} for key in ['MHT', 'LMT', 'KIS', 'LIS', 'UTL', 'OTH']],
            'rows': [
                {'iso3': 'AAA', 'year': 2020, 'group_id': 'MHT', 'berd_share_percent': 50, 'berd_coverage': 'complete'},
                {'iso3': 'AAA', 'year': 2020, 'group_id': 'KIS', 'berd_share_percent': None, 'berd_coverage': 'partial'},
            ],
        }

    def test_exact_iso_year_joins_and_missingness(self):
        result = build_snapshot_indicators(self.income, self.broad, self.industry, self.six_group,
                                           country_ids=['ZZZ'])
        rows = {(row['iso3'], row['year']): row for row in result['rows']}
        self.assertEqual(len(rows), 3 * 26)
        self.assertEqual(result['builtUTC'], 'test-build')
        self.assertEqual(rows['AAA', 2020]['gva_mht_percent'], 25)
        self.assertEqual(rows['AAA', 2020]['gva_kis_percent'], 45)
        self.assertEqual(rows['AAA', 2020]['mht_exports_percent_manufactured'], 31.4)
        self.assertEqual(rows['AAA', 2020]['bachelor_attainment_percent'], 22)
        self.assertIsNone(rows['AAA', 2020]['human_capital_index'])
        self.assertEqual(rows['AAA', 2019]['human_capital_index'], 0.7)
        self.assertIsNone(rows['AAA', 2021]['human_capital_index'])
        self.assertEqual(rows['AAA', 2020]['researchers_fte_total'], 9)
        self.assertEqual(rows['AAA', 2020]['researchers_fte_per_million'], 4.5)
        self.assertEqual(rows['AAA', 2020]['researchers_rate_method'], 'Reported FTE researchers per million people')
        self.assertEqual(rows['AAA', 2020]['berd_mht_percent'], 50)
        self.assertIsNone(rows['AAA', 2020]['berd_kis_percent'])
        self.assertEqual(rows['AAA', 2020]['berd_kis_coverage'], 'partial')
        self.assertIsNone(rows['ZZZ', 2020]['gva_mht_percent'])

    def test_reported_researcher_total_is_not_reconstructed(self):
        result = build_snapshot_indicators(self.income, self.broad, self.industry, self.six_group)
        rows = {(row['iso3'], row['year']): row for row in result['rows']}
        self.assertEqual(rows['ES-PV', 2020]['researchers_fte_total'], 10)
        self.assertEqual(rows['ES-PV', 2020]['researchers_fte_per_million'], 5)
        self.assertEqual(rows['ES-PV', 2020]['researchers_method'], 'Reported Eustat FTE total')
        self.assertEqual(rows['ES-PV', 2020]['researchers_rate_method'], 'Derived from same-year FTE total / population × 1,000,000')


if __name__ == '__main__':
    unittest.main()
