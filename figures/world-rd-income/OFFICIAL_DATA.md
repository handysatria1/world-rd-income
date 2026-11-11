# Basque Country and UK official-source completion

Checked 11 November 2026. Exact workbooks, HTML documentation and Eustat API/PC-Axis responses are archived in `data/raw/`, with URLs, retrieval times, request bodies and SHA-256 checksums in `manifest.json`.

| Series | Result for the requested 2020–2024 window |
|---|---|
| Basque funding and performers | All five years were already available from Eustat; retained. |
| Basque research panels | Added total and separate capital, 2000–2024. Basic/applied/experimental remain unavailable in the accessed public tables. Grey is unclassified current expenditure. |
| UK funding and performers | Existing OECD observations independently compared against 50 direct ONS current-GBP cells from 2022–2024; reference cells and rounding/discrepancy audit are separately downloadable. |
| UK business research | Direct ONS basic/applied/experimental **current costs**, with separately reported capital, for 2022–2024. Use matched totals from each year's publication. |
| UK government research | 2020–2023 from OECD; no compatible 2024 government-performed type split found in the ONS publications. |
| UK dashboard intensity | ONS reported values through 2024; 2020–2024 mean is 2.786%. One provider for the window, with an explicit GDP/publication-vintage break at 2022. |

## Basque Country: what can be classified

[Eustat's R&D data bank](https://en.eustat.eus/banku/id_043201/indexlistaopera.html) and [statistical tables](https://en.eustat.eus/estadisticas/tema_312/opt_1/tipo_1/temas.html) list funding, performers, disciplines and expenditure costs. `PX_043201_cid_res05.px` reports total, current expenditure, wage subcomponents, other current costs and capital; **“nature” is not basic/applied/experimental research**. The regional tables in [INE's 2024 R&D results](https://www.ine.es/dynt3/inebase/index.htm?padre=12876&capsel=12883) also do not list a regional research-type breakdown.

Only `naturaleza=10` (total) and `60` (capital) enter the research panels. Missing BR/AR/ED stay null. The total-minus-capital remainder is derived, not an observed research-type category. The business panel explicitly labels Eustat's combined **business + private non-profit** performers. All four available currency/price representations retain the existing same-year Spanish conversion proxies.

The cost and funding tables' totals agree for all 100 sector-years in 2000–2024. The derived grey remainder need not exactly equal the separately published current-cost cell: in 2000, the combined company/PNP sector reports €478,181k total, €399,510k current and €78,673k capital, a €2k discrepancy. Reported total/capital are preserved; no component is silently adjusted.

This documents the accessed public tables; it does not establish that Eustat cannot supply a custom research-type tabulation.

## UK: compatible research accounting and vintages

[ONS BERD official datasets](https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure/datasets/businessenterpriseresearchanddevelopmentukdesignatedasofficialstatistics), Tables **8 and 10** in each edition:

| Reference year / edition | Total | Basic current | Applied current | Experimental current | Capital |
|---|---:|---:|---:|---:|---:|
| 2022 / 2022 | 49,942 | 6,347 | 16,538 | 23,715 | 3,343 |
| 2023 / 2023 | 49,973 | 6,261 | 16,828 | 23,254 | 3,630 |
| 2024 / 2024 | 55,615 | 6,773 | 17,968 | 27,288 | 3,585 |

Units: current **GBP millions**. Independently rounded components can differ from reported totals by £1 million. Every observation carries a workbook/table/cell locator.

**These are annual publication vintages, not a fully revised 2022–2024 time series.** The 2024 release revises earlier business totals to £50,841m (2022) and £53,195m (2023), but its research-type table covers only 2024. Combining those revised totals/capital figures with older current research-type amounts would mix vintages within a bar; the dashboard instead uses the matched older Table 8 totals/capital. This means the UK business research total can differ from the separately revised performer panel. The publication-vintage limitation is retained in every row and chart export.

The [2024 BERD methodological notes](https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure/bulletins/businessenterpriseresearchanddevelopment/2024#data-sources-and-quality) state that the redesigned survey starts in 2022 and earlier breakdowns are not directly comparable. Thus 2020–2021 are not backfilled with old-method types.

The preserved OECD UK business estimates have three research-type amounts that exhaust the total; adding ONS capital to those estimates would double count. Entire 2022–2024 business-research blocks use direct ONS instead. The original OECD observations remain in `rd_research_oecd_alternatives.csv` and the untouched raw response. No ONS capital is added to OECD government research.

The [ONS GovERD 2024 dataset](https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure/datasets/scienceengineeringandtechnologystatisticsreferencetables), Table **10**, gives research types for **net expenditure** (in-house plus purchased/funded R&D less receipts), not government-performed R&D. Table **12** gives performed totals but no type split. These cannot fill the government-performer 2024 research-type gap. The bulletin also identifies GovERD periods as financial years, e.g. 2024 means 2024–25.

## Funding, intensity and PPP

[ONS GERD 2024](https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure/datasets/ukgrossdomesticexpenditureonresearchanddevelopment2021designatedasnationalstatistics), Tables **1–3**, are compared with the existing OECD funding/performance cube in `rd_ons_funding_comparison.csv`, using the sum of each source's half-last-displayed-digit rounding allowance. Differences beyond rounding are retained. In the checked snapshot, government-funded higher-education R&D for 2024 is **£7,206m in ONS Table 1 C9 versus £7,207.09m in OECD** (flag E, estimated): the £1.09m difference exceeds direct-cell rounding. ONS Note 1 describes regrouping UKRI/HEFBs, but the accessed sources do not establish the cause of this discrepancy. Neither value is silently corrected. The more precise OECD cube remains together. Direct ONS references are in `rd_ons_funding_reported.csv`; government includes UKRI and government funding includes HEFBs. Higher-education 2024 is estimated pending TRAC data (Comments 7).

Dashboard intensity uses **2.96, 2.81, 2.73, 2.72, 2.71%** for 2020–2024 when ONS has the greatest coverage. The first two are from [GERD 2023 official statistics](https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure/datasets/ukgrossdomesticexpenditureonresearchanddevelopment2021designatedasofficialstatistics), Table **6**, labelled indicative by Note 4. The last three are from GERD 2024 Table **5**, GDP vintage 31 March 2026. Source selection still prefers OECD on coverage ties. The ONS series is an additional dashboard-overlay source; scatter/history provider selection remains as documented in the main methodology. `rd_ons_intensity.csv` preserves annual locators and vintage notes.

ONS GBP research amounts are also converted to current and constant-2020 PPP using **same-year OECD UK total/total current-GBP-to-PPP ratios**. These are derived national conversion factors, not ONS's new R&D deflator. `rd_official_conversion.csv` contains both inputs, their flags and the divisor. Original GBP amounts, source scale, and reported/derived status are retained.

The completed funding comparison has **48 of 50 cells within direct-cell rounding** and two retained differences. Besides the 2024 higher-education funding cell above, 2023 government-performed total is **£4,305m in ONS Table 2a C11 versus £4,305.57m in OECD** (£0.57m difference, compared with a £0.5005m rounding allowance). These small differences qualify cross-source agreement; they are not extraction errors or imputed corrections.

## Reproduction

`official_sources.py` pins the reviewed ONS publication editions; weekly refresh re-fetches these URLs for revisions. Eustat queries return all available years within the supported 2000–2025 range. New ONS publication editions require a reviewed source/worksheet mapping, so a layout change cannot silently substitute a different series.

`verify_breakdown.py` independently decodes workbook cells and JSON-stat coordinates; verifies every new normalized amount, flags, conversion, all original OECD alternatives, ONS reference cells and intensity vintages; and compares every export to the embedded HTML/JSON and Excel workbook. `test_breakdown.js --built` checks all eight dashboard selections against independent Python calculations and tests partial Basque categories and UK missingness.
