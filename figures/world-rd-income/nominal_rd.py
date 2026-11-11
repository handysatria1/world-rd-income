"""Annual nominal GERD: reported OECD national currency and derived current USD.

USD estimates use same-economy, same-year R&D/GDP * total GDP / 100.
Provider alternatives stay separate; no PPP, per-capita or averaged GDP is used.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

from download_data import HISTORY_END, HISTORY_START, NOMINAL_SOURCES, UIS_ARCHIVE, uis_archive_url
from basque_rd import CODE as BASQUE_CODE, PROVIDER as EUSTAT_SOURCE, METHOD as EUSTAT_METHOD, PPP_METHOD

SOURCE_NAMES = {"oecd": "OECD MSTI", "wdi": "UNESCO UIS via World Bank WDI", "uis": "UNESCO UIS direct", "eustat": EUSTAT_SOURCE}
RD_FILES = {"oecd": "msti_gerd_percent_gdp_history.csv", "wdi": "wb_rd_history.json", "uis": UIS_ARCHIVE}
GDP_FILE = "wb_gdp_total_usd_history.json"
LOCAL_FILE = "msti_gerd_nominal_local_history.csv"
FORMULA = "annual GERD_percent_GDP / 100 * same-year total GDP (current US$)"


def finite_nonnegative(value) -> float:
    value = float(value)
    assert math.isfinite(value) and value >= 0, "Invalid R&D value"
    return value


def oecd_local_value(row: dict) -> float | None:
    for key, value in {"FREQ": "A", "MEASURE": "G", "UNIT_MEASURE": "XDC",
                       "PRICE_BASE": "V", "TRANSFORMATION": "_Z"}.items():
        assert row[key] == value, f"Unexpected nominal OECD dimension: {key}"
    multiplier = int(row["UNIT_MULT"])
    assert multiplier == 6, "Inspect a changed OECD unit multiplier before using it"
    if not row["OBS_VALUE"].strip():
        return None
    return finite_nonnegative(row["OBS_VALUE"]) * 10 ** multiplier


def uis_value(row: dict) -> float | None:
    # MAGNITUDE is a quality/category flag, NOT a numerical scale multiplier.
    magnitude = row["MAGNITUDE"]
    assert magnitude in {"", "NIL", "NA", "SUPP", "LOWREL", "INCLUDED", "INCLUDES"}
    if magnitude in {"NA", "SUPP", "INCLUDED"} or not row["VALUE"].strip():
        return None
    value = finite_nonnegative(row["VALUE"])
    if magnitude == "NIL":
        assert value == 0
    return value


def derive_series(rd: dict, gdp: dict) -> dict:
    """Join annual inputs by year, preserving missing GDP and observed zero R&D."""
    result = {}
    for year, observation in rd.items():
        income = gdp.get(year)
        percent = finite_nonnegative(observation["v"])
        total = None if income is None else float(income["v"])
        if total is not None:
            assert math.isfinite(total) and total > 0
        amount = None if total is None else percent / 100 * total
        assert amount is None or math.isfinite(amount)
        result[year] = {
            "v": amount, "rdPercent": percent, "gdpTotalUSD": total,
            "flags": observation.get("flags", ""), "note": observation.get("note", ""),
            "gdpFlags": "" if income is None else income.get("flags", ""),
            "gdpNote": "" if income is None else income.get("note", ""),
            "missingReason": "Missing same-year WDI total GDP in current US$" if total is None else "",
        }
    return result


def attach_nominal_data(countries: dict, raw: Path, manifest: dict) -> dict:
    """Validate archives, then add nominal series to each historical economy."""
    for name, url in NOMINAL_SOURCES.items():
        assert manifest[name]["url"] == url
        assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == manifest[name]["sha256"]
    assert manifest[UIS_ARCHIVE]["url"] == uis_archive_url((raw / "uis_science_bulk.html").read_bytes())
    assert hashlib.sha256((raw / UIS_ARCHIVE).read_bytes()).hexdigest() == manifest[UIS_ARCHIVE]["sha256"]
    for country in countries.values():
        country["gdpTotalUSD"] = {}
        country["rdNominal"] = {"usd": {}, "localOECD": {}}

    metadata, rows = json.loads((raw / GDP_FILE).read_text("utf-8"))
    assert int(metadata["pages"]) == int(metadata["page"]) == 1
    assert len(rows) == int(metadata["total"])
    seen = set()
    for row in rows:
        assert row["indicator"]["id"] == "NY.GDP.MKTP.CD"
        code, year = row["countryiso3code"], int(row["date"])
        assert HISTORY_START <= year <= HISTORY_END
        # Catalog country ID is populated even for aggregates with blank ISO3.
        key = (row["country"]["id"], year)
        assert key not in seen
        seen.add(key)
        if code not in countries or row["value"] is None:
            continue
        value = float(row["value"])
        assert math.isfinite(value) and value > 0
        countries[code]["gdpTotalUSD"][str(year)] = {
            "v": value, "flags": row.get("obs_status", ""), "note": row.get("footnote", "")}

    seen = set()
    with (raw / LOCAL_FILE).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            value = oecd_local_value(row)
            code, year = row["REF_AREA"], int(row["TIME_PERIOD"])
            assert HISTORY_START <= year <= HISTORY_END
            assert (code, year) not in seen
            seen.add((code, year))
            assert code in countries or code in {"OECD", "EU27_2020"}, f"Classify OECD area: {code}"
            if code not in countries or value is None:
                continue
            countries[code]["rdNominal"]["localOECD"][str(year)] = {
                "v": value, "sourceValue": float(row["OBS_VALUE"]), "unitMultiplier": int(row["UNIT_MULT"]),
                "flags": "|".join(row.get(k, "") for k in ["OBS_STATUS", "OBS_STATUS_2", "OBS_STATUS_3", "AUX_OBS_STATUS"] if row.get(k)),
                "note": "OECD XDC at current prices; native national currency, not US dollars. Original values are millions.",
            }

    uis, notes, seen = defaultdict(dict), defaultdict(list), set()
    with ZipFile(raw / UIS_ARCHIVE) as archive:
        assert archive.testzip() is None

        def csv_rows(name):
            return csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig")))

        labels = {r["INDICATOR_ID"]: r["INDICATOR_LABEL_EN"] for r in csv_rows("SCN-SDG_LABEL.csv")}
        assert labels["EXPGDP.TOT"] == "GERD as a percentage of GDP"
        for row in csv_rows("SCN-SDG_METADATA.csv"):
            if row["INDICATOR_ID"] == "EXPGDP.TOT":
                notes[(row["COUNTRY_ID"], row["YEAR"])].append(f"{row['TYPE']}: {row['METADATA']}")
        for row in csv_rows("SCN-SDG_DATA_NATIONAL.csv"):
            if row["INDICATOR_ID"] != "EXPGDP.TOT":
                continue
            code, year = row["COUNTRY_ID"], int(row["YEAR"])
            if not HISTORY_START <= year <= HISTORY_END:
                continue
            assert code in countries, f"Classify UIS economy: {code}"
            assert (code, year) not in seen
            seen.add((code, year))
            value = uis_value(row)
            if value is None:
                continue
            uis[code][str(year)] = {"v": value,
                "flags": "|".join(f"{k}={row[k]}" for k in ["MAGNITUDE", "QUALIFIER"] if row[k]),
                "note": "; ".join(notes[(code, row["YEAR"])])}

    for code, country in countries.items():
        for source, rd in {**country["rd"], "uis": uis[code]}.items():
            country["rdNominal"]["usd"][source] = derive_series(rd, country["gdpTotalUSD"])
    return {"formula": FORMULA, "usdStatus": "derived, not a directly reported dollar series",
            "localStatus": "reported OECD nominal GERD, normalized from millions to national-currency units",
            "uisRelease": manifest[UIS_ARCHIVE]["release"], "gdpDatasetDate": metadata.get("lastupdated", ""),
             "sourceNames": SOURCE_NAMES,
            "basqueMethod": EUSTAT_METHOD, "basquePPPMethod": PPP_METHOD,
            "limitations": "R&D/GDP and WDI GDP vintages/denominators can differ. USD estimates may not reproduce national accounts totals. Current-price amounts are not real growth. UIS and WDI can repeat the same national observations."}


def nominal_tables(data: dict) -> tuple[list, list, list]:
    """Long source-level database and complete economy-year availability audit."""
    records, coverage = [], []
    sources = data["sources"]
    basque = {r["year"]: r for r in data.get("basqueAnnual", [])}
    for country in data["countries"]:
        nominal = country["rdNominal"]
        base = {"economy": country["name"], "iso3": country["iso"]}
        for year in range(data["firstYear"], data["lastYear"] + 1):
            key = str(year)
            audit = {**base, "year": year, "gdp_total_usd_available": key in country["gdpTotalUSD"],
                     "oecd_reported_local_available": key in nominal["localOECD"]}
            local = nominal["localOECD"].get(key)
            if local:
                records.append({**base, "year": year, "rd_source": SOURCE_NAMES["oecd"],
                    "unit": "current national currency (OECD XDC)", "status": "reported", "amount": local["v"],
                    "method": "OECD source value * 10^UNIT_MULT", "rd_source_file": LOCAL_FILE,
                    "rd_url": sources[LOCAL_FILE]["url"], "rd_retrieved_utc": sources[LOCAL_FILE]["retrieved_utc"],
                    "source_value": local["sourceValue"], "source_unit_multiplier": local["unitMultiplier"],
                    "rd_flags": local["flags"], "rd_note": local["note"]})
            for source in SOURCE_NAMES:
                series = nominal["usd"].get(source, {})
                obs = series.get(key)
                audit[f"{source}_derived_usd_available"] = obs is not None and obs["v"] is not None
                audit[f"{source}_missing_reason"] = "No R&D share from this provider in this year" if obs is None else obs["missingReason"]
                if obs is None:
                    continue
                if source == "eustat":
                    inputs = basque[year]
                    for unit, status, amount, method, kind, divisor in [
                        ("current EUR", "reported", inputs["gerd_eur_reported"], "reported thousand EUR × 1000", None, None),
                        ("current US dollars", "derived", inputs["gerd_usd_derived"], EUSTAT_METHOD, "exchange", inputs["eur_per_usd"]),
                        ("current international dollars (PPP)", "derived", inputs["gerd_ppp_derived"], PPP_METHOD, "ppp", inputs["eur_per_international_dollar"]),
                    ]:
                        name = "eustat_rd_total.json"
                        conversion = {} if kind is None else sources[f"wb_spain_{kind}.json"]
                        records.append({**base, "year": year, "rd_source": EUSTAT_SOURCE, "unit": unit, "status": status,
                            "amount": amount, "method": method, "rd_source_file": name, "rd_url": sources[name]["url"],
                            "rd_retrieved_utc": sources[name]["retrieved_utc"], "source_value": nominal["localEustat"][key]["sourceValue"],
                            "source_unit_multiplier": 3, "rd_percent_gdp_input": inputs["rd_percent_gdp_derived"],
                            "rd_input_year": year, "rd_flags": "" if kind is None else "derived_currency_conversion",
                            "rd_note": inputs["regional_note"], "conversion_divisor": divisor,
                            "conversion_source_file": "" if kind is None else f"wb_spain_{kind}.json",
                            "conversion_url": conversion.get("url", ""), "conversion_retrieved_utc": conversion.get("retrieved_utc", ""),
                            "missing_reason": "Missing same-year conversion factor" if amount is None else ""})
                    continue
                name = RD_FILES[source]
                records.append({**base, "year": year, "rd_source": SOURCE_NAMES[source],
                    "unit": "current US dollars", "status": "derived", "amount": obs["v"], "method": FORMULA,
                    "rd_source_file": name, "rd_url": sources[name]["url"], "rd_retrieved_utc": sources[name]["retrieved_utc"],
                    "rd_percent_gdp_input": obs["rdPercent"], "rd_input_year": year,
                    "gdp_total_usd_input": obs["gdpTotalUSD"], "gdp_input_year": year if obs["gdpTotalUSD"] is not None else None,
                    "gdp_source_file": GDP_FILE, "gdp_url": sources[GDP_FILE]["url"], "gdp_retrieved_utc": sources[GDP_FILE]["retrieved_utc"],
                    "rd_flags": obs["flags"], "rd_note": obs["note"], "gdp_flags": obs["gdpFlags"], "gdp_note": obs["gdpNote"],
                    "missing_reason": obs["missingReason"]})
            audit["eustat_reported_eur_available"] = key in nominal.get("localEustat", {})
            audit["eustat_derived_ppp_available"] = nominal.get("pppEustat", {}).get(key, {}).get("v") is not None
            coverage.append(audit)
    definitions = [{"field": key, "description": value} for key, value in data["nominalRD"].items() if key != "sourceNames"]
    return records, coverage, definitions


def nominal_summary(data: dict) -> dict:
    countries = data["countries"]
    return {
        "oecd_reported_local_observations": sum(len(c["rdNominal"]["localOECD"]) for c in countries),
        "oecd_reported_local_economies": sum(bool(c["rdNominal"]["localOECD"]) for c in countries),
        "derived_usd_by_rd_source": {source: {
            "observations": sum(sum(o["v"] is not None for o in c["rdNominal"]["usd"].get(source, {}).values()) for c in countries),
            "economies": sum(any(o["v"] is not None for o in c["rdNominal"]["usd"].get(source, {}).values()) for c in countries),
            "missing_conversion_inputs": sum(sum(o["v"] is None for o in c["rdNominal"]["usd"].get(source, {}).values()) for c in countries),
        } for source in SOURCE_NAMES},
        "uis_release": data["nominalRD"]["uisRelease"],
    }


def write_nominal_csvs(data: dict, destination: Path) -> None:
    for name, rows in zip(["rd_nominal_annual.csv", "rd_nominal_coverage.csv", "rd_nominal_definitions.csv"], nominal_tables(data)):
        keys = list(dict.fromkeys(key for row in rows for key in row))
        with (destination / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
