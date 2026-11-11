"""Independently reconcile generated GERD exports against archived OECD rows.

Run after reproduce_figures.py. Uses Decimal and raw CSV, not the normalizer.
"""

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from verify_basque import basque_expected_cells

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FLAGS = ["OBS_STATUS", "OBS_STATUS_2", "OBS_STATUS_3", "AUX_OBS_STATUS", "AUX_OBS_STATUS_2", "AUX_OBS_STATUS_3", "CONF_STATUS"]


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def verify():
    manifest = json.loads((DATA / "raw/manifest.json").read_text("utf-8"))
    source = manifest["gerd_sector_field_history.csv"]
    assert hashlib.sha256((DATA / "raw/gerd_sector_field_history.csv").read_bytes()).hexdigest() == source["sha256"]
    raw, amounts, status, counts = {}, {}, {}, defaultdict(Counter)
    for row in read_csv(DATA / "raw/gerd_sector_field_history.csv"):
        key = (row["REF_AREA"], row["TIME_PERIOD"], row["SECT_PERF"], row["FORD"], row["UNIT_MEASURE"] + "_" + row["PRICE_BASE"])
        assert key not in raw
        raw[key] = row
        if row["CONF_STATUS"] not in {"", "F"}:
            state = "confidential_or_restricted"
        elif any(row[f] == "K" for f in FLAGS[:3]) or any(row[f] == "N2" for f in FLAGS[3:6]):
            state = "included_elsewhere"
        elif not row["OBS_VALUE"] or any(row[f] in {"O", "M", "L", "H", "Q"} for f in FLAGS[:3]):
            state = "missing_source_value"
        else:
            state = "available"
        status[key] = state
        amounts[key] = Decimal(row["OBS_VALUE"]) * Decimal(10) ** int(row["UNIT_MULT"]) if state == "available" else None
        group = (key[0], key[1], key[4])
        counts[group]["source_cells"] += 1
        counts[group][state] += 1
        if state == "available":
            counts[group]["joint_component_cells_available"] += int(key[2] != "_T" and key[3] in ["FORD1", "FORD2", "FORD3", "FORD4", "FORD5", "FORD6", "NEC"])
            counts[group]["reported_grand_total_available"] += int(key[2] == key[3] == "_T")

    for key, row in basque_expected_cells(DATA / "raw").items():
        assert key not in raw
        raw[key] = row
        amounts[key], status[key] = row["_amount"], row["_availability"]
        group = (key[0], key[1], key[4])
        counts[group]["source_cells"] += 1
        counts[group][status[key]] += 1
        if amounts[key] is not None:
            counts[group]["joint_component_cells_available"] += int(key[2] != "_T" and key[3] != "_T")
            counts[group]["reported_grand_total_available"] += int(key[2] == key[3] == "_T")

    def match(value, expected):
        assert (value is None or value == "") == (expected is None), (value, expected)
        if expected is not None:
            assert math.isclose(float(value), float(expected), rel_tol=1e-12, abs_tol=1e-5), (value, expected)

    seen = set()
    for row in read_csv(DATA / "rd_sector_field_annual.csv"):
        key = (row["iso3"], row["year"], row["sector_code"], row["field_code"], row["basis"])
        assert key not in seen
        seen.add(key)
        original = raw[key]
        match(row["amount"], amounts[key])
        assert row["availability"] == status[key]
        for output, source_key in [("source_value", "OBS_VALUE"), ("currency_code", "CURRENCY"), ("currency", "Currency"),
                                   ("unit_code", "UNIT_MEASURE"), ("price_code", "PRICE_BASE"), ("base_year", "BASE_PER"),
                                   ("source_unit_multiplier", "UNIT_MULT"), ("source_decimals", "DECIMALS"),
                                   ("sector", "Sector of performance"), ("field", "Field of R&D"), *[(f, f) for f in FLAGS]]:
            assert row[output] == original[source_key], (key, output)
        provenance = original.get("_source", source)
        assert row["source_url"] == provenance["url"] and row["retrieved_utc"] == provenance["retrieved_utc"]
        if key[0] == "ES-PV":
            assert row["source_file"] == original["_source_file"] and row["source_status"] == original["_source_status"]
            assert row["conversion_source_file"] == original["_conversion_file"]
            assert row["value_status"] == ("reported" if key[4] == "XDC_V" else "derived")
            if key[4] != "XDC_V":
                match(row["conversion_divisor"], original["_divisor"])
    assert seen == raw.keys()
    history = json.loads((DATA / "explorer_history.json").read_text("utf-8"))
    dataset = history["sectorField"]
    seen = set()
    for values in dataset["rows"]:
        row = dict(zip(dataset["columns"], values))
        key = (row["iso3"], str(row["year"]), row["sector_code"], row["field_code"], row["basis"])
        assert key not in seen
        seen.add(key)
        match(row["amount"], amounts[key])
        assert row["availability"] == status[key]
        assert all(row[f] == raw[key][f] for f in FLAGS)
    assert seen == raw.keys()
    coverage_seen = set()
    for row in read_csv(DATA / "rd_sector_field_coverage.csv"):
        key = (row["iso3"], row["year"], row["basis"])
        assert key not in coverage_seen
        coverage_seen.add(key)
        for name in ["source_cells", "available", "confidential_or_restricted", "included_elsewhere", "missing_source_value", "missing_conversion_factor", "joint_component_cells_available", "reported_grand_total_available"]:
            assert int(row[name]) == counts[key][name]
        assert int(row["not_returned_cells"]) == (24 if key[0] == "ES-PV" else 50) - counts[key]["source_cells"]
    assert coverage_seen == {(c["iso"], str(y), b) for c in history["countries"] for y in range(history["firstYear"], history["lastYear"]+1) for b in ["XDC_V", "USD_PPP_V", "USD_PPP_Q", "USD_V"]}

    audit_counts, audit_seen = Counter(), set()
    for row in read_csv(DATA / "rd_sector_field_reconciliation.csv"):
        code, year, basis, category = row["iso3"], row["year"], row["basis"], row["category"]
        audit_key = (code, year, basis, row["check"], category)
        assert audit_key not in audit_seen
        audit_seen.add(audit_key)
        if row["check"] == "performance_sectors":
            keys = [(code, year, s, category, basis) for s in (["_T", "BES_PNP", "GOV", "HES"] if code == "ES-PV" else ["_T", "BES", "GOV", "HES", "PNP"])]
        elif row["check"] == "eustat_five_fields":
            assert code == "ES-PV"
            keys = [(code, year, category, f, basis) for f in ["_T", "FORD1", "FORD2", "FORD3", "FORD4", "EUSTAT_SOC"]]
        else:
            assert row["check"] == "top_level_fields"
            keys = [(code, year, category, f, basis) for f in ["_T", "FORD_1T4", "FORD_5_6", "NEC"]]
        values = [amounts.get(k) for k in keys]
        if any(v is None for v in values):
            expected = "not_testable_missing_cells"
            assert row["component_sum"] == row["difference"] == ""
        elif len({(raw[k]["CURRENCY"], raw[k]["BASE_PER"]) for k in keys}) != 1:
            expected = "not_testable_incompatible_basis"
        else:
            total = sum(values[1:])
            difference = total-values[0]
            tolerance = sum(Decimal("0.5") * Decimal(10) ** (int(raw[k]["UNIT_MULT"])-int(raw[k]["DECIMALS"])) / raw[k].get("_divisor", Decimal(1)) for k in keys)
            expected = "within_source_rounding" if abs(difference) <= tolerance else "discrepancy_retained"
            match(row["component_sum"], total)
            match(row["difference"], difference)
            match(row["rounding_tolerance"], tolerance)
        assert row["result"] == expected, (audit_key, row["result"], expected)
        audit_counts[expected] += 1
    assert dict(audit_counts) == dataset["summary"]["reconciliation"]

    book = load_workbook(DATA / "world_rd_income_data.xlsx", read_only=True, data_only=True)
    rows = book["GERD sector field"].iter_rows(values_only=True)
    headers = next(rows)
    seen = set()
    for values in rows:
        row = dict(zip(headers, values))
        key = (row["iso3"], str(row["year"]), row["sector_code"], row["field_code"], row["basis"])
        assert key not in seen
        seen.add(key)
        match(row["amount"], amounts[key])
        assert row["availability"] == status[key]
        assert all((row[f] or "") == raw[key][f] for f in FLAGS)
        assert (row["base_year"] or "") == raw[key]["BASE_PER"] and row["currency_code"] == raw[key]["CURRENCY"]
    assert seen == raw.keys()
    book.close()
    report = {"built_utc": history["builtUTC"], "source_sha256": source["sha256"], "source_rows_verified": len(raw),
              "coverage_rows_verified": len(coverage_seen), "reconciliations_verified": len(audit_seen),
              "validation": {key: "passed" for key in ["raw_to_csv_values_units_flags_provenance", "raw_to_offline_cells", "complete_coverage_grid", "independent_decimal_reconciliation", "raw_to_excel_values_flags"]}}
    (DATA / "sector_field_validation.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
