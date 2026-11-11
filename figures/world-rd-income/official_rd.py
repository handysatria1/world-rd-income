"""Direct ONS observations, with publication vintages and matched price proxies."""

from decimal import Decimal

from openpyxl import load_workbook

from sector_field_rd import FLAGS

UK_TYPES = ("ONS reports basic/applied/experimental CURRENT expenditure and separate capital. "
            "Each year uses Tables 8 and 10 from that year's publication, with a matched total; "
            "2022/2023 are older unrevised publication vintages, not the revised totals in the 2024 release. "
            "The redesigned survey starts in 2022; pre-2022 breakdowns are not directly comparable. "
            "OECD estimated types allocate the total differently and are retained separately, not combined with ONS capital.")
UK_PROXY = ("ONS current GBP divided by the same-year OECD UK funding total current-GBP / PPP-total ratio. "
            "Implied national conversion, conditional on rounded OECD inputs; not the ONS R&D deflator. "
            "Constant PPP uses OECD base year 2020; current PPP uses current-year prices.")


def load_official(raw, oecd_rows):
    totals = {(r["year"], r["basis"]): r for r in oecd_rows if r["iso3"] == "GBR" and r["breakdown"] == "funding"
              and r["sector_code"] == r["category_code"] == "_T"}
    conversions, divisors = [], {}
    for year in range(2022, 2025):
        for basis in ["USD_PPP_V", "USD_PPP_Q"]:
            local, dollars = totals.get((year, "XDC_V")), totals.get((year, basis))
            valid = local and dollars and local["amount"] is not None and dollars["amount"] is not None and dollars["amount"] > 0
            if valid:
                assert local["currency_code"] == "GBP" and (basis != "USD_PPP_Q" or dollars["base_year"] == "2020")
                divisors[(year, basis)] = Decimal(local["source_value"]) / Decimal(dollars["source_value"])
            conversions.append({"iso3": "GBR", "year": year, "basis": basis,
                "gbp_per_ppp_dollar": str(divisors.get((year, basis), "")),
                "oecd_current_gbp_millions": local["source_value"] if local else "",
                "oecd_ppp_millions": dollars["source_value"] if dollars else "",
                "base_year": "2020" if basis == "USD_PPP_Q" else "",
                "input_flags": "|".join(f"{r['basis']}:{k}={r[k]}" for r in [local, dollars] if r for k in FLAGS if r[k]),
                "source_file": "gerd_funding_history.csv", "method": UK_PROXY})

    def record(year, kind, sector, category, value, source, locator, label, note, basis="XDC_V"):
        assert isinstance(value, (int, float)) and value >= 0, (source, locator, value)
        divisor = Decimal(1) if basis == "XDC_V" else divisors.get((year, basis))
        return {"iso3": "GBR", "year": year, "breakdown": kind, "sector_code": sector, "category_code": category,
            "basis": basis, "amount": None if divisor is None else float(Decimal(str(value)) * 10**6 / divisor),
            "source_value": str(value), "source_unit_multiplier": 6, "source_decimals": 0,
            "currency_code": "GBP" if basis == "XDC_V" else "USD", "source_currency_code": "GBP",
            "base_year": "2020" if basis == "USD_PPP_Q" else "", "availability": "available" if divisor else "missing_conversion_factor",
            **dict.fromkeys(FLAGS, ""), "source_file": source, "value_status": "reported" if basis == "XDC_V" else "derived",
            "conversion_divisor": "" if basis == "XDC_V" or divisor is None else str(divisor),
            "conversion_source_file": "" if basis == "XDC_V" else "gerd_funding_history.csv",
            "conversion_method": "source million GBP * 1000000" if basis == "XDC_V" else UK_PROXY,
            "source_category_label": label, "source_sector_label": sector, "source_status": "",
            "source_locator": locator, "reference_period": str(year), "methodology_note": note}

    research = []
    for year in range(2022, 2025):
        filename = f"ons_berd_{year}.xlsx"
        w = load_workbook(raw / filename, read_only=True, data_only=True)
        col = {2022: "B", 2023: "C", 2024: "D"}[year]
        trow, caprow = (9, 11) if year == 2022 else (10, 12)
        assert str(w["8"][col + "7"].value) == str(year) and "Current expenditure" in w["10"]["A1"].value
        assert w["10"][f"A{trow}"].value == "Total" and w["8"][f"A{caprow}"].value == "Capital total"
        assert w["10"][f"B{trow}"].value == w["8"][col + ("14" if year == 2022 else "9")].value
        for category, sheet, address, label in [
            ("_T", "8", col + "8", "Total"), ("CAP_EX_NEC", "8", col + str(caprow), "Capital total"),
            ("BR", "10", f"C{trow}", "Basic"), ("AR", "10", f"D{trow}", "Applied"),
            ("ED", "10", f"E{trow}", "Experimental development"),
        ]:
            for basis in ["XDC_V", "USD_PPP_V", "USD_PPP_Q"]:
                research.append(record(year, "research", "BES", category, w[sheet][address].value, filename,
                                       f"Table {sheet}, cell {address}", label, UK_TYPES, basis))
        w.close()

    # Keep direct ONS funding/performance observations alongside the more precise
    # OECD cube. They corroborate it; they must not replace a subset of its cells.
    funding = []
    filename = "ons_gerd_2024.xlsx"
    w = load_workbook(raw / filename, read_only=True, data_only=True)
    note = ("ONS 2024 GERD release. Current GBP; higher-education 2024 estimates pending TRAC. "
            "Government includes UKRI and government funding includes HEFBs. Independently rounded cells.")
    for col, sector in [("B", "GOV"), ("C", "HES"), ("D", "BES"), ("E", "PNP"), ("F", "_T")]:
        for row, cat in [(9, "GOV"), (10, "HES"), (11, "BES"), (12, "PNP"), (13, "ROW"), (14, "_T")]:
            address = col + str(row)
            funding.append(record(2024, "funding", sector, cat, w["1"][address].value, filename,
                                  f"Table 1, cell {address}", w["1"][f"A{row}"].value, note))
    for col, year in [("B", 2022), ("C", 2023)]:
        for sheet, sector, cat, row in [
            *[("2", s, "_T", r) for s, r in [("GOV", 11), ("HES", 14), ("BES", 15), ("PNP", 16)]],
            *[("3", "_T", c, r) for c, r in [("_T", 10), ("GOV", 11), ("HES", 14), ("BES", 15), ("PNP", 16), ("ROW", 17)]],
        ]:
            address = col + str(row)
            funding.append(record(year, "funding", sector, cat, w[sheet][address].value, filename,
                                  f"Table {sheet}a, cell {address}", w[sheet][f"A{row}"].value, note))
    intensity = {}
    for col, year in [("B", 2022), ("C", 2023), ("D", 2024)]:
        assert str(w["5"][col + "7"].value) == str(year)
        intensity[str(year)] = {"v": w["5"][col + "9"].value, "flags": "ONS reported; rounded to 0.01 percentage point",
            "note": "2024 GERD release, Table 5; GDP vintage 31 March 2026. " + note,
            "source_file": filename, "source_locator": f"Table 5, cell {col}9"}
    w.close()
    w = load_workbook(raw / "ons_gerd_2023_official.xlsx", read_only=True, data_only=True)
    for col, year in [("B", 2018), ("C", 2019), ("D", 2020), ("E", 2021)]:
        assert str(w["6"][col + "8"].value) == str(year)
        intensity[str(year)] = {"v": w["6"][col + "10"].value, "flags": "ONS indicative; earlier GDP/publication vintage",
            "note": "2023 GERD release Table 6 and Note 4: indicative; new R&D methodology not yet incorporated in that release's GDP. Methodology/vintage break at 2022.",
            "source_file": "ons_gerd_2023_official.xlsx", "source_locator": f"Table 6, cell {col}10"}
    w.close()
    return research, funding, intensity, conversions
