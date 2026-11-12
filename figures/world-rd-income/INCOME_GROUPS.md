# World Bank income groups and innovation comparisons

Data assembly: **Handy Satria**. Source files, metadata responses, retrieval times and SHA-256 checksums are archived under `data/income_raw/`.

## Classification

The current official workbook identifies **FY2027 (1 July 2026–30 June 2027)**, using **2025 Atlas-method GNI per capita**, not GDP per capita. Thresholds: low ≤ US$1,175; lower-middle US$1,176–4,635; upper-middle US$4,636–14,375; high > US$14,375. These are World Bank income groups, not IMF advanced/emerging classifications.

Sources: [definitions](https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups), [current workbook](https://ddh-openapi.worldbank.org/resources/DR0095333/download), [historical workbook](https://ddh-openapi.worldbank.org/resources/DR0095334/download). Current labels come from `List of economies`; history comes from `Country Analytical History`. The historical workbook's `Parameters` sheet retains old FY21 text; it is not used. FY2027 historical entries are checked against the current workbook. Exact cell locators are in `income_classifications.csv`.

The selected vintage is fixed across all observations in a comparison. Choosing FY2001, for example, does not imply classification from 2001 GDP. The optional middle-income group combines upper- and lower-middle memberships. Unclassified economies remain unclassified. Basque Country is a region and does not inherit Spain's classification.

Snapshot symbols: high = circle; upper-middle = square; lower-middle = diamond; low = triangle; unclassified/region = cross. Combined middle income uses a diamond. Filled/hollow symbols separately indicate complete/incomplete R&D-window coverage. Earlier comparison positions retain outlined squares and movement arrows. Income-group/sample filters recalculate regressions; text search only highlights.

## Four-panel indicators

All four panels use WDI source 2, with exact annual observations for 2000–2025, and retain source metadata/flags. This WDI-only panel can differ from the national explorer, which also selects OECD/ONS/Eustat sources.

- `GB.XPD.RSDV.GD.ZS`: R&D expenditure, % GDP; UNESCO UIS.
- `SP.POP.SCIE.RD.P6`: researchers in R&D, per million people; UNESCO UIS. Consult archived metadata for the source's FTE definition.
- `IP.PAT.RESD`: resident patent applications; WIPO. Optional nonresident series `IP.PAT.NRES`. Optional office total is a **derived** sum requiring both inputs; filings are not grants or unique inventions.
- `IP.JRN.ARTC.SC`: scientific and technical journal articles; NSF. This is not all scholarly publications.

The default pairs 2000 and 2013. Rates use **unweighted economy means**; counts use **sums over observed economies**. Optional means and medians are available. These statistics are calculated here and are not official World Bank group aggregates or GDP/population-weighted rates. Incomplete samples must not be interpreted as full-group totals.

The default paired sample requires an observation at both requested years, separately for each indicator. All-available sampling instead allows membership in the observed sample to vary across years. Each bar includes n, the selected group's economy count, included codes, and excluded/missing codes. Empty samples are missing, not zero. Countries' revisions, coverage and reporting definitions can differ. Regional observations and source aggregate series are excluded from group statistics.

The plotted CSV contains statistics, method, sample, classification vintage and membership. The input export records country values, flags, exclusion reasons, exact source response and 1-based record. Annual missing rows are retained in `innovation_annual.csv`. No nearest-year substitution is made.

## Country-level indicators

Alongside the existing Internet-users series (`IT.NET.USER.ZS`) and 0–100 government-effectiveness score (`GOV_WGI_GE_SC`), the country explorer includes the separate WGI government-effectiveness estimate (`GOV_WGI_GE.EST`, which may be negative), Human Capital Index (`HD.HCI.OVRL`, non-annual), and cumulative bachelor's attainment among people ages 25+ (`SE.TER.CUAT.BA.ZS`). When a World Bank API record lacks ISO3, the pipeline maps its source country code through the archived World Bank country catalog. Values are joined by economy and exact year; missing years are not filled.

The 0–100 governance score remains distinct from the WGI estimate. It is retrieved from the official World Bank CSV ZIP, with source-cell locators retained in the annual data export. Indicator-specific value ranges are checked during the build. The dashboard provides a separate country view for each measure and preserves reported years and missing observations.

Under **Innovation**, choose **Researchers by economy**, **Patent applications by economy** or **Journal articles by economy**. These views use the shared selection of up to 16 economies, in the selected order, and the shared income-group filter. Each row is an individual observation, without group aggregation. Each view offers **Total / Per million people**, remembering its selection. Researchers are full-time equivalents (FTE), not headcounts. Patent applicants can be residents, nonresidents, or their derived office total.

WDI researchers are natively a population rate; total FTE is **calculated** as rate × same-year `SP.POP.TOTL` / 1,000,000. Patent/article rates are **calculated** as count / same-year population × 1,000,000. A conversion requires positive finite population from that exact year; no different-year denominator is substituted. These conversions inherit the source precision and vintages, and do not constitute independently reported totals. The WDI population snapshot is archived separately with its own retrieval/update dates.

- **Exact year:** use that year's observation only, retaining missing values.
- **Latest available:** choose the most recent usable observation separately for each economy, indicator/patent definition and measure, within 2000–2025. Required population inputs must also be available. Actual years appear beside every value.
- **Latest common year:** choose the most recent year with a usable observation and any required population input for every selected economy. No economy is silently dropped. If there is no common year, all rows remain missing and the reason is shown. Basque researchers participate using Eustat data; WDI-equivalent Basque patent/article counts remain unavailable.

Zero is a valid observation in all modes. A derived patent total requires both resident and nonresident observations in the same year, including when choosing latest/common years. Income classification affects labels and filters, not the reported country values.

Country charts export SVG, PNG and CSV. The CSV retains missing rows, requested and actual years, latest available year, units, classification vintage, indicator codes, source files and records, component values (in indicator order), flags, notes, URLs, update/retrieval dates and dataset build time. WDI records are 1-based; Eustat JSON-stat locators explicitly use 0-based array indices and dimension coordinates. Patent totals identify both components. Population values, year, whether used, method, source records/inputs, flags and dates have separate columns. The expandable table and definitions show metadata.

### Basque Country: Eustat

Original responses, exact POST queries, workbooks, definitions, display tables and SHA-256 hashes are archived in `data/basque_innovation_raw/`; normalized inputs are in `basque_innovation_annual.csv`. Basque Country remains a regional, unclassified comparator excluded from income-group aggregates.

- **Researchers:** [Eustat table PX_043201_cid_res08.px](https://www.eustat.eus/bankupx/api/v1/en/DB/PX_043201_cid_res08.px), all execution sectors (`00`), researchers (`200`), both sexes (`10`). The dashboard uses 2000–2024: 5,494 FTE in 2000 and 17,296.2 FTE in 2024. Totals are native Eustat observations; population rates are calculated here. The [display table](https://en.eustat.eus/elementos/tbl0010998_i.html) confirms FTE and was updated 14 November 2025. JSON-stat's `9999` update date is a placeholder, not a real source update.
- **Population:** [PX_010154_cepv1_ep17.px](https://www.eustat.eus/bankupx/api/v1/en/DB/PX_010154_cepv1_ep17.px), whole Basque Country (`00`), both sexes (`10`), all birth years (`1000`). Use reported 1 July counts in 2022 and 2023; otherwise mean the observation year's and next year's 1 January counts. This is a **calculated midyear proxy**, flagged `MIDYEAR_PROXY`, with both dates, array indices and original values exported. It approximates the WDI midyear denominator convention, not a separately reported annual population. January 2025 supports the 2024 proxy; it alone does not support 2025. No verified population update date is available from this archive.
- **Patent context:** [Eustat EIS knowledge-assets table](https://en.eustat.eus/elementos/tbl0014425_i.html), `patents.xlsx`, `Hoja1` row 6, years in row 5. PCT applications per billion GDP in PPP euros, 2015–2022. This is neither the resident/nonresident office count nor a per-population rate. No unsupported count or population conversion is made.
- **Publication context:** [Eustat attractive-research-systems table](https://en.eustat.eus/elementos/tbl0006196_i.html), `publications.xlsx`, `Hoja1` rows 6–7, years in row 5. International scientific co-publications per million people (2017–2024), and the worldwide top-10%-cited publication share (2015–2022). These differ from the WDI journal-article series; totals cannot be recovered from the archived ratios with a verified matching denominator.

The EIS tables are the **2025 edition**, updated 30 October 2025; workbook column years are the observation years. Eustat's archived EIS methodology §§3.8, 5.1 and 18.5 warns about edition changes, reference-year choices and imputation. Cell-specific imputation flags are not supplied. Blanks remain missing; no local imputation is added. The contextual panel retains published units regardless of the main chart's scale. Latest uses each context indicator's most recent value; exact years are strict; common-year context uses the main comparison's common year, and remains missing if none exists. Its separate CSV preserves definitions and workbook cell references.

## Rebuild

Run `income_sources.py` and `basque_innovation_sources.py` (checksum-reuse archives), then `income_data.py`, `verify_basque_innovation.py` and `node test_income.js`. Use `--refresh` only when deliberately changing the source vintage. `build_site.py` packages these outputs into the unified dashboard. The full dashboard uses lazy-loaded local resources; after extracting the research ZIP, serve its root with `python -m http.server` and open the localhost address. Original self-contained national/sector pages remain in the archive.
