"""Reproducible example stacked charts and their exact common-year calculations."""

import csv
import json
from statistics import mean

import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Patch

from breakdown_rd import PARTITIONS, records

EXAMPLES = ["USA", "CHN", "KOR", "GBR", "SGP", "ES-PV"]
COLORS = {"GOV": "#4779b5", "BES": "#e08c32", "HES": "#64a46c", "PNP": "#b874a3", "ROW": "#8a77b0",
          "BES_PNP": "#ca9847", "BR": "#4779b5", "AR": "#e08c32", "ED": "#64a46c", "CAP_EX_NEC": "#b874a3"}
LABELS = {"GOV": "Government", "BES": "Business", "HES": "Higher education", "PNP": "Private non-profit",
          "ROW": "Rest of the world", "BES_PNP": "Business + private non-profit", "BR": "Basic research",
          "AR": "Applied research", "ED": "Experimental development", "CAP_EX_NEC": "Capital, not elsewhere recorded"}
NAMES = {"USA": "United States", "CHN": "China", "KOR": "Korea", "GBR": "United Kingdom", "SGP": "Singapore", "ES-PV": "Basque Country"}


def comparison(data, chart, sector="GOV", basis="USD_PPP_Q", start=2020, end=2024,
               countries=None, strict=False, share_mode="ratio"):
    """Independent Python equivalent of breakdown_core.js, compared by tests."""
    countries = EXAMPLES if countries is None else countries
    kind = "research" if chart.startswith("research") else "funding"
    if chart.endswith("amount"):
        share_mode = "ratio"
    performers = chart.startswith("performer")
    sector = sector if kind == "research" else "_T"
    requested = list(range(start, end + 1))
    cells = {(r["iso3"], r["year"], r["sector_code"], r["category_code"]): r for r in records(data["breakdowns"])
             if r["iso3"] in countries and r["basis"] == basis and r["breakdown"] == kind and r["year"] in requested}
    result = []
    for iso in countries:
        actual_sector = "BES_PNP" if iso == "ES-PV" and sector == "BES" and kind == "research" else sector
        categories = (["GOV", "BES_PNP", "HES"] if iso == "ES-PV" else ["GOV", "BES", "HES", "PNP"]) if performers else PARTITIONS[kind]
        def get(year, category):
            return cells.get((iso, year, category if performers else actual_sector, "_T" if performers else category))
        def available(year, category):
            return get(year, category) is not None and get(year, category)["amount"] is not None
        present = [c for c in categories if any(available(y, c) for y in requested)]
        years = [y for y in requested if available(y, "_T") and all(available(y, c) for c in present)] if present else []
        bases = {(get(y, c)["currency_code"], get(y, c)["base_year"]) for y in years for c in ["_T", *present]}
        if len(bases) > 1 or strict and len(years) != len(requested):
            years = []
        total = mean(get(y, "_T")["amount"] for y in years) if years else None
        country = next(c for c in data["countries"] if c["iso"] == iso)
        rd = dict(country["rd"])
        providers = list(country.get("rdProviders", [s for s in ["oecd", "wdi", "eustat"] if s in rd]))
        if iso in data["breakdowns"].get("officialIntensity", {}):
            rd["ons"] = data["breakdowns"]["officialIntensity"][iso]
            providers.append("ons")
        source = max(providers, key=lambda s: sum(str(y) in rd[s] for y in years))
        intensity = mean(rd[source][str(y)]["v"] for y in years) if years and all(str(y) in rd[source] for y in years) else None
        parts = []
        for c in categories:
            amount = mean(get(y, c)["amount"] for y in years) if years and all(available(y, c) for y in years) else None
            share = None
            if amount is not None and all(get(y, "_T")["amount"] > 0 for y in years):
                share = mean(get(y, c)["amount"] / get(y, "_T")["amount"] * 100 for y in years) if share_mode == "annual" else amount / total * 100
            parts.append({"code": c, "amount": amount, "share": share})
        result.append({"iso": iso, "chart": chart, "sector": actual_sector, "basis": basis, "start": start, "end": end,
                       "years": years, "parts": parts, "total": total, "intensity": intensity, "intensity_source": source,
                       "residual": None if total is None else total - sum(p["amount"] for p in parts if p["amount"] is not None),
                       "residual_share": None if total is None or any(get(y, "_T")["amount"] <= 0 for y in years) else 100 - sum(p["share"] for p in parts if p["share"] is not None)})
    return result


def panel(ax, rows, title, percentage=False, overlay=False):
    codes = list(dict.fromkeys(p["code"] for r in rows for p in r["parts"]))
    ymax = 100 if percentage else 0
    ax._rd_segments = []
    for i, r in enumerate(rows):
        bottom = 0
        for p in r["parts"]:
            v = p["share"] if percentage else None if p["amount"] is None else p["amount"] / 1e9
            if v is None:
                continue
            rect = ax.bar(i, v, bottom=bottom, width=.62, color=COLORS[p["code"]], zorder=3)[0]
            ax._rd_segments.append((rect, p["share"], p["code"]))
            bottom += v
        residual = r["residual_share"] if percentage else None if r["residual"] is None else r["residual"] / 1e9
        if residual is not None and residual > 0:
            rect = ax.bar(i, residual, bottom=bottom, width=.62, color="#d1d8df", zorder=3)[0]
            ax._rd_segments.append((rect, r["residual_share"], "residual"))
            bottom += residual
        ymax = max(ymax, bottom)
        if not r["years"]:
            ax.text(i, 3 if percentage else .5, "No data", ha="center", color="#536574", fontsize=10)
        elif not percentage:
            ax.annotate(f"{r['total']/1e9:.2f}", (i, bottom), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=9)
    ax.set_ylim(0, max(1, ymax) * (1.04 if percentage else 1.18))
    ax.set_xticks(range(len(rows)), [NAMES[r["iso"]].replace(" ", "\n") + "\n" +
                 (f"{min(r['years'])}–{max(r['years'])}\n({len(r['years'])}/5 years)" if r["years"] else "no observations") for r in rows])
    ax.tick_params(axis="x", colors="#146b88", labelsize=9, length=0)
    ax.set_ylabel("Share of reported expenditure (%)" if percentage else "Mean annual GERD (constant 2020 US$ PPP billions)")
    ax.set_title(title, loc="left", fontsize=13, pad=18)
    ax.grid(axis="y", color="#e1e7ec", zorder=0)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    if overlay:
        twin = ax.twinx()
        values = [(i, r["intensity"]) for i, r in enumerate(rows) if r["intensity"] is not None]
        twin.scatter([i for i, v in values], [v for i, v in values], color="#146b88", edgecolor="white", s=58, zorder=5)
        twin.set_ylim(0, max([1, *[v for i, v in values]]) * 1.25)
        twin.set_ylabel("Mean R&D intensity (% of GDP) · teal points", color="#146b88")
        twin.tick_params(axis="y", colors="#146b88")
        twin.spines["top"].set_visible(False)
        ax._rd_intensity = (twin, dict(values))
    return [Patch(color=COLORS[c], label=LABELS[c]) for c in codes] + [Patch(color="#d1d8df", label="Unallocated difference (derived)")]


def label_percentages(fig):
    """Label actual rendered segment sizes; avoid tiny segments and intensity points."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    font = FontProperties(size=9)
    for ax in fig.axes:
        for rect, share, code in getattr(ax, "_rd_segments", []):
            if share is None or rect.get_height() <= 0:
                continue
            label = f"{share:.1f}%"
            w, h, _ = renderer.get_text_width_height_descent(label, font, ismath=False)
            box = rect.get_window_extent(renderer)
            if box.width < w + 8 or box.height < h + 8:
                continue
            x, y = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
            if hasattr(ax, "_rd_intensity"):
                twin, values = ax._rd_intensity
                i = round(rect.get_x() + rect.get_width() / 2)
                if i in values:
                    point_y = twin.transData.transform((i, values[i]))[1]
                    clearance = h / 2 + 9 * fig.dpi / 72
                    if abs(y - point_y) < clearance:
                        y = next((v for v in [box.y0 + h / 2 + 4, box.y1 - h / 2 - 4]
                                  if abs(v - point_y) >= clearance), None)
                        if y is None:
                            continue
            color = "#172d3d" if code in ["BES", "HES", "BES_PNP", "AR", "ED", "residual"] else "white"
            ax.text(*ax.transData.inverted().transform((x, y)), label, ha="center", va="center", color=color, fontsize=9, zorder=4)


def build_breakdown_figures(data, out, destination):
    selections = {"funding_amount": comparison(data, "funding_amount"), "funding_share": comparison(data, "funding_share"),
                  "performer_amount": comparison(data, "performer_amount"),
                  "performer_share": comparison(data, "performer_share"),
                  "research_gov": comparison(data, "research_share", "GOV"), "research_business": comparison(data, "research_share", "BES"),
                  "research_gov_amount": comparison(data, "research_amount", "GOV"), "research_business_amount": comparison(data, "research_amount", "BES")}
    (destination / "rd_breakdown_examples.json").write_text(json.dumps(selections, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    csv_rows = [{"selection": name, **{k: v for k, v in r.items() if k != "parts"}, "years": ";".join(map(str, r["years"])),
                 "category": p["code"], "mean_annual_amount": p["amount"], "share_percent": p["share"]}
                for name, selected in selections.items() for r in selected for p in r["parts"]]
    with (destination / "rd_breakdown_examples.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0])); writer.writeheader(); writer.writerows(csv_rows)
    notes = ["Requested window: 2020–2024. Each bar uses common available years; actual coverage is printed below it. Missing categories are not zero.",
             "Segment labels: % of reported total where space permits; all shares and inputs are in accompanying CSVs. Known categories are not rescaled; grey is an accounting gap.",
             "Composition weights use constant-2020 PPP amounts. Intensity is omitted if any bar year is unavailable; intensity and expenditure sources/vintages may differ.",
             "OECD RDS / MSTI; Eustat; ONS. PPP conversion proxies: Spain for Basque Country, UK for ONS research; see conversion CSVs."]
    for name in ["rd_funding_intensity_2020_2024", "rd_performer_intensity_2020_2024", "rd_performer_composition_2020_2024",
                 "rd_funding_performer_composition_2020_2024", "rd_research_type_composition_2020_2024"]:
        if "intensity" in name:
            fig, ax = plt.subplots(figsize=(12, 7.6))
            performer = "performer" in name
            handles = panel(ax, selections["performer_amount" if performer else "funding_amount"],
                            "Who performs R&D? Expenditure and intensity" if performer else "Who funds R&D? Expenditure and intensity", overlay=True)
            extra = ("China / Singapore: PNP performance not returned. Basque business + private non-profit performers stay combined." if performer else
                     "China: HES and PNP funding not reported separately. Singapore: PNP funding not returned; 2024 unavailable. Intensity uses exactly each bar's years.")
            extra += "\nUK intensity: ONS 2020–2024, with indicative earlier values and a GDP/publication-vintage break at 2022."
        elif name == "rd_performer_composition_2020_2024":
            fig, ax = plt.subplots(figsize=(12, 7.6))
            handles = panel(ax, selections["performer_share"], "Who performs R&D? Performing-sector percentages", percentage=True)
            extra = "Performing sectors carry out the R&D. China / Singapore: PNP performance not returned. Basque business + private non-profit performers stay combined."
        elif "funding_performer" in name:
            fig, axes = plt.subplots(1, 2, figsize=(16, 8))
            handles = panel(axes[0], selections["funding_share"], "Funding sources", percentage=True)
            more = panel(axes[1], selections["performer_share"], "Performing sectors", percentage=True)
            handles += [h for h in more if h.get_label() not in {x.get_label() for x in handles}]
            extra = "China: HES/PNP funding and PNP performance not returned. Singapore: PNP not returned. Basque business + PNP performers stay combined."
        else:
            fig, axes = plt.subplots(1, 2, figsize=(16, 8))
            handles = panel(axes[0], selections["research_gov"], "Government-performed R&D", percentage=True)
            panel(axes[1], selections["research_business"], "Business-performed R&D", percentage=True)
            extra = ("Basque: capital only; grey = unclassified current costs; business + PNP combined. UK GOV types: 2020–2023; 2024 unavailable.\n"
                     "UK business: ONS 2022–2024 publication vintages, current research + capital; earlier totals unrevised. GOV means performer, not funder.")
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, .99), ncol=3 if "intensity" in name else 4, frameon=False, fontsize=9)
        fig.text(.06, .025, "\n".join([*notes, extra]), fontsize=8, color="#536574", linespacing=1.6)
        fig.subplots_adjust(top=.83, bottom=.28, left=.07, right=.92, wspace=.25)
        label_percentages(fig)
        for extension in ["png", "svg", "pdf"]:
            fig.savefig(out / f"{name}.{extension}", dpi=240, facecolor="white")
        plt.close(fig)
