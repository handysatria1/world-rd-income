"""Independently verify raw funding/type inputs against every CSV/embedded/Excel cell.

Intentionally does not import the production normalizer or reconciliation code.
"""

import csv
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
DATA, RAW = ROOT / "data", ROOT / "data" / "raw"
FLAGS = ["OBS_STATUS", "OBS_STATUS_2", "OBS_STATUS_3", "AUX_OBS_STATUS", "AUX_OBS_STATUS_2", "AUX_OBS_STATUS_3", "CONF_STATUS"]
KEY = ["iso3", "year", "breakdown", "sector_code", "category_code", "basis"]
NUMERIC = {"year", "amount", "source_unit_multiplier", "source_decimals"}


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def close(actual, expected):
    assert (actual is None or actual == "") == (expected is None or expected == ""), (actual, expected)
    if expected is not None and expected != "":
        assert math.isclose(float(actual), float(expected), rel_tol=2e-12, abs_tol=1e-5), (actual, expected)


def key(r):
    return tuple(str(r[k]) for k in KEY)


def expected_inputs():
    expected, spanish = {}, {}
    for kind in ["funding", "research"]:
        for r in csv_rows(RAW / f"gerd_{kind}_history.csv"):
            category = r["SECT_FUND" if kind == "funding" else "TYPE_RD"]
            k = (r["REF_AREA"], r["TIME_PERIOD"], kind, r["SECT_PERF"], category, r["UNIT_MEASURE"] + "_" + r["PRICE_BASE"])
            state = "available"
            if r["CONF_STATUS"] not in ["", "F"]:
                state = "confidential_or_restricted"
            elif "K" in [r[f] for f in FLAGS[:3]] or "N2" in [r[f] for f in FLAGS[3:6]]:
                state = "included_elsewhere"
            elif not r["OBS_VALUE"].strip() or any(r[f] in ["O", "M", "L", "H", "Q"] for f in FLAGS[:3]):
                state = "missing_source_value"
            amount = Decimal(r["OBS_VALUE"]) * Decimal(10) ** int(r["UNIT_MULT"]) if state == "available" else None
            assert k not in expected
            expected[k] = {**dict(zip(KEY, k)), "amount": amount, "source_value": r["OBS_VALUE"], "source_unit_multiplier": r["UNIT_MULT"],
                "source_decimals": r["DECIMALS"], "currency_code": r["CURRENCY"], "base_year": r["BASE_PER"], "availability": state,
                **{f: r[f] for f in FLAGS}, "source_file": f"gerd_{kind}_history.csv", "value_status": "reported",
                "conversion_divisor": "", "conversion_source_file": "", "source_category_label": r["Sources of funds" if kind == "funding" else "Type of R&D"],
                "source_sector_label": r["Sector of performance"], "source_status": ""}
            if k[0] == "ESP" and kind == "funding" and k[3] == k[4] == "_T":
                spanish[(k[1], k[5])] = expected[k]
    divisors = {}
    for year in range(2000, 2026):
        v, q = (spanish.get((str(year), b)) for b in ["XDC_V", "USD_PPP_Q"])
        if v and q and v["amount"] is not None and q["amount"] is not None and q["amount"] > 0:
            divisors[str(year)] = Decimal(v["source_value"]) / Decimal(q["source_value"])
    rates = {kind: {r["date"]: r["value"] for r in json.loads((RAW / f"wb_spain_{kind}.json").read_bytes(), parse_float=Decimal)[1]}
             for kind in ["exchange", "ppp"]}
    d = json.loads((RAW / "eustat_rd_funding.json").read_bytes(), parse_float=Decimal)["dataset"]
    dimensions = d["dimension"]
    ids = dimensions["id"]
    assert ids == ["sector de ejecución", "origen de los fondos", "periodo"]
    indices = [sorted(dimensions[k]["category"]["index"], key=dimensions[k]["category"]["index"].get) for k in ids]
    assert indices[0] == ["00", "10", "20", "30"] and indices[1] == ["10", "20", "25", "30", "40", "50"]
    assert len(d["value"]) == math.prod(len(x) for x in indices)
    for i, (sector, funder, year) in enumerate(itertools.product(*indices)):
        if not 2000 <= int(year) <= 2025:
            continue
        value = d["value"][i]
        for basis, factor, filename in [("XDC_V", Decimal(1), ""), ("USD_V", rates["exchange"].get(year), "wb_spain_exchange.json"),
                                       ("USD_PPP_V", rates["ppp"].get(year), "wb_spain_ppp.json"), ("USD_PPP_Q", divisors.get(year), "gerd_funding_history.csv")]:
            k = ("ES-PV", year, "funding", {"00": "_T", "10": "BES_PNP", "20": "GOV", "30": "HES"}[sector],
                 {"10": "_T", "20": "GOV", "25": "HES", "30": "BES", "40": "PNP", "50": "ROW"}[funder], basis)
            amount = None if value is None or factor is None else Decimal(value) * 1000 / factor
            expected[k] = {**dict(zip(KEY, k)), "amount": amount, "source_value": "" if value is None else str(value),
                "source_unit_multiplier": "3", "source_decimals": "0", "currency_code": "EUR" if basis == "XDC_V" else "USD",
                "base_year": "2020" if basis == "USD_PPP_Q" else "", "availability": "available" if amount is not None else "missing_source_value" if value is None else "missing_conversion_factor",
                **dict.fromkeys(FLAGS, ""), "source_file": "eustat_rd_funding.json", "value_status": "reported" if basis == "XDC_V" else "derived",
                "conversion_divisor": "" if basis == "XDC_V" or factor is None else str(factor), "conversion_source_file": filename,
                "source_category_label": dimensions[ids[1]]["category"]["label"][funder],
                "source_sector_label": dimensions[ids[0]]["category"]["label"][sector], "source_status": d.get("status", {}).get(str(i), "")}
    return expected, divisors


def official_expected(expected, divisors):
    """Separate raw-table decoding: no imports from either production loader."""
    d = json.loads((RAW / "eustat_rd_cost.json").read_bytes(), parse_float=Decimal)["dataset"]
    dims = d["dimension"]
    assert dims["id"] == ["sector de ejecución", "naturaleza", "periodo"]
    coordinates = [sorted(dims[name]["category"]["index"], key=dims[name]["category"]["index"].get) for name in dims["id"]]
    rates = {b: {r["date"]: r["value"] for r in json.loads((RAW / filename).read_bytes(), parse_float=Decimal)[1]}
             for b, filename in [("USD_V", "wb_spain_exchange.json"), ("USD_PPP_V", "wb_spain_ppp.json")]}
    for i, (sector, nature, year) in enumerate(itertools.product(*coordinates)):
        if int(year) < 2000 or int(year) > 2025 or nature not in ["10", "60"]:
            continue
        value = d["value"][i]
        for basis in ["XDC_V", "USD_V", "USD_PPP_V", "USD_PPP_Q"]:
            factor = Decimal(1) if basis == "XDC_V" else divisors.get(year) if basis == "USD_PPP_Q" else rates[basis].get(year)
            s = {"00": "_T", "10": "BES_PNP", "20": "GOV", "30": "HES"}[sector]
            template = expected[("ES-PV", year, "funding", s, "_T", basis)]
            k = ("ES-PV", year, "research", s, "_T" if nature == "10" else "CAP_EX_NEC", basis)
            amount = None if value is None or factor is None else value * 1000 / factor
            expected[k] = {**template, **dict(zip(KEY, k)), "amount": amount, "source_value": "" if value is None else str(value),
                "availability": "available" if amount is not None else "missing_source_value" if value is None else "missing_conversion_factor",
                "source_file": "eustat_rd_cost.json", "source_category_label": dims["naturaleza"]["category"]["label"][nature],
                "source_status": d.get("status", {}).get(str(i), ""), "source_currency_code": "EUR", "reference_period": year}
    alternatives = {k: v for k, v in expected.items() if k[0] == "GBR" and k[2:4] == ("research", "BES") and k[1] in ["2022", "2023", "2024"]}
    for k in alternatives:
        del expected[k]
    conversion_expected = {}
    for year, total, capital, basic, applied, experimental in [
        (2022, "B8", "B11", "C9", "D9", "E9"),
        (2023, "C8", "C12", "C10", "D10", "E10"),
        (2024, "D8", "D12", "C10", "D10", "E10"),
    ]:
        filename = f"ons_berd_{year}.xlsx"
        w = load_workbook(RAW / filename, data_only=True, read_only=True)
        for category, sheet, address, label in [("_T", "8", total, "Total"), ("CAP_EX_NEC", "8", capital, "Capital total"),
                ("BR", "10", basic, "Basic"), ("AR", "10", applied, "Applied"), ("ED", "10", experimental, "Experimental development")]:
            value = Decimal(str(w[sheet][address].value))
            for basis in ["XDC_V", "USD_PPP_V", "USD_PPP_Q"]:
                local = expected[("GBR", str(year), "funding", "_T", "_T", "XDC_V")]
                ppp = expected[("GBR", str(year), "funding", "_T", "_T", basis)]
                factor = Decimal(local["source_value"]) / Decimal(ppp["source_value"])
                if basis != "XDC_V":
                    conversion_expected[(str(year), basis)] = factor
                k = ("GBR", str(year), "research", "BES", category, basis)
                expected[k] = {**dict(zip(KEY, k)), "amount": value * 10**6 / factor, "source_value": str(value),
                    "source_unit_multiplier": "6", "source_decimals": "0", "currency_code": "GBP" if basis == "XDC_V" else "USD",
                    "base_year": "2020" if basis == "USD_PPP_Q" else "", "availability": "available", **dict.fromkeys(FLAGS, ""),
                    "source_file": filename, "value_status": "reported" if basis == "XDC_V" else "derived",
                    "conversion_divisor": "" if basis == "XDC_V" else str(factor),
                    "conversion_source_file": "" if basis == "XDC_V" else "gerd_funding_history.csv",
                    "source_category_label": label, "source_sector_label": "BES", "source_status": "",
                    "source_locator": f"Table {sheet}, cell {address}", "reference_period": str(year), "source_currency_code": "GBP"}
        w.close()
    for r in csv_rows(DATA / "rd_official_conversion.csv"):
        close(r["gbp_per_ppp_dollar"], conversion_expected.pop((r["year"], r["basis"])))
    assert not conversion_expected
    seen = set()
    for r in csv_rows(DATA / "rd_research_oecd_alternatives.csv"):
        k = key(r); assert k not in seen; seen.add(k)
        for col, value in alternatives[k].items():
            if col in NUMERIC:
                close(r[col], value)
            else:
                assert r[col] == value, (k, col)
    assert seen == set(alternatives)
    # Independent coordinate checks for the direct ONS funding reference export.
    w = load_workbook(RAW / "ons_gerd_2024.xlsx", data_only=True, read_only=True)
    funding_expected = {}
    for j, s in enumerate(["GOV", "HES", "BES", "PNP", "_T"], 2):
        for i, c in enumerate(["GOV", "HES", "BES", "PNP", "ROW", "_T"], 9):
            funding_expected[("2024", s, c)] = w["1"].cell(i, j).value
    for j, year in [(2, "2022"), (3, "2023")]:
        for s, i in [("GOV", 11), ("HES", 14), ("BES", 15), ("PNP", 16)]:
            funding_expected[(year, s, "_T")] = w["2"].cell(i, j).value
        for c, i in [("_T", 10), ("GOV", 11), ("HES", 14), ("BES", 15), ("PNP", 16), ("ROW", 17)]:
            funding_expected[(year, "_T", c)] = w["3"].cell(i, j).value
    comparisons = {(r["year"], r["sector_code"], r["category_code"]): r for r in csv_rows(DATA / "rd_ons_funding_comparison.csv")}
    for r in csv_rows(DATA / "rd_ons_funding_reported.csv"):
        v = funding_expected.pop((r["year"], r["sector_code"], r["category_code"]))
        close(r["source_value"], v); close(r["amount"], v * 10**6)
        assert r["source_file"] == "ons_gerd_2024.xlsx" and r["basis"] == "XDC_V"
        # Compare sources without assuming agreement; verify every retained discrepancy.
        other = expected[key(r)]
        audit = comparisons.pop((r["year"], r["sector_code"], r["category_code"]))
        difference = Decimal(v) * 10**6 - other["amount"]
        tolerance = Decimal(500000) + Decimal("0.5") * Decimal(10) ** (int(other["source_unit_multiplier"]) - int(other["source_decimals"]))
        close(audit["ons_amount"], Decimal(v) * 10**6); close(audit["oecd_amount"], other["amount"])
        close(audit["ons_minus_oecd"], difference); close(audit["rounding_tolerance"], tolerance)
        assert audit["result"] == ("within_source_rounding" if abs(difference) <= tolerance else "discrepancy_retained")
        assert audit["ons_source_locator"] == r["source_locator"] and audit["oecd_source_file"] == other["source_file"]
    assert not funding_expected and not comparisons
    old = load_workbook(RAW / "ons_gerd_2023_official.xlsx", data_only=True, read_only=True)
    intensity_expected = {str(y): ("ons_gerd_2023_official.xlsx", old["6"].cell(10, y - 2016).value) for y in range(2018, 2022)}
    intensity_expected.update({str(y): ("ons_gerd_2024.xlsx", w["5"].cell(9, y - 2020).value) for y in range(2022, 2025)})
    for r in csv_rows(DATA / "rd_ons_intensity.csv"):
        filename, v = intensity_expected.pop(r["year"])
        close(r["percent_gdp"], v); assert r["source_file"] == filename and r["iso3"] == "GBR"
    assert not intensity_expected
    old.close(); w.close()
    return expected


def verify():
    manifest = json.loads((RAW / "manifest.json").read_bytes())
    for name, info in manifest.items():
        assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == info["sha256"]
        if info.get("method") == "POST":
            assert hashlib.sha256(info["request_body"].encode()).hexdigest() == info["request_sha256"]
    expected, divisors = expected_inputs()
    expected = official_expected(expected, divisors)
    seen, counts = set(), defaultdict(Counter)
    for r in csv_rows(DATA / "rd_breakdown_annual.csv"):
        k = key(r); assert k not in seen; seen.add(k)
        e = expected[k]
        for col, v in e.items():
            if col in NUMERIC:
                close(r[col], v)
            else:
                assert r[col] == v, (k, col, r[col], v)
        assert r["source_url"] == manifest[r["source_file"]]["url"]
        assert r["retrieved_utc"] == manifest[r["source_file"]]["retrieved_utc"]
        assert r["amount_scale"] == "units"
        if r["conversion_source_file"]:
            assert r["conversion_source_url"] == manifest[r["conversion_source_file"]]["url"]
        count = counts[(r["iso3"], r["year"], r["basis"], r["breakdown"])]
        count["source_cells"] += 1; count[r["availability"]] += 1
    assert seen == set(expected)
    for r in csv_rows(DATA / "rd_breakdown_conversion.csv"):
        close(r["eur_per_constant_2020_ppp_dollar"], divisors.get(r["year"]))
        assert r["base_year"] == "2020" and r["proxy_economy"] == "ESP"
    coverage_count = 0
    for r in csv_rows(DATA / "rd_breakdown_coverage.csv"):
        count = counts[(r["iso3"], r["year"], r["basis"], r["breakdown"])]
        for col in ["source_cells", "available", "missing_source_value", "included_elsewhere", "confidential_or_restricted", "missing_conversion_factor"]:
            assert int(r[col]) == count[col]
        assert r["coverage_status"] == ("source_rows_returned" if count else "not_returned")
        coverage_count += 1
    checks = Counter()
    for r in csv_rows(DATA / "rd_breakdown_reconciliation.csv"):
        def pick(s, c):
            return expected.get((r["iso3"], r["year"], r["breakdown"], s, c, r["basis"]))
        if r["check"] == "categories":
            total = pick(r["category"], "_T"); parts = [pick(r["category"], c) for c in r["components"].split("|")]
        else:
            total = pick("_T", r["category"]); parts = [pick(s, r["category"]) for s in r["components"].split("|")]
        close(r["reported_total"], None if total is None else total["amount"])
        all_rows = [total, *parts]
        if any(x is None or x["amount"] is None for x in all_rows):
            assert r["result"] == "not_testable_missing_cells"
            assert r["component_sum"] == r["difference"] == r["rounding_tolerance"] == ""
        else:
            assert len({(x["currency_code"], x["base_year"]) for x in all_rows}) == 1
            summed = sum(x["amount"] for x in parts)
            tolerance = sum(Decimal("0.5") * Decimal(10) ** (int(x["source_unit_multiplier"]) - int(x["source_decimals"])) / Decimal(x["conversion_divisor"] or "1") for x in all_rows)
            diff = summed - total["amount"]
            close(r["component_sum"], summed); close(r["difference"], diff); close(r["rounding_tolerance"], tolerance)
            assert r["result"] == ("within_source_rounding" if abs(diff) <= tolerance else "discrepancy_retained")
        checks[r["result"]] += 1
    data = json.loads((DATA / "explorer_history.json").read_bytes())
    embedded = data["breakdowns"]
    assert len(embedded["rows"]) == len(expected)
    assert coverage_count == len(data["countries"]) * 26 * 4 * 2
    for values in embedded["rows"]:
        r = dict(zip(embedded["columns"], values)); e = expected[key(r)]
        for col, v in e.items():
            if col in NUMERIC:
                close(r[col], v)
            else:
                assert str(r[col]) == v
    # Check the actual self-contained HTML payload, not only its JSON sidecar.
    document = (ROOT / "output" / "world_rd_income_explorer.html").read_text("utf-8")
    start = document.index('<script type="application/json" id="history-data">') + len('<script type="application/json" id="history-data">')
    embedded_html = json.loads(document[start:document.index('</script>', start)])
    assert embedded_html["breakdowns"] == embedded
    for filename, array in [("rd_research_oecd_alternatives.csv", "alternativeRows"), ("rd_ons_funding_reported.csv", "officialFundingRows")]:
        packed = {key(dict(zip(embedded["columns"], values))): dict(zip(embedded["columns"], values)) for values in embedded[array]}
        for r in csv_rows(DATA / filename):
            saved = packed.pop(key(r))
            for col in embedded["columns"]:
                if col in NUMERIC:
                    close(saved[col], r[col])
                else:
                    assert str(saved[col]) == r[col], (filename, key(r), col)
        assert not packed
    for r in csv_rows(DATA / "rd_ons_intensity.csv"):
        saved = embedded["officialIntensity"][r["iso3"]][r["year"]]
        close(saved["v"], r["percent_gdp"])
        for col in ["flags", "note", "source_file", "source_locator"]:
            assert saved[col] == r[col]
    del document, embedded_html, expected
    # Stream every new sheet against its CSV including flags and provenance.
    workbook = load_workbook(DATA / "world_rd_income_data.xlsx", read_only=True, data_only=True)
    sheet_names = [("annual", "GERD funding research"), ("coverage", "GERD breakdown coverage"),
                   ("reconciliation", "GERD breakdown reconciliation"), ("definitions", "GERD breakdown definitions"),
                   ("conversion", "GERD regional price proxy")]
    excel_counts = {}
    sheet_files = [(f"rd_breakdown_{suffix}.csv", sheet) for suffix, sheet in sheet_names]
    sheet_files += [("rd_official_conversion.csv", "ONS PPP conversion inputs"),
                    ("rd_research_oecd_alternatives.csv", "OECD alternative UK research"),
                    ("rd_ons_funding_reported.csv", "ONS reported funding"), ("rd_ons_intensity.csv", "ONS reported intensity"),
                    ("rd_ons_funding_comparison.csv", "ONS OECD funding comparison")]
    for filename, sheet in sheet_files:
        values = workbook[sheet].iter_rows(values_only=True); headers = next(values); n = 0
        for source, saved in itertools.zip_longest(csv_rows(DATA / filename), values):
            assert source is not None and saved is not None
            saved = list(saved) + [None] * (len(headers) - len(saved))
            for col, value in zip(headers, saved):
                target = source[col]
                if isinstance(value, (int, float)):
                    close(value, target)
                else:
                    assert ("" if value is None else str(value)) == target, (sheet, n, col, value, target)
            n += 1
        excel_counts[sheet] = n
    workbook.close()
    report = {"built_utc": data["builtUTC"], "rows": len(seen), "coverage_rows": coverage_count,
              "reconciliation": dict(checks), "workbook_rows": excel_counts,
              "ons_oecd_funding_comparison": dict(Counter(r["result"] for r in csv_rows(DATA / "rd_ons_funding_comparison.csv"))),
              "validation": {k: "passed" for k in ["raw_hashes_and_post_bodies", "all_raw_cells_flags_and_conversions",
                 "full_coverage_grid", "independent_decimal_reconciliation", "embedded_json_and_html", "all_new_excel_cells",
                 "direct_ons_cells_and_original_oecd_alternatives", "ons_funding_comparison_discrepancies_retained", "ons_intensity_vintages", "eustat_capital_without_type_imputation"]}}
    (DATA / "breakdown_validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
