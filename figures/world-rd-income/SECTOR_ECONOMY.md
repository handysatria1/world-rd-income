# Employment, productivity and goods-export charts

Data assembly and chart author: **Handy Satria**.

The `sector-economy.html` chart maker supplies five layouts: employment stacks,
paired GVA/employment share stacks, sector-panel GVA per person, economy-panel
GVA per person, and goods-export composition. Examples use China, US, UK, Korea,
Singapore and Basque Country; the order and selection are editable (up to 16).
Employment/productivity examples use 2022; exports use 2024. Source values are
not fitted to reference images. Latest-per-economy, latest-common and explicit
year modes are available. An explicit year never falls back to another year.

## Employment and the six-sector denominator

Countries use **OECD Trade in Employment (TiM), 2025 edition**, measure `EMPN`,
unit `PS`, multiplier 3 (thousand persons), annual frequency and world counterpart.
The archived OECD dataset page states that employment by industry is consistent
with TiVA output and value added. These are harmonised estimates; the page's
older descriptive country count is not used to infer current data coverage.

Basque Country uses **Eustat A38 national accounts employment**, table
`PX_170112_cpib_pib_a_08.px`, territory `_T`, employment type `50`
(`Employed persons. TOTAL`), data type `10`. Counts are persons, not jobs or
full-time equivalents. Eustat's original PC-Axis notes specify base 2022 and that
code 08 includes both chemicals and pharmaceuticals through 2020; code 07 is
therefore not counted separately in those years.

Mappings are the same as [the GVA classification](BROAD_SECTORS.md):

| Group | Divisions / sections |
|---|---|
| MHT: Medium/high-tech manufacturing | 20, 21, 26–30 |
| LMT: Low/medium-tech manufacturing | 10–19, 22–25, 31–33 |
| KIS: Knowledge-intensive services | J, K, M, P |
| LIS: Labour-intensive services | G, H, I, L, N, O, Q, R, S, T |
| UTL: Utilities | D, E |
| OTH: Other production | A, B, F |

The denominator is the sum of these six disjoint groups, covering A–T. Grouped
employment is reconciled to reported total employment. Eustat U is subtracted
when reported; when U is unreported, the reported total is compared directly
with the grouped sum, without assigning a zero to the missing U cell. This is
an aggregate reconciliation, not evidence that an unreported cell is zero.
Both the unreported cell and the residual are retained in the downloads.

Economy selection uses the existing country/region catalog. Provider aggregates
and unmatched codes (including Montserrat, `MSR`) are listed explicitly in the
validation report rather than presented as harmonised country observations.

OECD employment cells are published to 0.1 thousand persons. The reconciliation
tolerance is 50 persons times the number of summed source cells plus the total
cell; Eustat's integer-person tolerance is 20 persons. Grouped totals are used
in shares and ratios, so they can differ slightly from the separately reported
total. For example, 2022 grouped US employment is 167,639,600 versus the reported
167,639,800; Korea is 28,073,100 versus 28,073,000. No components are rescaled.
Missing required components suppress a complete chart bar. A reported zero is
retained as zero.

## GVA/employment comparisons and productivity

GVA comes from the separately validated `broad_sector_annual.csv`: OECD TiVA 2025
`VALU` for countries and Eustat current-price A38 accounts for Basque Country.
Shares compare the **same economy, year and sector grouping**. Productivity is:

`current USD GVA / employed persons / 1,000`

and is labelled **current US$ thousand per employed person**. Only strictly
positive employment denominators and valid same-year GVA/employment coverage
produce a ratio. Economy totals are `sum(GVA) / sum(persons)`, not an unweighted
mean of sector ratios. There is no temporal interpolation or nearest-year join.

Sector panels show the **unweighted median of the available selected economies**
for that sector. Missing economies are omitted from the median, not replaced by
zero; an empty set has no median. With latest-per-economy selection the median
can mix years, which are displayed. Economy panels show the economy-total ratio
as a dashed reference. Panels use individual scales to retain legibility.

These are nominal basic-price ratios, **not PPP-adjusted productivity or output
per hour**. Differences reflect exchange rates, prices, working hours and sector
composition as well as real productivity. Imputed rents in real estate (within
LIS) and capital intensity can strongly affect sector ratios. The grouping is
user supplied; its service labels are not an official technology taxonomy.

## Goods exports: scope and mapping

Countries use **OECD Bilateral Trade in Goods by End-use (BTiGE)**:
`A.<reporter>.X.TOTAL.<product>.W.USD`, multiplier 3 (current USD thousands).
`X` is the exports flow, not the separate domestic-products or re-export flow.
The archived `oecd_btige_readme.xlsx`, **ReadMe** sheet, describes primarily
UN Comtrade annual data with national-source and OECD estimate supplements,
mapped from Harmonised System products to CPA 2.1 and end use. Its **CPA products**
sheet lists the available product taxonomy and **FromHS2022-ToCPA-ToENDUSE**
contains the correspondence. These are gross goods trade values, not domestic
value added embodied in exports or exports of services.

- MHT = CPA divisions **20, 21, 26–30**.
- LMT = CPA divisions **10–19, 22–25, 31–32**.
- Other/unallocated = reported total goods exports minus both manufacturing groups.

CPA C33 repair/installation services is outside BTiGE's listed manufacturing
goods-product scope; its absence is **not** coded as an observed zero. Division
totals are also checked against reported CPA manufacturing `C`. A discrepancy
above `max(US$10, goods total × 1e-8)` suppresses the chart bar and remains visible
in the coverage audit. Material discrepancies exist for some historical reporter
years; totals are not silently repaired. Negative residuals and nonpositive
totals are also excluded from complete charts.

Basque Country uses Eustat **foreign goods trade** (exports beyond Spain, not
interregional sales to the rest of Spain). Selections are flow `10`, territory
`00`, area `100`, unit `10` (thousand EUR):

- `PX_143101_cece_ar242.px`: native technology groups A (high), B (high-intermediate),
  C (low-intermediate), D (low), E (zero technology), `*` (total).
- `PX_143101_cece_ar241.px`: technology sectors defining those native groups.
- `PX_143101_cece_ar17.px`: NACE-09 three-digit activities.

The native taxonomy puts weapons (254) and medical/dental instruments (325) in
high-intermediate, and shipbuilding (301) in low-intermediate. To match the
requested division-based classification:

```
MHT = A + B − NACE 254 − NACE 325 + NACE 301
LMT = C + D + NACE 254 + NACE 325 − NACE 301
Other/unallocated = reported total − MHT − LMT
```

This uses reported aggregates and three observed adjustment cells; it does not
sum a sparse three-digit table with invented zeros. Missing adjustment cells
would suppress the groups. Native A is checked against technology sectors 01–03,
B against 04–08, C against 09–14, D against 15–18, E against 99 wherever the
sector components are complete. A and B must both have complete checks; the
maximum available discrepancy must be at most EUR 5,000, reflecting independently
rounded thousand-EUR cells. C includes unreported sector cells 09 and 14 in the
current archive, so its full component audit is unavailable; its published
aggregate is retained. This partial audit is a remaining limitation.

For 2024, Basque MHT is **EUR 16,663,674 thousand**, LMT **EUR 13,122,484 thousand**,
and the residual **EUR 1,476,196 thousand**, out of the reported **31,262,354 thousand**.
The residual differs by EUR 1 thousand from native group E due to rounding.
Earlier years with a negative residual are suppressed, even if rounding could
explain it. Eustat's archived notes say final data through 2024 and provisional
from 2025; the latter is labelled explicitly.

The other/unallocated category can include nonmanufactured goods and unallocated
products; it must not be interpreted as a clean technology category or compared
with the six-sector “Other production” group. CPA and NACE classify products by
associated activity, not the industry of the exporting firm. Basque foreign
trade and country goods trade also have different geographic boundaries.

## Currency conversion, provenance and missingness

Basque EUR GVA and exports use the same-year Spanish World Bank WDI exchange
rate `PA.NUS.FCRF`, EUR per US dollar: `USD = EUR / rate`. Inputs are preserved in
`data/broad_sector_raw/wb_spain_exchange.json`. Missing exchange rates leave USD
amounts blank; export percentage charts can still use complete local-currency
values. No PPP or constant-price conversion is performed.

The independent `data/sector_economy_raw/manifest.json` records exact URLs, POST
bodies, retrieval timestamps, content types, byte lengths and SHA-256 hashes for
16 responses. `sector_economy_components.csv` preserves source values, units,
multipliers, source flags and 1-based CSV/flattened JSON-stat record numbers.
Absent source status fields mean “no flag supplied”, not a quality endorsement.
Eustat null values with `-` remain missing. Source responses retain complete
metadata and original status arrays.

The workbook contains employment, same-year GVA/productivity inputs, exports,
source cells, coverage/reconciliation and export mapping. Annual rows label sums,
ratios and residuals as derived, retain local currency and conversion inputs, and
link to original source records. GVA raw source cells remain in the companion GVA
workbook and reproducible ZIP. The browser's plotted-data CSV supplies the chosen
years, source labels, flags and medians; complete audit trails are in the full
workbooks and ZIP. R&D–income remains the main dashboard; these are supplements.

## Reproduction

After reproducing and verifying the GVA supplement:

```sh
python sector_economy_sources.py --refresh
python sector_economy.py
python verify_sector_economy.py
node test_sector_economy.js --built
python sector_economy_figures.py
python build_site.py --destination ../../_site
python verify_broad_site.py --site ../../_site
```

Omit `--refresh` to reuse hash-verified archived responses. The site destination
must be empty. All five examples are supplied as PNG, editable SVG and PDF.
The interactive page supports SVG/PNG/plotted CSV and browser print-to-PDF.
Independent verification covers source cells, explicit mappings, currency
conversion, same-year joins, ratios, shares, examples, all workbook rows and
embedded browser values. The weekly pipeline performs the same checks before
publishing, and the source/archive build timestamps are separate from the
R&D–income analysis timestamp.
