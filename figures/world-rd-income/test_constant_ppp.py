"""Exact-country/year, constant-price units and provenance regression checks."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from constant_ppp import INDICATOR, attach_constant_ppp, attach_observations


class ConstantPPPTests(unittest.TestCase):
    def setUp(self):
        self.data = {'firstYear': 2020, 'lastYear': 2022, 'countries': [
            {'iso': 'USA', 'name': 'United States', 'gdp': {'nominal': {'2021': {'v': 1}}, 'ppp': {}}},
            {'iso': 'ES-PV', 'name': 'Basque Country', 'geographyType': 'region', 'gdp': {'nominal': {}, 'ppp': {}}},
        ]}
        self.info = {'url': 'https://example.org/wdi.zip', 'retrieved_utc': '2026-11-15', 'sha256': 'test'}

    def observation(self, iso='USA', year=2021, value=123):
        return {'indicator': {'id': INDICATOR, 'value': 'GDP per capita, PPP (constant 2021 international $)'},
                'countryiso3code': iso, 'date': str(year), 'value': value, '_source_record': 'WDICSV.CSV:row 2, column 5'}

    def test_exact_join_without_filling_or_regional_proxy(self):
        original = copy.deepcopy(self.data)
        rows = [self.observation(), self.observation(year=2022, value=None),
                self.observation('ESP', value=999), self.observation('WLD', value=999),
                self.observation('ES-PV', value=999)]
        audit = attach_observations(self.data, rows, self.info)
        usa, basque = self.data['countries']
        self.assertEqual(usa['gdp']['pppConstant']['2021']['v'], 123)
        self.assertNotIn('2020', usa['gdp']['pppConstant'])
        self.assertNotIn('2022', usa['gdp']['pppConstant'])
        self.assertEqual(basque['gdp']['pppConstant'], {})
        self.assertEqual(usa['gdp']['nominal'], original['countries'][0]['gdp']['nominal'])
        self.assertIsNone(audit[1]['value'])
        self.assertEqual(self.data['constantPPP']['observations'], 1)

    def test_reject_duplicate_wrong_indicator_and_wrong_price_base(self):
        row = self.observation()
        with self.assertRaises(AssertionError):
            attach_observations(copy.deepcopy(self.data), [row, row], self.info)
        for key, value in [('id', 'NY.GDP.PCAP.PP.CD'), ('value', 'PPP (constant 2017 international $)')]:
            bad = self.observation()
            bad['indicator'][key] = value
            with self.assertRaises(AssertionError):
                attach_observations(copy.deepcopy(self.data), [bad], self.info)

    def test_original_archive_cells_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            with ZipFile(raw / 'wdi_csv.zip', 'w') as archive:
                archive.writestr('WDICSV.CSV', 'Country Name,Country Code,Indicator Name,Indicator Code,2020,2021,2022\n'
                                 f'United States,USA,"GDP per capita, PPP (constant 2021 international $)",{INDICATOR},,123,..\n')
            info = {**self.info, 'sha256': hashlib.sha256((raw / 'wdi_csv.zip').read_bytes()).hexdigest()}
            (raw / 'manifest.json').write_text(json.dumps({'wdi_csv.zip': info}), encoding='utf-8')
            audit = attach_constant_ppp(self.data, raw)
            self.assertEqual(len(audit), 3)
            self.assertEqual(audit[1]['source_record'], 'WDICSV.CSV:row 2, column 6 (2021)')
            (raw / 'wdi_csv.zip').write_bytes(b'tampered')
            with self.assertRaises(AssertionError):
                attach_constant_ppp(self.data, raw)


if __name__ == '__main__':
    unittest.main()
