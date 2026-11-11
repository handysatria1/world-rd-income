# Industry R&D combined with the sector economy

Data assembly and analysis: **Handy Satria**. [Interactive chart maker](https://handysatria1.github.io/world-rd-income/rd-industry.html).

## Scope and source requests

Industry R&D is **business enterprise expenditure on R&D (BERD)**, classified by the **main activity of the performer**. It is not total national R&D (GERD), R&D funding by industry, or R&D benefiting each industry. For example, specialist R&D businesses in M72 belong to knowledge-intensive services even when their research benefits manufacturing.

- OECD RDS: `OECD.STI.STP:DSD_RDS_BERD@DF_BERD_INDU(1.0)`, annual, measure `B`, performer `BES`, total funding and costs, size `_Z`, criteria `MA`, unit `XDC`, current prices `V`. The exact request and structure/codelists are in `data/rd_industry_raw/manifest.json`; the response carries ISO currency codes, million-unit multipliers and all three observation and auxiliary flag fields plus confidentiality status. The downloader requests XDC+USD, but this archived response contains XDC only; changed dimensions stop the builder for review.
- Eustat: [PxWeb table `PX_043201_cid_e05_19t.px`](https://www.eustat.eus/bankupx/api/v1/en/DB/PX_043201_cid_e05_19t.px), nature `10` (total expenditure), native activity branches, thousand current EUR. This is **companies + private non-profit institutions (PNPI)**. The metadata, selected JSON-stat response and PC-Axis table are archived. Its 20 branch codes include total. Selected branches now supply **partial** group amounts; mixed branches remain unallocated. See the native mapping below.
- Singapore: A*STAR [National Survey of RIE 2023 and official Excel appendix](https://www.a-star.edu.sg/news/national-survey-of-rie), `Table 3.1!J5:J19` (industry expenditure, 2023), and `Table 5.1!A14:A37,I14:I37` (annual private-sector totals, 2000–2023). Units are million SGD. The report defines private sector as business enterprises excluding higher-learning institutions (section 7.4.1, p. 13); expenditure is intramural (7.3.1, p. 12), currency SGD (7.3.4, p. 13), industry classification SSIC2020 (7.4.2, p. 13), and **S&T R&D excludes social sciences and humanities** (7.1.1, p. 11). The survey page, official workbook, report and explanatory booklet are archived. RIE fills total-only gaps after the OECD series and supplies a coherent 2023 native industry block; OECD detail through 2013 remains selected. The two sources are not added together.
- Currency conversion: WDI `PA.NUS.FCRF`, annual official local-currency units per US dollar. Metadata and all returned source observations are archived.
- Exact same-year economic inputs: the validated [GVA supplement](BROAD_SECTORS.md) and [employment, productivity and goods-export supplement](SECTOR_ECONOMY.md). GERD amounts, source-specific GERD/GDP and nominal/PPP income come from the existing annual [R&D/income database](README.md).

No ANBERD estimates are used. Its different coverage and estimated observations are not substituted into the selected RDS series. WDI/UIS nominal GERD estimates reuse underlying R&D intensity and GDP data and are not independent measurements.

## Six-group classification

| Group | ISIC Rev.4 scope |
|---|---|
| MHT — medium/high-tech manufacturing | C20, C21, C26–C30 |
| LMT — low/medium-tech manufacturing | C10–C19, C22–C25, C31–C33 |
| KIS — knowledge-intensive services | J, K, M, P |
| LIS — labour-intensive services | G, H, I, L, N, O, Q, R, S, T |
| UTL — utilities | D, E |
| OTH — other production | A, B, F |

These are the supplied analytical groups, not an assertion that all activities within each group have equal knowledge or technology intensity. A–T are covered; **U is excluded**. The archived OECD ISIC4 codelist supplies 419 genuine four-digit classes. Numeric ranges do not invent nonexistent classes. Parent and child observations overlap and cannot both be summed.

For each economy/year, the mapper chooses non-overlapping class sets wholly inside a group, preferring broad released totals to their components. Reviewed public differences can identify a group or subset: `M_N−N`, `M_N−M`, `O_P−O84`, `O_P−P85`, `C25T30−C25`, manufacturing total minus a complete MHT/LMT counterpart, `GTN−(J+K+M)`, and `_T−C−D_E−GTU` for A/B/F. Already complete group sums are retained; both manufacturing groups are never replaced with complementary residuals. Differences are disabled for blocks carrying `S2` or `V2` non-additivity flags, and negative differences are not selected. Each selected expression has a signed class vector consisting only of zeroes and ones, with no cross-group overlap.

`STU`, `OTU` and `GTU` contain U. Their values cannot be assigned wholesale to LIS. A published zero for an aggregate is not used to impute its individual cells. The class crosswalk and every selected signed expression, source row locator, covered class and missing class are downloadable.

### Singapore and Basque native-branch supplement

The following are **analyst-reviewed containments based on the published industry labels**, not official code-level concordances. They identify partial contributions only. Exact ISIC class coverage cannot be reconstructed from these aggregates: `group_complete` is false, covered/missing class lists are blank (unresolved, not zero coverage), and `class_coverage_basis` records this distinction. These rows cannot generate whole-group R&D/GVA or per-worker ratios. The original-branch table and CSV expose every native amount, including unresolved categories, parents and totals.

| Source | Partial allocation | Selected original branches |
|---|---|---|
| Singapore 2023 | MHT | Electronics (`Table 3.1!J9`) |
| Singapore 2023 | LMT | General manufacturing (`J12`) |
| Singapore 2023 | KIS | R&D services + information/communications (`J14 + J16`) |
| Singapore 2023 | LIS | Wholesale/retail trade (`J17`) |
| Eustat, 2003–2024 | MHT | Machine tools, domestic appliances, other machinery, electrical material, electronic material, transport material (codes `140,160,180,200,220,260`) |
| Eustat, 2003–2024 | LMT | Rubber/plastic, non-metal industry, metallurgy, metal articles (`060,080,100,120`) |
| Eustat, 2003–2024 | KIS | Computing and R&D activities (`340,360`) |
| Eustat, 2003–2024 | OTH | Construction (`320`) |

Singapore uses EDB manufacturing clusters (report section 8.4.5, p. 18). Electronics is treated as an electronics-manufacturing contribution to MHT; general manufacturing as a residual low/medium-manufacturing contribution to LMT. **These label-based interpretations remain subject to a finer SSIC cluster concordance**; they do not establish complete C26 or LMT coverage. Biomedical can include medical supplies (C325, LMT), chemicals can include refining (C19, LMT), precision engineering can include components across manufacturing divisions, and transport engineering can include repair (C33, LMT). Financial/other business and residual services can span KIS/LIS. The primary/construction label does not document the utilities boundary. These unresolved clusters are retained without allocation, not assigned by their apparent technology intensity.

Eustat's [branch definition](https://en.eustat.eus/documentos/opt_1/tema_312/elem_25882/definicion.html) says company main activity and CNAE09, but lists no actual branch codes/concordance and also retains a CNAE93 reference. We therefore use only clear named branches and make no exact-class completeness claim. Chemistry/refining (`040`), agriculture/mining/energy (`020`), precision material (`240`), residual manufacturing (`280`), other business (`380`) and other services (`400`) remain unallocated. [Methodology](https://en.eustat.eus/document/datos/fm_043201_i.html) states a homogeneous series from 2003; pre-2003 source values are visible but not mapped. The alternative [high-technology definition](https://en.eustat.eus/documentos/elem_27063/definicion.html) includes weapons C25.4 and medical supplies C32.5 but excludes shipbuilding C30.1 from high/medium-high: simply summing its technology bands would **not** reproduce this project's MHT/LMT definitions.

The user-supplied workbook was checked against the official appendix: all **132** checked cells match (`Table 3.1`, A/J rows 5–19; `Table 5.1`, A/H/I rows 4–37). Supplied-file SHA-256: `13261bbad0bd5b1474abeabbf81f8ebd993e86c11daee85887f2a88c08f8ba3e`. The archive uses the official download. The supplied copy's repeated industry block (rows 25–41), extra economic sheets and added calculations are not source R&D observations. Only original expenditure cells are read; sales revenue is not GVA. Industry values from 2023 never fill another year.

Source conventions remain relevant: Singapore survey reporting can use calendar or fiscal years (8.3.1, p. 17), and source imputation is described in 8.4.6 (pp. 18–19); the appendix provides no cell-specific status flags. No additional project imputation is performed. Empty flags do not imply that the source used none.

## Missingness, flags and allocation audit

- Confidential/restricted, included-elsewhere and missing source observations are unavailable. Genuine reported zeroes are preserved. No confidential source cells are filled in; public aggregate differences produce labelled derived group values.
- `W` / `O2` observations include unspecified other categories and are excluded from group aggregation. Breaks, estimates, provisional observations, definition differences and auxiliary flags are retained. Structural completeness means that the full requested class set is identified; it does not eliminate survey coverage differences, revisions or measurement uncertainty.
- **Assigned R&D** can be only part of a sector. `group_complete`, `group_coverage`, covered/missing classes and source terms identify the distinction. Partial assigned amounts are hatched in charts; shares use the reported industry-R&D total, not the mapped subset as denominator.
- **Unallocated/reconciliation = reported total − sum of all assigned groups.** This includes unsplittable categories, unavailable detail, U and discrepancies among source totals. It is not a seventh economic sector and is not “Other production”. A small remainder does not establish complete classification.
- Negative remainders are preserved, including rounding-sized cases. Stacks, R&D/GVA and R&D/worker ratios for those economy-years are suppressed rather than rescaled or clipped. Source-derived amounts remain in the downloads. The audit retains an arithmetic rounding bound; it is not a statistical error estimate.

The supplement retains 44,816 OECD cells, 500 Basque native cells (2000–2024), and 39 Singapore workbook cells (15 industry-table values plus 24 annual totals). Singapore 2022 now has a reported total of **SGD 8,130.09 million**, with its industry split unavailable. Singapore 2023 has **SGD 8,955.99 million** total and partial MHT/LMT/KIS/LIS allocations. RIE totals also fill 2000–2009. The default example selects **latest usable years**, labelled separately, so the composition view exposes Singapore 2023 alongside the latest available years for other economies. Fixed-year selection remains available and never substitutes a nearby year. Basque selected branches fill partial MHT/LMT/KIS/OTH values through 2024. The picker includes economies with economic/context observations even without industry R&D. The 2000–2025 window is a request range, not an availability claim. Recent Chinese detail primarily identifies manufacturing and mining. No complete LIS class set is identified in this archive. See generated coverage and validation files for current counts after refresh.

## Units and exact joins

`amount_local = reported value × 10^unit_multiplier`; `amount_USD = amount_local / same-year currency-per-USD`.

The RDS currency attribute determines conversion. USD is identity; EUR uses Spain’s EUR/USD series even where an OECD historical observation already reports EUR before that country adopted the euro. Other currencies must match the country’s reviewed code. Unverified TWD conversions and pre-2005 RON/TRY observations remain unavailable in USD. Local amounts and shares can remain usable without USD. No interpolation, extrapolation, nearby-year substitution, PPP conversion or deflation is performed.

For **complete** industry groups only, with exact economy/year/group matches and positive denominators:

- `R&D intensity = group BERD USD / group GVA USD × 100`.
- `R&D per worker = group BERD USD / group employed persons`.
- The joined productivity measure remains `current basic-price GVA USD / employed persons / 1,000`.

GVA and employment cover the whole economic industry, whereas the numerator covers business performers. These are industry-level measures, not company-only GVA intensities or R&D per researcher. R&D surveys and national accounts can assign multi-activity firms differently. Nominal USD comparisons reflect market exchange rates, price levels, source definitions and vintages; they are not PPP or hourly productivity comparisons. The intensity/productivity scatter shares GVA between its two formulas and supports no causal inference.

Goods exports join only MHT and LMT. They classify products by associated industry, not the main activity of exporting firms. LMT exports exclude C33 repair/installation services while R&D, GVA and employment include C33. Export shares use total goods exports, R&D shares use reported BERD (Basque: companies + PNPI), and GVA/employment shares use their six-group totals. Export residuals are not assigned to OTH or service groups. No R&D/export intensity is calculated.

National GERD stays separate: OECD, WDI/UIS and Eustat amounts and intensity retain their original reported/derived status and input-row links. OECD/WDI USD GERD are derived using GERD/GDP times same-year WDI GDP; they need not reconcile exactly to currency-converted RDS BERD because of scope, vintages and denominator differences. Direct UIS and ONS alternatives remain in the context CSV. Basque Country overlaps Spain and should not be added to it.

## Files and reproduction

- `rd_industry_annual.csv`: six rows per economy/year, assigned values, completeness, flags, exact expressions, classes, currency and FX locators.
- `rd_economy_joined.csv`: these R&D rows plus exact GVA, persons, productivity, goods exports, R&D ratios, national GERD and income.
- `rd_economy_context.csv`: source-specific GERD, R&D intensity, income, industry total and economic totals, with source-table/row links.
- `rd_industry_components.csv`: every original normalized industry cell, including unavailable, Basque native and Singapore workbook cells. `source_sheet`/`source_cell` locate Excel observations; JSON/CSV inputs use `raw_record`.
- `rd_industry_coverage.csv`, `rd_industry_mapping.csv`, `rd_industry_fx.csv`: allocation/reconciliation, class-set and currency audits.
- `rd_industry_economy.xlsx`: the seven CSV tables as sheets, with the same values and missingness.
- `rd_industry_explorer.json`: embedded browser data; `rd_industry_validation.json` and `rd_industry_verification.json`: input/output hashes and verification counts.

After building the underlying R&D/income, GVA and sector-economy inputs:

```sh
python rd_industry_sources.py          # reuse verified archive; --refresh for a new vintage
python -m unittest test_rd_industry.py
python rd_industry.py
python verify_rd_industry.py
node test_rd_industry.js --built
python build_site.py --destination ../../_site   # empty destination
python verify_broad_site.py --site ../../_site
```

The independent verifier re-reads original CSV, JSON-stat and Excel cells; reconstructs signed OECD class expressions and the selected disjoint native branches; checks that native assignments remain partial; matches economic CSV rows by exact keys; checks every ratio and FX factor; and compares all workbook/embedded values. Unit tests cover overlap, confidential/included-elsewhere handling, observed zeroes, manufacturing complements, negative differences and non-additivity; browser-core tests cover fixed/latest/common years, Singapore's total-only years, 2023 industry detail and unavailable ratios. All archived responses retain exact request URLs/bodies, retrieval metadata and SHA-256 hashes in the research ZIP. Build input hashes identify the economic and national-context vintages used.
