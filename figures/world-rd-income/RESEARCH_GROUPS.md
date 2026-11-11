# Sixteen research groups: GVA, BERD and employment

Data assembly: **Handy Satria**. This is the user's supplied classification, an additional partition alongside the earlier six-group classification.

| ID | Research group | ISIC Rev.4 target |
|---|---|---|
| 01 | Agriculture | A |
| 02 | Mining & quarrying | B |
| 03 | General manufacturing | C10–18, C31–33 |
| 04 | Chemicals & non-metallic | C19–23 |
| 05 | Transport equipment | C29–30 |
| 06 | Computer, electronic & optical | C26 |
| 07 | Electrical, machinery & metals | C24–25, C27–28 |
| 08 | Utilities & waste management | D–E |
| 09 | Construction | F |
| 10 | Trade, transport & hospitality | G–I |
| 11 | Information & communication | J |
| 12 | Finance & insurance | K |
| 13 | Real estate | L |
| 14 | Professional & business support | M–N |
| 15 | Public administration, education & health | O–Q |
| 16 | Other services | R–T |

**Group 16 clarification:** the user confirmed R–T only. The image's overlapping BERD rows O–U, O–P and Q are not summed. An exact O–U − (O/P) − Q − U residual can be used only when all excluded activities are publicly covered. Missing/confidential U is never assumed zero. The 16 groups are disjoint and cover A–T, the same activity universe as the original six groups.

## Reclassification and source selection

GVA and employment are re-summed from the original OECD TiVA/TiM and Eustat A38 components, retaining units, source rows and flags. Eustat A38 code 08 includes chemicals 07 through 2020 and is counted once. The target classification is identical for all three metrics; equivalent source aggregates are allowed (e.g. C29 + C30 and C29_30).

BERD uses the **same selected coherent economy/year source blocks** as the preceding six-group data: OECD RDS by performer main activity, Singapore RIE, or Eustat companies + PNPI. Exact OECD class sets are used to choose disjoint released observations. A parent and its children are never added together. Public aggregate subtraction is allowed only when the excluded class set is fully observed and no non-additivity flag prohibits it. Negative derived candidates are rejected; negative overall remainders invalidate shares and BERD ratios but remain in the audit.

Native labels support **partial** allocations only. Broader new groups resolve some previous cross-boundary labels: Basque chemistry/refining, rubber/plastics and non-metal industry fit 04; metallurgy/metal articles/machinery/electrical fit 07; electronic material 06; transport material 05; construction 09; computer activities 11; R&D/other business services 14. These allocations begin in 2003, consistent with the earlier source review. Singapore chemicals fits 04, electronics 06, R&D 14, information/communications 11 and wholesale/retail trade 10. Mixed biomedical, precision/transport engineering, financial/other services and general manufacturing branches remain unallocated where this partition cannot be established. Singapore general manufacturing is not assumed to equal the newly named group 03. Exact ISIC completeness is not inferred from labels.

## Shares, joins and relation to earlier data

- GVA/employment amounts may be partial sums. Whole-group values/ratios require complete source components.
- GVA/employment shares use the existing **complete, reconciled A–T denominator**. Complete 16-group sums are checked against the earlier six-group totals.
- Assigned BERD shares use **reported industry R&D totals**, which can include U. A share is not the sector's expenditure coverage percentage. Unallocated amounts include unresolved branches, missing/confidential cells, U and discrepancies.
- Ratios require exact economy/year/group matches and complete numerator/denominator coverage: BERD/GVA (%), BERD/person and GVA/person (current USD). Employment is persons, not researchers or FTEs; GVA is current basic-price activity, not turnover. These are descriptive indicators with different institutional scopes.
- Currency conversion reuses the previously verified same-year exchange rates. Missing conversions remain missing. Provider-USD GVA and converted local-currency BERD remain distinguished.
- `research_group_joined.csv` includes national GERD alternatives, GDP/person and total goods exports from `rd_economy_context.csv`, joined by exact economy/year. No new 16-group goods-export allocation is asserted.
- `research_group_bridge.csv` records class-set intersections with the six groups. Groups such as 04/07 cross MHT/LMT and 14/15 cross KIS/LIS. **Amounts cannot be split between classifications using fixed shares**; original source components are required.

## Downloads and verification

### Exploring the comparisons

- **Compare economies**: one panel per selected economy, with paired horizontal GVA and assigned BERD bars. **Compare industries**: one panel per industry, comparing the selected economies. Both rank by GVA, descending; missing GVA ranks last and is never replaced with zero.
- Manufacturing uses groups **03–07**; services uses **10–16**. The all-groups preset retains the full A–T partition. Presets select groups without renormalizing shares. GVA shares use the A–T total; BERD shares use reported industry R&D, including any unallocated activities.
- Amounts use **current US$ billions**, with the same linear scale for GVA and BERD within each panel. Panels have individually labelled scales. Partial allocations remain hatched and do not purport to measure whole-group expenditure.
- Latest/common paired years require at least one selected group with both GVA and BERD observations in that exact economy/year. Other groups can still be missing or partial and remain labelled. Fixed years never fall back to another observation.
- **Compare years** uses one economy from the shared selection and up to three distinct exact years (default 2000, 2010, 2022), displayed chronologically. Its local years replace the shared reporting-year control for this layout. Toggle amounts/shares to compare historical levels or composition.
- Endpoint changes compare the earliest and latest selected years. Share changes are **last minus first, in percentage points**. Amount changes are **100 × (last − first) / first, in percent**. Current-USD changes include inflation and exchange-rate movements; they are not real growth.
- Changes are withheld for missing/partial endpoints, different sources or BERD scopes, or nonpositive amount baselines. Complete endpoints do not establish full time-series comparability: retained source flags and methodology changes still matter. The endpoint CSV includes input values, units, sources, scopes, flags, coverage and source expressions; the joined CSV retains all selected-year observations and national context.
- In the original six-group view, **horizontal GVA/BERD stacks** preserve unallocated R&D explicitly and require same-year GVA and BERD. The original vertical GVA/BERD/employment stacks remain selectable and require all three metrics for latest/common-year selection.

`research_groups.xlsx` contains classification, class bridge, metric-level annual data, joined observations, source terms and allocation audit. `research_group_components.csv` gives signed coefficients, scaled source values, exact source files/locators and flags. For original response hashes, use the preceding GVA/employment/BERD manifests in the research archive. `research_group_validation.json` records all input/output hashes.

Rebuild with `research_groups.py`, verify with `verify_dashboard.py --site <staged-site>` after `build_site.py`. The dashboard loads per-economy research-group data on demand. Latest usable depends on the chosen measure; stacked comparisons require some usable values for all three metrics. Each actual selected year is displayed; fixed years never fall back to another year. A country without data remains visible as missing.
