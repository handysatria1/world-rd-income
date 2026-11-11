"""Guard the classification boundaries and released-aggregate accounting."""
import unittest
from pathlib import Path

from rd_industry_mapping import Classification, aggregate, combination
from sector_field_rd import FLAGS, normalized_value


class IndustryAccounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = Classification(Path(__file__).parent / 'data/rd_industry_raw/oecd_berd_structure.xml')

    def cells(self, **values):
        return {k: {'amount_local': v, 'rounding_local': .5, 'aggregation_eligible': True} for k, v in values.items()}

    def test_main_activity_boundaries(self):
        c = self.c
        self.assertLessEqual(c.coverage('C301'), c.groups['MHT'])
        self.assertLessEqual(c.coverage('C325'), c.groups['LMT'])
        self.assertLessEqual(c.coverage('C33'), c.groups['LMT'])
        self.assertLessEqual(c.coverage('M72'), c.groups['KIS'])
        self.assertEqual(c.coverage('C241_2431') | c.coverage('C242_2432'), c.coverage('C24'))
        self.assertEqual(c.coverage('STU') - c.coverage('U'), c.coverage('S') | c.coverage('T'))

    def test_parent_child_not_double_counted(self):
        r = aggregate(self.cells(C26=100, C261=30, C262=40, C263=30), self.c)['MHT']
        self.assertEqual(r['value'], 100)
        self.assertEqual(r['terms'], {'C26': 1})

    def test_public_manufacturing_difference(self):
        cells = self.cells(C=100, C20=10, C21=10, C26=10, C27=10, C28=10, C29=10, C30=10)
        result = aggregate(cells, self.c)
        self.assertEqual(result['MHT']['value'], 70)
        self.assertEqual(result['LMT']['value'], 30)
        self.assertEqual(result['LMT']['classes'], self.c.groups['LMT'])
        # If both groups are observed, retain them rather than deriving both complements.
        cells.update(self.cells(**{f'C{d}': 1 for d in [*range(10, 20), 22, 23, 24, 25, 31, 32, 33]}))
        result = aggregate(cells, self.c)
        self.assertEqual(result['MHT']['value'], 70)
        self.assertEqual(result['LMT']['value'], 17)

    def test_nonadditive_difference_not_used(self):
        cells = self.cells(M_N=100, N=20)
        self.assertEqual(aggregate(cells, self.c)['KIS']['value'], 80)
        cells['M_N']['AUX_OBS_STATUS'] = 'S2'
        self.assertIsNone(aggregate(cells, self.c)['KIS'])

    def test_no_U_leak_or_negative_complement(self):
        r = aggregate(self.cells(STU=500, S951=10, M_N=10, N=20), self.c)
        self.assertEqual(r['LIS']['value'], 30)
        self.assertNotEqual(r['LIS']['classes'], self.c.groups['LIS'])
        self.assertIsNone(r['KIS'])

    def test_confidential_included_and_zero(self):
        base = {'UNIT_MULT': '6', 'OBS_VALUE': '0', **dict.fromkeys(FLAGS, '')}
        self.assertEqual(normalized_value(base), (0, 'available'))
        for field, value in [('CONF_STATUS', 'C'), ('OBS_STATUS_2', 'K'), ('AUX_OBS_STATUS', 'N2')]:
            self.assertIsNone(normalized_value({**base, field: value})[0])
        cells = self.cells(C26=100, C261=20)
        cells['C26']['aggregation_eligible'] = False
        self.assertEqual(aggregate(cells, self.c)['MHT']['value'], 20)

    def test_overlap_is_rejected(self):
        a = {'value': 1, 'rounding': 0, 'classes': self.c.coverage('C26'), 'terms': {'C26': 1}}
        b = {'value': 1, 'rounding': 0, 'classes': self.c.coverage('C261'), 'terms': {'C261': 1}}
        with self.assertRaises(AssertionError):
            combination([(1, a), (1, b)])


if __name__ == '__main__':
    unittest.main()
