"""Rebuild worldwide R&D / 2025 income figures from archived source data.

R&D is GERD as a percentage of GDP. Select one entire source series per
economy: most nonmissing years in 2020–2024, preferring OECD on ties.
Main figures use reported-year means; companion figures require all five years.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from adjustText import adjust_text
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.transforms import Bbox
from scipy.stats import linregress, spearmanr

from download_data import HISTORY_SOURCES, INDICATORS, NOMINAL_SOURCES, SECTOR_FIELD_SOURCES, SOURCES, UIS_ARCHIVE
from historical_explorer import build_explorer, load_history
from nominal_rd import nominal_summary, nominal_tables
from sector_field_rd import sector_field_tables
from breakdown_rd import breakdown_tables
from breakdown_figures import build_breakdown_figures
from basque_rd import CODE as BASQUE_CODE, PROVIDER as EUSTAT_SOURCE, basque_tables

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
OUT = ROOT / "output"
YEARS = list(range(2020, 2025))
GDP_YEAR = 2025
OECD_SOURCE = "OECD MSTI"
UIS_SOURCE = "UNESCO UIS via World Bank WDI"
OECD_MEMBERS = set(
    "AUS AUT BEL CAN CHL COL CRI CZE DNK EST FIN FRA DEU GRC HUN ISL IRL ISR "
    "ITA JPN KOR LVA LTU LUX MEX NLD NZL NOR POL PRT SVK SVN ESP SWE CHE TUR GBR USA".split()
)
DISPLAY = {
    "KOR": "Korea", "RUS": "Russia", "GBR": "United Kingdom", "USA": "United States",
    "HKG": "Hong Kong", "MAC": "Macao", "TUR": "Türkiye", "TWN": "Chinese Taipei",
}
LABELS = set(
    "CHN KOR GBR USA SGP IND IDN BRA RUS MEX ZAF ISR CHE LUX IRL JPN DEU AUS "
    "FRA SWE MAC QAT NOR HKG SAU ES-PV".split()
)
TEAL, INK, MUTED = "#146b88", "#172d3d", "#536574"
COUNTRY_COLOR = TEAL
SPECS = [
    {"id": "world_2025_nominal", "kind": "nominal", "strict": False},
    {"id": "world_2025_ppp", "kind": "ppp", "strict": False},
    {"id": "world_2025_nominal_complete_five_years", "kind": "nominal", "strict": True},
    {"id": "world_2025_ppp_complete_five_years", "kind": "ppp", "strict": True},
]


def verify_inputs() -> dict:
    manifest = json.loads((RAW / "manifest.json").read_text("utf-8"))
    for name, url in SOURCES.items():
        assert manifest[name]["url"] == url
        assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == manifest[name]["sha256"]
    return manifest


def wb_payload(name: str) -> list:
    payload = json.loads((RAW / name).read_text("utf-8"))
    assert len(payload) == 2 and payload[0]["pages"] == 1
    assert len(payload[1]) == payload[0]["total"]
    return payload[1]


def load_wb_series(key: str) -> pd.DataFrame:
    indicator = INDICATORS[key][0]
    catalog = {r["iso2Code"]: r for r in wb_payload("wb_countries.json")}
    rows = []
    for row in wb_payload(f"wb_{key}.json"):
        assert row["indicator"]["id"] == indicator
        code = row["countryiso3code"]
        if not code:
            # WDI omits this field for some income-group aggregates. Resolve
            # their identifiers from the catalog; keep the original blank too.
            entry = catalog[row["country"]["id"]]
            assert entry["region"]["id"] == "NA"
            code = entry["id"]
        rows.append({
            "iso3": code, "country": row["country"]["value"],
            "api_countryiso3code": row["countryiso3code"], "wb_country_id": row["country"]["id"],
            "year": int(row["date"]), "value": row["value"],
            "indicator": indicator, "obs_status": row["obs_status"],
            "footnote": row.get("footnote", ""), "unit_field": row["unit"],
        })
    frame = pd.DataFrame(rows)
    frame["value"] = pd.to_numeric(frame["value"], errors="raise")
    assert not frame.duplicated(["iso3", "year"]).any()
    assert frame["year"].isin(YEARS if key == "rd" else [GDP_YEAR]).all()
    assert frame["value"].dropna().ge(0).all()
    if key != "rd":
        assert frame["value"].dropna().gt(0).all()
    return frame


def prepare_data(history=None):
    history = load_history() if history is None else history
    basque = next(c for c in history["countries"] if c["iso"] == BASQUE_CODE)
    catalog = wb_payload("wb_countries.json")
    countries = pd.DataFrame([
        {"iso3": r["id"], "country": r["name"], "region": r["region"]["value"].strip(),
         "income_group": r["incomeLevel"]["value"], "in_world_bank_catalog": True}
        for r in catalog if r["region"]["id"] != "NA"
    ]).set_index("iso3")
    aggregates = {r["id"] for r in catalog if r["region"]["id"] == "NA"}
    assert not countries.index.duplicated().any()
    wb = {key: load_wb_series(key) for key in INDICATORS}
    oecd = pd.read_csv(RAW / "msti_gerd_percent_gdp_2020_2024.csv", keep_default_na=False)
    for column, value in {"FREQ": "A", "MEASURE": "G", "UNIT_MEASURE": "PT_B1GQ",
                          "PRICE_BASE": "_Z", "TRANSFORMATION": "_Z"}.items():
        assert oecd[column].eq(value).all()
    assert oecd["UNIT_MULT"].astype(int).eq(0).all()
    oecd["OBS_VALUE"] = pd.to_numeric(oecd["OBS_VALUE"], errors="coerce")
    assert oecd["TIME_PERIOD"].isin(YEARS).all()
    assert not oecd.duplicated(["REF_AREA", "TIME_PERIOD"]).any()
    assert oecd["OBS_VALUE"].dropna().ge(0).all()
    # This observed non-aggregate OECD economy has no World Bank country entry.
    outside = set(oecd["REF_AREA"]) - set(countries.index) - {"OECD", "EU27_2020"}
    assert outside.issubset({"TWN"}), f"Classify new OECD area(s) before proceeding: {outside}"
    if "TWN" in outside:
        countries.loc["TWN"] = ["Chinese Taipei", "Outside World Bank catalog", "", False]
    countries.loc[BASQUE_CODE] = ["Basque Country", "Spain (subnational region)", "", False]
    countries["geography_type"] = ["region" if c == BASQUE_CODE else "economy" for c in countries.index]
    countries["regression_eligible"] = countries.index != BASQUE_CODE
    countries["oecd_member"] = countries.index.isin(OECD_MEMBERS)
    assert not set(countries.index) & aggregates
    universe = set(countries.index)
    oecd_rows = []
    for _, r in oecd[oecd["REF_AREA"].isin(universe)].dropna(subset=["OBS_VALUE"]).iterrows():
        oecd_rows.append({
            "iso3": r["REF_AREA"], "year": int(r["TIME_PERIOD"]), "value": float(r["OBS_VALUE"]),
            "rd_source": OECD_SOURCE, "obs_status": r["OBS_STATUS"],
            "obs_status_2": r["OBS_STATUS_2"], "obs_status_3": r["OBS_STATUS_3"],
            "aux_obs_status": r["AUX_OBS_STATUS"], "footnote": "",
        })
    oecd_annual = pd.DataFrame(oecd_rows)
    basque_annual = pd.DataFrame([{"iso3": BASQUE_CODE, "year": y, "value": basque["rd"]["eustat"][str(y)]["v"],
        "rd_source": EUSTAT_SOURCE, "obs_status": "derived_ratio", "obs_status_2": "", "obs_status_3": "",
        "aux_obs_status": "", "footnote": basque["rd"]["eustat"][str(y)]["note"]}
        for y in YEARS if str(y) in basque["rd"]["eustat"]], columns=oecd_annual.columns)
    uis_annual = wb["rd"].loc[wb["rd"]["iso3"].isin(universe)].dropna(subset=["value"]).copy()
    uis_annual["rd_source"] = UIS_SOURCE
    for col in ["obs_status_2", "obs_status_3", "aux_obs_status"]:
        uis_annual[col] = ""
    chosen, decisions = [], []
    for iso3 in sorted(universe):
        o = oecd_annual[oecd_annual["iso3"].eq(iso3)]
        w = uis_annual[uis_annual["iso3"].eq(iso3)]
        pick = o if len(o) >= len(w) else w
        if iso3 == BASQUE_CODE:
            pick = basque_annual
        source = "" if pick.empty else pick["rd_source"].iloc[0]
        chosen.append(pick[oecd_annual.columns])
        decisions.append({
            "iso3": iso3, "oecd_n_years": len(o), "wdi_n_years": len(w),
            "oecd_years": ";".join(map(str, sorted(o["year"]))),
            "wdi_years": ";".join(map(str, sorted(w["year"]))),
            "selected_source": source,
            "eustat_n_years": len(basque_annual) if iso3 == BASQUE_CODE else 0,
            "oecd_mean_available": o["value"].mean(), "wdi_mean_available": w["value"].mean(),
            "selection_rule": "Most reported years in 2020-2024; OECD preferred on ties",
        })
    selected = pd.concat(chosen, ignore_index=True).sort_values(["iso3", "year"])
    assert not selected.duplicated(["iso3", "year"]).any()
    assert selected.groupby("iso3")["rd_source"].nunique().eq(1).all()
    summaries = []
    for iso3, group in selected.groupby("iso3"):
        years = sorted(group["year"])
        flags = "; ".join(
            f"{int(r['year'])}:" + ("|".join(str(r[col]) for col in ["obs_status", "obs_status_2", "obs_status_3", "aux_obs_status"] if str(r[col])) or "unflagged")
            for _, r in group.iterrows()
        )
        mean = float(group["value"].mean())
        record = {
            "iso3": iso3, "rd_percent_gdp": mean, "rd_n_years": len(group),
            "rd_years": ";".join(map(str, years)),
            "rd_missing_years": ";".join(map(str, sorted(set(YEARS) - set(years)))),
            "rd_complete_five_years": years == YEARS,
            "rd_strict_five_year_mean": mean if years == YEARS else np.nan,
            "rd_source": group["rd_source"].iloc[0], "rd_status_by_year": flags,
        }
        for year in YEARS:
            value = group.loc[group["year"].eq(year), "value"]
            record[f"rd_{year}"] = value.iloc[0] if len(value) else np.nan
        summaries.append(record)
    summary = pd.DataFrame(summaries).set_index("iso3")
    coverage = countries.join(summary)
    coverage["rd_n_years"] = coverage["rd_n_years"].fillna(0).astype(int)
    coverage["rd_complete_five_years"] = coverage["rd_n_years"].eq(5)
    coverage["rd_source"] = coverage["rd_source"].fillna("")
    for key in ("nominal", "ppp"):
        gdp = wb[key].set_index("iso3")
        for source, destination in [("value", f"gdp_{key}_2025"), ("obs_status", f"gdp_{key}_status"), ("footnote", f"gdp_{key}_footnote")]:
            coverage[destination] = gdp[source]
        obs = basque["gdp"][key].get(str(GDP_YEAR), {})
        coverage.loc[BASQUE_CODE, [f"gdp_{key}_2025", f"gdp_{key}_status", f"gdp_{key}_footnote"]] = [obs.get("v", np.nan), obs.get("flags", ""), obs.get("note", "")]
        coverage[f"included_{key}"] = coverage["rd_n_years"].gt(0) & coverage[f"gdp_{key}_2025"].notna()
        coverage[f"excluded_reason_{key}"] = coverage.apply(
            lambda r: "; ".join(
                (["No reported GERD/GDP observation within 2020-2024 in selected sources"] if r["rd_n_years"] == 0 else [])
                + ([f"No 2025 {key} GDP per capita in World Bank WDI"] if pd.isna(r[f"gdp_{key}_2025"]) else [])
            ), axis=1,
        )
    # Keep the nominal/PPP comparison on a common sample as availability changes.
    # The individual eligibility flags above remain available in the coverage audit.
    coverage["included_paired"] = coverage["included_nominal"] & coverage["included_ppp"]
    coverage["excluded_reason_paired"] = coverage.apply(
        lambda r: "; ".join(dict.fromkeys(
            reason for key in ("nominal", "ppp")
            for reason in r[f"excluded_reason_{key}"].split("; ") if reason
        )), axis=1,
    )
    # Independently verify every mean from the visible five annual-value columns.
    annual_columns = [f"rd_{y}" for y in YEARS]
    assert np.allclose(coverage[annual_columns].mean(axis=1), coverage["rd_percent_gdp"], equal_nan=True)
    assert coverage[annual_columns].count(axis=1).eq(coverage["rd_n_years"]).all()
    assert coverage["rd_strict_five_year_mean"].notna().equals(coverage["rd_complete_five_years"])
    benchmark_rows = oecd[oecd["REF_AREA"].eq("OECD")].dropna(subset=["OBS_VALUE"])
    assert set(benchmark_rows["TIME_PERIOD"]) == set(YEARS)
    benchmark = float(benchmark_rows["OBS_VALUE"].mean())
    return coverage.reset_index(), selected, pd.DataFrame(decisions), wb, oecd, benchmark


def sample_for(coverage: pd.DataFrame, spec: dict) -> pd.DataFrame:
    sample = coverage[coverage["included_paired"]].copy()
    if spec["strict"]:
        sample = sample[sample["rd_complete_five_years"]].copy()
    sample["gdp_per_capita"] = sample[f"gdp_{spec['kind']}_2025"]
    sample["gdp_year"] = GDP_YEAR
    sample["gdp_unit"] = "current US dollars" if spec["kind"] == "nominal" else "current international dollars (PPP)"
    return sample.sort_values("iso3").reset_index(drop=True)


def fit(sample: pd.DataFrame) -> dict:
    plotted_n = len(sample)
    plotted_complete = int(sample["rd_n_years"].eq(5).sum())
    sample = sample[sample["regression_eligible"]] if "regression_eligible" in sample else sample
    x = np.log(sample["gdp_per_capita"].to_numpy(float))
    y = sample["rd_percent_gdp"].to_numpy(float)
    assert len(sample) >= 3 and np.isfinite(x).all() and np.isfinite(y).all(), "Insufficient valid observations for regression"
    assert np.ptp(x) > 0 and np.ptp(y) > 0, "Regression requires variation in both variables"
    result = linregress(x, y)
    coefficients = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), y, rcond=None)[0]
    fitted = coefficients[0] + coefficients[1] * x
    r2 = 1 - np.sum((y - fitted) ** 2) / np.sum((y - y.mean()) ** 2)
    assert np.allclose(coefficients, [result.intercept, result.slope], atol=1e-10)
    assert np.isclose(r2, result.rvalue ** 2, atol=1e-12)
    return {
        "n": len(sample), "plotted_n": plotted_n, "complete_five_year_n": plotted_complete,
        "intercept": float(result.intercept), "slope_log_gdp": float(result.slope),
        "r_squared": float(r2), "spearman_rho": float(spearmanr(x, y).statistic),
        "equation": "GERD_percent_GDP = intercept + slope_log_gdp * ln(GDP_per_capita)",
    }


def place_labels(fig, ax, sample: pd.DataFrame) -> list:
    labeled = sample[sample["iso3"].isin(LABELS)]
    texts = []
    for _, row in labeled.iterrows():
        name = DISPLAY.get(row["iso3"], row["country"])
        if row["rd_n_years"] < 5:
            name += "*"
        texts.append(ax.text(
            row["gdp_per_capita"] + 900, row["rd_percent_gdp"] + 0.08, name,
            fontsize=9.3, color=COUNTRY_COLOR,
            weight="normal", zorder=5,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 0.6},
        ))
        texts[-1].set_gid(f"country-label-{row['iso3']}")
    np.random.seed(42)
    adjust_text(
        texts, x=sample["gdp_per_capita"].to_numpy(), y=sample["rd_percent_gdp"].to_numpy(),
        target_x=labeled["gdp_per_capita"].to_numpy(), target_y=labeled["rd_percent_gdp"].to_numpy(),
        ax=ax, expand=(1.12, 1.3), force_text=(0.4, 0.6), force_static=(0.3, 0.5),
        force_pull=(0.004, 0.004), max_move=(14, 18), iter_lim=1400,
    )
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for _ in range(500):
        boxes = [t.get_window_extent(renderer).expanded(1.03, 1.08) for t in texts]
        collision = next(((i, j) for i in range(len(texts)) for j in range(i + 1, len(texts)) if boxes[i].overlaps(boxes[j])), None)
        if collision is None:
            break
        i, j = collision
        px, py = ax.transData.transform(texts[j].get_position())
        step = boxes[i].y1 - boxes[j].y0 + 2
        if boxes[j].y1 + step > ax.bbox.y1:
            step = -(boxes[j].y1 - boxes[i].y0 + 2)
        texts[j].set_position(ax.transData.inverted().transform((px, py + step)))
    extra_texts, extra_rows = space_available_labels(fig, ax, sample)
    texts += extra_texts
    labeled = pd.concat([labeled, extra_rows])
    for text, (_, row) in zip(texts, labeled.iterrows()):
        box = text.get_window_extent(renderer)
        target = ax.transData.transform((row["gdp_per_capita"], row["rd_percent_gdp"]))
        edge = np.array([np.clip(target[0], box.x0, box.x1), np.clip(target[1], box.y0, box.y1)])
        if np.linalg.norm(edge - target) > 7:
            ax.annotate("", xy=(row["gdp_per_capita"], row["rd_percent_gdp"]),
                        xytext=ax.transData.inverted().transform(edge),
                        arrowprops={"arrowstyle": "-", "color": "#98aab6", "lw": 0.6,
                                    "shrinkA": 2, "shrinkB": 4}, zorder=3)
    fig.canvas.draw()
    boxes = [t.get_window_extent(fig.canvas.get_renderer()) for t in texts]
    assert not any(boxes[i].overlaps(boxes[j]) for i in range(len(boxes)) for j in range(i + 1, len(boxes))), "Country labels overlap"
    assert all(b.x0 >= ax.bbox.x0 - 1 and b.x1 <= ax.bbox.x1 + 1 and b.y0 >= ax.bbox.y0 - 1 and b.y1 <= ax.bbox.y1 + 1 for b in boxes)
    return texts


def space_available_labels(fig, ax, sample: pd.DataFrame) -> tuple[list, pd.DataFrame]:
    """Add nearby names only when their rendered boxes fit in free plot space."""
    renderer = fig.canvas.get_renderer()
    point_xy = ax.transData.transform(sample[["gdp_per_capita", "rd_percent_gdp"]].to_numpy())
    point_boxes = [Bbox.from_bounds(x - 6, y - 6, 12, 12) for x, y in point_xy]
    occupied = [text.get_window_extent(renderer).padded(5) for text in ax.texts]
    if ax.get_legend() is not None:
        occupied.append(ax.get_legend().get_window_extent(renderer).padded(5))
    candidates = []
    for position, (_, row) in enumerate(sample.iterrows()):
        if row["iso3"] in LABELS:
            continue
        neighbours = int((np.linalg.norm(point_xy - point_xy[position], axis=1) < 40).sum()) - 1
        # Keep dense clusters sparse, even if a long leader could reach blank space.
        if neighbours >= 4:
            continue
        candidates.append((neighbours, -row["rd_percent_gdp"], row["iso3"], position))
    texts, indices = [], []
    for _, _, _, position in sorted(candidates):
        row = sample.iloc[position]
        x, y = point_xy[position]
        name = DISPLAY.get(row["iso3"], row["country"]) + ("*" if row["rd_n_years"] < 5 else "")
        text = ax.text(0, 0, name, fontsize=9.3, color=COUNTRY_COLOR, weight="normal", zorder=5,
                       bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.92, "pad": 0.6})
        # Try short offsets; never force a name into the crowded lower-left.
        placed = False
        for dx, dy, ha, va in [
            (10, 10, "left", "bottom"), (10, -10, "left", "top"),
            (-10, 10, "right", "bottom"), (-10, -10, "right", "top"),
            (12, 0, "left", "center"), (-12, 0, "right", "center"),
            (0, 12, "center", "bottom"), (0, -12, "center", "top"),
            (18, 0, "left", "center"), (-18, 0, "right", "center"),
        ]:
            text.set_position(ax.transData.inverted().transform((x + dx, y + dy)))
            text.set_ha(ha)
            text.set_va(va)
            box = text.get_window_extent(renderer).padded(3)
            if not (ax.bbox.x0 + 2 <= box.x0 and box.x1 <= ax.bbox.x1 - 2
                    and ax.bbox.y0 + 2 <= box.y0 and box.y1 <= ax.bbox.y1 - 2):
                continue
            if any(box.overlaps(other) for other in occupied + point_boxes):
                continue
            text.set_gid(f"country-label-{row['iso3']}")
            occupied.append(box.padded(2))
            texts.append(text)
            indices.append(position)
            placed = True
            break
        if not placed:
            text.remove()
    return texts, sample.iloc[indices]


def figure(sample: pd.DataFrame, spec: dict, stats: dict, dates: str):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
        "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "svg.fonttype": "none", "pdf.fonttype": 42, "svg.hashsalt": "world-rd-income",
        "axes.spines.top": False, "axes.spines.right": False,
    })
    fig, ax = plt.subplots(figsize=(14.4, 9.5), facecolor="white")
    fig.subplots_adjust(left=0.083, right=0.96, top=0.80, bottom=0.23)
    fig.text(0.083, 0.953, "WORLDWIDE AVAILABLE DATA  /  R&D AND ECONOMIC PERFORMANCE", color=TEAL, weight="bold", fontsize=10)
    title = "R&D intensity and income worldwide"
    if spec["strict"]:
        title += ": complete five-year averages"
    fig.text(0.083, 0.91, title, fontsize=21, weight="bold")
    conversion = "current US dollars" if spec["kind"] == "nominal" else "current international dollars (PPP)"
    window = "Complete 2020–2024 R&D mean" if spec["strict"] else "Mean of reported R&D observations in 2020–2024"
    fig.text(0.083, 0.868, f"{window} • GDP per capita, 2025 • {conversion}", fontsize=11.2, color=MUTED)
    xmax = max(200000, np.ceil(sample["gdp_per_capita"].max() / 20000) * 20000 + 20000)
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, max(8, np.ceil(sample["rd_percent_gdp"].max()) + 1))
    ax.set_axisbelow(True)
    ax.grid(color="#e1e7ec", linewidth=0.7)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#b4c1cb")
    ax.xaxis.set_major_locator(MultipleLocator(20000))
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.tick_params(length=0, pad=8)
    ax.set_xlabel(f"GDP per capita, 2025 ({conversion})", fontsize=11, weight="bold", labelpad=14)
    ylabel = "Mean R&D expenditure, 2020–2024 (% of GDP)" if spec["strict"] else "Mean R&D expenditure, reported years in 2020–2024 (% of GDP)"
    ax.set_ylabel(ylabel, fontsize=11, weight="bold", labelpad=15)
    xx = np.geomspace(sample["gdp_per_capita"].min(), sample["gdp_per_capita"].max(), 600)
    ax.plot(xx, stats["intercept"] + stats["slope_log_gdp"] * np.log(xx),
            color=TEAL, lw=1.9, linestyle=(0, (1.4, 2.5)), zorder=2)
    for _, row in sample.iterrows():
        color = COUNTRY_COLOR
        complete = row["rd_n_years"] == 5
        artist = ax.scatter(row["gdp_per_capita"], row["rd_percent_gdp"], s=39,
                            facecolor=color if complete else "white", edgecolor=color,
                            linewidth=0.9, zorder=4)
        artist.set_gid(f"{spec['id']}-{row['iso3']}")
    ax.text(0.986, 0.957, f"Logarithmic fit\n$R^2$ = {stats['r_squared']:.3f}  |  n = {stats['n']} countries/economies",
            transform=ax.transAxes, ha="right", va="top", fontsize=10.6,
            bbox={"facecolor": "#f0f5f8", "edgecolor": "none", "pad": 9})
    handles = [Line2D([], [], color=COUNTRY_COLOR, marker="o", linestyle="None", markersize=5, label="All five R&D years reported")]
    if not spec["strict"]:
        handles.append(Line2D([], [], color=COUNTRY_COLOR, marker="o", markerfacecolor="white", linestyle="None", markersize=5, label="One to four R&D years reported"))
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=9)
    place_labels(fig, ax, sample)
    if spec["strict"]:
        note = f"All {stats['plotted_n']} plotted economies/regions have R&D in each year, 2020–2024."
    else:
        note = f"* Incomplete R&D coverage: {stats['complete_five_year_n']} of {stats['plotted_n']} plotted economies/regions have all five years. Means use available years."
    notes = [
        note,
        "Basque Country is a regional comparison, excluded from the fit because it overlaps Spain; PPP uses Spain's national GDP-PPP proxy.",
        "Fit: R&D intensity = a + b ln(GDP per capita), equal economy weights. No interpolation or year substitution; association is not causation.",
        f"Sources: OECD MSTI; UNESCO/WDI; Eustat (Basque R&D/GDP), Spain WDI currency/PPP factors. Retrieved: {dates}.",
    ]
    for i, text in enumerate(notes):
        fig.text(0.083, 0.133 - i * 0.023, text, fontsize=8.5, color=MUTED)
    return fig


def workbook(frames: dict) -> None:
    """Stream the large joint GERD table so weekly builds have bounded memory."""
    from itertools import chain, islice
    from openpyxl import Workbook
    from openpyxl.cell import WriteOnlyCell
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    book = Workbook(write_only=True)
    for name, frame in frames.items():
        if isinstance(frame, pd.DataFrame):
            headers = list(frame.columns)
            rows = frame.itertuples(index=False, name=None)
        else:
            first = next(frame)
            headers = list(first)
            rows = (tuple(r.get(key) for key in headers) for r in chain([first], frame))
        preview = list(islice(rows, 119))
        sheet = book.create_sheet(name)
        sheet.freeze_panes = "C2"
        sheet.row_dimensions[1].height = 34
        for i, key in enumerate(headers):
            length = max([len(str(key)), *[len(str(r[i] if r[i] is not None else "")) for r in preview]])
            sheet.column_dimensions[get_column_letter(i + 1)].width = min(max(length + 2, 12), 58)
        heading = []
        for key in headers:
            cell = WriteOnlyCell(sheet, value=key)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="146B88")
            cell.alignment = Alignment(wrap_text=True, vertical="center")
            heading.append(cell)
        sheet.append(heading)
        count = 1
        for row in chain(preview, rows):
            cells = []
            for key, value in zip(headers, row):
                if isinstance(value, (dict, list, tuple)):
                    value = str(value)
                elif pd.isna(value):
                    value = None
                cell = WriteOnlyCell(sheet, value=value)
                if isinstance(value, str):
                    cell.data_type = "s"
                if key in {"rd_percent_gdp", "rd_strict_five_year_mean", "r_squared"}:
                    cell.number_format = "0.0000"
                elif key == "amount" or str(key).startswith("gdp_") and str(key).endswith("2025"):
                    cell.number_format = "#,##0.00"
                cells.append(cell)
            sheet.append(cells)
            count += 1
        assert count <= 1_048_576, f"Excel row limit exceeded in {name}"
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{count}"
    book.save(DATA / "world_rd_income_data.xlsx")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = verify_inputs()
    history = load_history()
    coverage, selected, decisions, wb, oecd, benchmark = prepare_data(history)
    dates = ", ".join(sorted({v["retrieved_utc"][:10] for name, v in manifest.items()
                              if name not in HISTORY_SOURCES and name not in NOMINAL_SOURCES
                              and name not in SECTOR_FIELD_SOURCES and name != UIS_ARCHIVE}))
    samples = {spec["id"]: sample_for(coverage, spec) for spec in SPECS}
    for a, b in [(SPECS[0], SPECS[1]), (SPECS[2], SPECS[3])]:
        assert samples[a["id"]]["iso3"].equals(samples[b["id"]]["iso3"]), "Nominal and PPP samples differ: inspect and document before plotting"
        assert samples[a["id"]]["rd_percent_gdp"].equals(samples[b["id"]]["rd_percent_gdp"])
    statistics, sensitivities = [], []
    with PdfPages(OUT / "world_rd_income_2025.pdf") as main_pdf, PdfPages(OUT / "world_rd_income_complete_five_years.pdf") as strict_pdf:
        for spec in SPECS:
            sample = samples[spec["id"]]
            stats = {"figure": spec["id"], "income_measure": spec["kind"], **fit(sample), "oecd_benchmark_percent_gdp": benchmark}
            statistics.append(stats)
            sample.to_csv(DATA / f"{spec['id']}.csv", index=False, encoding="utf-8-sig")
            fig = figure(sample, spec, stats, dates)
            for extension in ("png", "svg", "pdf"):
                fig.savefig(OUT / f"{spec['id']}.{extension}", dpi=300, facecolor="white")
            (strict_pdf if spec["strict"] else main_pdf).savefig(fig, facecolor="white")
            plt.close(fig)
            print(f"{spec['id']}: plotted={stats['plotted_n']}; regression n={stats['n']}; complete plotted={stats['complete_five_year_n']}; R2={stats['r_squared']:.6f}")
            if spec["strict"]:
                continue
            uis_means = wb["rd"].dropna(subset=["value"]).groupby("iso3")["value"].mean()
            uis_counts = wb["rd"].dropna(subset=["value"]).groupby("iso3")["value"].size()
            uis_only = sample.copy()
            uis_only["rd_percent_gdp"] = uis_only["iso3"].map(uis_means)
            uis_only["rd_n_years"] = uis_only["iso3"].map(uis_counts)
            uis_only = uis_only.dropna(subset=["rd_percent_gdp"])
            groups = {
                "All eligible economies, chosen source": sample,
                "Complete five-year R&D coverage": sample[sample["rd_n_years"].eq(5)],
                "At least three R&D observations": sample[sample["rd_n_years"].ge(3)],
                "Excluding Ireland and Luxembourg": sample[~sample["iso3"].isin(["IRL", "LUX"])],
                "Excluding Israel": sample[~sample["iso3"].eq("ISR")],
                "OECD members only": sample[sample["oecd_member"]],
                "UNESCO via WDI R&D only, no OECD substitution": uis_only,
            }
            for description, subset in groups.items():
                sensitivities.append({"income_measure": spec["kind"], "sample": description, **fit(subset)})
    statistics = pd.DataFrame(statistics)
    sensitivities = pd.DataFrame(sensitivities)
    frames = {
        "Nominal 2025": samples[SPECS[0]["id"]], "PPP 2025": samples[SPECS[1]["id"]],
        "Complete five years": samples[SPECS[2]["id"]], "Coverage and exclusions": coverage,
        "Selected annual RD": selected.merge(coverage[["iso3", "country"]], on="iso3", validate="many_to_one"),
        "Source selection": decisions.merge(coverage[["iso3", "country"]], on="iso3", validate="one_to_one"),
        "Model statistics": statistics, "Sensitivity checks": sensitivities,
        "Sources": pd.DataFrame([{"file": name, **info} for name, info in manifest.items()]),
        "Indicator metadata": pd.DataFrame([r for key in INDICATORS for r in wb_payload(f"wb_{key}_metadata.json")]).drop(columns=["source", "topics"]),
        "OECD raw RD": oecd, "WDI raw RD": wb["rd"], "WDI raw nominal GDP": wb["nominal"], "WDI raw PPP GDP": wb["ppp"],
    }
    for name, rows in zip(["RD nominal annual", "RD nominal coverage", "RD nominal definitions"], nominal_tables(history)):
        frames[name] = pd.DataFrame(rows)
    for _, name, rows in sector_field_tables(history):
        frames[name] = rows
    for _, name, rows in basque_tables(history):
        frames[name] = rows
    for _, name, rows in breakdown_tables(history):
        frames[name] = rows
    for filename, frame in {
        "coverage_and_exclusions.csv": coverage, "selected_annual_rd.csv": frames["Selected annual RD"],
        "source_selection.csv": frames["Source selection"], "model_statistics.csv": statistics,
        "sensitivity_checks.csv": sensitivities,
    }.items():
        frame.to_csv(DATA / filename, index=False, encoding="utf-8-sig")
    workbook(frames)
    build_breakdown_figures(history, OUT, DATA)
    sample = samples[SPECS[0]["id"]]
    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_retrieval_dates": dates, "python": platform.python_version(),
        "wdi_dataset_lastupdated": {key: manifest[f"wb_{key}.json"].get("api_lastupdated", "") for key in INDICATORS},
        "study_years": {"rd": YEARS, "gdp": GDP_YEAR},
        "sample_rule": "At least one R&D year and both 2025 income measures; same economies in both charts",
        "world_bank_catalog_economies": int(coverage["in_world_bank_catalog"].sum()),
        "additional_oecd_economies": coverage.loc[~coverage["in_world_bank_catalog"] & coverage["geography_type"].ne("region"), "iso3"].tolist(),
        "additional_regions": [BASQUE_CODE], "regional_regression_rule": "Basque Country shown but excluded from country regressions because it overlaps Spain",
        "audited_economies": len(coverage), "any_rd_2020_2024": int(coverage["rd_n_years"].gt(0).sum()),
        "sample_rd_source_counts": sample["rd_source"].value_counts().to_dict(),
        "sample_rd_year_counts": sample["rd_n_years"].value_counts().sort_index().to_dict(),
        "individually_eligible": {key: int(coverage[f"included_{key}"].sum()) for key in ("nominal", "ppp")},
        "paired_eligible": len(sample),
        "rd_available_but_missing_2025_income": coverage.loc[coverage["rd_n_years"].gt(0) & ~coverage["included_paired"], ["iso3", "country", "excluded_reason_paired"]].to_dict("records"),
        "models": statistics.to_dict("records"),
        "nominal_rd": nominal_summary(history),
        "sector_field_gerd": history["sectorField"]["summary"],
        "funding_research": history["breakdowns"]["summary"],
        "validation": {name: "passed" for name in [
            "source_checksums_and_urls", "complete_api_pagination", "series_codes_dimensions_units_and_years",
            "unique_economy_year_observations", "aggregates_excluded", "one_rd_source_per_economy",
            "independent_mean_check_from_annual_columns", "strict_five_year_means_require_all_years",
            "independent_OLS_and_R_squared", "nominal_PPP_identical_samples_and_RD", "label_overlap_and_bounds",
        ]},
    }
    (DATA / "validation_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    current_results(report)
    build_explorer(report, history)
    print(json.dumps({k: v for k, v in report.items() if k not in ["models", "validation"]}, indent=2))
    print("Saved PNG, SVG, PDF, interactive HTML, CSV, Excel and validation outputs.")


def current_results(report: dict) -> None:
    """Generate current results/captions so refreshed sites do not quote old prose."""
    lines = [
        "# Current build results", "",
        f"Source retrieval dates (UTC): {report['source_retrieval_dates']}.  ",
        f"Chart built (UTC): {report['built_utc']}.", "",
        "Static figures and main workbook analysis: R&D years 2020–2024; GDP year 2025. Each chart pair uses economies with both income measures.",
        "The interactive explorer offers selectable years within 2000–2025, two-endpoint comparisons and annual country histories. Use its CSV download for the active selection.", "",
        "| Figure | Plotted economies/regions | Regression economies | Complete R&D coverage | R² |",
        "|---|---:|---:|---:|---:|",
    ]
    for model in report["models"]:
        lines.append(f"| {model['figure']} | {model['plotted_n']} | {model['n']} | {model['complete_five_year_n']} | {model['r_squared']:.6f} |")
    lines += [
        "", "## Coverage", "",
        f"Audited economies: {report['audited_economies']}; with some R&D: {report['any_rd_2020_2024']}; paired sample: {report['paired_eligible']}.",
        f"Individually eligible before requiring both income measures: {report['individually_eligible']}.",
        f"Paired sample R&D sources: {report['sample_rd_source_counts']}.",
        f"Paired sample number of reported R&D years: {report['sample_rd_year_counts']}.", "",
        "Economies with R&D but missing at least one requested income measure:", "",
    ]
    for row in report["rd_available_but_missing_2025_income"]:
        lines.append(f"- {row['country']} ({row['iso3']}): {row['excluded_reason_paired']}.")
    if not report["rd_available_but_missing_2025_income"]:
        lines.append("None.")
    nominal = report["nominal_rd"]
    lines += ["", "## Nominal R&D database, 2000–2025", "",
              f"OECD reported nominal GERD: {nominal['oecd_reported_local_observations']} country-year observations across {nominal['oecd_reported_local_economies']} economies, in current national-currency units.",
              "Country US-dollar estimates use annual GERD/GDP (%) / 100 × same-year WDI GDP. Basque amounts instead directly convert Eustat reported EUR using annual Spanish WDI exchange/PPP factors; reported EUR and derived USD/PPP remain separate.",
              f"USD availability by R&D source: {nominal['derived_usd_by_rd_source']}. Direct UIS release: {nominal['uis_release']}.",
              "See rd_nominal_annual.csv, rd_nominal_coverage.csv and the workbook's RD nominal sheets for input values, units, source URLs, flags and missingness. UIS/WDI alternatives can repeat underlying observations; do not add them together.",
              ""]
    sector = report["sector_field_gerd"]
    breakdown = report["funding_research"]
    lines += ["## Funding sources and research types", "",
              f"{breakdown['rows']:,} normalized rows ({breakdown['numeric_amounts']:,} numeric amounts) across {breakdown['economies_regions']} economies/regions, requested years 2000–2025.",
              f"Reconciliation: {breakdown['reconciliation']}.",
              "The scrolling Funding, performers & research dashboard shows eight charts together, with shared economy/year controls, percentage labels and per-chart SVG/CSV exports. Five static figure families compare USA, China, Korea, United Kingdom, Singapore and Basque Country over available common years in 2020–2024, including standalone performing-sector amounts and percentages.",
              "Direct-source completion: Eustat supplies Basque total/capital (types remain missing); ONS supplies UK business current research types + separate capital for 2022–2024, with matched publication-vintage totals, and dashboard intensity through 2024. UK government research types for 2024 and comparable business types for 2020–2021 remain unavailable. See OFFICIAL_DATA.md for scope, vintages and source locators.",
              "Basque constant-2020 PPP amounts are a derived Spanish national conversion proxy. Basque research-type observations were not identified in accessed Eustat tables. Missing categories remain visible; no zero imputation or forced 100% normalization.",
              "See rd_breakdown_annual.csv, coverage/reconciliation/definitions/conversion CSVs, rd_breakdown_examples.csv and the workbook's GERD funding/research sheets.", ""]
    lines += ["## GERD by sector of performance and field of R&D", "",
              f"OECD + Eustat joint breakdown: {sector['source_rows']:,} normalized rows across {sector['economies']} economies/regions; {sector['available_values']:,} numeric amounts. Available years: {sector['first_available_year']}–{sector['last_available_year']} within the requested 2000–2025 window.",
              f"Unit/price representations: {sector['rows_by_basis']}; constant-price base years: {sector['constant_price_base_years']}.",
              f"Cell availability: {sector['availability']}. Reconciliation audit: {sector['reconciliation']}.",
              "These unit representations overlap. Totals and combined field groups must not be added to their components. Confidential, included-elsewhere and missing cells are not zero. Reported totals are retained even when breakdowns do not reconcile.",
              "See rd_sector_field_annual.csv, rd_sector_field_coverage.csv, rd_sector_field_reconciliation.csv and rd_sector_field_definitions.csv, plus the workbook's GERD sheets and the offline Sector × field view.",
              f"Source retrieved (UTC): {sector['source_retrieved_utc']}.",
              "", "## Updated figure captions", ""]
    for model in report["models"]:
        strict = model["figure"].endswith("complete_five_years")
        unit = "current US dollars at market exchange rates" if model["income_measure"] == "nominal" else "current international dollars at purchasing power parities"
        averaging = "all five annual observations required" if strict else "reported years only; hollow markers indicate incomplete coverage"
        lines += [
            f"### {model['figure']}", "",
            f"Each point represents one of {model['plotted_n']} economies/regions with R&D and both 2025 income measures. "
            f"R&D is the arithmetic mean of annual GERD/GDP percentages within 2020–2024 ({averaging}); "
            f"{model['complete_five_year_n']} economies report all five years. GDP per capita is for 2025, in {unit}. "
            f"The dotted curve is an equally weighted OLS fit of R&D intensity on ln(GDP per capita), R² = {model['r_squared']:.3f}. "
            "One complete R&D source series per economy is selected by most reported years, preferring OECD on ties. "
            "Basque Country is shown but excluded from the fit because it overlaps Spain. Eustat supplies Basque R&D and GDP; annual WDI Spain exchange rates and national GDP PPP convert EUR to USD and international dollars (regional proxy). Sources for other economies: OECD MSTI; UNESCO/WDI (R&D); WDI (GDP). "
            f"Source retrieval dates (UTC): {report['source_retrieval_dates']}. Missing observations are not imputed. Association is not causation.", "",
        ]
    lines += [
        "The README's numerical discussion describes the initial 10 November 2026 snapshot. "
        "Use this file, model_statistics.csv, sensitivity_checks.csv and coverage_and_exclusions.csv for this build.", "",
    ]
    (DATA / "current_results.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
