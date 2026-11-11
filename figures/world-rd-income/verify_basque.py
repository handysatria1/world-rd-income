"""Independent raw-input verification of Basque conversions and generated exports.

Does not import the Eustat normalizer. Sector/field verifier also uses the expected
cells below to check every CSV, embedded and workbook cell and reconciliation.
"""

import csv
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CODE = "ES-PV"


def payload(path):
    return json.loads(path.read_bytes(), parse_float=Decimal)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def factors(raw):
    return {kind: {r["date"]: None if r["value"] is None else Decimal(r["value"])
                   for r in payload(raw / f"wb_spain_{kind}.json")[1]} for kind in ["exchange", "ppp"]}


def basque_expected_cells(raw):
    rates = factors(raw)
    manifest = json.loads((raw / "manifest.json").read_bytes())
    fields = ["_T", "FORD1", "FORD2", "FORD3", "FORD4", "EUSTAT_SOC"]
    labels = ["Total", "Natural sciences", "Engineering and technology", "Medical and health sciences", "Agricultural and veterinary sciences",
              "Social sciences (Eustat grouping; no humanities split)"]
    # OECD labels are independently checked in the OECD raw table; use its
    # authoritative labels for the four broad fields mapped to shared codes.
    for r in read_csv(raw / "gerd_sector_field_history.csv"):
        if r["FORD"] in fields[:-1]:
            labels[fields.index(r["FORD"])] = r["Field of R&D"]
    expected = {}
    sector_labels = {"_T": "Total", "BES_PNP": "Companies + private non-profit institutions (Eustat)", "GOV": "Government sector", "HES": "Higher education sector"}
    for sector, table in [("_T", "total"), ("BES_PNP", "business_pnp"), ("GOV", "government"), ("HES", "higher_education")]:
        name = f"eustat_rd_{table}.json"
        dataset = payload(raw / name)["dataset"]
        dims = dataset["dimension"]
        ids = dims["id"]
        assert len(ids) == 3 and ids[1:] == ["naturaleza", "periodo"]
        assert list(dims[ids[0]]["category"]["index"]) == ["00", "10", "20", "30", "40", "50"]
        assert list(dims["naturaleza"]["category"]["index"]) == ["10"]
        years = dims["periodo"]["category"]["index"]
        for field_index, field in enumerate(fields):
            for year, year_index in years.items():
                if not 2000 <= int(year) <= 2025:
                    continue
                offset = field_index * len(years) + year_index
                value = dataset["value"][offset]
                source_status = dataset.get("status", {}).get(str(offset), "")
                assert not source_status or value is None
                for basis, kind in [("XDC_V", None), ("USD_V", "exchange"), ("USD_PPP_V", "ppp")]:
                    divisor = Decimal(1) if kind is None else rates[kind].get(year)
                    amount = None if value is None or divisor is None else Decimal(value) * 1000 / divisor
                    state = "available" if amount is not None else "missing_source_value" if value is None else "missing_conversion_factor"
                    expected[(CODE, year, sector, field, basis)] = {
                        "OBS_VALUE": "" if value is None else str(value), "UNIT_MULT": "3", "DECIMALS": "0", "CURRENCY": "EUR" if kind is None else "USD",
                        "Currency": "Euro" if kind is None else "US dollar", "UNIT_MEASURE": "XDC" if kind is None else "USD" if kind == "exchange" else "USD_PPP",
                        "PRICE_BASE": "V", "BASE_PER": "", "Sector of performance": sector_labels[sector], "Field of R&D": labels[field_index],
                        "_amount": amount, "_availability": state, "_source_file": name,
                        "_source": manifest[name], "_divisor": divisor, "_source_status": source_status,
                        "_conversion_file": "" if kind is None else f"wb_spain_{kind}.json",
                        **dict.fromkeys(["OBS_STATUS", "OBS_STATUS_2", "OBS_STATUS_3", "AUX_OBS_STATUS", "AUX_OBS_STATUS_2", "AUX_OBS_STATUS_3", "CONF_STATUS"], ""),
                    }
    return expected


def close(value, expected):
    assert (value is None or value == "") == (expected is None), (value, expected)
    if expected is not None:
        assert math.isclose(float(value), float(expected), rel_tol=1e-12, abs_tol=1e-5), (value, expected)


def verify():
    raw = DATA / "raw"
    manifest = json.loads((raw / "manifest.json").read_bytes())
    for name, info in manifest.items():
        if name.startswith(("eustat_", "wb_spain_")):
            assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == info["sha256"]
    cells = basque_expected_cells(raw)
    rates = factors(raw)
    source_series = {}
    for kind in ["total", "per_capita"]:
        d = payload(raw / f"eustat_gdp_{kind}.json")["dataset"]
        years = d["dimension"]["periodo"]["category"]["index"]
        assert len(d["value"]) == len(years)
        source_series[kind] = {y: None if d["value"][i] is None else Decimal(d["value"][i]) * (1000 if kind == "total" else 1) for y, i in years.items()}
    history = json.loads((DATA / "explorer_history.json").read_bytes())
    country = next(c for c in history["countries"] if c["iso"] == CODE)
    assert country["geographyType"] == "region" and country["parentEconomy"] == "ESP" and country["regressionEligible"] is False
    annual = list(read_csv(DATA / "basque_annual.csv"))
    assert {r["year"] for r in annual} == set(map(str, range(2000, 2026))) and len(annual) == 26
    def divide(a, b):
        return None if a is None or b is None else a / b
    expected = {}
    for row in annual:
        year = row["year"]
        eur = cells.get((CODE, year, "_T", "_T", "XDC_V"), {}).get("_amount")
        gdp, pc = source_series["total"].get(year), source_series["per_capita"].get(year)
        fx, ppp = rates["exchange"].get(year), rates["ppp"].get(year)
        vals = {"gerd_eur_reported": eur, "gdp_eur_reported": gdp, "gdp_per_capita_eur_reported": pc,
                "eur_per_usd": fx, "eur_per_international_dollar": ppp, "gerd_usd_derived": divide(eur, fx), "gerd_ppp_derived": divide(eur, ppp),
                "gdp_total_usd_derived": divide(gdp, fx), "gdp_per_capita_usd_derived": divide(pc, fx), "gdp_per_capita_ppp_derived": divide(pc, ppp),
                "rd_percent_gdp_derived": divide(None if eur is None else eur * 100, gdp)}
        expected[year] = vals
        for k, value in vals.items():
            close(row[k], value)
            close(next(r for r in history["basqueAnnual"] if str(r["year"]) == year)[k], value)
        for category, key in [("nominal", "gdp_per_capita_usd_derived"), ("ppp", "gdp_per_capita_ppp_derived")]:
            close(country["gdp"][category].get(year, {}).get("v"), vals[key])
        close(country["rd"]["eustat"].get(year, {}).get("v"), vals["rd_percent_gdp_derived"])
        close(country["rdNominal"]["usd"]["eustat"].get(year, {}).get("v"), vals["gerd_usd_derived"])
        close(country["rdNominal"]["pppEustat"].get(year, {}).get("v"), vals["gerd_ppp_derived"])
        for name in ["rd", "gdp", "gdp_per_capita", "exchange", "ppp"]:
            source = manifest[row[f"{name}_source_file"]]
            assert row[f"{name}_source_url"] == source["url"] and row[f"{name}_retrieved_utc"] == source["retrieved_utc"]
    unit_keys = {"current EUR": "gerd_eur_reported", "current US dollars": "gerd_usd_derived", "current international dollars (PPP)": "gerd_ppp_derived"}
    nominal = [r for r in read_csv(DATA / "rd_nominal_annual.csv") if r["iso3"] == CODE]
    nominal_expected = {(y, u) for y, v in expected.items() if v["gerd_eur_reported"] is not None for u in unit_keys}
    assert {(r["year"], r["unit"]) for r in nominal} == nominal_expected and len(nominal) == len(nominal_expected)
    for row in nominal:
        close(row["amount"], expected[row["year"]][unit_keys[row["unit"]]])
        assert row["rd_source"] == "Eustat (Basque Country)" and row["rd_source_file"] == "eustat_rd_total.json"
        assert row["status"] == ("reported" if row["unit"] == "current EUR" else "derived")
        close(Decimal(row["source_value"]) * 1000, expected[row["year"]]["gerd_eur_reported"])
    # Static source-selection and GDP exports must contain the same regional data.
    coverage = next(r for r in read_csv(DATA / "coverage_and_exclusions.csv") if r["iso3"] == CODE)
    assert coverage["regression_eligible"] == "False" and coverage["rd_source"] == "Eustat (Basque Country)"
    available = [expected[str(y)]["rd_percent_gdp_derived"] for y in range(2020, 2025) if expected[str(y)]["rd_percent_gdp_derived"] is not None]
    close(coverage["rd_percent_gdp"], sum(available) / len(available))
    close(coverage["gdp_nominal_2025"], expected["2025"]["gdp_per_capita_usd_derived"])
    close(coverage["gdp_ppp_2025"], expected["2025"]["gdp_per_capita_ppp_derived"])
    book = load_workbook(DATA / "world_rd_income_data.xlsx", read_only=True, data_only=True)
    rows = book["Basque annual conversions"].iter_rows(values_only=True)
    headers = next(rows)
    count = 0
    for values in rows:
        row = dict(zip(headers, values))
        for key, value in expected[str(row["year"])].items():
            close(row[key], value)
        count += 1
    assert count == 26
    rows = book["RD nominal annual"].iter_rows(values_only=True)
    headers = next(rows)
    count = 0
    for values in rows:
        row = dict(zip(headers, values))
        if row["iso3"] == CODE:
            close(row["amount"], expected[str(row["year"])][unit_keys[row["unit"]]])
            count += 1
    assert count == len(nominal)
    book.close()
    report = {"built_utc": history["builtUTC"], "annual_years_verified": len(annual), "nominal_rows_verified": len(nominal),
              "sector_field_expected_cells": len(cells), "validation": {k: "passed" for k in [
                  "regional_source_checksums", "same_year_eur_usd_ppp_conversions", "intensity_from_eustat_denominator", "missing_annual_levels_not_inferred",
                  "regional_identity_and_regression_exclusion", "raw_to_csv_json_and_excel", "static_default_selection"]}}
    (DATA / "basque_validation.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    verify()
