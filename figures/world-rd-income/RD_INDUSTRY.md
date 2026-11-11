# Industry R&D combined with the sector economy

Data assembly and analysis: **Handy Satria**. [Interactive chart maker](https://handysatria1.github.io/world-rd-income/rd-industry.html).

## Scope and source requests

Industry R&D is **business enterprise expenditure on R&D (BERD)**, classified by the **main activity of the performer**. It is not total national R&D (GERD), R&D funding by industry, or R&D benefiting each industry. For example, specialist R&D businesses in M72 belong to knowledge-intensive services even when their research benefits manufacturing.

- OECD RDS: `OECD.STI.STP:DSD_RDS_BERD@DF_BERD_INDU(1.0)`, annual, measure `B`, performer `BES`, total funding and costs, size `_Z`, criteria `MA`, unit `XDC`, current prices `V`. The exact request and structure/codelists are in `data/rd_industry_raw/manifest.json`; the response carries ISO currency codes, million-unit multipliers and all three observation and auxiliary flag fields plus confidentiality status. The downloader requests XDC+USD, but this archived response contains XDC only; changed dimensions stop the builder for review.
- Eustat: [PxWeb table `PX_043201_cid_e05_19t.px`](https://www.eustat.eus/bankupx/api/v1/en/DB/PX_043201_cid_e05_19t.px), nature `10` (total expenditure), native activity branches, thousand current EUR. This is **companies + private non-profit institutions (PNPI)**. The metadata, selected JSON-stat response and PC-Axis table are archived. Its 20 branch codes include total. The native groups cross the requested boundaries (e.g. chemistry plus petroleum refining, and agriculture/mining plus energy); an exact ISIC4 bridge has not been established. All native values and totals are retained, with six-group allocation unavailable.
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

## Missingness, flags and allocation audit

- Confidential/restricted, included-elsewhere and missing source observations are unavailable. Genuine reported zeroes are preserved. No confidential source cells are filled in; public aggregate differences produce labelled derived group values.
- `W` / `O2` observations include unspecified other categories and are excluded from group aggregation. Breaks, estimates, provisional observations, definition differences and auxiliary flags are retained. Structural completeness means that the full requested class set is identified; it does not eliminate survey coverage differences, revisions or measurement uncertainty.
- **Assigned R&D** can be only part of a sector. `group_complete`, `group_coverage`, covered/missing classes and source terms identify the distinction. Partial assigned amounts are hatched in charts; shares use the reported industry-R&D total, not the mapped subset as denominator.
- **Unallocated/reconciliation = reported total − sum of all assigned groups.** This includes unsplittable categories, unavailable detail, U and discrepancies among source totals. It is not a seventh economic sector and is not “Other production”. A small remainder does not establish complete classification.
- Negative remainders are preserved, including rounding-sized cases. Stacks, R&D/GVA and R&D/worker ratios for those economy-years are suppressed rather than rescaled or clipped. Source-derived amounts remain in the downloads. The audit retains an arithmetic rounding bound; it is not a statistical error estimate.

In the initial 11 November 2026 extension, 44,816 OECD cells across 43 countries and 500 Basque native cells (2000–2024) are retained. The picker includes economies with economic/context observations even without industry R&D. The 2000–2025 window is a request range, not an availability claim. Singapore’s latest numeric industry year is 2013; a 2022 selection therefore has no industry R&D. Recent Chinese detail primarily identifies manufacturing and mining. No complete LIS class set is identified in this archive. See generated coverage and validation files for current counts after refresh.

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
- `rd_industry_components.csv`: every original normalized industry cell, including unavailable and Basque native cells.
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

The independent verifier re-reads original cells and class semantics, reconstructs signed group expressions, checks disjoint coverage and U exclusion, matches economic CSV rows by exact keys, checks every ratio and FX factor, and compares all workbook/embedded values. Unit tests cover overlap, confidential/included-elsewhere handling, observed zeroes, manufacturing complements, negative differences and non-additivity; browser-core tests cover fixed/latest/common years and unavailable ratios. All seven archived responses retain exact request URLs/bodies, retrieval metadata and SHA-256 hashes in the research ZIP. Build input hashes identify the economic and national-context vintages used.
