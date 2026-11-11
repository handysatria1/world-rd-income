"""Scientific safeguards for reported units, same-year estimates and UIS flags."""

import unittest

from download_data import uis_archive_url
from nominal_rd import derive_series, oecd_local_value, uis_value


class NominalRDTests(unittest.TestCase):
    def test_annual_join_never_substitutes_nearby_gdp_or_averages(self):
        rd = {"2020": {"v": 2}, "2021": {"v": 4}, "2022": {"v": 0}, "2023": {"v": 3}}
        gdp = {"2020": {"v": 1_000_000_000}, "2021": {"v": 3_000_000_000}, "2022": {"v": 4_000_000_000}, "2024": {"v": 9_000_000_000}}
        actual = derive_series(rd, gdp)
        self.assertEqual([actual[y]["v"] for y in rd], [20_000_000, 120_000_000, 0, None])
        self.assertIn("Missing same-year", actual["2023"]["missingReason"])
        # Annual amounts average to 70m; mean intensity * mean GDP would wrongly give 60m.
        self.assertEqual((actual["2020"]["v"] + actual["2021"]["v"]) / 2, 70_000_000)
        self.assertNotIn("2024", actual)

    def test_oecd_millions_and_price_basis(self):
        row = {"FREQ": "A", "MEASURE": "G", "UNIT_MEASURE": "XDC", "PRICE_BASE": "V",
               "TRANSFORMATION": "_Z", "UNIT_MULT": "6", "OBS_VALUE": "952115"}
        self.assertEqual(oecd_local_value(row), 952_115_000_000)
        for changed in [{"UNIT_MEASURE": "USD_PPP"}, {"PRICE_BASE": "Q"}, {"UNIT_MULT": "0"}]:
            with self.assertRaises(AssertionError):
                oecd_local_value({**row, **changed})
        self.assertIsNone(oecd_local_value({**row, "OBS_VALUE": ""}))

    def test_uis_nonapplicable_zero_is_not_observed_zero(self):
        self.assertIsNone(uis_value({"VALUE": "0", "MAGNITUDE": "NA"}))
        self.assertEqual(uis_value({"VALUE": "0", "MAGNITUDE": "NIL"}), 0)
        self.assertIsNone(uis_value({"VALUE": "", "MAGNITUDE": "SUPP"}))
        self.assertEqual(uis_value({"VALUE": "2.5", "MAGNITUDE": "LOWREL"}), 2.5)

    def test_invalid_inputs_are_rejected(self):
        for bad in [-1, float("nan"), float("inf")]:
            with self.assertRaises(AssertionError):
                derive_series({"2020": {"v": bad}}, {"2020": {"v": 100}})
        with self.assertRaises(AssertionError):
            derive_series({"2020": {"v": 2}}, {"2020": {"v": 0}})

    def test_uis_release_discovery_requires_unambiguous_official_link(self):
        link = "https://download.uis.unesco.org/bdds/202602/SCN-SDG.zip"
        self.assertEqual(uis_archive_url(f'<a href="{link}">Science</a>'.encode()), link)
        with self.assertRaises(AssertionError):
            uis_archive_url(b"No current Science archive")
        with self.assertRaises(AssertionError):
            uis_archive_url((link + " " + link.replace("202602", "202702")).encode())


if __name__ == "__main__":
    unittest.main()
