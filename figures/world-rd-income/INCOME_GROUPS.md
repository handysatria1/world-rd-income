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

## Rebuild

Run `income_sources.py` (checksum-reuses archives), then `income_data.py`. Use `--refresh` only when deliberately changing the source vintage. `build_site.py` packages these outputs into the unified dashboard. The full dashboard uses lazy-loaded local resources; after extracting the research ZIP, serve its root with `python -m http.server` and open the localhost address. Original self-contained national/sector pages remain in the archive.
