# Export technology and detailed value added

Analysis and data assembly: **Handy Satria**. Original data remain attributed to their providers.

This supplement has its own retrieval manifest (`data/industry_raw/manifest.json`) and build timestamp (`data/industry_validation.json`). Its annual R&D/income joins identify the original R&D/income build. The manuscript's frozen inputs are retained; the supplement is a new analytical input requiring an explicit manuscript specification decision.

## Reproduce

```sh
python industry_sources.py          # reuse checksum-verified inputs, download missing inputs
python industry_data.py            # normalize, join, audit and build the companion workbook
python verify_industry.py          # independently reconcile normalized rows with original responses
python build_site.py --destination ../../_site
```

Use `python industry_sources.py --refresh` to request a new source vintage. The 2000–2025 request window matches the existing dashboard; availability is determined from returned observations, not the request endpoint year. Downloads are not interpolated or extrapolated. UNIDO dataset IDs are discovered on each refresh, rather than hard-coded.

## 1. Medium- and high-technology export percentage

- Provider: **World Bank WDI**, underlying source **UNIDO Competitive Industrial Performance (CIP)**.
- Indicator: **TX.MNF.TECH.ZS.UN**, *Medium and high-tech exports (% manufactured exports)*.
- Definition in the archived indicator metadata: share of medium- and high-tech manufactured exports in **total manufactured exports**. It is not a percentage of GDP, all merchandise exports, domestic value added, or the high-tech-only WDI measure.
- [Indicator metadata](https://api.worldbank.org/v2/indicator/TX.MNF.TECH.ZS.UN?source=2&format=json).
- `mht_exports_annual.csv`: all audited economies × 2000–2025, preserving source nulls, flags, footnotes, and missing/not-returned distinctions. WDI regional/income aggregates are excluded using its country catalog.
- `rd_income_exports_annual.csv`: same-country, **same-year** joins to the existing R&D and nominal/PPP income history. OECD, WDI, Eustat and the reviewed ONS R&D intensity series are separate columns, allowing explicit source selection. Original flags and notes accompany each R&D/income series. No carry-forward income or exports.
- `rd_income_exports_snapshot.csv`: existing nominal cross-section plus each 2020–2024 export share, the available-year arithmetic mean and its observation count, and latest export share **with its year**. The mean is a derived unweighted average of annual percentages, not the share of pooled five-year exports. Missing years are not zeros. Original cross-section R&D and income columns are retained verbatim.

## 2. Value added at ISIC Rev.4 two-digit division level

The sources are retained separately. A country can have overlapping observations from several sources; they are not independent data points or automatically interchangeable. The scope of the downloaded measures is:

| Source ID | Official source and selection | Coverage and interpretation |
|---|---|---|
| `OECD_NA` | OECD annual national accounts, `OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE6,2.0`; annual, total institutional sector, transaction `B1G`, domestic currency `XDC`, current prices `V`, untransformed `N` | Wider economy. Available activity detail differs substantially by country/year. Both original broad aggregates and division-level entries are returned. |
| `OECD_STAN` | OECD STAN 2025 edition, `OECD.STI.PIE,DSD_STAN@DF_STAN_2025,1.0`; annual, `B1G`, `V`, `XDC` | Wider economy, with national accounts as a principal input and additional estimates. Preserve `OBS_STATUS`, including estimated (`E`) observations. This is not independent confirmation of OECD national accounts. |
| `UNIDO_INDSTAT` | [UNIDO INDSTAT Rev.4](https://stat.unido.org/portal/dataset/getDataset/INDSTAT/4), variable `20` (Value added), all catalog countries and genuine two-character numeric activity codes | Industrial statistics: mining, manufacturing, electricity/gas and water/waste, sections **B–E**. Establishment survey coverage and valuation can differ from whole-economy national accounts. It does not supply agriculture, construction or services. |

### Activity detail and combinations

The archived OECD structures explicitly identify the activity codelist as **ISIC Rev.4** (`CL_ACTIVITY_ISIC4`). Single codes such as `C20` map to division `20`. Section codes **D, L, O, P and U** each contain exactly one division (35, 68, 84, 85 and 99); their mapping is marked `single_division_section_equivalent`, and the code verifies that the section and division descriptions agree in the archived codelist. These equivalences do not split a multi-division aggregate.

All other broad sections, combinations such as `C10T12` or `J62_63`, and finer-than-division activities remain in `gva_other_activities.csv`. They are not allocated to constituent divisions. **Do not sum all activities in that file:** parent/child categories overlap.

UNIDO sometimes assigns a nominal two-digit activity code to a combined series. The response fields `c` and `cn` identify the combination and its description; e.g. an activity `11` with `cn = "11 includes 12"` is **not** a division-11-only observation. Every record with either combination field populated is excluded from the single-division file and preserved in `gva_other_activities.csv`.

A single-division code is not a guarantee of complete economic coverage. For example, UNIDO observation notes specify exclusions or partial coverage within divisions. Read the associated country, year, activity, variable and observation notes in `gva_metadata.csv` before comparative analysis. No note-driven adjustments or synthetic allocations are made.

### Units, currencies, prices and valuation

- `value_reported` retains the source number. For OECD, `unit_multiplier` is the SDMX power of ten; `value_national_currency = value_reported × 10^unit_multiplier` is a **derived scaling**, not a currency conversion. This vintage reports millions (`6`).
- OECD national accounts supplies a per-observation `CURRENCY` code, retained as `currency_code`. The selected STAN response does **not** supply this field; it remains blank. `XDC` identifies domestic currency but does not resolve a historical currency code.
- UNIDO `v` is national-currency units, and `u` is the provider's current-USD amount. Both are retained; `value_usd_provider` is not our conversion. The portal's currency selector uses `u` for USD and `v` for national currency; its denomination selector divides these unit amounts by 1,000/1,000,000/1,000,000,000 for display. Checked against the public frontend on 11 November 2026: [data browser](https://stat.unido.org/data/table?dataset=indstat&revision=4), `data_browser_react/js/dist/main.js` (`we` display function).
- UNIDO's [database description](https://stat.unido.org/data/database-descriptions), section *INDSTAT Revision 4*, states that monetary data are current-price national currency and USD, using period-average exchange rates from the IMF and other sources. Its displayed historical coverage text is older than the current API release; the actual downloaded coverage audit is authoritative for this build.
- The UNIDO country catalog usually omits currency names and contains a few labels that are insufficient to establish historical units. `currency_label_provider` preserves these raw labels, but `currency_code` remains unresolved. We do not infer currencies from country names or silently reuse current currencies for earlier years.
- All selected amounts are **current prices**. They are not constant-price growth measures and are not PPP-adjusted.
- OECD `B1G` is gross value added; country-specific valuation is not resolved in the selected CSV attributes. It is explicitly left for national-accounts metadata review. UNIDO valuation notes (e.g. factor values, basic values, producers' values) are retained. The Indonesia 2020–2022 sample is labelled **value added at factor values**, with survey coverage notes. UNIDO is therefore presented as industrial **value added**, not silently treated as a uniformly basic-price national-accounts GVA panel.

### Missing values and metadata

- Missing API values remain blank. Unreturned country/year/division cells are not inserted as zeros.
- UNIDO returns some numeric zeros, which its own UI displays as an em dash. These are retained as numeric zero with `value_status = provider_zero_displayed_as_dash`, rather than asserting that they are true economic zeros. The coverage audit includes separate numeric and nonzero division counts.
- Negative value added, if returned, is retained. Non-finite numbers and duplicated observation keys fail the build.
- OECD status/confidentiality/estimation attributes are preserved. The complete raw row also remains available through `source_file` and `raw_record` (one-based index among CSV data rows, excluding the header, or the UNIDO JSON `data` array).
- `gva_metadata.csv` holds UNIDO country/variable/year/activity notes and observation notes. Join by source + ISO3; additionally use year, activity, or `raw_record` according to `level`. For observation-level metadata, `key` is the original response record index. `gva_definitions.csv` contains relevant OECD codelist descriptions.

## Coverage and downloads

- `gva_isic2.csv`: separate-source single-division observations, including explicit one-division section equivalences, missing returned records, and preserved flags. Codes have leading zeros: import division columns as text.
- `gva_other_activities.csv`: retained aggregates, finer activities and UNIDO combination records. Not a disjoint economic partition.
- `gva_country_year_coverage.csv`: every audited economy × source × requested year, including zero-coverage entries. Counts do not establish full coverage of all divisions or establishment sizes.
- `industry_country_coverage.csv`: latest export share/year and latest division-availability year/count for each GVA source. Latest means the latest year with **any** numeric division data; completeness can decrease in that year.
- `industry_exports_gva.xlsx`: companion workbook containing these normalized data, joins, definitions, notes and coverage audits.
- `industry.html`: export lookup and source-specific latest-available detailed value-added tables. Full annual data are available as CSV/Excel.
- `industry_source_inventory.csv` and `industry_source_manifest.json`: exact URLs, POST request bodies, retrieval timestamps and response SHA-256 hashes. Original responses are in the research ZIP under `data/industry_raw/`.

No universal worldwide two-digit, whole-economy GVA coverage is claimed. UNdata broad-sector tables and Eurostat's mixed-detail NACE Rev.2 A64 data were also investigated; they are not relabelled as a complete ISIC two-digit panel. Basque Country has an explicit missing-coverage entry in this supplement; Spain's national values are not assigned to it.
