# Six-sector gross value added chart

Data assembly and software: **Handy Satria**. [Open the chart maker](https://handysatria1.github.io/world-rd-income/broad-sectors.html).

Choose up to 16 economies, reorder them, select the latest complete year per economy, the latest common complete year, or an explicit year. Switch between 100% stacks and current-US-dollar amounts, edit the title and percentage precision, and download SVG, PNG or the plotted CSV. Print/save as PDF is available through the browser. The full workbook contains annual grouped values, original components, coverage/reconciliation and the classification.

## Supplied classification

This is the user's SIC-based grouping, applied to corresponding ISIC Rev.4 and Eustat CNAE-2009/A38 activities. These broad labels do not establish that each included activity meets another institution's technology/knowledge-intensity definition.

| Group | Sections | Divisions |
|---|---|---|
| Low/medium-tech manufacturing | C | 10–19, 22–25, 31–33 |
| Medium/high-tech manufacturing | C | 20, 21, 26–30 |
| Other production | A, B, F | 01–03, 05–09, 41–43 |
| Knowledge-intensive services | J, K, M, P | 58–66, 69–75, 85 |
| Labour-intensive services | G, H, I, L, N, O, Q, R, S, T | 45–47, 49–53, 55–56, 68, 77–82, 84, 86–88, 90–98 |
| Utilities | D, E | 35–39 |

The groups partition **87 divisions in sections A–T**. Section U/division 99 (extraterritorial organisations) and net taxes on products are excluded. **GVA is not GDP at market prices.** Each percentage is its group's GVA divided by the sum of these six groups, multiplied by 100. Totals above the bars use this same denominator.

## Sources and exact selections

### OECD TiVA 2025 / ICIO

- Dataflow: `OECD.STI.PIE,DSD_TIVA_MAINLV@DF_MAINLV,1.1`; measure `VALU`, domestic industry value added; all economies/activities, counterpart `W`, unit `USD`, frequency `A`.
- [Exact 2000–2025 CSV request](https://sdmx.oecd.org/sti-public/rest/v1/data/OECD.STI.PIE,DSD_TIVA_MAINLV@DF_MAINLV,1.1/VALU...W.USD.A?startPeriod=2000&endPeriod=2025&format=csvfile).
- Units: **current USD millions**, at **basic prices**. Multiply provider values by 1,000,000; sums are derived from reported provider estimates. OECD ICIO tables harmonise and balance national inputs; they need not reproduce a separately downloaded national-accounts vintage.
- The resolved structure/codelists and ICIO 2025 README workbook are archived alongside the CSV. Activity aggregates wholly contained in a group are counted once: for example `C24_25`, `C31T33`, and `D_E`. No mixed group is allocated by estimated shares and no aggregate is added to its components.
- The 11 November 2026 response has 182,160 rows, 80 recognized country/economy areas and 19 provider aggregate codes excluded from the chart. The country series cover 2000–2022. The build records excluded codes explicitly; its country catalog comes from the industry coverage file.

### Eustat Basque Country A38 economic accounts

- Table: `PX_170112_cpib_pib_a_01.px`, [API metadata/data endpoint](https://www.eustat.eus/bankupx/api/v1/en/DB/PX_170112_cpib_pib_a_01.px).
- POST selects Basque Country (`territorio histórico=_T`), level (`tipo de dato=10`) and current thousand EUR (`tipo de medida=10`), with all sectors/years. The exact JSON body is retained in the manifest; the metadata and full PC-Axis response are archived as well.
- Sum the disjoint A38 activities mapped in `broad_sector_classification.csv`; multiply source values by 1,000. Code **50** is reported GVA at basic prices; **60** is net taxes on products; **70** is GDP at market prices. Codes 60/70 are never substituted for GVA.
- The PC-Axis English `NOTEX` specifies **base 2022**, **2025 provisional**, and that **code 08 includes both chemicals (07) and pharmaceuticals (08) during 1995–2020**. The historical sum counts 08 once and omits the missing 07, preserving the combination note. Both activities belong to the same medium/high-tech group. From 2021, 07 and 08 are counted separately.
- Code **38** is section U, outside the grouped denominator. Where reported, it is retained in reconciliation. Its missing value is not recoded as zero; in those cases the provider-total residual is reported and checked against tolerance without an observed U adjustment.
- Basque Country (`ES-PV`) is the Basque Autonomous Community within Spain. It overlaps Spain and is not an independent country comparison for pooled statistical analysis.

### Same-year currency conversion

Current Basque USD = current EUR / **same-year Spanish EUR per USD**, from WDI source 2, indicator `PA.NUS.FCRF` ([exact request](https://api.worldbank.org/v2/country/ESP/indicator/PA.NUS.FCRF?source=2&date=2000:2025&format=json&per_page=100&footnote=y)). This is an annual-average market exchange-rate conversion, not PPP or an inflation adjustment. Original EUR amounts, factor, factor-year record, status and footnote remain in the annual export. Percentages use EUR and therefore do not require FX; USD-mode eligibility does require FX.

## Missingness, reconciliation and interpretation

- Complete coverage requires all selected provider activities in all six groups. Missing cells and absent records remain missing; reported zeros remain zero. Partial group amounts are never presented as a complete percentage stack.
- A complete positive total with nonnegative groups must reconcile with the provider total within `max(50,000 source-currency units, abs(provider total) × 1e-7)`, after removing reported U where available. This is a numerical tolerance, not a statistical uncertainty interval. Residuals and tolerance are exported. An unreconciled total is ineligible for plotting.
- Latest-year mode can mix years. Common-year mode takes the intersection of eligible years for every selected economy. An explicit year never falls back to an earlier year. The selected measure determines eligibility when FX is missing.
- The 11 November 2026 build has **1,866 available economy-years**, plus **240 missing-component economy-years**, across 80 economies and one region. Latest complete example years are 2022 for Korea, Singapore, China, US and UK, and 2025 (provisional) for Basque Country. Their latest common complete year is 2022.
- Dollar amounts reflect economy size, exchange rates and current prices. Shares describe value-added composition, not employment, exports, R&D spending, productivity or causal effects. Cross-source harmonisation and revisions limit precise country/region comparisons.
- Chart labels round independently and may not sum to exactly 100%; the unrounded CSV does. Labels too small to fit are available in the table and hover text. A blank source status does not establish finality. Explicit provisional year notes accompany exports.

## Reproducibility and provenance

`data/broad_sector_raw/manifest.json` is independent of the R&D/income and detailed-industry manifests. It retains seven exact response files, URLs, retrieval dates, request bodies, response sizes and SHA-256 checksums. `source_file` plus the **1-based data-record ordinal** (excluding the CSV header, or flattened JSON-stat value index + 1) locates every component. Annual rows list the exact activities and record ordinals, normalized currency amounts, derived USD values, shares, statuses and notes. The full raw archive is in the research ZIP.

Public exports are `broad_sector_source_manifest.json`, `broad_sector_source_inventory.csv`, `broad_sector_annual.csv`, `broad_sector_components.csv`, `broad_sector_coverage.csv`, `broad_sector_classification.csv`, `broad_sector_gva.xlsx`, the browser JSON, and validation/verification reports. The research ZIP's root `broad-sectors.html` works offline with local companion links.

From `figures/world-rd-income`, after the base and industry builds:

```text
python broad_sector_sources.py --refresh
python broad_sectors.py
python verify_broad_sectors.py
node test_broad_sector.js --built
python broad_sector_figures.py
python build_site.py --destination ../../_site
python verify_broad_site.py --site ../../_site
```

Omit `--refresh` to reuse checksum-verified archived sources. Use an empty site destination. `verify_broad_sectors.py` independently reads provider cells, checks disjoint components, conversion arithmetic, shares, totals and Eustat's historical combination. Selection tests check year intersection, order, explicit missingness and missing FX. The site packager checks report/source/output hashes before copying. The same steps run on the existing weekly schedule.

Suggested citation: Handy Satria (2026), *Worldwide R&D and income explorer, 2000–2025: six-sector GVA chart*. Record the release tag/build timestamp and acknowledge OECD, Eustat and World Bank. This addition has its own build timestamp; the underlying R&D/income analytical snapshot is recorded separately.
