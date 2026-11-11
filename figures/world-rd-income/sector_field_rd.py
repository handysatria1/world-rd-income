"""OECD GERD jointly classified by performer and field; retain reported cells.

No sums replace source totals. Reconciliation uses disjoint categories, only with
all components available on the same currency/price/base-year basis.
"""

from __future__ import annotations

import csv
import hashlib
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from download_data import HISTORY_END, HISTORY_START, SECTOR_FIELD_SOURCES
from basque_sources import CODE as BASQUE_CODE, SOURCES as BASQUE_SOURCES
from basque_rd import FIELD_MAP, SECTOR_FILES, REGIONAL_NOTE

SOURCE_FILE = "gerd_sector_field_history.csv"
STRUCTURE_FILE = "gerd_ford_structure.xml"
FLOW = "OECD.STI.STP:DSD_RDS_GERD@DF_GERD_FORD(1.0)"
SECTORS = ["_T", "BES", "GOV", "HES", "PNP"]
FIELDS = ["_T", "FORD1", "FORD2", "FORD3", "FORD4", "FORD5", "FORD6", "NEC", "FORD_1T4", "FORD_5_6"]
GROUPS = {"FORD_1T4": ["FORD1", "FORD2", "FORD3", "FORD4"], "FORD_5_6": ["FORD5", "FORD6"]}
FLAGS = ["OBS_STATUS", "OBS_STATUS_2", "OBS_STATUS_3", "AUX_OBS_STATUS", "AUX_OBS_STATUS_2", "AUX_OBS_STATUS_3", "CONF_STATUS"]
BASES = {
    "XDC_V": {"unit": "XDC", "price": "V", "label": "Current national currency"},
    "USD_PPP_V": {"unit": "USD_PPP", "price": "V", "label": "Current US dollars, PPP converted"},
    "USD_PPP_Q": {"unit": "USD_PPP", "price": "Q", "label": "Constant-price US dollars, PPP converted (base year recorded per cell)"},
    "USD_V": {"unit": "USD", "price": "V", "label": "Current US dollars, market exchange rate"},
}
# Compact representation for the self-contained offline explorer. Labels and
# provenance are shared dictionaries; CSV/Excel exports expand them explicitly.
COLUMNS = ["iso3", "year", "sector_code", "field_code", "basis", "amount", "source_value",
           "source_unit_multiplier", "currency_code", "base_year", "source_decimals", "availability", *FLAGS,
           "source_file", "value_status", "conversion_divisor", "conversion_source_file", "conversion_method",
           "source_field_label", "source_sector_label", "source_status"]
NS = {"s": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
      "c": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"}


def normalized_value(row: dict) -> tuple[float | None, str]:
    multiplier = int(row["UNIT_MULT"])
    assert multiplier == 6, "Inspect changed OECD GERD scale"
    statuses = {row[k] for k in FLAGS[:3]}
    auxiliary = {row[k] for k in FLAGS[3:6]}
    text = row["OBS_VALUE"].strip()
    value = None if not text else float(text)
    assert value is None or math.isfinite(value) and value >= 0
    if row["CONF_STATUS"] not in {"", "F"}:
        return None, "confidential_or_restricted"
    if "K" in statuses or "N2" in auxiliary:
        return None, "included_elsewhere"
    if value is None or statuses & {"O", "M", "L", "H", "Q"}:
        return None, "missing_source_value"
    return float(Decimal(text) * 10 ** multiplier), "available"


def load_sector_field(raw: Path, manifest: dict, countries: dict, basque_cells: list | None = None) -> dict:
    for name, url in SECTOR_FIELD_SOURCES.items():
        assert manifest[name]["url"] == url
        assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == manifest[name]["sha256"]
    xml = ET.parse(raw / STRUCTURE_FILE).getroot()
    codebooks, parents = {}, {}
    for cl in xml.findall(".//s:Codelist", NS):
        labels = {}
        for code in cl.findall("s:Code", NS):
            label = next(n.text for n in code.findall("c:Name", NS)
                         if n.get("{http://www.w3.org/XML/1998/namespace}lang") == "en")
            labels[code.get("id")] = label
            if cl.get("id") == "CL_FORD":
                parent = code.find("s:Parent/Ref", NS)
                parents[code.get("id")] = "" if parent is None else parent.get("id")
        codebooks[cl.get("id")] = labels
    for group, children in GROUPS.items():
        assert all(parents[c] == group for c in children), "Inspect changed OECD field hierarchy"
    sectors = {code: codebooks["CL_SECT_FUND"][code] for code in SECTORS}
    fields = {code: codebooks["CL_FORD"][code] for code in FIELDS}
    rows, seen, area_names = [], set(), {}
    with (raw / SOURCE_FILE).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for key, expected in {"STRUCTURE_ID": FLOW, "FREQ": "A", "MEASURE": "G", "SECT_FUND": "_Z",
                                  "TYPE_COST": "_Z", "TYPE_RD": "_Z", "SEO": "_Z"}.items():
                assert row[key] == expected, f"Unexpected GERD dimension: {key}"
            code, year = row["REF_AREA"], int(row["TIME_PERIOD"])
            assert code in countries, f"Classify new OECD GERD area: {code}"
            assert HISTORY_START <= year <= HISTORY_END
            sector, field = row["SECT_PERF"], row["FORD"]
            assert sector in sectors and row["Sector of performance"] == sectors[sector]
            assert field in fields and row["Field of R&D"] == fields[field]
            basis = row["UNIT_MEASURE"] + "_" + row["PRICE_BASE"]
            assert basis in BASES
            base_year = row["BASE_PER"]
            assert (base_year.isdigit() if row["PRICE_BASE"] == "Q" else not base_year)
            currency = row["CURRENCY"]
            assert currency in codebooks["CL_UNIT_MEASURE"]
            assert row["Currency"] == codebooks["CL_UNIT_MEASURE"][currency]
            if row["UNIT_MEASURE"] == "USD_PPP":
                assert currency == "USD"
            for flag in FLAGS:
                book = "CL_CONF_STATUS" if flag == "CONF_STATUS" else "CL_AUX_OBS_STATUS" if flag.startswith("AUX") else "CL_OBS_STATUS"
                assert not row[flag] or row[flag] in codebooks[book]
            # One cell per requested SDMX series/year. Currency is an attribute,
            # not permission to silently accept a duplicate series.
            key = (code, year, sector, field, basis)
            assert key not in seen, f"Duplicate GERD cell: {key}"
            seen.add(key)
            amount, availability = normalized_value(row)
            decimals = int(row["DECIMALS"])
            assert 0 <= decimals <= 15
            area_names[code] = row["Reference area"]
            rows.append([code, year, sector, field, basis, amount, row["OBS_VALUE"], int(row["UNIT_MULT"]),
                         currency, base_year, decimals, availability, *[row[k] for k in FLAGS],
                         SOURCE_FILE, "reported", "", "", "source value * 10^UNIT_MULT", row["Field of R&D"], row["Sector of performance"], ""])
    assert rows, "Empty OECD sector/field response"
    rows.sort(key=lambda r: (r[0], r[1], SECTORS.index(r[2]), FIELDS.index(r[3]), r[4]))
    classifications = {}
    if basque_cells:
        sectors["BES_PNP"] = "Companies + private non-profit institutions (Eustat)"
        fields["EUSTAT_SOC"] = "Social sciences (Eustat grouping; no humanities split)"
        parents["EUSTAT_SOC"] = "_T"
        area_names[BASQUE_CODE] = "Basque Country"
        classifications[BASQUE_CODE] = {"sectors": list(SECTOR_FILES), "fields": list(FIELD_MAP.values())}
        for cell in basque_cells:
            key = tuple(cell[k] for k in ["iso3", "year", "sector_code", "field_code", "basis"])
            assert key not in seen
            seen.add(key)
            rows.append([cell.get(k, "") for k in COLUMNS])
    return {"columns": COLUMNS, "rows": rows, "sectors": sectors, "fields": fields,
            "fieldParents": {code: parents[code] for code in fields}, "fieldGroups": GROUPS,
            "defaultSectors": SECTORS, "defaultFields": FIELDS, "areaClassifications": classifications,
            "areaNotes": {BASQUE_CODE: REGIONAL_NOTE + " Eustat combines companies with PNPI. Its five-field classification is retained; Social sciences is not forced into OECD FORD5 or FORD_5_6. No separate humanities/NEC values are inferred."},
            "bases": BASES, "areaNames": area_names, "sourceFile": SOURCE_FILE, "source": manifest[SOURCE_FILE],
            "sources": {name: manifest[name] for name in [SOURCE_FILE, *BASQUE_SOURCES]},
            "flow": FLOW, "flagLabels": {key: codebooks[key] for key in ["CL_OBS_STATUS", "CL_AUX_OBS_STATUS", "CL_CONF_STATUS"]},
            "currencies": {code: codebooks["CL_UNIT_MEASURE"][code] for code in {r[8] for r in rows}}}


def records(dataset: dict):
    for values in dataset["rows"]:
        yield dict(zip(dataset["columns"], values))


def annual_records(dataset: dict):
    for row in records(dataset):
        sector, field = row["sector_code"], row["field_code"]
        source = dataset["sources"][row["source_file"]]
        conversion = dataset["sources"].get(row["conversion_source_file"], {})
        yield {"iso3": row["iso3"], "economy": dataset["areaNames"][row["iso3"]], "year": row["year"],
               "sector_code": sector, "sector": dataset["sectors"][sector],
               "field_code": field, "field": dataset["fields"][field],
               "sector_level": "total" if sector == "_T" else "combined_group" if sector == "BES_PNP" else "component",
               "field_level": "total" if field == "_T" else "combined_group" if field in GROUPS else "component",
               "field_parent": dataset["fieldParents"][field],
               "basis": row["basis"], "unit_code": BASES[row["basis"]]["unit"],
               "price_code": BASES[row["basis"]]["price"], "unit_and_price": BASES[row["basis"]]["label"],
               "currency_code": row["currency_code"], "currency": dataset["currencies"][row["currency_code"]],
               "base_year": row["base_year"], "amount": row["amount"], "amount_scale": "units",
               "availability": row["availability"], "source_value": row["source_value"],
               "source_unit_multiplier": row["source_unit_multiplier"], "source_decimals": row["source_decimals"],
               **{flag: row[flag] for flag in FLAGS}, "source_file": row["source_file"],
               "source_url": source["url"], "retrieved_utc": source["retrieved_utc"],
               **{key: row[key] for key in COLUMNS[COLUMNS.index("value_status"): ]},
               "source_currency": "EUR" if row["iso3"] == BASQUE_CODE else row["currency_code"],
               "conversion_source_url": conversion.get("url", ""), "conversion_retrieved_utc": conversion.get("retrieved_utc", "")}


def coverage_records(dataset: dict, countries: list):
    counts = defaultdict(Counter)
    details = defaultdict(set)
    for row in records(dataset):
        key = (row["iso3"], row["year"], row["basis"])
        counts[key]["source_cells"] += 1
        counts[key][row["availability"]] += 1
        if row["amount"] is not None:
            if row["sector_code"] != "_T" and row["field_code"] in [*sum(GROUPS.values(), []), "NEC", "EUSTAT_SOC"]:
                counts[key]["joint_component_cells_available"] += 1
            if row["sector_code"] == row["field_code"] == "_T":
                counts[key]["reported_grand_total_available"] += 1
        details[key].add((row["currency_code"], row["base_year"]))
    for country in countries:
        for year in range(HISTORY_START, HISTORY_END + 1):
            for basis in BASES:
                key = (country["iso"], year, basis)
                count = counts[key]
                yield {"iso3": country["iso"], "economy": country["name"], "year": year, "basis": basis,
                       "currency_base_year_pairs": "|".join(f"{c}:{b}" for c, b in sorted(details[key])),
                       **{k: count[k] for k in ["source_cells", "available", "confidential_or_restricted", "included_elsewhere",
                                                 "missing_source_value", "missing_conversion_factor", "joint_component_cells_available", "reported_grand_total_available"]},
                        "not_returned_cells": len(dataset["areaClassifications"].get(country["iso"], {}).get("sectors", SECTORS)) * len(dataset["areaClassifications"].get(country["iso"], {}).get("fields", FIELDS)) - count["source_cells"]}


def reconcile(total: dict | None, components: list[dict | None]) -> dict:
    """An incomplete partition is untestable; absence never stands for zero."""
    all_rows = [total, *components]
    result = {"reported_total": None if total is None else total["amount"], "component_sum": None,
              "difference": None, "rounding_tolerance": None, "result": "not_testable_missing_cells"}
    if any(row is None or row["amount"] is None for row in all_rows):
        return result
    if len({(r["basis"], r["currency_code"], r["base_year"]) for r in all_rows}) != 1:
        return {**result, "result": "not_testable_incompatible_basis"}
    def exact(row):
        if row.get("source_value"):
            return Decimal(row["source_value"]) * 10 ** row["source_unit_multiplier"] / Decimal(row.get("conversion_divisor") or "1")
        return Decimal(str(row["amount"]))

    value = sum(exact(r) for r in components)
    tolerance = sum(Decimal("0.5") * Decimal(10) ** (r["source_unit_multiplier"] - r["source_decimals"]) / Decimal(r.get("conversion_divisor") or "1") for r in all_rows)
    difference = value - exact(total)
    return {"reported_total": total["amount"], "component_sum": float(value), "difference": float(difference),
            "rounding_tolerance": float(tolerance),
            "result": "within_source_rounding" if abs(difference) <= tolerance else "discrepancy_retained"}


def reconciliation_records(dataset: dict):
    blocks = defaultdict(dict)
    for row in records(dataset):
        blocks[(row["iso3"], row["year"], row["basis"])][(row["sector_code"], row["field_code"])] = row
    for (code, year, basis), cells in sorted(blocks.items()):
        # Only disjoint, exhaustive top-level categories. Combined fields are
        # never added to their children; missing NEC is NOT assumed to be zero.
        partitions = [("performance_sectors", field, ("_T", field), [(s, field) for s in SECTORS[1:]]) for field in FIELDS]
        partitions += [("top_level_fields", sector, (sector, "_T"),
                         [(sector, f) for f in ["FORD_1T4", "FORD_5_6", "NEC"]]) for sector in SECTORS]
        if code == BASQUE_CODE:
            sectors, fields = list(SECTOR_FILES), list(FIELD_MAP.values())
            partitions = [("performance_sectors", f, ("_T", f), [(s, f) for s in sectors[1:]]) for f in fields]
            partitions += [("eustat_five_fields", s, (s, "_T"), [(s, f) for f in fields[1:]]) for s in sectors]
        for axis, category, target, components in partitions:
            if not any(key in cells for key in [target, *components]):
                continue
            chosen = [cells.get(key) for key in [target, *components]]
            flags = sorted({f"{flag}={r[flag]}" for r in chosen if r for flag in FLAGS if r[flag]})
            yield {"iso3": code, "year": year, "basis": basis, "check": axis, "category": category,
                   "components": "|".join(s if axis == "performance_sectors" else f for s, f in components),
                   "currency_base_year_pairs": "|".join(sorted({r["currency_code"] + ":" + r["base_year"] for r in chosen if r})),
                   **reconcile(chosen[0], chosen[1:]), "flags": "|".join(flags)}


def definition_records(dataset: dict):
    definitions = {
        "measure": "Gross domestic expenditure on R&D (GERD), annual; performers, not funders.",
        "source": dataset["flow"], "source_url": dataset["source"]["url"],
        "structure_url": SECTOR_FIELD_SOURCES[STRUCTURE_FILE],
        "fixed_dimensions": "FREQ=A; MEASURE=G; SECT_FUND=TYPE_COST=TYPE_RD=SEO=_Z (not applicable).",
        "amount": "Reported rows: source_value * 10^source_unit_multiplier, in units (OECD millions; Eustat thousand EUR). Derived Eustat rows additionally divide by conversion_divisor, retaining the original EUR value. Missing values and source symbols are retained.",
        "price_basis": "XDC_V: nominal national currency; USD_V: current market-exchange-rate USD (Basque only); USD_PPP_V: current PPP dollars; USD_PPP_Q: constant PPP dollars, BASE_PER recorded per row (OECD only). PPP dollars are not market-exchange-rate US dollars.",
        "currency": "OECD CURRENCY attribute, preserved exactly; historical national-currency series may be redenominated. Never infer the currency from the year.",
        "missingness": "Missing, confidential/restricted and included-elsewhere cells remain null, not zero. Not returned is distinct from an explicit blank source row. Only genuinely observed zeros are numeric zero.",
        "overlap": "Sector/field totals overlap components. FORD_1T4 contains FORD1–4, including medical and agricultural sciences; FORD_5_6 contains FORD5–6. Never sum groups with their children or total with components.",
        "reconciliation": "Compare reported sector totals with BES+GOV+HES+PNP, and field totals with FORD_1T4+FORD_5_6+NEC, only if all values share a currency/price/base year. Missing NEC is not zero. Tolerance sums half of each cell's last displayed source decimal; discrepancies are retained, not corrected.",
        "independence": "Each provider's three unit/price representations describe the same underlying cells, not independent observations. Coverage is uneven and a total does not imply detailed field coverage. Basque Country overlaps Spain.",
        "nominal_database": "This OECD RDS dataflow is kept separately from MSTI totals and derived WDI/UIS dollar amounts; their vintages and definitions may differ.",
        "coverage": "Full existing economy catalog x requested years x three bases. not_returned_cells counts absence from the supported 5-sector x 10-field grid; it does not imply reporting is expected or categories are additive.",
        "basque_region": REGIONAL_NOTE,
        "basque_classification": "Eustat: total, companies+PNPI, government, higher education; fields natural, engineering, medical, agricultural and the original Social sciences grouping. BES_PNP is not BES alone. EUSTAT_SOC is not assumed identical to FORD5 or FORD_5_6. Source-specific grids and exhaustive partitions are used; no missing NEC or separate PNP is imputed.",
        "basque_conversion": "Reported thousand EUR × 1000. USD_V divides EUR by same-year WDI PA.NUS.FCRF for Spain; USD_PPP_V divides EUR by same-year WDI PA.NUS.PPP for Spain (GDP PPP, national proxy). These derived rows retain original EUR values, scale, divisor and conversion source. No constant-price series is derived. Rounding tolerances are converted by the same divisor, conditional on that factor. Eustat source_status '.' accompanies null, not zero; no confidentiality meaning is inferred.",
    }
    definitions["coverage"] = "Full economy catalog x 2000–2025 x four bases. OECD grid: 5 sectors x 10 fields; Eustat grid: 4 sectors x 6 fields. USD_V currently available for Basque Country only; constant PPP currently OECD only. Not returned does not imply zero or expected reporting."
    for key, description in definitions.items():
        yield {"kind": "definition", "code": key, "label": description, "parent": ""}
    for kind, labels in [("sector", dataset["sectors"]), ("field", dataset["fields"]), ("currency", dataset["currencies"]), *dataset["flagLabels"].items()]:
        for code, label in labels.items():
            yield {"kind": kind, "code": code, "label": label, "parent": dataset["fieldParents"].get(code, "") if kind == "field" else ""}


def sector_field_summary(dataset: dict) -> dict:
    rows = list(records(dataset))
    years = [r["year"] for r in rows if r["amount"] is not None]
    return {"source_rows": len(rows), "economies": len(dataset["areaNames"]),
            "first_available_year": min(years), "last_available_year": max(years),
            "available_values": sum(r["amount"] is not None for r in rows),
            "availability": dict(Counter(r["availability"] for r in rows)),
            "rows_by_basis": dict(Counter(r["basis"] for r in rows)),
            "constant_price_base_years": sorted({r["base_year"] for r in rows if r["base_year"]}),
            "reconciliation": dict(Counter(r["result"] for r in reconciliation_records(dataset))),
            "source_retrieved_utc": dataset["source"]["retrieved_utc"]}


def sector_field_tables(data: dict):
    dataset = data["sectorField"]
    return [("rd_sector_field_annual.csv", "GERD sector field", annual_records(dataset)),
            ("rd_sector_field_coverage.csv", "GERD SF coverage", coverage_records(dataset, data["countries"])),
            ("rd_sector_field_reconciliation.csv", "GERD SF reconciliation", reconciliation_records(dataset)),
            ("rd_sector_field_definitions.csv", "GERD SF definitions", definition_records(dataset))]


def write_sector_field_csvs(data: dict, destination: Path) -> None:
    for filename, _, rows in sector_field_tables(data):
        first = next(rows)
        with (destination / filename).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(first))
            writer.writeheader()
            writer.writerow(first)
            writer.writerows(rows)
