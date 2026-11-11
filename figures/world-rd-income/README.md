# Worldwide R&D and income explorer, 2000–2025

**[Open the live dashboard](https://handysatria1.github.io/world-rd-income/)** · **[Download archived builds](https://github.com/handysatria1/world-rd-income/releases)**. The source repository contains the code; linked `data/` and `output/` files below are generated locally or included in the downloadable research package.

This extends the previous OECD reconstruction to worldwide available data. Scatterplots show **gross domestic expenditure on R&D (GERD) as a percentage of GDP**. The database also includes nominal R&D amounts and GERD classified by **performer × field**, **performer × funding source**, and **performer × research type**. GDP per capita is available in **current US dollars** and **current international dollars at purchasing power parities (PPP)**. The interactive explorer covers **2000–2025**; its default scatter selection and static scatter figures use **2020–2024 R&D against 2025 income**.

**Snapshot note:** Fixed-year numerical results, coverage counts, examples and captions below describe the initial **10 November 2026** snapshot. Historical responses were added on **11 November 2026**. Every rebuild generates [current static results and captions](data/current_results.md), current CSVs/workbook and dates on the interactive chart. Use those generated outputs after refreshing. [Automatic weekly refresh and GitHub Pages setup](AUTOMATION.md).

## Suggested reference

If you use this dashboard, code, derived datasets or figures, please cite:

> Handy Satria. (2026). *Worldwide R&D and income explorer, 2000–2025* [Interactive dashboard and reproducible research software]. https://handysatria1.github.io/world-rd-income/

[BibTeX](CITATION.bib) · [Citation metadata (CFF)](CITATION.cff). For reproducibility, record the archived release tag or commit, the data build timestamp and your access date. Acknowledge the original data providers for the observations used; exact source details are preserved in the downloads.

## Interactive explorer

**[Six-sector GVA chart maker](https://handysatria1.github.io/world-rd-income/broad-sectors.html):** select and reorder up to 16 economies, choose latest/common/explicit years, and export PNG/SVG/CSV or print/PDF. Uses the supplied SIC-based groups, OECD TiVA for 80 economies and Eustat A38 for Basque Country. [Methods, classification, provenance and reproduction](BROAD_SECTORS.md) · [Excel workbook](https://handysatria1.github.io/world-rd-income/broad_sector_gva.xlsx). The default example is Korea, Singapore, China, Basque Country, US and UK; each bar identifies its actual year.

Open [world_rd_income_explorer.html](output/world_rd_income_explorer.html) in a browser. Data, styling and JavaScript are embedded in this single file, so it works offline without external libraries.

- **Year snapshot:** choose a GDP year and one R&D year, a 3-/5-year window ending in your chosen year, or a custom range. Optionally require every R&D year. Switch nominal/PPP income and linear/logarithmic income axes.
- **Compare positions:** choose earlier/later GDP years, or click **Compare 2010 → 2025**. Squares mark the earlier positions, circles the later positions, and arrows connect them. By default, R&D windows shift with GDP: 2020–2024 versus 2025 becomes 2005–2009 versus 2010. **Use the same R&D window** holds R&D fixed to isolate income movement.
- **Country history:** select an economy and year range to see annual GDP, R&D intensity and **derived nominal R&D expenditure in current US dollars**. The table also contains OECD's reported nominal GERD in national currency. Lines break at missing years. Each series shows its own available observations.
- **Sector × field:** select an economy, year and currency/price basis to inspect the joint OECD/Eustat GERD matrix. Values are displayed in millions; select any cell for source flags and units. **Download selected cells CSV** exports values in units, including explicit absent/missing cells. This view works independently of GDP coverage and includes Chinese Taipei and Basque Country.
- **Funding, performers & research:** scroll through eight charts together: funding and performing-sector amounts with intensity, their sector percentages, and government/business research-type percentages and amounts. Shared economy, year-window and price controls update every chart. Each chart has its own SVG/CSV exports and complete percentage table. Segment percentages appear where they fit; small segments remain available on hover and in the table.
- Hover/click points for values, actual reporting years and source flags. Search highlights points and filters the table. **Download plotted CSV** exports the full active sample or country history, including coverage/source details.

Snapshots select one R&D provider per economy/window by the most reported years, preferring OECD MSTI on ties. Comparisons select one provider across the **union of both R&D windows** and use only economies eligible at **both endpoints**. Both regressions use that common cohort. The comparison's provider/sample can therefore differ from a standalone snapshot. Country history selects one provider across the displayed range. Providers are never spliced within these selections.

Scatterplots require both nominal and PPP GDP at each requested endpoint, preserving the sample when the income measure changes. Year/window/coverage controls recalculate the equally weighted logarithmic regression; search and country selection do not refit it. Basque Country is a regional comparison point excluded from country regressions because it overlaps Spain. Country markers and normal-weight names use teal (`#146b88`), with names added where space permits, including Netherlands and Denmark in the default views.

The normalized annual archive is [explorer_history.json](data/explorer_history.json), with validation in [explorer_validation.json](data/explorer_validation.json). OECD/WDI historical values are the downloaded **latest vintage**, including subsequent revisions. Direct ONS business research types retain each year's publication vintage with its matching total, as documented below. Income changes include inflation and exchange-rate/PPP effects and are **not real economic growth**. Available years vary by economy; missing observations are never imputed. The static PDFs, main workbook analysis and figure captions describe the fixed default analysis; separate workbook sheets contain the annual nominal-R&D database. The browser's CSV records other selections.

## Basque Country: official regional data and conversions

**Basque Country (ES-PV)** means Spain's Basque Autonomous Community, not the wider cross-border cultural region. `ES-PV` is an ISO 3166-2 subdivision code; the legacy `iso3` column also accepts this explicitly typed regional identifier. Spain remains present; the Basque point is excluded from both static and interactive country regressions. The default build therefore plots **106 economies/regions**, with **105** in the regression (complete subset: **57** plotted, **56** in the fit).

Select **Basque Country (ES-PV)** in any of the five views; research panels show reported capital and a grey unclassified-current-cost remainder, with basic/applied/experimental types explicitly missing. Its history includes reported EUR R&D, derived current USD and a separate PPP expenditure chart. [Annual regional inputs and conversions](data/basque_annual.csv) are also in the workbook's **Basque annual conversions** sheet. R&D totals and joint cells are integrated into the annual databases, coverage and reconciliation exports.

### Sources

Eustat's [official PxWeb API](https://en.eustat.eus/ayuda_banco_API.html) supplies metadata by GET and selected JSON-stat data by POST. Exact responses, request bodies, request/response SHA-256 hashes, URLs and retrieval dates are archived in `data/raw/manifest.json`. The source registry is `basque_sources.py`.

| Data | Eustat table ID | Source units |
|---|---|---|
| All performers, by scientific field | `PX_043201_cid_res01.px` | Thousand current EUR |
| Companies + private non-profit institutions, by field | `PX_043201_cid_e12.px` | Thousand current EUR |
| Government performers, by field | `PX_043201_cid_ap01.px` | Thousand current EUR |
| Higher education performers, by field | `PX_043201_cid_es01n.px` | Thousand current EUR |
| Total GDP, market prices | `PX_170112_cpib_pib_a_06.px` | Thousand current EUR |
| GDP per person | `PX_170112_cpib_pib_a_11.px` | Current EUR/person |

Tables are at `https://www.eustat.eus/bankupx/api/v1/en/DB/{table ID}`. Total expenditure nature, Basque territory, GDP level and current-price selections are explicit; funding breakdowns and capital/current subcomponents are not added together. The 11 November 2026 archive has **2000–2024** R&D levels and **2000–2025** GDP. GDP/person 2025 is marked **advance** in the [archived display table](https://en.eustat.eus/elementos/ele0014300/tbl0014375_i.html), base 2022. No unflagged observation is assumed final. Eustat JSON-stat currently returns `updated=9999-12-31T22:59:59Z`; this is retained as supplied but is **not a valid publication date**. PC-Axis responses establish zero source decimals where the JSON-stat precision extension is absent.

The [2025 advance R&D release](https://en.eustat.eus/elementos/ele0027200/not0027219_i.html), dated 21 July 2026, gives provisional growth (+6.1%), based on units representing 87.6% of 2024 expenditure. It does not provide an annual expenditure level. Consequently no 2025 GERD amount or intensity is extrapolated. Refreshes will automatically include a reported 2025 level when it appears in the detailed tables.

### Conversion methodology

- **Current US dollars = current EUR / same-year EUR per US dollar.** The factor is Spain's World Bank WDI `PA.NUS.FCRF`, the official annual-average exchange rate. It applies to both GDP and GERD.
- **Current international dollars = current EUR / same-year EUR per international dollar.** The factor is Spain's WDI `PA.NUS.PPP`, the national **GDP PPP**. Applying it to Basque GDP and GERD assumes the Spanish national price level is an appropriate regional proxy. It is **not** a measured Basque PPP, an R&D-specific price index, Eurostat PPS, or a constant-price series.
- **Annual R&D intensity = Eustat GERD EUR / same-year Eustat GDP EUR × 100.** This is explicitly derived using the archived latest GDP vintage, not a copied Eustat percentage. Revisions can change it relative to earlier releases. Window averages take the arithmetic mean of annual percentages.
- Year matching is exact. Missing inputs stay missing; no previous-year factors, average-window conversions or regional price extrapolations are used.

The WDI requests are `https://api.worldbank.org/v2/country/ESP/indicator/{indicator}?source=2&date=2000:2025&format=json&per_page=100&footnote=y`; indicator definitions are archived separately. Converted cell rows retain their **original EUR source value**, scale, source status, annual conversion divisor and factor provenance. `value_status` distinguishes reported EUR from derived USD/PPP. Converted rounding tolerances condition on the supplied divisor; they do not quantify PPP uncertainty.

### Classification and checks

The Eustat matrix has **four performer rows/columns including total**, and **five fields plus total**. **BES_PNP** combines companies with private non-profits; it is never presented as BES alone or split by subtraction. Four broad fields map to FORD1–4. The original table's “Social sciences” group uses **EUSTAT_SOC**: the [Eustat field definition](https://en.eustat.eus/documentos/opt_1/tema_312/elem_25874/definicion.html) mentions humanities, but the downloaded tables do not separately identify them. This unresolved grouping is not forced into FORD5 or FORD_5_6. No humanities or NEC value is imputed.

Reconciliation uses Eustat's three performer groups and five reported field groups, with complete compatible inputs required. Missing JSON-stat `.` cells remain null and retain that source symbol; discrepancies are recorded. There are **600 original cells** in the requested years, represented as **1,800 EUR/USD/PPP rows** (1,791 numeric, nine missing across representations) in this archive. `USD_V` is the market-exchange-rate basis, currently supplied for Basque Country. This sector/field cube has no Basque constant-price PPP amounts; the funding cube uses the explicitly labelled national proxy documented below.

`verify_basque.py` independently reads archived JSON-stat values and WDI factors to check annual inputs, conversions, intensity, missingness, static selection, embedded history, CSVs and workbook. `verify_sector_field.py` checks every OECD/Eustat cell and reconciliation. `node test_explorer.js --built` checks all four Basque views, provider selection, region-specific grids and exclusion from country fits. Reports: [Basque verification](data/basque_validation.json), [sector/field verification](data/sector_field_validation.json).

## Nominal R&D expenditure database

Annual coverage is **2000–2025**, subject to source availability. Nominal expenditure means an economy's total GERD at **current prices**, rather than its share of GDP or expenditure per person.

- **[Annual nominal R&D database (CSV)](data/rd_nominal_annual.csv):** one row per economy, year, provider and currency basis. Reported and derived values are explicitly distinguished. Includes input values/years, exact source URLs and retrieval dates, original scale, flags, notes and missing-input reasons.
- **[Full annual coverage audit (CSV)](data/rd_nominal_coverage.csv):** every audited economy/year, including missing amounts.
- **[Definitions (CSV)](data/rd_nominal_definitions.csv)** and **[Excel workbook](data/world_rd_income_data.xlsx)**: sheets `RD nominal annual`, `RD nominal coverage` and `RD nominal definitions`.

| Series | Source and method | Unit / status |
|---|---|---|
| OECD nominal GERD | MSTI `G`, `XDC`, `V`, annual, no transformation; source value × `10^UNIT_MULT` | **Reported current national currency**, normalized from millions to units |
| OECD-based US$ estimate | Annual OECD GERD/GDP (%) × same-year WDI total GDP / 100 | **Derived current US dollars** |
| WDI/UNESCO-based US$ estimate | Annual WDI `GB.XPD.RSDV.GD.ZS` × same-year WDI total GDP / 100 | **Derived current US dollars** |
| Direct UNESCO-based US$ estimate | Annual UIS `EXPGDP.TOT` × same-year WDI total GDP / 100 | **Derived current US dollars** |
| Eustat regional GERD | Reported thousand EUR × 1,000; annual Spanish WDI factors for conversions (above) | **Reported current EUR; derived current USD and international dollars (PPP)** |

Total GDP is World Bank `NY.GDP.MKTP.CD` (**not GDP per capita**), from [this historical API request](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?source=2&date=2000:2025&format=json&per_page=20000&footnote=y). The [OECD nominal-GERD request](https://sdmx.oecd.org/public/rest/v1/data/OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/.A.G.XDC.V._Z?startPeriod=2000&endPeriod=2025&format=csvfilewithlabels) provides national-currency amounts. `XDC` is OECD's national-currency designation; no unverified ISO currency code or exchange-rate conversion is assigned. National-currency amounts cannot be compared across economies as though they were US dollars.

The WDI indicator catalog and the current UIS Science SDG release expose R&D intensity, rather than a directly reported nominal-US-dollar GERD series. The database therefore labels dollar amounts as **derived estimates**. Only inputs from the **same economy and year** are multiplied. Neither multi-year mean intensity nor a later GDP year enters this calculation. Missing same-year GDP leaves the estimate missing even when a reported local-currency amount exists; for example, Chinese Taipei has OECD local-currency GERD but no WDI total GDP. Zero R&D is retained when actually observed.

R&D/GDP denominators, national-account revisions and source vintages can differ, so an estimate may differ from an officially reported national total converted to US dollars. The alternatives are kept separately and must **not be summed or treated as independent measurements**. WDI's R&D series originates from UIS; direct UIS adds its release provenance and detailed metadata. Country history uses the same OECD/WDI provider selected for its intensity series; its CSV includes the alternative nominal estimates.

At initial addition on **11 November 2026**, there are **1,077 reported OECD country-year amounts across 47 economies**, **1,052 OECD-based US$ estimates across 46 economies**, and **2,208 estimates across 155 economies each** for WDI and direct UIS. Direct UIS is the **February 2026** release. These are provider-specific counts with overlapping observations; see the generated [current results](data/current_results.md) after refresh.

In this archived release, all **2,212** direct-UIS R&D-share observations match the WDI R&D-share observations exactly; their derived nominal amounts consequently match as well. The separate records preserve dissemination provenance and UIS-specific metadata.

Direct UIS inputs come from the **Science → SDG 9.5** archive linked on the [official bulk-download page](https://databrowser.uis.unesco.org/resources/bulk). Each refresh discovers that page's current `SCN-SDG.zip`, archives both the discovery page and exact ZIP, and records the release, checksums and retrieval dates. The archive includes the original labels, metadata and release README. UIS `MAGNITUDE` is a categorical flag, not a scale multiplier: `NA` is missing, while `NIL` is an observed zero. UNESCO data are attributed to the UNESCO Institute for Statistics and supplied under the archive's [CC BY-SA 3.0 IGO licence](https://creativecommons.org/licenses/by-sa/3.0/igo/); derived UIS dollar values are adaptations using WDI GDP.

## GERD by sector of performance and field of R&D

Source: OECD **“Gross domestic expenditure on R&D by sector of performance and field of R&D”**, dataflow `OECD.STI.STP,DSD_RDS_GERD@DF_GERD_FORD,1.0`.

- [Exact annual 2000–2025 CSV request](https://sdmx.oecd.org/public/rest/v1/data/OECD.STI.STP,DSD_RDS_GERD@DF_GERD_FORD,1.0/.A.G.._Z._Z._Z.._Z..?startPeriod=2000&endPeriod=2025&format=csvfilewithlabels).
- [Structure, codelists and field hierarchy](https://sdmx.oecd.org/public/rest/v1/dataflow/OECD.STI.STP/DSD_RDS_GERD@DF_GERD_FORD/1.0?references=all).
- **[Annual joint database](data/rd_sector_field_annual.csv)**: one row per returned economy/year/performing sector/field/unit-price combination, including blank source cells. Original values and scale, normalized amount, explicit currency, base year, all seven status/confidentiality fields, labels and provenance are retained.
- **[Coverage audit](data/rd_sector_field_coverage.csv)**: every catalog economy/year/unit-price basis, including absent years and economies. Counts numeric cells, explicit missing/confidential/included-elsewhere cells, absent combinations and available joint components. A grand total does not establish detailed coverage.
- **[Reconciliation audit](data/rd_sector_field_reconciliation.csv)**: reported totals compared to complete disjoint partitions where possible; discrepancies remain visible.
- **[Definitions and flag dictionary](data/rd_sector_field_definitions.csv)**: source dimensions, classification hierarchy and meanings of source flags.
- **[Excel workbook](data/world_rd_income_data.xlsx)**: `GERD sector field`, `GERD SF coverage`, `GERD SF reconciliation`, `GERD SF definitions`.

The initial **11 November 2026** extract contains **84,735 source rows across 45 economies**, with **82,683 numeric amounts**. Available observations span **2000–2024**; no 2025 data were returned. Each of three representations has 28,245 rows:

| Basis | Meaning |
|---|---|
| `XDC_V` | Current national currency; nominal amounts, with OECD's explicit `CURRENCY` attribute |
| `USD_PPP_V` | Current-price US dollars converted at purchasing power parities |
| `USD_PPP_Q` | Constant-price PPP dollars; base year **2020** in this snapshot |

These are overlapping unit/price representations, not independent observations. **PPP dollars are not US dollars at market exchange rates.** The original observations are in millions (`UNIT_MULT=6`); normalized CSV/Excel amounts are in units. `source_value` retains the source text, including blanks. The source currency attribute is preserved exactly rather than inferred from the historical year; series may use redenominated historical currencies. Constant-price base years remain explicit per cell and may change in later releases.

**Performing sectors:** `_T` total, `BES` business enterprise, `GOV` government, `HES` higher education, `PNP` private non-profit. These identify where research is performed, **not who funds it**. Funding, cost, R&D type and socio-economic objective dimensions are `_Z` (not applicable) in this joint dataflow.

**Fields:** `FORD1` natural sciences; `FORD2` engineering/technology; `FORD3` medical/health; `FORD4` agricultural/veterinary; `FORD5` social sciences; `FORD6` humanities/arts; `NEC` not elsewhere classified; `_T` total. The source hierarchy also supplies `FORD_1T4`, labelled “Natural sciences and engineering,” containing **all fields 1–4**, and `FORD_5_6`, containing fields 5–6. Totals and these combined groups overlap their components: **never sum the whole table**. Labels and parent relationships come from the archived OECD codelists.

The extract includes **1,122 confidential cells**, **3 included-elsewhere cells**, and **927 other blank source values**. They remain missing, not zero. A source row with a blank value is distinct from an unreturned combination; the coverage audit and browser export preserve that distinction. Observed zeros remain zero. Definition differences, estimates, breaks, provisional values, included categories and all auxiliary flags are retained. Important auxiliary flags include `S2` (“Unrevised breakdown not adding to the revised total”) and `V2` (“The sum of the breakdown does not add to the total”).

Reconciliation checks `BES+GOV+HES+PNP` against the reported sector total for each field, and `FORD_1T4+FORD_5_6+NEC` against the reported field total for each sector. **Every component must be available on a compatible currency/price/base-year basis**; an absent `NEC` is not assumed zero. The tolerance is the sum of half a last displayed source decimal for each participating cell. Initial results are **9,569 checks within source rounding**, **997 discrepancies retained**, and **26,295 incomplete checks**. These counts include overlapping currency/price representations. A passed check is accounting consistency, not evidence that the categories have identical definitions across economies. Source totals are never replaced by sums or residuals.

`sector_field_rd.py` builds the database and audits; compact rows and shared metadata are embedded in `explorer_history.json` and the offline HTML. The joint RDS dataflow is kept identifiable alongside the MSTI/UIS nominal database because source vintages and definitions can differ. `verify_sector_field.py` independently compares every exported/embedded/Excel cell against raw OECD/Eustat data and recomputes the reconciliation audit using decimal arithmetic; results are recorded in [sector_field_validation.json](data/sector_field_validation.json).

## Initial default results and static figures (before Basque addition)

| R&D averaging rule | Economies | 2025 current US$ R² | 2025 PPP R² |
|---|---:|---:|---:|
| Mean of reported observations within 2020–2024 | 105 | 0.358811 | 0.267396 |
| Complete five-year mean: every year 2020–2024 reported | 56 | 0.341079 | 0.227153 |

- **[Main figures: two-page PDF](output/world_rd_income_2025.pdf)** — all 105 eligible economies.
- [Current-US-dollar figure](output/world_2025_nominal.png) · [PPP figure](output/world_2025_ppp.png).
- **[Strict five-year-average figures: two-page PDF](output/world_rd_income_complete_five_years.pdf)** — the 56 complete-coverage economies.
- **[Interactive charts and plotted-data tables](output/world_rd_income_explorer.html)** — selectable years/windows, position comparisons, country history and CSV exports.
- **[Excel workbook](data/world_rd_income_data.xlsx)** — annual observations, averages, both income measures, exclusions, source selection, coefficients, sensitivity checks, nominal R&D, and joint sector/field GERD with coverage and reconciliation.

All four figures also have 300-dpi PNG, editable-text SVG and vector PDF versions in `output/`. All use the same axis limits in this snapshot. Selected labels keep the printed charts readable; **all eligible economies are plotted and enter the fit**. The main nominal and PPP figures have exactly the same 105 observations and R&D values. The strict pair likewise uses the same 56 observations.

## What “worldwide” means here

The coverage audit considers **217 non-aggregate countries/economies in the World Bank country catalog**, plus **Chinese Taipei (TWN)** from OECD MSTI, for **218 audited economies**. The World Bank catalog includes separately reported territories/economies, such as Hong Kong and Macao; it is not a list of sovereign states only. There is no OECD-membership or income-level restriction.

- **111** audited economies have at least one 2020–2024 R&D observation in the selected sources.
- **105** also have both requested 2025 GDP-per-capita measures. All 38 OECD members are included.
- **107** have no R&D observation within the requested window in the selected sources.
- **6** have some R&D data but no 2025 GDP-per-capita observation in the selected World Bank series: **United Arab Emirates, Bermuda, Cuba, Liechtenstein, Syrian Arab Republic and Chinese Taipei**. Chinese Taipei has no entry in the World Bank country catalog.

These are **worldwide available-data figures**, not complete observations for every country in the world. Exclusion means missing data in the selected source/window, not zero R&D or proof that data are unavailable from every possible provider. Regional, income-group, World, EU and OECD aggregates are excluded from country plots and regressions.

The full audit, including countries with neither variable, is in [coverage_and_exclusions.csv](data/coverage_and_exclusions.csv).

## Sources and selection rule

**[Detailed source guide](https://handysatria1.github.io/world-rd-income/sources.html)** · **[Complete source inventory (CSV)](https://handysatria1.github.io/world-rd-income/source_inventory.csv)** · **[Original provenance manifest (JSON)](https://handysatria1.github.io/world-rd-income/source_manifest.json)**. The guide identifies all providers, dataset/indicator/table IDs, ONS cell locators, units, query ranges, transformations and coverage-review sources. Its inventory is regenerated from each build's exact raw manifest and includes request bodies, URLs, retrieval timestamps, byte counts, checksums and release/update fields. These links describe the current published build; use the research ZIP from an archived release for an older vintage. Guide source: `data_sources.html`; inventory generation: `source_guide.py`.

### R&D: OECD MSTI and UNESCO UIS via World Bank WDI

1. **OECD Main Science and Technology Indicators:** `OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3`; annual `G` (GERD), `PT_B1GQ` (percentage of GDP), 2020–2024. The exact OECD snapshot used for the previous reconstruction is carried forward.
   - [OECD CSV request](https://sdmx.oecd.org/public/rest/v1/data/OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/.A.G.PT_B1GQ._Z._Z?startPeriod=2020&endPeriod=2024&format=csvfilewithlabels).
2. **World Bank World Development Indicators (WDI), source 2:** `GB.XPD.RSDV.GD.ZS`, “Research and development expenditure (% of GDP).” WDI identifies the **UNESCO Institute for Statistics** as the source. The definition includes current and capital GERD across business enterprise, government, higher education and private non-profit sectors.
   - [Worldwide R&D API request](https://api.worldbank.org/v2/country/all/indicator/GB.XPD.RSDV.GD.ZS?source=2&date=2020:2024&format=json&per_page=20000&footnote=y).
   - [Indicator definition and source metadata](https://api.worldbank.org/v2/indicator/GB.XPD.RSDV.GD.ZS?source=2&format=json).

**One entire R&D series is selected per economy:** choose the source with the **greatest number of nonmissing annual observations in 2020–2024**; prefer **OECD on ties**. Selection depends on coverage, not the values or fitted R². Years from different providers are not spliced within an economy.

This preserves the OECD series for 44 of the plotted economies and uses UNESCO/WDI for 61. For example, OECD provides China through 2024 and Australia in 2021 and 2023. Russia uses UNESCO/WDI because it supplies five years whereas this OECD extract supplies only 2020. [Source-selection audit](data/source_selection.csv) records both providers' years, counts and means for every audited economy.

The two providers can disseminate related underlying national observations; they are not independent evidence. Revisions, GDP denominator revisions, status flags and reporting vintages can differ. The sensitivity analysis therefore also recomputes both fits using UNESCO/WDI R&D alone on the same 105-economy sample.

### GDP per capita: World Bank WDI

Both income measures use WDI consistently for the country regression sample; the regional Basque comparison uses Eustat EUR amounts and the conversion method above:

| Measure | Indicator | Unit |
|---|---|---|
| GDP per capita at market exchange rates | `NY.GDP.PCAP.CD` | Current US dollars per person |
| GDP per capita at purchasing power parities | `NY.GDP.PCAP.PP.CD` | Current international dollars per person |

- [2025 nominal GDP API request](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?source=2&date=2025&format=json&per_page=20000&footnote=y).
- [2025 PPP GDP API request](https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.PP.CD?source=2&date=2025&format=json&per_page=20000&footnote=y).
- [Nominal definition and sources](https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.CD?source=2&format=json) · [PPP definition and sources](https://api.worldbank.org/v2/indicator/NY.GDP.PCAP.PP.CD?source=2&format=json).
- [Country/economy catalog](https://api.worldbank.org/v2/country?format=json&per_page=400); entries whose region is `Aggregates` are not economies in the sample.

The explorer uses the same indicators with **2000–2025** queries: `msti_gerd_percent_gdp_history.csv`, `wb_rd_history.json`, `wb_nominal_history.json` and `wb_ppp_history.json`. Exact historical request URLs and retrieval dates are in `data/raw/manifest.json`. The fixed-year inputs above remain the basis of the static figures and workbook.

WDI's GDP sources include national statistics, OECD national accounts and World Bank estimates; PPP metadata additionally identifies ICP, Eurostat/OECD PPP programmes and IMF WEO inputs. **PPP is expressed in current international dollars, not market-exchange-rate US dollars.** Neither measure is a constant-price growth series. Source year labels and footnotes are preserved; no 2024 value is relabelled as 2025, and no separate forecast is substituted for a missing WDI value. Blank API observation-status fields do not establish that an observation is final or free of estimation.

### Archiving and source flags

`data/raw/` contains exact JSON/CSV responses, OECD structure/codelist XML, WDI indicator metadata and a manifest of request URLs, retrieval timestamps, byte counts and SHA-256 checksums. The WDI observation responses report `lastupdated = 2026-10-08`; this is a dataset-level update date, not the revision date of each observation. The R&D indicator's source-description text still references a 2025 UNESCO release/access date; it should not be mistaken for an observation-specific vintage.

OECD estimated/provisional values, breaks and definition flags are retained. WDI status and footnote fields are retained as returned, including blanks. The coverage analysis does not infer missing values from blank flags. Some WDI income-group aggregates have blank ISO3 fields; their catalog identifiers are resolved for the normalized raw tables while the original fields remain available. They do not enter the regressions.

## Averages and missing years

The broad-sample mean for economy *i* is:

```text
mean_RD_i = sum(reported annual GERD/GDP percentages in 2020–2024)
            / number of reported years in that window
```

It is an arithmetic mean of annual percentages, **not** a ratio of summed R&D expenditure to summed GDP. Each available year has equal weight. No missing value is assigned zero, interpolated or carried forward. Only years inside the requested R&D window enter its average; that window is 2020–2024 for the static analysis.

| Number of reported R&D years | Economies in the 105-economy sample |
|---:|---:|
| 1 | 16 |
| 2 | 12 |
| 3 | 4 |
| 4 | 17 |
| 5 | 56 |

The 49 incomplete cases have hollow markers; their printed labels have asterisks where shown. **An average based on one year is that observation, not a measured five-year average.** For example, India's selected observation is 2020 only; Singapore has 2020–2023, and Australia has 2021 and 2023. Exact years and all five annual-value columns are supplied for every economy.

The strict companion figures require observations for **all five years** and divide the sum by five. `rd_strict_five_year_mean` is blank for every incomplete case. This supplies the literal complete-2020–2024 comparison while exposing the loss of geographic coverage. Restricting to complete reporting changes the sample; it does not repair the missing economies or eliminate selection bias.

## Regression

Each figure estimates, by equally weighted ordinary least squares:

```text
GERD_percent_GDP_i = a + b * ln(GDP_per_capita_i) + error_i
```

Only the GDP predictor is logged. Static figures use a linear horizontal axis, producing a logarithmic fitted curve; the explorer also offers a logarithmic display. The display choice does not change the model. Coefficients are not constrained to produce positive predictions at every income level; parts of the unconstrained curve below zero are outside the plotted R&D range.

**R² measures fitted variation in R&D intensity against log income. It does not measure GDP explained by R&D, a causal effect, an optimal spending target or the return on R&D investment.** Income and R&D may affect one another; confounding, reporting selection and differences in economic structure remain. Using earlier R&D years does not by itself identify causality. The curve's shape is imposed by the logarithmic specification.

### Sensitivity checks

| Sample / R&D source | n | Nominal R² | PPP R² |
|---|---:|---:|---:|
| Main worldwide sample | 105 | 0.359 | 0.267 |
| All five R&D years reported | 56 | 0.341 | 0.227 |
| At least three R&D observations | 77 | 0.355 | 0.255 |
| Excluding Ireland and Luxembourg | 103 | 0.377 | 0.280 |
| Excluding Israel | 104 | 0.391 | 0.304 |
| OECD members only, same source rule and 2025 GDP | 38 | 0.226 | 0.146 |
| UNESCO/WDI R&D only, same GDP and economies | 105 | 0.373 | 0.279 |

These illustrate sample and source dependence; they are not a basis for selecting a preferred answer. UNESCO/WDI alone supplies full five-year R&D coverage for only 22 of these 105 economies. The global fits are stronger than those within the OECD-member subset under this protocol, but neither comparison identifies a causal return.

The earlier OECD-only figures also used OECD GDP, a narrower geography and, for the matched-year comparisons, 2023. Their differences from this package cannot be attributed to geographic expansion alone. Coefficients and rank correlations are in [model_statistics.csv](data/model_statistics.csv) and [sensitivity_checks.csv](data/sensitivity_checks.csv).

## Ready-to-use caption for the broad PPP figure

> **R&D intensity in 2020–2024 and GDP per capita in 2025: worldwide available data.** Each point represents one of 105 countries/economies with at least one R&D observation within 2020–2024 and both requested 2025 income measures. R&D intensity is the arithmetic mean of reported annual GERD/GDP percentages in that window; 56 economies report all five years, and hollow markers identify incomplete coverage. GDP per capita is in current international dollars at purchasing power parities. The dotted line is an equally weighted OLS fit of R&D intensity on the natural logarithm of GDP per capita (R² = 0.267). One R&D source is chosen per economy by greatest within-window year coverage, preferring OECD on ties. Selected economies are labelled; all points enter the fit. Sources: OECD MSTI; UNESCO UIS via World Bank WDI; World Bank WDI national accounts, retrieved 10 November 2026. No missing observations are imputed. The association does not establish causality.

For the nominal figure replace the income unit with “current US dollars at market exchange rates” and R² with 0.359. For the strict five-year figures specify 56 economies, all five annual observations required, and R² = 0.341 (nominal) or 0.227 (PPP).

## Reproduction

All economy markers and country labels use teal (`#146b88`) and normal font weight. Static styling is in `reproduce_figures.py` (`COUNTRY_COLOR = TEAL`); interactive styling is in `explorer.js` and `explorer.css`. `historical_explorer.py` embeds the HTML/CSS, annual data, `explorer_core.js` calculations and `explorer.js` UI. `nominal_rd.py` validates reported nominal units, joins annual R&D/GDP to total GDP and builds the database/audit. Rebuilding regenerates all outputs.

The original selected labels are retained, and additional country names are placed automatically where there is space near their point. Candidate labels are checked against existing text, markers, the legend and plot bounds; dense clusters remain sparsely labelled. This can show different additional names in the nominal and PPP views because their spacing differs. Hover tooltips and the table still identify every plotted economy.

Python 3.12.16 and the dependency versions in `requirements.txt` were used. Node.js 24 runs the JavaScript calculation checks; the browser itself needs no Node installation. From this directory, with Node available:

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
node test_explorer.js
.venv/Scripts/python.exe -m unittest test_nominal_rd.py test_sector_field_rd.py
.venv/Scripts/python.exe reproduce_figures.py
.venv/Scripts/python.exe verify_sector_field.py
.venv/Scripts/python.exe verify_basque.py
node test_explorer.js --built
```

Rebuilding uses only this package's checksum-verified archived inputs and requires no network access. To refresh source data:

```powershell
.venv/Scripts/python.exe download_data.py --refresh
.venv/Scripts/python.exe reproduce_figures.py
```

Refreshing replaces the archived vintage after all responses have downloaded and passed response validation. The default downloader reuses existing files; on a first download it can reuse the exact earlier OECD snapshot if present, otherwise it retrieves OECD directly. The plotting script does not depend on the earlier package. Queries pin WDI source 2 and OECD structure version 1.3.

For scheduled refresh and publication, follow [AUTOMATION.md](AUTOMATION.md). Static chart pairs explicitly select the common sample with both income measures; `included_nominal` and `included_ppp` record individual eligibility, while `included_paired` and `excluded_reason_paired` record the plotted sample. The browser supplies its own active-selection audit. Weekly refresh updates observations inside the archived 2000–2025 range, while the default selection and static study years stay fixed.

## Validation

The script checks source hashes and URLs, API pagination, series identifiers/dimensions, years, nonnegative R&D and positive income, uniqueness, exclusion of aggregates, use of one R&D source per economy, independently calculated means, full-year requirements, independently calculated OLS/R², identical nominal/PPP samples and R&D values, and printed-label overlap/bounds. Figures were visually inspected. [Machine-readable validation report](data/validation_report.json).

Historical extraction checks hashes/URLs, complete API responses, series dimensions/years, unique economy-years, valid units/values and aggregate exclusion. `node test_explorer.js` exercises missing observations, observed zeros, source selection, paired cohorts, shifted/fixed windows, annual gaps, invalid selections and logarithmic OLS. Seven real-data selections were independently checked against SciPy; the default browser sample and fit were checked against the static analysis.

`python -m unittest test_nominal_rd.py` checks million-to-unit scaling, rejection of PPP/constant-price inputs, same-year joins, missing GDP, observed zeros versus UIS non-applicable zeros, and official UIS release discovery. JavaScript checks also verify that nominal history follows its selected intensity provider and does not fill gaps with another provider's values.

The Excel workbook preserves source values and flags and includes country-level source decisions. Raw API responses remain authoritative for the exact downloaded representation. These outputs are a reproducible descriptive analysis, not a publication summary.
## Funding sources and research types

**Direct Basque/UK source update:** see [OFFICIAL_DATA.md](OFFICIAL_DATA.md). Eustat total/capital observations now populate the Basque research panels, with research types still missing. UK business types use direct ONS current-cost observations plus separate capital for 2022–2024, retaining each publication's matched total and vintage. ONS also supplies dashboard intensity through 2024 and independently verified funding/performance reference cells. All source differences and remaining gaps are explicit.

The offline explorer includes a scrolling **Funding, performers & research** dashboard. Eight charts are visible together, with shared one-, three-, five-year and custom windows, selectable economies, price bases and composition averaging. Funding sources identify who pays; performing sectors identify who carries out the R&D. Government/business research panels are always displayed; the additional-performer control also supports higher education, private non-profits or all performers. Every panel has its own SVG/CSV export and expandable table of all percentages, including small segments.

The percentage-label checkbox applies to every chart. Labels appear inside both amount and composition bars when the rendered segment is large enough. Amount-chart percentages always use category mean / reported mean total, so they match the drawn amounts; the composition averaging setting applies to percentage charts. Missing categories are not labelled zero. Mixed national currencies prevent amount comparisons but leave the individual-economy percentage charts available.

- OECD `DSD_RDS_GERD@DF_GERD_SOF`: performer × funding source, including detailed subcategories.
- OECD `DSD_RDS_GERD@DF_GERD_TORD`: performer × basic/applied/experimental research, retaining separately reported unclassified capital.
- Eustat `PX_043201_cid_res06.px`: Basque performer × funding source. Companies and private non-profit **performers** stay combined; their **funding sources** are separate.
- These are two separate cubes: they do not identify funding source × research type. Government research-type charts show government-**performed** research.

Each bar uses common years across its reported total and every category with numeric observations in the requested window. Never average components on different year sets. Categories absent throughout remain null, with an explicitly derived accounting residual where totals exceed known components. Negative discrepancies are retained. Strict mode requires all requested years, not all categories. The default composition is a ratio of summed amounts; an optional mean of annual shares is available. Intensity averages exactly the bar years, from one provider, and is absent if any year is missing. Economies can have different year subsets; the chart discloses them.

**Basque constant-2020 PPP:** this new view derives EUR amounts using the same-year ratio of OECD Spain's constant-2020 PPP GERD to its nominal-EUR GERD, both total/total observations in the funding cube. This is an implied national conversion proxy, conditional on rounded source inputs, not a Basque price survey or an R&D-specific deflator. `rd_breakdown_conversion.csv` archives both inputs, divisor and flags. Existing sector/field data keep their original bases. Eustat `.` and `-` symbols remain null; their precise meanings are unresolved. No Basque basic/applied/experimental split was identified in the accessed Eustat tables: “nature” classifies current/capital costs instead. No Spanish research mix is substituted.

New deliverables:

- `data/rd_breakdown_annual.csv`, `_coverage.csv`, `_reconciliation.csv`, `_definitions.csv`, `_conversion.csv`.
- Matching five Excel sheets, with original values, flags, scale, currency/base year, reported/derived status, source URLs and conversion provenance.
- `data/rd_breakdown_examples.csv` and `.json`: exact default chart calculations.
- `output/rd_funding_intensity_2020_2024.{png,svg,pdf}`.
- `output/rd_performer_intensity_2020_2024.{png,svg,pdf}`.
- `output/rd_performer_composition_2020_2024.{png,svg,pdf}`.
- `output/rd_funding_performer_composition_2020_2024.{png,svg,pdf}`.
- `output/rd_research_type_composition_2020_2024.{png,svg,pdf}`.

Additional validation commands (after rebuilding): `python verify_breakdown.py` and `node test_breakdown.js --built`. The former independently checks all raw cells, conversions, flags, coverage, reconciliation, embedded HTML and new workbook sheets. The latter tests common-year/missingness edge cases and independently compares JavaScript results with Python figure calculations. Packaging requires the matching successful verification report.
## Export technology and ISIC two-digit value-added supplement

See [INDUSTRY_DATA.md](INDUSTRY_DATA.md) for the separately versioned World Bank/UNIDO export percentages and OECD/UNIDO value-added data. The companion workbook, annual joins, country/year coverage, original responses and exact requests are included in research downloads. Run `industry_sources.py`, `industry_data.py` and `verify_industry.py` after the main scientific build and before `build_site.py`. The supplement's interactive page is `industry.html`.

The [China source assessment](CHINA_GVA.md) documents TiVA total value added (`VALU`, 31 ISIC divisions annually in 2000–2022) and the official NBS 2023 input–output benchmark (211 native product sectors). The NBS CSV preserves original names, codes, components and Excel cell locators; its ISIC correspondence remains unresolved.
