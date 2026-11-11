"""Build the offline, selectable-year explorer from archived annual observations."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

from download_data import HISTORY_END, HISTORY_SOURCES, HISTORY_START, INDICATORS, NOMINAL_SOURCES, SECTOR_FIELD_SOURCES, SOURCES, UIS_ARCHIVE
from nominal_rd import attach_nominal_data, nominal_summary, write_nominal_csvs
from sector_field_rd import load_sector_field, sector_field_summary, write_sector_field_csvs
from basque_sources import SOURCES as BASQUE_SOURCES
from basque_rd import load_basque, write_basque_csv
from breakdown_sources import SOURCES as BREAKDOWN_SOURCES
from official_sources import SOURCES as OFFICIAL_SOURCES
from breakdown_rd import load_breakdowns, summary as breakdown_summary, write_breakdown_csvs

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"


def load_history() -> dict:
    manifest = json.loads((RAW / "manifest.json").read_text("utf-8"))
    names = ["wb_countries.json", *HISTORY_SOURCES]
    for name in names:
        assert manifest[name]["url"] == SOURCES[name]
        assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == manifest[name]["sha256"]

    def payload(name):
        meta, rows = json.loads((RAW / name).read_text("utf-8"))
        assert int(meta["pages"]) == 1 and int(meta["page"]) == 1
        assert len(rows) == int(meta["total"])
        return rows

    catalog = payload("wb_countries.json")
    iso2 = {r["iso2Code"]: r for r in catalog}
    countries = {
        r["id"]: {"iso": r["id"], "name": r["name"], "rd": {"oecd": {}, "wdi": {}},
                  "gdp": {"nominal": {}, "ppp": {}}}
        for r in catalog if r["region"]["id"] != "NA"
    }
    countries["TWN"] = {"iso": "TWN", "name": "Chinese Taipei", "rd": {"oecd": {}, "wdi": {}},
                        "gdp": {"nominal": {}, "ppp": {}}}
    for key, (indicator, _) in INDICATORS.items():
        seen = set()
        for row in payload(f"wb_{key}_history.json"):
            assert row["indicator"]["id"] == indicator
            code = row["countryiso3code"] or iso2[row["country"]["id"]]["id"]
            year = int(row["date"])
            assert HISTORY_START <= year <= HISTORY_END
            assert (code, year) not in seen
            seen.add((code, year))
            value = row["value"]
            if code not in countries or value is None:
                continue
            value = float(value)
            assert math.isfinite(value) and (value >= 0 if key == "rd" else value > 0)
            observation = {"v": value, "flags": row.get("obs_status", ""), "note": row.get("footnote", "")}
            series = countries[code]["rd"]["wdi"] if key == "rd" else countries[code]["gdp"][key]
            series[str(year)] = observation

    benchmark, seen = {}, set()
    with (RAW / "msti_gerd_percent_gdp_history.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for column, value in {"FREQ": "A", "MEASURE": "G", "UNIT_MEASURE": "PT_B1GQ",
                                  "PRICE_BASE": "_Z", "TRANSFORMATION": "_Z"}.items():
                assert row[column] == value
            assert int(row["UNIT_MULT"]) == 0
            code, year = row["REF_AREA"], int(row["TIME_PERIOD"])
            assert HISTORY_START <= year <= HISTORY_END
            assert (code, year) not in seen
            seen.add((code, year))
            assert code in countries or code in {"OECD", "EU27_2020"}, f"Classify new OECD area: {code}"
            if not row["OBS_VALUE"].strip():
                continue
            value = float(row["OBS_VALUE"])
            assert math.isfinite(value) and value >= 0
            observation = {"v": value, "flags": "|".join(row.get(k, "") for k in
                           ["OBS_STATUS", "OBS_STATUS_2", "OBS_STATUS_3", "AUX_OBS_STATUS"] if row.get(k)), "note": ""}
            if code == "OECD":
                benchmark[str(year)] = observation
            elif code in countries:
                countries[code]["rd"]["oecd"][str(year)] = observation

    nominal = attach_nominal_data(countries, RAW, manifest)
    basque, basque_annual, basque_cells = load_basque(RAW, manifest)
    countries[basque["iso"]] = basque
    sector_field = load_sector_field(RAW, manifest, countries, basque_cells)
    sector_field["summary"] = sector_field_summary(sector_field)
    breakdowns = load_breakdowns(RAW, manifest, countries)
    breakdowns["summary"] = breakdown_summary(breakdowns)
    names += [*NOMINAL_SOURCES, UIS_ARCHIVE, *SECTOR_FIELD_SOURCES, *BASQUE_SOURCES, *BREAKDOWN_SOURCES, *OFFICIAL_SOURCES]
    return {
        "firstYear": HISTORY_START, "lastYear": HISTORY_END,
        "countries": sorted(countries.values(), key=lambda r: r["name"]),
        "benchmark": benchmark,
        "nominalRD": nominal,
        "basqueAnnual": basque_annual,
        "sectorField": sector_field,
        "breakdowns": breakdowns,
        "retrievalDates": sorted({manifest[name]["retrieved_utc"][:10] for name in names}),
        "datasetDates": {key: manifest[f"wb_{key}_history.json"].get("api_lastupdated", "") for key in INDICATORS},
        "sources": {name: manifest[name] for name in names},
    }


def build_explorer(report: dict, data: dict | None = None) -> None:
    if data is None:
        data = load_history()
    data["builtUTC"] = report["built_utc"]
    write_nominal_csvs(data, ROOT / "data")
    write_sector_field_csvs(data, ROOT / "data")
    write_basque_csv(data, ROOT / "data")
    write_breakdown_csvs(data, ROOT / "data")
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    (ROOT / "data" / "explorer_history.json").write_text(serialized + "\n", encoding="utf-8")
    safe_json = serialized.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    template = (ROOT / "explorer.html").read_text("utf-8")
    for marker, value in {
        "__EXPLORER_CSS__": (ROOT / "explorer.css").read_text("utf-8"),
        "__EXPLORER_DATA__": safe_json,
        "__EXPLORER_CORE__": (ROOT / "explorer_core.js").read_text("utf-8"),
        "__BREAKDOWN_CORE__": (ROOT / "breakdown_core.js").read_text("utf-8"),
        "__EXPLORER_JS__": (ROOT / "explorer.js").read_text("utf-8"),
    }.items():
        assert template.count(marker) == 1
        template = template.replace(marker, value)
    (ROOT / "output" / "world_rd_income_explorer.html").write_text(template, encoding="utf-8")
    validation = {
        "built_utc": report["built_utc"], "first_year": HISTORY_START, "last_year": HISTORY_END,
        "economies": len(data["countries"]),
        "observations": {key: sum(len(c["rd"]["wdi"] if key == "rd" else c["gdp"][key])
                                      for c in data["countries"]) for key in INDICATORS},
        "oecd_rd_observations": sum(len(c["rd"]["oecd"]) for c in data["countries"]),
        "nominal_rd": nominal_summary(data),
        "sector_field_gerd": data["sectorField"]["summary"],
        "funding_research": data["breakdowns"]["summary"],
        "validation": {key: "passed" for key in ["hashes_and_urls", "complete_api_responses", "series_dimensions_and_years",
                                                   "unique_economy_years", "finite_values_and_valid_units", "aggregates_excluded",
                                                   "nominal_units_and_price_basis", "same_year_total_gdp_inputs", "uis_metadata_and_release",
                                                   "sector_field_dimensions_units_flags_and_hierarchy", "unique_sector_field_cells",
                                                   "sector_field_reconciliation_recorded_without_imputation"]},
    }
    (ROOT / "data" / "explorer_validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_explorer(json.loads((ROOT / "data" / "validation_report.json").read_text("utf-8")))
