# China value added: OECD TiVA and official NBS sources

Data assembly and assessment: **Handy Satria**. Sources checked on 11 November 2026. The archived source responses and their exact requests are recorded in `data/industry_raw/manifest.json`.

## Result

| Source | Retrieved coverage | Classification and interpretation |
|---|---|---|
| OECD TiVA 2025, `VALU`, China | Annual 2000–2022; 80 returned activity categories per year, including overlapping aggregates | 31 single ISIC Rev.4 divisions per year: 27 explicit division codes and four one-division section equivalents. Remaining categories include multi-division aggregates and sub-divisions. |
| China National Bureau of Statistics (NBS), 2023 competitive input–output table | 2023 benchmark; 211 native product sectors with numeric value added | Original NBS product-sector codes and Chinese names. These have not been harmonised to ISIC. They are not added to the division-only dataset or its country-coverage counts. |

**Assessment:** TiVA closes part of the China gap in the international division panel. The official NBS table supplies much finer native detail and a newer benchmark, but requires a product-sector/classification reconciliation before constructing comparable ISIC divisions.

## OECD TiVA: use total industry value added

- [TiVA overview and definitions](https://www.oecd.org/en/topics/sub-issues/trade-in-value-added.html).
- Dataflow: `OECD.STI.PIE,DSD_TIVA_MAINLV@DF_MAINLV,1.1`, *Trade in Value Added (TiVA) 2025 edition: Principal Indicators, levels*.
- [Exact China data request](https://sdmx.oecd.org/sti-public/rest/v1/data/OECD.STI.PIE,DSD_TIVA_MAINLV@DF_MAINLV,1.1/VALU.CHN..W.USD.A?startPeriod=2000&endPeriod=2025&format=csvfile).
- Measure **`VALU` = Value added**, as defined by `CL_TIVA_MEASURE` in the [resolved dataflow structure](https://sdmx.oecd.org/sti-public/rest/v1/dataflow/OECD.STI.PIE/DSD_TIVA_MAINLV@DF_MAINLV/1.1?references=all). This selects total value added, rather than `EXGR_DVA` (domestic value added embodied in exports).
- Geography `CHN`; counterpart `W`; annual frequency; provider unit **current USD millions**. The [ICIO ReadMe](https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2025/ReadMe_ICIO_small.xlsx), `ReadMe` and `Structure` sheets, identifies current USD millions and **value added at basic prices**.
- `value_reported` preserves USD millions. `value_usd_provider` scales that amount by `10^6` into USD units; this is a derived unit scaling of provider USD, not our exchange-rate conversion. `value_national_currency` is blank, and `currency_code = USD` describes the reported source currency. No CNY series is inferred.
- The requested window extends to 2025, but this retrieved edition ends in **2022**. Years 2023–2025 remain missing. The [2025 ICIO supplementary notes](https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2025/ICIO2025annex.pdf), p. 1, confirms the edition's 1995–2022 span; this project selects 2000 onward.
- TiVA is derived from harmonised, balanced OECD ICIO tables. It is an internationally comparable estimated series, not an untouched NBS release. `est_method` records this interpretation; no unreported SDMX observation-status flag is invented. See the supplementary notes, p. 1 and Tables 3–4, and the [ICIO methods page](https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html).

### Actual division detail

The 31 divisions are **01, 02, 03, 05, 06, 07, 08, 09, 16, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 35, 49, 50, 51, 52, 53, 61, 68, 84, 85**. The last set includes section equivalents D→35, L→68, O→84 and P→85, explicitly flagged in the output. There are 713 single-division observations (31 × 23 years).

Examples of unresolved groupings are food/beverages/tobacco (`C10T12`), textiles/apparel/leather (`C13T15`), paper/printing (`C17_18`), accommodation/food services (`I`), and computer/information services (`J62_63`). These are retained in `gva_other_activities.csv` without allocation. The API also supplies full divisions `C24` and `C30` alongside their finer components; the full-division values are provider observations, not our reconstructed sums. See the SDMX activity codes and supplementary notes, Table 2.

This TiVA retrieval is **China-only**. Other economies are labelled `not_requested_for_this_source`; that does not imply that TiVA lacks them. `gva_isic2.csv` and the companion workbook identify the source as `OECD_TIVA_CHN`.

## Direct official Chinese government data

The [NBS National Data portal](https://data.stats.gov.cn/) has migrated to a new interface. Its home page links **投入产出表 → 2023年投入产出表 → 竞争型投入产出表** (Input–output tables → 2023 → Competitive table).

- [Open the selected official table](https://data.stats.gov.cn/dg/website/page.html#/pc/national/home/report?reportId=41a5187ae4114d50aeb6288a54d25234&catalogId=2ab4dc96a65a4c5192478c9798c77f7b&type=inOut).
- [Official downloadable workbook](https://data.stats.gov.cn/dg/website/publicrelease.pblib/pblibedit/upload/file/xlsx/894bad73a17f4b5b88102f6310584a31).
- The reproducible downloader resolves the selected 2023 table and its workbook from the [public NBS catalogue](https://data.stats.gov.cn/dg/website/publicrelease/web/external/queryPbLibCatalogTree?code=15) and report response. The catalogue also lists benchmarks for 2002, 2005, 2007, 2010, 2012, 2015, 2017, 2018 and 2020; these were identified, but their numeric tables are not included in this addition.

### Extraction and accounting checks

In worksheet **`2023年全国投入产出表`**:

- `A2`: **producers' prices in 2023**; `A3`: **万元**, ten thousand yuan.
- Row 5: native product-sector names; row 6: five-character native sector codes. Preserve leading zeros.
- Row 223, code `TVA`, **增加值合计**: total value added for each of the 211 sector columns. This is value added, not gross output, turnover or an industrial growth rate.
- Rows 219–222: compensation of employees, net production taxes, depreciation of fixed assets, and operating surplus. Their sum reconciles to each reported value-added cell within floating-point precision.
- Row 218: intermediate inputs; row 224: total inputs. Total inputs minus intermediate inputs also reconciles to value added.

`china_nbs_io_value_added.csv` preserves full-precision reported amounts, all four components, input totals, original sheet/cell locators and native names. National-currency units are derived as `value_reported × 10^4`, with currency **CNY**. No USD conversion or year interpolation is applied. The same table is a separate sheet in `industry_exports_gva.xlsx`.

### Classification and comparability limits

The national classification is not identical to ISIC. The official [GB/T 4754–2017 classification, amended](https://www.stats.gov.cn/sj/tjbz/gmjjhyfl/202501/P020250116506795831658.pdf) explicitly states in its foreword that its relationship to ISIC Rev.4 is **non-equivalent**; its contents list an ISIC correspondence in Appendix C. This correspondence is a useful starting point, but it does not itself establish a one-to-one mapping of these 211 input–output product sectors. A validated sector-definition bridge is still needed, especially where one native sector spans several ISIC divisions.

NBS's producers'-price benchmark and OECD's basic-price ICIO estimates also differ in valuation, reference year, classification, compilation and potentially revision vintage. Their values should not be spliced or treated as independent corroborating observations. The NBS data remain a native-detail official benchmark with an explicit unresolved ISIC mapping.

For a coarser annual cross-check, the [China Statistical Yearbook 2025](https://www.stats.gov.cn/sj/ndsj/2025/indexeh.htm), [Table 3-6, Value-added by Sector](https://www.stats.gov.cn/sj/ndsj/2025/html/E03-06.jpg), reports 2020–2023 current-price values in 100 million yuan, but at broad-sector detail rather than a complete ISIC division panel. The table image was inspected; its values have not been added as another harmonised series.
