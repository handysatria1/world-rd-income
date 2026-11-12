"""Synthetic checks for country averages and income-group aggregation."""
import unittest

from absorptive_capacity import METRICS, build_absorptive_capacity


def make_country(iso, name, current, values, history=None, region=False):
    series = {}
    for key, years in values.items():
        series[key] = {str(year): {'v': value} for year, value in years.items()}
    return {'iso': iso, 'name': name, 'current': current, 'history': history or {},
            'region': region, 'series': series}


class AbsorptiveCapacityTests(unittest.TestCase):
    def setUp(self):
        metrics = {metric['key']: {'code': 'CODE-' + metric['key']} for metric in METRICS}
        self.payload = {
            'builtUTC': 'test-build', 'currentVintage': 'FY2027',
            'historicalVintages': ['FY2027', 'FY2020'], 'indicators': metrics,
            'countries': [
                make_country('AAA', 'Alpha', 'HIC', {
                    'researchers': {2000: 0, 2001: None, 2025: 10},
                    'rd': {2000: 1, 2002: 3},
                    'governmentEffectivenessEstimate': {2000: -0.5, 2001: 0.5},
                }, {'FY2020': 'HIC', 'FY2027': 'HIC'}),
                make_country('BBB', 'Beta', 'UMC', {
                    'researchers': {2000: 20}, 'rd': {2000: 9},
                }, {'FY2020': 'HIC', 'FY2027': 'UMC'}),
                make_country('CCC', 'Gamma', 'LMC', {
                    'researchers': {2000: 40}, 'rd': {2000: 21},
                }, {'FY2020': 'LIC', 'FY2027': 'LMC'}),
                make_country('DDD', 'Delta', 'LIC', {'rd': {2000: None}},
                             {'FY2020': 'UMC', 'FY2027': 'LIC'}),
                make_country('EEE', 'Epsilon', 'UNK', {'rd': {2000: 100}},
                             {'FY2020': 'UNK', 'FY2027': 'UNK'}),
                make_country('REG', 'Region', 'UNK', {'rd': {2000: 100}}, region=True),
            ],
        }

    def test_country_averages_skip_missing_preserve_zero_and_exclude_regions(self):
        result = build_absorptive_capacity(self.payload)
        rows = {row['iso3']: row for row in result['country_rows']}
        self.assertEqual(set(rows), {'AAA', 'BBB', 'CCC', 'DDD', 'EEE'})
        self.assertEqual(rows['AAA']['researcher_density_mean_per_million'], 5)
        self.assertEqual(rows['AAA']['researcher_density_n_years'], 2)
        self.assertEqual(rows['AAA']['researcher_density_first_year'], 2000)
        self.assertEqual(rows['AAA']['researcher_density_last_year'], 2025)
        self.assertIsNone(rows['DDD']['rd_expenditure_mean_percent_gdp'])
        estimate = rows['AAA']['government_effectiveness_estimate_mean']
        self.assertEqual(estimate, 0)
        self.assertEqual(result['json']['builtUTC'], 'test-build')

    def test_income_group_means_are_equal_country_means_and_vintage_sensitive(self):
        result = build_absorptive_capacity(self.payload)
        groups = {(row['classification_vintage'], row['income_group_code'], row['metric']): row
                  for row in result['group_rows']}
        middle = groups['FY2027', 'MIC', 'researchers']
        self.assertEqual(middle['mean_of_country_means'], 30)
        self.assertEqual(middle['economies_with_data'], 2)
        self.assertEqual(middle['economies_in_group'], 2)
        self.assertEqual(middle['included_iso3'], 'BBB;CCC')
        self.assertEqual(groups['FY2020', 'HIC', 'researchers']['mean_of_country_means'], 12.5)
        self.assertEqual(groups['FY2027', 'LIC', 'rd']['economies_with_data'], 0)
        self.assertIsNone(groups['FY2027', 'LIC', 'rd']['mean_of_country_means'])


if __name__ == '__main__':
    unittest.main()
