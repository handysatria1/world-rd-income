# GDP per capita: three income-axis options

The snapshot, two-year comparison and national history GDP control offers:

1. Current US$: `NY.GDP.PCAP.CD` (existing series).
2. PPP (current international $): `NY.GDP.PCAP.PP.CD` (existing series).
3. PPP (constant 2021 international $): [`NY.GDP.PCAP.PP.KD`](https://data.worldbank.org/indicator/NY.GDP.PCAP.PP.KD).

The third series is read directly from the official, dated World Bank WDI CSV
archive discovered on its catalog page. It is **not** obtained by applying an
estimated inflation factor to the existing current-price series. The archive
is shared with the innovation pipeline in `data/income_raw/`; its source URL,
retrieval time and SHA-256 checksum are retained. Annual exports preserve the
exact ZIP member, CSV row and year-column locator.

`download_data.py` archives these inputs; `historical_explorer.py` attaches the
observations using `constant_ppp.py` and writes
`data/gdp_per_capita_ppp_constant_2021.csv`. The dashboard publishes this audit
and `constant_ppp_manifest.json`. Archive metadata must explicitly identify
constant **2021** international dollars; a future rebase requires review.

All joins use exact ISO3 and calendar year, retaining gaps. World Bank
aggregates are excluded using the existing country universe. Basque Country
has no observation in this country-level series: Spain's value, its current
PPP proxy and other years are never substituted. The two existing current-price
choices preserve their paired cohort. Constant-price scatterplots require the
constant-price series instead; comparisons require it at both endpoints and
use one paired sample for both fits. Latest/common-year modes use their existing
explicit selection rules with the selected income measure.

Axes, tooltips, history, CSV units, regressions and source captions follow the
selected measure. Only GDP per capita changes: R&D intensity remains a GDP
share and nominal R&D expenditure totals remain current-price totals.

Run `node test_explorer.js`, `node test_source_captions.js` and
`python -m unittest test_constant_ppp.py`. Browser tests should compare each
plotted constant-price value directly with the archived WDI cell, including
missing values, endpoint pairing, latest/common years and history downloads.
