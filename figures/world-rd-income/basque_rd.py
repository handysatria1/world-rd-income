"""Normalize Eustat regional amounts and year-matched Spanish conversion factors.

Spain's GDP PPP is a national proxy, not a measured Basque regional price index.
Regional points are displayed but excluded from country regressions (Spain overlaps).
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import re
from decimal import Decimal
from pathlib import Path

from basque_sources import CODE, FACTORS, REQUESTS, SOURCES, TABLES

NAME = "Basque Country"
PROVIDER = "Eustat (Basque Country)"
FIELD_MAP = {"00": "_T", "10": "FORD1", "20": "FORD2", "30": "FORD3", "40": "FORD4", "50": "EUSTAT_SOC"}
FIELD_LABELS = ["Total", "Exact and Natural sciences", "Engineering and Technology", "Medical sciences (Pharmacies included)",
                "Agricultural sciences (livestock, fishing and forestry included)", "Social sciences"]
SECTOR_FILES = {"_T": "rd_total", "BES_PNP": "rd_business_pnp", "GOV": "rd_government", "HES": "rd_higher_education"}
SECTOR_LABELS = {"_T": "Total", "BES_PNP": "Companies and private non-profit institutions (Eustat)",
                 "GOV": "Government", "HES": "Higher education"}
REGIONAL_NOTE = ("Basque Autonomous Community (Spain), ISO 3166-2 ES-PV; overlaps Spain. "
                 "Shown as a regional comparison; excluded from country regressions. "
                 "Current international dollars use Spain's national GDP PPP as a regional proxy, not a Basque price survey.")
METHOD = "Eustat reported current EUR / same-year Spain EUR per US$ (WDI PA.NUS.FCRF)"
PPP_METHOD = "Eustat reported current EUR / same-year Spain EUR per international dollar (WDI PA.NUS.PPP; national GDP-PPP proxy)"


def px_rows(path: Path):
    """Decode JSON-stat 1.2 in documented row-major order, retaining statuses."""
    dataset = json.loads(path.read_bytes(), parse_float=Decimal)["dataset"]
    dimension = dataset["dimension"]
    ids, sizes = dimension["id"], dimension["size"]
    categories = []
    for code, size in zip(ids, sizes):
        index = dimension[code]["category"]["index"]
        values = sorted(index, key=index.get) if isinstance(index, dict) else index
        assert len(values) == size
        categories.append(values)
    values = dataset["value"]
    assert isinstance(values, list) and len(values) == math.prod(sizes)
    statuses = dataset.get("status", {})
    for i, keys in enumerate(itertools.product(*categories)):
        coordinates = dict(zip(ids, keys))
        labels = {code: dimension[code]["category"]["label"][value] for code, value in coordinates.items()}
        status = statuses[i] if isinstance(statuses, list) else statuses.get(str(i), "")
        yield coordinates, labels, values[i], status or "", dataset


def load_basque(raw: Path, manifest: dict) -> tuple[dict, list[dict], list[dict]]:
    for name, url in SOURCES.items():
        assert manifest[name]["url"] == url
        assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == manifest[name]["sha256"]
        if name in REQUESTS:
            assert json.loads(manifest[name]["request_body"]) == REQUESTS[name]
            assert hashlib.sha256(manifest[name]["request_body"].encode()).hexdigest() == manifest[name]["request_sha256"]
    gdp_notes = (raw / "eustat_gdp_per_capita_notes.html").read_text("utf-8")
    assert "Current prices (euros and variation rate)" in gdp_notes
    advance_years = set(map(int, re.findall(r">\s*(\d{4})\(a\)\s*<", gdp_notes)))
    assert "(a)Advanced data" in gdp_notes or not advance_years
    factors, factor_obs = {}, {}
    for kind, indicator in FACTORS.items():
        meta, rows = json.loads((raw / f"wb_spain_{kind}.json").read_bytes(), parse_float=Decimal)
        assert int(meta["pages"]) == int(meta["page"]) == 1 and len(rows) == int(meta["total"])
        factors[kind], factor_obs[kind] = {}, {}
        for row in rows:
            assert row["countryiso3code"] == "ESP" and row["indicator"]["id"] == indicator
            year = int(row["date"])
            assert year not in factors[kind]
            value = row["value"]
            assert value is None or Decimal(value) > 0
            factors[kind][year] = None if value is None else Decimal(value)
            factor_obs[kind][year] = row
    local, pc, cells = {}, {}, []
    for key in ["gdp_per_capita", "gdp_total", *SECTOR_FILES.values()]:
        name = f"eustat_{key}.json"
        for coordinates, labels, value, status, dataset in px_rows(raw / name):
            year = int(coordinates["periodo"])
            if not 2000 <= year <= 2025:
                continue
            # Unexpected classifications must be reviewed before any new build.
            assert status in {"", "."}, f"Inspect new Eustat status before using amounts: {name}, {status}"
            assert not status or value is None, "A flagged numeric Eustat value requires review"
            assert value is None or Decimal(value) >= 0
            if key.startswith("gdp_"):
                assert labels[next(iter(coordinates))] == "Basque Country"
                if key == "gdp_total":
                    assert labels["tipo de medida"] == "Current prices (thousand euros)" and labels["tipo de dato"] == "Level"
                assert value is None or Decimal(value) > 0
                target = pc if key == "gdp_per_capita" else local
                assert year not in target
                target[year] = None if value is None else Decimal(value) * (1 if key == "gdp_per_capita" else 1000)
            else:
                assert coordinates["naturaleza"] == "10" and labels["naturaleza"] == "Total"
                decimals = dataset.get("extension", {}).get("px", {}).get("decimals")
                if decimals is None:
                    px = (raw / f"eustat_{key}.px").read_bytes()
                    decimals = int(re.search(rb"(?:^|\n)DECIMALS=(\d+);", px)[1])
                    assert b'UNITS[en]="thousand euro";' in px
                assert decimals == 0
                field_key = next(k for k in coordinates if k not in {"naturaleza", "periodo"})
                assert coordinates[field_key] in FIELD_MAP
                assert labels[field_key] == FIELD_LABELS[list(FIELD_MAP).index(coordinates[field_key])]
                assert "thousand euro" in dataset["label"]
                sector = next(s for s, f in SECTOR_FILES.items() if f == key)
                cells.append({"year": year, "sector_code": sector, "field_code": FIELD_MAP[coordinates[field_key]],
                              "source_field_label": labels[field_key], "source_sector_label": SECTOR_LABELS[sector],
                              "source_value": "" if value is None else str(value), "source_file": name, "source_status": status,
                              "eur": None if value is None else Decimal(value) * 1000})
    totals = {r["year"]: r for r in cells if r["sector_code"] == r["field_code"] == "_T"}
    assert len({(r["year"], r["sector_code"], r["field_code"]) for r in cells}) == len(cells)
    country = {"iso": CODE, "name": NAME, "geographyType": "region", "parentEconomy": "ESP",
               "regressionEligible": False, "note": REGIONAL_NOTE, "rdProviders": ["eustat"],
               "rd": {"oecd": {}, "wdi": {}, "eustat": {}}, "gdp": {"nominal": {}, "ppp": {}},
               "gdpTotalUSD": {}, "rdNominal": {"localOECD": {}, "localEustat": {}, "pppEustat": {},
                                                 "usd": {"oecd": {}, "wdi": {}, "uis": {}, "eustat": {}}}}
    annual = []
    def number(v):
        return None if v is None else float(v)
    def divide(value, divisor):
        return None if value is None or divisor is None else value / divisor
    for year in range(2000, 2026):
        key = str(year)
        eur = totals.get(year, {}).get("eur")
        gdp, per_capita = local.get(year), pc.get(year)
        fx, ppp = factors["exchange"].get(year), factors["ppp"].get(year)
        share = None if eur is None or gdp is None else eur / gdp * 100
        usd, intl = divide(eur, fx), divide(eur, ppp)
        note = "Derived intensity: Eustat reported GERD EUR / same-year Eustat current-price GDP EUR × 100; latest GDP vintage may revise published ratios."
        if share is not None:
            country["rd"]["eustat"][key] = {"v": number(share), "flags": "derived_ratio", "note": note}
        for kind, factor in [("nominal", fx), ("ppp", ppp)]:
            amount = divide(per_capita, factor)
            if amount is not None:
                country["gdp"][kind][key] = {"v": number(amount), "flags": "derived; national_PPP_proxy" if kind == "ppp" else "derived",
                    "note": (PPP_METHOD if kind == "ppp" else METHOD) + "; GDP/person in EUR from Eustat; " + REGIONAL_NOTE}
                if year in advance_years:
                    country["gdp"][kind][key]["flags"] += "; Eustat_advance"
        total_usd = divide(gdp, fx)
        if total_usd is not None:
            country["gdpTotalUSD"][key] = {"v": number(total_usd), "flags": "derived", "note": METHOD + "; Eustat GDP total"}
        if eur is not None:
            country["rdNominal"]["localEustat"][key] = {"v": number(eur), "sourceValue": totals[year]["source_value"], "unitMultiplier": 3}
            country["rdNominal"]["pppEustat"][key] = {"v": number(intl), "note": PPP_METHOD}
            country["rdNominal"]["usd"]["eustat"][key] = {"v": number(usd), "rdPercent": number(share), "gdpTotalUSD": number(total_usd),
                "flags": "derived_currency_conversion", "note": METHOD, "gdpFlags": "derived", "gdpNote": "Eustat GDP, converted using Spain's exchange rate",
                "missingReason": "Missing same-year exchange factor" if fx is None else ""}
        record = {"iso3": CODE, "economy": NAME, "geography_type": "region", "parent_economy": "ESP", "regression_eligible": False,
            "year": year, "gerd_eur_reported": number(eur), "gdp_eur_reported": number(gdp), "gdp_per_capita_eur_reported": number(per_capita),
            "gdp_per_capita_status": "advance (Eustat display-table footnote)" if year in advance_years else "no advance flag in archived display table",
            "rd_percent_gdp_derived": number(share), "eur_per_usd": number(fx), "eur_per_international_dollar": number(ppp),
            "gerd_usd_derived": number(usd), "gerd_ppp_derived": number(intl), "gdp_total_usd_derived": number(total_usd),
            "gdp_per_capita_usd_derived": number(divide(per_capita, fx)), "gdp_per_capita_ppp_derived": number(divide(per_capita, ppp)),
            "rd_missing_reason": "No reported annual expenditure level in archived Eustat tables; advance growth is not an expenditure level" if eur is None else "",
            "usd_method": METHOD, "ppp_method": PPP_METHOD, "intensity_method": note, "regional_note": REGIONAL_NOTE}
        for label, name in [("rd", "eustat_rd_total.json"), ("gdp", "eustat_gdp_total.json"),
                            ("gdp_per_capita", "eustat_gdp_per_capita.json"), ("exchange", "wb_spain_exchange.json"), ("ppp", "wb_spain_ppp.json")]:
            record.update({f"{label}_source_file": name, f"{label}_source_url": manifest[name]["url"],
                           f"{label}_retrieved_utc": manifest[name]["retrieved_utc"]})
        for kind in FACTORS:
            obs = factor_obs[kind].get(year, {})
            record[f"{kind}_flags"] = obs.get("obs_status", "")
            record[f"{kind}_note"] = obs.get("footnote", "")
        annual.append(record)
    # Converted cells retain their original EUR value and exact annual divisor.
    converted = []
    for cell in cells:
        for basis, kind in [("XDC_V", None), ("USD_V", "exchange"), ("USD_PPP_V", "ppp")]:
            divisor = Decimal(1) if kind is None else factors[kind].get(cell["year"])
            amount = divide(cell["eur"], divisor)
            converted.append({k: v for k, v in {
                **cell, "iso3": CODE, "basis": basis, "amount": number(amount), "source_unit_multiplier": 3,
                "currency_code": "EUR" if kind is None else "USD", "base_year": "", "source_decimals": 0,
                "availability": "available" if amount is not None else "missing_conversion_factor" if cell["eur"] is not None else "missing_source_value",
                "value_status": "reported" if kind is None else "derived", "conversion_divisor": "" if kind is None or divisor is None else str(divisor),
                "conversion_source_file": "" if kind is None else f"wb_spain_{kind}.json",
                "conversion_method": "source thousand EUR × 1000" if kind is None else METHOD if kind == "exchange" else PPP_METHOD,
            }.items() if k != "eur"})
    return country, annual, converted


def basque_tables(data: dict):
    return [("basque_annual.csv", "Basque annual conversions", iter(data["basqueAnnual"]))]


def write_basque_csv(data: dict, destination: Path):
    for name, _, rows in basque_tables(data):
        first = next(rows)
        with (destination / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(first))
            writer.writeheader()
            writer.writerow(first)
            writer.writerows(rows)
