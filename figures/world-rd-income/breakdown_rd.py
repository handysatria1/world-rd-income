"""Annual performer × funder and performer × research-type data and audits.

The two cubes are independent classifications: never infer funder × research type.
Amounts are in units. Subcategories and totals are preserved, not added together.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from basque_rd import px_rows, METHOD, PPP_METHOD
from breakdown_sources import FLOWS, REQUESTS, SOURCES
from official_sources import SOURCES as OFFICIAL_SOURCES
from official_rd import load_official, UK_TYPES, UK_PROXY
from sector_field_rd import BASES, FLAGS, NS, normalized_value, reconcile

COLUMNS = ["iso3", "year", "breakdown", "sector_code", "category_code", "basis", "amount",
           "source_value", "source_unit_multiplier", "currency_code", "base_year", "source_decimals",
           "availability", *FLAGS, "source_file", "value_status", "conversion_divisor",
           "conversion_source_file", "conversion_method", "source_category_label", "source_sector_label", "source_status",
           "source_locator", "reference_period", "methodology_note", "source_currency_code"]
SECTORS = ["_T", "BES", "GOV", "HES", "PNP"]
PARTITIONS = {"funding": ["GOV", "BES", "HES", "PNP", "ROW"], "research": ["BR", "AR", "ED", "CAP_EX_NEC"]}
PROXY_METHOD = ("Eustat current EUR / (OECD Spain GERD current EUR / OECD Spain GERD constant-2020 PPP dollars), "
                "same year and SOF total/total series. Implied national conversion proxy, not a regional or R&D-specific price index; "
                "conditional on rounded OECD inputs. See rd_breakdown_conversion.csv.")


def codebooks(path):
    books, parents = {}, {}
    for cl in ET.parse(path).findall(".//s:Codelist", NS):
        book = {}
        for code in cl.findall("s:Code", NS):
            book[code.get("id")] = next(n.text for n in code.findall("c:Name", NS)
                                       if n.get("{http://www.w3.org/XML/1998/namespace}lang") == "en")
            parent = code.find("s:Parent/Ref", NS)
            parents[(cl.get("id"), code.get("id"))] = "" if parent is None else parent.get("id")
        books[cl.get("id")] = book
    return books, parents


def load_breakdowns(raw: Path, manifest: dict, countries: dict) -> dict:
    for name, url in {**SOURCES, **OFFICIAL_SOURCES}.items():
        assert manifest[name]["url"] == url
        assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == manifest[name]["sha256"]
        if name in REQUESTS:
            assert json.loads(manifest[name]["request_body"]) == REQUESTS[name]
            assert hashlib.sha256(manifest[name]["request_body"].encode()).hexdigest() == manifest[name]["request_sha256"]
    rows, categories, parents, seen, names = [], {}, {}, set(), {}
    for kind, flow in FLOWS.items():
        books, hierarchy = codebooks(raw / f"gerd_{kind}_structure.xml")
        dim = "SECT_FUND" if kind == "funding" else "TYPE_RD"
        book = "CL_" + dim
        categories[kind] = {k: v for k, v in books[book].items() if k != "_Z"}
        parents[kind] = {k: hierarchy[(book, k)] for k in categories[kind]}
        source = f"gerd_{kind}_history.csv"
        with (raw / source).open(encoding="utf-8-sig", newline="") as handle:
            for r in csv.DictReader(handle):
                fixed = {"STRUCTURE_ID": f"OECD.STI.STP:{flow}(1.0)", "FREQ": "A", "MEASURE": "G",
                         "TYPE_COST": "_Z", "FORD": "_Z", "SEO": "_Z",
                         "TYPE_RD" if kind == "funding" else "SECT_FUND": "_Z"}
                assert all(r[k] == v for k, v in fixed.items()), fixed
                iso, year, sector, category = r["REF_AREA"], int(r["TIME_PERIOD"]), r["SECT_PERF"], r[dim]
                assert iso in countries and 2000 <= year <= 2025 and sector in SECTORS
                assert r["Sector of performance"] == books["CL_SECT_FUND"][sector]
                assert r["Sources of funds" if kind == "funding" else "Type of R&D"] == categories[kind][category]
                basis = r["UNIT_MEASURE"] + "_" + r["PRICE_BASE"]
                assert basis in {"XDC_V", "USD_PPP_V", "USD_PPP_Q"}
                assert r["BASE_PER"] == ("2020" if basis == "USD_PPP_Q" else ""), "Review changed price base before publishing"
                assert r["Currency"] == books["CL_UNIT_MEASURE"][r["CURRENCY"]]
                assert basis == "XDC_V" or r["CURRENCY"] == "USD"
                for flag in FLAGS:
                    b = "CL_CONF_STATUS" if flag == "CONF_STATUS" else "CL_AUX_OBS_STATUS" if flag.startswith("AUX") else "CL_OBS_STATUS"
                    assert not r[flag] or r[flag] in books[b]
                key = (iso, year, kind, sector, category, basis)
                assert key not in seen, key
                seen.add(key)
                value, status = normalized_value(r)
                assert 0 <= int(r["DECIMALS"]) <= 15
                names[iso] = r["Reference area"]
                rows.append(dict(zip(COLUMNS, [*key, value, r["OBS_VALUE"], int(r["UNIT_MULT"]), r["CURRENCY"],
                    r["BASE_PER"], int(r["DECIMALS"]), status, *[r[k] for k in FLAGS], source, "reported", "", "",
                    "source value * 10^UNIT_MULT", categories[kind][category], r["Sector of performance"], ""])))
    # Implied Spain price/PPP conversion from two representations of the SAME total.
    spanish = {(r["year"], r["basis"]): r for r in rows if r["iso3"] == "ESP" and r["breakdown"] == "funding"
               and r["sector_code"] == r["category_code"] == "_T"}
    conversions, divisors = [], {}
    for year in range(2000, 2026):
        v, q = spanish.get((year, "XDC_V")), spanish.get((year, "USD_PPP_Q"))
        valid = v and q and v["amount"] is not None and q["amount"] is not None and q["amount"] > 0
        if valid:
            assert v["currency_code"] == "EUR" and q["base_year"] == "2020"
            divisors[year] = Decimal(v["source_value"]) / Decimal(q["source_value"])
        conversions.append({"year": year, "proxy_economy": "ESP", "target_region": "ES-PV", "base_year": "2020",
            "spain_gerd_current_eur_millions": v["source_value"] if v else "",
            "spain_gerd_constant_2020_ppp_millions": q["source_value"] if q else "",
            "eur_per_constant_2020_ppp_dollar": str(divisors.get(year, "")),
            "input_flags": "|".join(f"{r['basis']}:{k}={r[k]}" for r in [v, q] if r for k in FLAGS if r[k]),
            "availability": "available" if valid else "missing_conversion_inputs", "method": PROXY_METHOD,
            "source_file": "gerd_funding_history.csv", "source_url": manifest["gerd_funding_history.csv"]["url"],
            "retrieved_utc": manifest["gerd_funding_history.csv"]["retrieved_utc"]})
    factors = {k: {int(r["date"]): r["value"] for r in json.loads((raw / f"wb_spain_{k}.json").read_bytes(), parse_float=Decimal)[1]}
               for k in ["exchange", "ppp"]}
    sector_map = {"00": "_T", "10": "BES_PNP", "20": "GOV", "30": "HES"}
    funding_map = {"10": "_T", "20": "GOV", "25": "HES", "30": "BES", "40": "PNP", "50": "ROW"}
    meta = json.loads((raw / "eustat_rd_funding_metadata.json").read_bytes())["variables"]
    assert meta[0]["values"] == list(sector_map) and meta[0]["valueTexts"] == ["Total", "Company sector and PNPI", "Public Administration Sector", "Higher Education Sector"]
    assert meta[1]["values"] == list(funding_map) and meta[1]["valueTexts"] == ["Total", "Public Administrations", "Higher education teaching", "Businesses", "Private non profit making institutions", "Coming from abroad"]
    px = (raw / "eustat_rd_funding.px").read_bytes()
    decimals = int(re.search(rb"(?:^|\n)DECIMALS=(\d+);", px)[1])
    assert b'UNITS[en]="thousands euro";' in px and decimals == 0
    for coords, labels, value, status, dataset in px_rows(raw / "eustat_rd_funding.json"):
        year = int(coords["periodo"])
        if not 2000 <= year <= 2025:
            continue
        assert "thousand euro" in dataset["label"] and status in {"", ".", "-"}
        assert not status or value is None
        assert value is None or value >= 0
        for basis, divisor, source, method in [
            ("XDC_V", Decimal(1), "", "source thousand EUR * 1000"),
            ("USD_V", factors["exchange"].get(year), "wb_spain_exchange.json", METHOD),
            ("USD_PPP_V", factors["ppp"].get(year), "wb_spain_ppp.json", PPP_METHOD),
            ("USD_PPP_Q", divisors.get(year), "gerd_funding_history.csv", PROXY_METHOD),
        ]:
            amount = None if value is None or divisor is None else float(Decimal(value) * 1000 / divisor)
            rows.append({"iso3": "ES-PV", "year": year, "breakdown": "funding", "sector_code": sector_map[coords["sector de ejecución"]],
                "category_code": funding_map[coords["origen de los fondos"]], "basis": basis, "amount": amount,
                "source_value": "" if value is None else str(value), "source_unit_multiplier": 3,
                "currency_code": "EUR" if basis == "XDC_V" else "USD", "base_year": "2020" if basis == "USD_PPP_Q" else "",
                "source_decimals": decimals, "availability": "available" if amount is not None else "missing_source_value" if value is None else "missing_conversion_factor",
                **dict.fromkeys(FLAGS, ""), "source_file": "eustat_rd_funding.json", "value_status": "reported" if basis == "XDC_V" else "derived",
                "conversion_divisor": "" if basis == "XDC_V" or divisor is None else str(divisor), "conversion_source_file": source,
                "conversion_method": method, "source_category_label": labels["origen de los fondos"],
                "source_sector_label": labels["sector de ejecución"], "source_status": status})
    names["ES-PV"] = "Basque Country"
    # This is a cost table: only total and capital can enter the research panel.
    # Basic/applied/experimental observations remain absent, not estimated.
    for coords, labels, value, status, dataset in px_rows(raw / "eustat_rd_cost.json"):
        year = int(coords["periodo"])
        if not 2000 <= year <= 2025 or coords["naturaleza"] not in {"10", "60"}:
            continue
        assert labels["naturaleza"] == {"10": "Total", "60": "-Capital expenditures"}[coords["naturaleza"]]
        assert value is None or value >= 0
        for basis, divisor, source, method in [
            ("XDC_V", Decimal(1), "", "source thousand EUR * 1000"),
            ("USD_V", factors["exchange"].get(year), "wb_spain_exchange.json", METHOD),
            ("USD_PPP_V", factors["ppp"].get(year), "wb_spain_ppp.json", PPP_METHOD),
            ("USD_PPP_Q", divisors.get(year), "gerd_funding_history.csv", PROXY_METHOD),
        ]:
            amount = None if value is None or divisor is None else float(Decimal(value) * 1000 / divisor)
            rows.append({"iso3": "ES-PV", "year": year, "breakdown": "research", "sector_code": sector_map[coords["sector de ejecución"]],
                "category_code": "_T" if coords["naturaleza"] == "10" else "CAP_EX_NEC", "basis": basis, "amount": amount,
                "source_value": "" if value is None else str(value), "source_unit_multiplier": 3, "source_decimals": 0,
                "currency_code": "EUR" if basis == "XDC_V" else "USD", "source_currency_code": "EUR",
                "base_year": "2020" if basis == "USD_PPP_Q" else "", "availability": "available" if amount is not None else "missing_source_value" if value is None else "missing_conversion_factor",
                **dict.fromkeys(FLAGS, ""), "source_file": "eustat_rd_cost.json", "value_status": "reported" if basis == "XDC_V" else "derived",
                "conversion_divisor": "" if basis == "XDC_V" or divisor is None else str(divisor), "conversion_source_file": source,
                "conversion_method": method, "source_category_label": labels["naturaleza"], "source_sector_label": labels["sector de ejecución"],
                "source_status": status, "source_locator": "PX_043201_cid_res05: " + str(coords), "reference_period": str(year),
                "methodology_note": "Only total and separately reported capital are available. Basic/applied/experimental split not published in the accessed tables. Grey remainder is unclassified current expenditure. Business + PNP are combined."})
    cost_px = (raw / "eustat_rd_cost.px").read_bytes()
    assert b'UNITS[en]="thousands euro";' in cost_px and re.search(rb"(?:^|\n)DECIMALS=(\d+);", cost_px)[1] == b"0"
    official, official_funding, intensity, uk_conversions = load_official(raw, rows)
    # Preserve the differently defined OECD estimates in their own export.
    replaced = lambda r: r["iso3"] == "GBR" and r["breakdown"] == "research" and r["sector_code"] == "BES" and 2022 <= r["year"] <= 2024
    alternatives = [r for r in rows if replaced(r)]
    rows = [r for r in rows if not replaced(r)] + official
    for r in [*rows, *alternatives, *official_funding]:
        for k in COLUMNS:
            r.setdefault(k, "")
        if not r["source_currency_code"]:
            r["source_currency_code"] = "EUR" if r["iso3"] == "ES-PV" else r["currency_code"]
    rows.sort(key=lambda r: tuple(r[k] for k in COLUMNS[:6]))
    assert len({tuple(r[k] for k in COLUMNS[:6]) for r in rows}) == len(rows)
    return {"columns": COLUMNS, "rows": [[r[k] for k in COLUMNS] for r in rows], "categories": categories,
            "categoryParents": parents, "partitions": PARTITIONS, "areaNames": names,
            "sectors": {**{s: books["CL_SECT_FUND"][s] for s in SECTORS}, "BES_PNP": "Companies + private non-profits (Eustat)"},
            "bases": {**BASES, "USD_PPP_Q": {**BASES["USD_PPP_Q"], "label": "Constant 2020 US dollars, PPP converted"}},
            "sources": {name: manifest[name] for name in [*SOURCES, *OFFICIAL_SOURCES, "wb_spain_exchange.json", "wb_spain_ppp.json"]},
            "flagLabels": {k: books[k] for k in ["CL_OBS_STATUS", "CL_AUX_OBS_STATUS", "CL_CONF_STATUS"]},
            "conversions": conversions, "officialConversions": uk_conversions,
            "alternativeRows": [[r[k] for k in COLUMNS] for r in alternatives],
            "officialFundingRows": [[r[k] for k in COLUMNS] for r in official_funding],
            "officialIntensity": {"GBR": intensity}}


def records(dataset):
    for values in dataset["rows"]:
        yield dict(zip(COLUMNS, values))


def annual_records(dataset):
    for r in records(dataset):
        source = dataset["sources"][r["source_file"]]
        conversion = dataset["sources"].get(r["conversion_source_file"], {})
        yield {**r, "economy": dataset["areaNames"][r["iso3"]], "sector": dataset["sectors"][r["sector_code"]],
               "category": dataset["categories"][r["breakdown"]][r["category_code"]],
               "category_parent": dataset["categoryParents"][r["breakdown"]][r["category_code"]],
               "amount_scale": "units", "unit_and_price": dataset["bases"][r["basis"]]["label"],
                "source_currency": r["source_currency_code"],
               "source_url": source["url"], "retrieved_utc": source["retrieved_utc"],
               "conversion_source_url": conversion.get("url", ""), "conversion_retrieved_utc": conversion.get("retrieved_utc", "")}


def reconciliation_records(dataset):
    blocks = defaultdict(dict)
    for r in records(dataset):
        blocks[(r["iso3"], r["year"], r["basis"], r["breakdown"])][(r["sector_code"], r["category_code"])] = r
    for (iso, year, basis, kind), cells in sorted(blocks.items()):
        sectors = ["_T", "BES_PNP", "GOV", "HES"] if iso == "ES-PV" else SECTORS
        checks = [("categories", s, (s, "_T"), [(s, c) for c in PARTITIONS[kind]]) for s in sectors]
        checks += [("performers", c, ("_T", c), [(s, c) for s in sectors[1:]]) for c in sorted({k[1] for k in cells})]
        for axis, category, total, parts in checks:
            if not any(k in cells for k in [total, *parts]):
                continue
            chosen = [cells.get(k) for k in [total, *parts]]
            yield {"iso3": iso, "year": year, "basis": basis, "breakdown": kind, "check": axis, "category": category,
                   "components": "|".join(c if axis == "categories" else s for s, c in parts),
                   **reconcile(chosen[0], chosen[1:]),
                   "flags": "|".join(sorted({f"{k}={r[k]}" for r in chosen if r for k in FLAGS if r[k]}))}


def coverage_records(dataset, countries):
    counts = defaultdict(Counter)
    for r in records(dataset):
        count = counts[(r["iso3"], r["year"], r["basis"], r["breakdown"])]
        count["source_cells"] += 1
        count[r["availability"]] += 1
    for country in countries:
        for year in range(2000, 2026):
            for basis in BASES:
                for kind in PARTITIONS:
                    count = counts[(country["iso"], year, basis, kind)]
                    yield {"iso3": country["iso"], "economy": country["name"], "year": year, "basis": basis, "breakdown": kind,
                           **{k: count[k] for k in ["source_cells", "available", "missing_source_value", "included_elsewhere",
                                                   "confidential_or_restricted", "missing_conversion_factor"]},
                            "coverage_status": "source_rows_returned" if count else "not_returned"}


def official_funding_comparison(dataset):
    """Compare aligned source cells; preserve disagreements beyond displayed rounding."""
    key = lambda r: (r["year"], r["sector_code"], r["category_code"])
    oecd = {key(r): r for r in records(dataset) if r["iso3"] == "GBR" and r["breakdown"] == "funding" and r["basis"] == "XDC_V"}
    for ons in records({**dataset, "rows": dataset["officialFundingRows"]}):
        other = oecd[key(ons)]
        assert ons["currency_code"] == other["currency_code"] == "GBP"
        amounts = [Decimal(r["source_value"]) * Decimal(10) ** r["source_unit_multiplier"] for r in [ons, other]]
        difference = amounts[0] - amounts[1]
        tolerance = sum(Decimal("0.5") * Decimal(10) ** (r["source_unit_multiplier"] - r["source_decimals"]) for r in [ons, other])
        yield {"iso3": "GBR", "year": ons["year"], "sector_code": ons["sector_code"], "category_code": ons["category_code"],
            "basis": "XDC_V", "currency_code": "GBP", "ons_amount": str(amounts[0]), "oecd_amount": str(amounts[1]),
            "ons_minus_oecd": str(difference), "rounding_tolerance": str(tolerance),
            "result": "within_source_rounding" if abs(difference) <= tolerance else "discrepancy_retained",
            "ons_source_file": ons["source_file"], "ons_source_locator": ons["source_locator"],
            "ons_source_url": dataset["sources"][ons["source_file"]]["url"],
            "oecd_source_file": other["source_file"], "oecd_source_url": dataset["sources"][other["source_file"]]["url"],
            "oecd_flags": "|".join(f"{k}={other[k]}" for k in FLAGS if other[k])}


DEFINITIONS = {
    "scope": "Two independent cubes: performer x funder and performer x type of R&D. They do NOT establish funder x type. GOV research means government-performed, not government-funded research.",
    "amounts": "OECD reported millions x 1e6; Eustat thousand EUR x 1000. Null includes missing/restricted/included elsewhere. Eustat '.' and '-' symbols accompany null; their specific meaning is unresolved and neither is converted to zero. Absence is not zero. Detailed subcategories overlap parents and must not be stacked with them.",
    "window": "For each bar, find categories with at least one numeric observation in the requested window. Use the intersection of their numeric years and the reported total's years. Never average different components over different years. Strict mode requires all requested years. Economies may have different common-year subsets; labels and exports disclose these.",
    "composition": "Default: 100 x sum(category amounts) / sum(reported total amounts) over common years (ratio of means). Optional: arithmetic mean of same-year category/total percentages. These differ when total spending changes. No renormalization of known categories. Undefined shares for zero/nonpositive totals stay null.",
    "incomplete_categories": "A category absent throughout the window remains null. A bar can show the other categories with a labelled unallocated residual (reported total minus known components); this is a derived accounting gap, not a classified observation. Negative discrepancies are retained. Complete-year coverage does not imply complete categories.",
    "intensity": "Overlay: arithmetic mean of GERD/GDP percentages for exactly the bar years, using one provider by coverage (OECD preferred on ties). Show no overlay if any bar year is missing. Intensity provider/vintage may differ from RDS expenditure; it is not calculated from constant-price expenditure.",
    "research_types": "Basic, applied, experimental development, plus capital expenditure not elsewhere recorded. Capital is a separate category, not a research type; do not quietly force three types to 100%. Missing capital does not prove zero. Reconciliation requires all four components.",
    "basque": "Eustat performer BES_PNP combines companies and private non-profits; separate funding BES and PNP do exist. The research panels show reported total and capital from the cost table; basic/applied/experimental remain unreported. The grey remainder is unclassified current expenditure, not a type estimate. Region overlaps Spain.",
    "uk_research": UK_TYPES + " Government 2024 types remain unavailable: ONS GovERD Table 10 is NET expenditure, not government-performed R&D.",
    "uk_conversion": UK_PROXY,
    "uk_funding_check": "Direct ONS funding references are compared with the OECD cube using summed half-last-displayed-digit rounding tolerances. Any disagreement is retained in rd_ons_funding_comparison.csv; neither source is silently overwritten.",
    "uk_intensity": "Dashboard overlays additionally consider one ONS provider series: 2018–2021 from the 2023 release (indicative), 2022–2024 from the 2024 release. Earlier and later GDP vintages differ; 2022 is a methodology/vintage break. Select by coverage, preferring OECD on ties. Do not splice ONS and OECD within a window.",
    "basque_constant_ppp": PROXY_METHOD,
    "bases": "Current national currency, current USD at market rate (Basque only), current PPP and constant-2020 PPP are distinct. The latter is supplied by OECD; Basque uses a derived national conversion proxy. Do not compare amounts across national currencies. No missing conversion is carried forward.",
    "reconciliation": "Complete disjoint partitions only, on identical currency/price/base year. Decimal arithmetic and half-last-displayed-digit tolerances; conditional on conversion factors. Discrepancies remain in the data. Dataflows may disagree; no cross-flow replacement of totals.",
}


def definition_records(dataset):
    for code, label in DEFINITIONS.items():
        yield {"kind": "definition", "code": code, "label": label, "parent": ""}
    for kind, labels in {"sector": dataset["sectors"], **dataset["categories"], **dataset["flagLabels"]}.items():
        for code, label in labels.items():
            yield {"kind": kind, "code": code, "label": label, "parent": dataset["categoryParents"].get(kind, {}).get(code, "")}


def summary(dataset):
    rows = list(records(dataset))
    return {"rows": len(rows), "numeric_amounts": sum(r["amount"] is not None for r in rows),
            "economies_regions": len(dataset["areaNames"]), "rows_by_breakdown": dict(Counter(r["breakdown"] for r in rows)),
            "availability": dict(Counter(r["availability"] for r in rows)),
            "reconciliation": dict(Counter(r["result"] for r in reconciliation_records(dataset)))}


def breakdown_tables(data):
    d = data["breakdowns"]
    return [("rd_breakdown_annual.csv", "GERD funding research", annual_records(d)),
            ("rd_breakdown_coverage.csv", "GERD breakdown coverage", coverage_records(d, data["countries"])),
            ("rd_breakdown_reconciliation.csv", "GERD breakdown reconciliation", reconciliation_records(d)),
            ("rd_breakdown_definitions.csv", "GERD breakdown definitions", definition_records(d)),
            ("rd_breakdown_conversion.csv", "GERD regional price proxy", iter(d["conversions"])),
            ("rd_official_conversion.csv", "ONS PPP conversion inputs", iter(d["officialConversions"])),
            ("rd_research_oecd_alternatives.csv", "OECD alternative UK research", annual_records({**d, "rows": d["alternativeRows"]})),
            ("rd_ons_funding_reported.csv", "ONS reported funding", annual_records({**d, "rows": d["officialFundingRows"]})),
            ("rd_ons_funding_comparison.csv", "ONS OECD funding comparison", official_funding_comparison(d)),
            ("rd_ons_intensity.csv", "ONS reported intensity", ({"iso3": iso, "year": int(year), "percent_gdp": r["v"],
                **{k: r[k] for k in ["flags", "note", "source_file", "source_locator"]},
                "source_url": d["sources"][r["source_file"]]["url"]}
                for iso, series in d["officialIntensity"].items() for year, r in sorted(series.items())))]


def write_breakdown_csvs(data, destination):
    for name, _, rows in breakdown_tables(data):
        first = next(rows)
        with (destination / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(first))
            writer.writeheader()
            writer.writerow(first)
            writer.writerows(rows)
