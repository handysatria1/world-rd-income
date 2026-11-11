# Government industry source review

Compiled by **Handy Satria**. Reviewed 11 November 2026. Observation years, release dates and retrieval timestamps are distinct.

## What the latest comparison means

“Latest available” selects **GVA and business R&D years independently**, within each economy and selected industry filter. Both years appear in the chart and CSV. This fixes Singapore's former fallback to 2013: its assigned RIE industry R&D now uses **2023**, alongside the latest assignable GVA year. Exact years and latest common year retain same-year selection. Ratios always use complete, same-year inputs; independently selected display rows carry no cross-year ratios.

The **6-sector and 16-group paired comparison views** use the same reviewed source additions. The older specialist six-sector employment, export and composition views retain their original source-specific datasets and dates. All-country historical coverage remains available.

## Sources checked

| Economy | Newest detailed observations verified here | Use and boundary |
|---|---|---|
| Singapore | SingStat M354861 manufacturing establishment value added **2025**, preliminary; M015731 national accounts **2025**; A*STAR RIE industry R&D **2023** | Original SSIC divisions / RIE clusters are shown in **Official published industries**. RIE chemicals and electronics remain partial assignments in the 16-group chart. No unverified cluster split. |
| UK | ONS current-price low-level GVA **2025**, 2026 Q2 workbook; ONS BERD performer industry **2024** | Division-level UK SIC 2007 aggregates are used in both comparison classifications. BERD comes from **sheet 3**, not product-group sheet 2. GVA 2025 uses short-term output proxies. |
| USA | BEA value added **2025**, published 30 September 2026; NCSES BERD **2024**, Table 65 | Native NAICS industries are shown with original labels. Table 65 adjusts domestic R&D for international comparability, removing depreciation and adding R&D capital. It covers nonfarm for-profit companies with ≥10 employees, not all businesses. Industry follows the largest domestic R&D business segment, with the sampling classification as fallback. No exact NAICS-to-ISIC equivalence is asserted. |
| Korea | MSIT R&D Survey **2024**, Table 18, printed p.38; BOK **2025** preliminary accounts release | MSIT native industries are shown without splitting mixed medical/precision/optical categories. Detailed **2025 GVA in the aligned charts is OECD STAN**, not the direct BOK release workbook. STAN source flags and estimation methods remain visible. |
| China | NBS industry R&D **2025**, communiqué Appendix Table 1; detailed NBS input-output value added **2023** | R&D covers industrial enterprises above designated size (main-business revenue ≥CNY20 million). This is not all-business BERD. Input-output product-sector value added uses producers' prices and is not harmonised ISIC GVA. Both are available under their native definitions. |
| Basque Country | Eustat A38 GVA **2025**, provisional; Eustat industry R&D **2024** | Existing verified regional observations retained. R&D covers companies + PNPI. INE's definitive 2024 release was checked: national industry distributions cannot fill regional industry gaps. |

Direct source URLs, source cells, retrieval times, SHA-256 hashes, original units, flags and currency conversions appear in `government_industry_observations.csv`. `government_industry_source_manifest.json` contains the new direct-government archive. Existing RIE, Eustat, STAN, ONS BERD and NBS input-output archives retain their original manifests in the research ZIP.

Official catalogues: [SingStat](https://tablebuilder.singstat.gov.sg/), [A*STAR RIE](https://www.a-star.edu.sg/news/national-survey-of-rie), [ONS GVA](https://www.ons.gov.uk/economy/grossdomesticproductgdp/datasets/ukgdpolowlevelaggregates/current), [BEA](https://apps.bea.gov/industry/Release/XLS/GDPxInd/ValueAdded.xlsx), [NCSES](https://ncses.nsf.gov/surveys/business-enterprise-research-development/2024), [MSIT](https://www.msit.go.kr/bbs/view.do?sCode=user&bbsSeqNo=79&nttSeqNo=3173719), [BOK](https://www.bok.or.kr/eng/bbs/E0000634/view.do?nttId=10098383&menuNo=400069), [NBS](https://www.stats.gov.cn/sj/zxfb/202610/t20261016_1965512.html), [INE](https://www.ine.es/dyngs/Prensa/IMASD2024.htm).

## Why source-native data remain separate

- Singapore 2025 manufacturing establishment value added is **SGD132,813.8 million**, whereas national-accounts manufacturing GVA is **SGD137,611.7 million**. They cannot share a denominator silently. The establishment table has no separate division 33 row; a verified repair-activity bridge is unavailable. Its 2025 native figures are therefore not presented as exact ISIC groups.
- SingStat **M355181** also provides manufacturing-cluster value added through 2025. It is available as a separate source choice, including Electronics, Chemicals, Biomedical Manufacturing, Precision Engineering, Transport Engineering and General Manufacturing. These cluster labels are not relabelled as ISIC groups.
- RIE Table 3.1 gives six manufacturing clusters, totalling **SGD4,338.59 million** in 2023. Biomedical, precision, transport engineering and general manufacturing cannot be assigned wholesale to the five requested groups without a verified classification bridge. The complete six-cluster figures remain visible and downloadable.
- The US and Korean national categories differ from ISIC; an apparently similar label does not prove identical class coverage. Native tables retain overlapping parent/child rows, which must not be added indiscriminately.
- ONS `[c]` is confidential. `[x]` means nil, unavailable or too small to display. Both remain null; neither becomes zero or an inferred confidential residual. NCSES original flags, including `i`, are retained verbatim; this extraction does not reinterpret an undecoded flag as full reliability.
- Group 16 is **R–T only**. ONS's combined 94–99 branch crosses U and is not assigned to group 16. A broad total is never used to manufacture a missing U value.
- OECD STAN `OBS_STATUS=E; EST_METHOD=POST` means the observation is marked estimated with method POST. It is not relabelled as a directly observed BOK statistic. `OBS_STATUS=A` is retained verbatim and does not establish absence of all modelling.

## Reproduction and checks

After the original datasets are built, run:

```text
python government_industry_sources.py
python government_industry.py
python research_groups.py
python verify_government_industry.py
node test_research_groups.js --built
python build_site.py --destination <empty-directory>
python verify_dashboard.py --site <directory>
```

The extractor reads downloaded workbook cells, SingStat JSON, NBS HTML tables and structured MSIT HWPX table cells. It hashes source bytes and preserves locators. The verifier checks source-cell values, exact-year FX, source scopes, suppression, RIE reconciliation, UK/Korean manufacturing sums and both group partitions. Reviewed snapshot spot checks intentionally stop when a provider revises the checked cells, requiring review.

The two largest standalone national R&D CSV downloads are now losslessly compressed as `.csv.gz` to keep the website within GitHub Pages' size limit. The full research ZIP retains the original CSV files.

No missing observations are interpolated, carried forward or converted to zero. The user's supplied screenshot's manufacturing-group figures remain independently unvalidated.
