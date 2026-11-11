"""Guard scientific distinctions in joint GERD cells and reconciliation."""

import unittest

from sector_field_rd import FLAGS, normalized_value, reconcile, reconciliation_records


class SectorFieldTests(unittest.TestCase):
    def test_missing_and_confidential_are_not_observed_zeros(self):
        row = {**dict.fromkeys(FLAGS, ""), "OBS_VALUE": "0", "UNIT_MULT": "6"}
        self.assertEqual(normalized_value(row), (0, "available"))
        self.assertEqual(normalized_value({**row, "OBS_VALUE": "1.234"}), (1_234_000, "available"))
        for changes, status in [({"CONF_STATUS": "C"}, "confidential_or_restricted"),
                                ({"OBS_STATUS_2": "K"}, "included_elsewhere"),
                                ({"AUX_OBS_STATUS_3": "N2"}, "included_elsewhere"),
                                ({"OBS_VALUE": ""}, "missing_source_value")]:
            self.assertEqual(normalized_value({**row, **changes}), (None, status))
        for changes in [{"UNIT_MULT": "0"}, {"OBS_VALUE": "nan"}, {"OBS_VALUE": "-1"}]:
            with self.assertRaises(AssertionError):
                normalized_value({**row, **changes})

    def cell(self, amount, **kwargs):
        return {"amount": amount, "basis": "XDC_V", "currency_code": "EUR", "base_year": "",
                "source_unit_multiplier": 6, "source_decimals": 3, **kwargs}

    def test_missing_component_never_becomes_zero_or_residual(self):
        total = self.cell(100)
        self.assertEqual(reconcile(total, [self.cell(100), None])["result"], "not_testable_missing_cells")
        self.assertIsNone(reconcile(total, [self.cell(None)])["component_sum"])
        self.assertEqual(reconcile(total, [self.cell(100), self.cell(0)])["result"], "within_source_rounding")

    def test_currency_and_price_base_are_part_of_reconciliation(self):
        for change in [{"currency_code": "GBP"}, {"basis": "USD_PPP_V"}, {"base_year": "2020"}]:
            self.assertEqual(reconcile(self.cell(100), [self.cell(100, **change)])["result"], "not_testable_incompatible_basis")

    def test_rounding_and_real_discrepancies_are_distinguished(self):
        self.assertEqual(reconcile(self.cell(10e6), [self.cell(10e6+900)])["result"], "within_source_rounding")
        actual = reconcile(self.cell(10e6), [self.cell(11e6)])
        self.assertEqual(actual["result"], "discrepancy_retained")
        self.assertEqual(actual["reported_total"], 10e6)
        self.assertEqual(actual["difference"], 1e6)

    def test_field_groups_not_added_to_their_children(self):
        rows = []
        for field, amount in [("_T", 100e6), ("FORD_1T4", 80e6), ("FORD_5_6", 20e6), ("NEC", 0),
                              ("FORD1", 30e6), ("FORD2", 30e6), ("FORD3", 10e6), ("FORD4", 10e6)]:
            rows.append({"iso3": "X", "year": 2023, "sector_code": "HES", "field_code": field,
                         **self.cell(amount), **dict.fromkeys(FLAGS, "")})
        dataset = {"columns": list(rows[0]), "rows": [list(r.values()) for r in rows]}
        audit = next(r for r in reconciliation_records(dataset) if r["check"] == "top_level_fields" and r["category"] == "HES")
        self.assertEqual(audit["component_sum"], 100e6)
        self.assertEqual(audit["result"], "within_source_rounding")

    def test_derived_currency_reconciles_in_converted_units(self):
        # Exact source sum differs by 1 thousand EUR; divide both the difference
        # and the half-last-decimal tolerances by the annual EUR/USD factor.
        def converted(source):
            return self.cell(source * 1000 / .5, source_value=str(source), source_unit_multiplier=3,
                             source_decimals=0, conversion_divisor="0.5", basis="USD_V", currency_code="USD")
        audit = reconcile(converted(100), [converted(60), converted(41)])
        self.assertEqual(audit["difference"], 2000)
        self.assertEqual(audit["rounding_tolerance"], 3000)
        self.assertEqual(audit["result"], "within_source_rounding")


if __name__ == "__main__":
    unittest.main()
