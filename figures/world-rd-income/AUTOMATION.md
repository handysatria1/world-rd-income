# Automatic updates with GitHub Actions and GitHub Pages

The supplied workflow checks OECD, World Bank, UNESCO UIS, Eustat and the reviewed ONS editions **every Monday at 06:23 UTC**. Each successful run downloads current responses, recalculates all figures and publishes the interactive chart through GitHub Pages. You can also run it manually. This is scheduled polling: a source change appears after the next successful run, rather than immediately when the provider updates its database.

The workflow also refreshes the separately versioned [export technology and detailed value-added supplement](INDUSTRY_DATA.md), including UNIDO INDSTAT. It runs `industry_sources.py --refresh`, `industry_data.py` and `verify_industry.py` before packaging. The supplement joins to that run's validated R&D/income history and retains a separate source manifest and build timestamp.

It also refreshes the [six-sector GVA chart](BROAD_SECTORS.md): all-country OECD TiVA `VALU`, Eustat A38 and annual WDI exchange rates, with a separate manifest. Grouped data, source-cell verification, year-selection checks, the example figures, chart maker and downloads are rebuilt before publication.

The [employment, productivity and goods-export extension](SECTOR_ECONOMY.md) then refreshes OECD TiM, BTiGE and Eustat inputs in its own manifest. `sector_economy.py` rebuilds the six-sector employment sums, exact-year GVA/person joins and custom export groups. Independent source-cell, conversion, ratio, workbook and selection checks run before rendering the five examples and packaging the site.

The [industry R&D/economy extension](RD_INDUSTRY.md) refreshes OECD RDS main-activity BERD, Eustat native business + PNPI branches and WDI currency factors. It rebuilds disjoint six-group allocations, coverage audits and exact economic joins, runs classification/selection tests and independent source/workbook verification, then packages the six-layout R&D chart maker and combined downloads.

Project website: **https://handysatria1.github.io/world-rd-income/**. Source repository and archived releases: **https://github.com/handysatria1/world-rd-income**.

## 1. Upload the source files

Use this layout in your GitHub repository, on its **default branch** (usually `main`):

```text
.github/
  workflows/
    update-world-rd-income.yml
    publish-world-rd-snapshot.yml
figures/
  world-rd-income/
    download_data.py
    reproduce_figures.py
    build_site.py
    historical_explorer.py
    nominal_rd.py
    test_nominal_rd.py
    sector_field_rd.py
    test_sector_field_rd.py
    verify_sector_field.py
    basque_sources.py
    basque_rd.py
    verify_basque.py
    breakdown_sources.py
    breakdown_rd.py
    breakdown_figures.py
    breakdown_core.js
    test_breakdown.js
    verify_breakdown.py
    official_sources.py
    official_rd.py
    explorer.html
    explorer.css
    explorer_core.js
    explorer.js
    test_explorer.js
    requirements.txt
    README.md
    AUTOMATION.md
    OFFICIAL_DATA.md
    CITATION.cff
    CITATION.bib
    source_guide.py
    data_sources.html
    industry_sources.py
    industry_data.py
    verify_industry.py
    industry_site.py
    industry.html
    INDUSTRY_DATA.md
    china_gva.py
    CHINA_GVA.md
    broad_sector_sources.py
    broad_sectors.py
    verify_broad_sectors.py
    broad_sector_figures.py
    broad_sector_site.py
    verify_broad_site.py
    broad-sectors.html
    broad_sector_core.js
    broad_sector_chart.js
    test_broad_sector.js
    BROAD_SECTORS.md
    sector_economy_sources.py
    sector_economy.py
    verify_sector_economy.py
    sector_economy_figures.py
    sector_economy_site.py
    sector-economy.html
    sector_economy_core.js
    sector_economy_chart.js
    test_sector_economy.js
    SECTOR_ECONOMY.md
    rd_industry_sources.py
    rd_industry_mapping.py
    rd_industry.py
    verify_rd_industry.py
    test_rd_industry.py
    rd_industry_site.py
    rd-industry.html
    rd_industry_core.js
    rd_industry_chart.js
    test_rd_industry.js
    RD_INDUSTRY.md
```

The workflow is at [../../.github/workflows/update-world-rd-income.yml](../../.github/workflows/update-world-rd-income.yml) in this workspace. On GitHub's website, use **Add file → Create new file**, enter that exact `.github/workflows/update-world-rd-income.yml` path, paste its contents, and commit. Upload all source files shown under `figures/world-rd-income/` without flattening the folders. The public repository tracks source files; large generated `data/`, `output/` and `_site/` files are delivered through Pages and release assets. The refresh workflow generates them from fresh downloads.

An uploaded `index.html` alone cannot update itself. The Python, HTML/CSS and JavaScript source files and workflow are needed for automated generation. The workflow expects the layout above; its paths must be edited if you use a different layout. It installs Python 3.12 and Node.js 24, runs the JavaScript calculation and nominal-R&D unit/join checks, then refreshes, rebuilds and validates the outputs.

## 2. Enable Pages and start the first run

1. In the repository, go to **Settings → Pages**.
2. Set **Build and deployment → Source → GitHub Actions**. This replaces the earlier “Deploy from a branch” setting.
3. Open **Actions → Update worldwide R&D charts → Run workflow** and choose the default branch.
4. Wait for both **build** and **deploy** to succeed. The deployment shows the website URL, normally `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/`.

No OECD/World Bank API key or personal access token is required. The workflow uses GitHub's built-in token with Pages deployment permissions. GitHub Actions must be enabled in the repository. Public repositories can use GitHub Pages on GitHub Free.

The manual button appears after the workflow file is on the default branch. A change to the package files on that branch also triggers a rebuild. Configure Pages before relying on an initial upload-triggered run; if that run failed before Pages was enabled, use **Run workflow** again.

## What updates

- Newly reported or revised **2000–2025 annual R&D and GDP-per-capita observations**, plus the fixed-year snapshots used by the static analysis.
- OECD reported nominal GERD in current national currency, World Bank total GDP in current US$, and separate derived nominal-US-dollar R&D series using OECD, WDI/UNESCO and direct UIS intensities. Source inputs and nominal coverage are included in CSVs and the workbook.
- OECD RDS GERD jointly classified by performing sector and field, including current national currency and current/constant PPP amounts. All source cells and flags, the classification hierarchy, coverage and reconciliation audits are refreshed and independently checked against the raw archive, embedded data and workbook.
- Eustat Basque Country R&D totals and sector/field tables, GDP and GDP/person, plus annual Spanish WDI exchange and GDP-PPP factors. Exact PxWeb POST bodies and response bytes are retained. New reported 2025 levels are included automatically when published in the selected tables; advance growth rates are not turned into expenditure levels. Unknown classification/status changes stop the build for inspection. Basque Country remains a regional comparison point outside country regressions.
- Country coverage, selected R&D sources, reported-year means, strict five-year means, regression coefficients/R², all static figures, the interactive charts and workbook.
- The webpage's source-retrieval dates, build timestamp, WDI dataset update dates and coverage counts.
- `data/current_results.md`, including current static results and captions; both `data/validation_report.json` and `data/explorer_validation.json`; `data/explorer_history.json`; and all coverage/source-selection audits.

**Interactive years are selectable within 2000–2025.** The default selection and static PDFs/main Excel analysis remain 2020–2024 R&D against 2025 GDP. Visitors can choose individual R&D years, 3-/5-year averages or custom ranges, GDP years, paired position comparisons and annual country histories, including derived nominal R&D. Their active selections are downloadable as CSV. Additional workbook sheets contain the full nominal-R&D database. The workflow refreshes data within the archived range; extending beyond 2025 requires updating the history bounds and displayed range labels.

The direct UIS release is discovered from the current Science `SCN-SDG.zip` link on its official bulk-download page. The page, archive and release identifier are preserved in the raw manifest. A changed or ambiguous discovery link, new unknown economy, or changed indicator/unit schema stops the build for inspection. The downloader stages UIS with the other inputs before promoting any downloaded files.

Country scatterplots require at least one R&D year and **both** income measures, or every R&D year when complete coverage is selected. Comparisons require eligibility at both endpoints and select one provider across the union of both R&D windows; both endpoint regressions use the common sample. Source selection uses the most R&D years, preferring OECD on ties, without splicing providers. Country histories use one R&D provider across the displayed range and show each series' available years, with gaps. The static coverage audit retains separate nominal/PPP eligibility and a shared `included_paired` flag; the browser shows active-selection exclusions.

The README's numbers and example caption describe the **initial 10 November 2026 snapshot**. After a refresh, use the generated current results/captions, chart, CSVs and workbook. The workflow does not automatically rewrite that historical narrative.

## Published files and reproducibility

The initial validated **11 November 2026** build is retained in the repository's `snapshot-2026-11-11` release. `world-rd-income.zip` contains the exact research package; `pages-site.zip` contains the complete website and companion downloads. Release notes record their SHA-256 checksums. To deploy or restore that exact website, run **Actions → Publish validated R&D snapshot → Run workflow**, supplying the release tag and the expected SHA-256 of `pages-site.zip`. The workflow verifies the checksum before deployment. This manual snapshot workflow shares the refresh workflow's deployment lock; the next successful weekly refresh publishes newer results normally.

Each successful deployment contains:

- `index.html`: the standalone historical explorer with year/window controls, five views (including Sector × field and the scrolling Funding, performers & research dashboard), search, tooltips, dates, country tables and per-chart CSV/SVG exports.
- `current_results.md`: current fixed-year statistics, coverage and captions.
- `broad-sectors.html`: six-sector chart maker, alongside `broad_sector_gva.xlsx`, annual/component/classification/coverage CSVs, source manifest/inventory, verification reports, and PNG/SVG/PDF example figures. The research ZIP includes an offline root page with local download links.
- `rd_nominal_annual.csv` and `rd_nominal_coverage.csv`: nominal R&D database and full economy-year coverage audit, with reported/derived status and explicit currencies.
- `rd_sector_field_annual.csv`, `rd_sector_field_coverage.csv`, `rd_sector_field_reconciliation.csv`, `rd_sector_field_definitions.csv`: joint GERD database, coverage, accounting audit and definitions/flags. Source currency and base year are explicit; totals and combined groups overlap components.
- `world_rd_income_data.xlsx`: the workbook, including annual nominal R&D, inputs, coverage and definitions.
- `basque_annual.csv`: reported EUR inputs, annual exchange/PPP factors, derived regional amounts/intensity and provenance; also included as a workbook sheet.
- `world-rd-income.zip`: this build's raw responses and checksum/URL/timestamp manifest, annual historical data, workbook, figures, Python/HTML/CSS/JavaScript sources and checks, workflow, pinned requirements and documentation.
- `CITATION.cff` and `CITATION.bib`: suggested-reference metadata, also included in the research ZIP and linked from the dashboard. The repository-root `CITATION.cff` enables GitHub's **Cite this repository** feature.
- `sources.html`, `source_inventory.csv` and `source_manifest.json`: detailed provider/dataset/units/conversion guide, build-specific request inventory, and the exact raw provenance manifest. Packaging verifies every listed response's byte count and checksum, then regenerates the inventory from that build's archive. The guide template and generator are included in the research ZIP.

The website publishes the latest successful build. Generated files are deployed as a Pages artifact; **the workflow does not commit refreshed files to the repository branch**. Download the ZIP when you need to retain a particular vintage for research. The raw files within that ZIP reproduce that build without another network request.

Every scheduled run rebuilds, including runs where the source values are unchanged. “Source retrieval” and “chart built” dates are distinguished from WDI's dataset-level `lastupdated` dates; none is an individual observation's revision date. New data outside the queried 2000–2025 range do not appear automatically.

## Schedule and maintenance

The workflow contains:

```yaml
schedule:
  - cron: '23 6 * * 1'  # Monday, 06:23 UTC
workflow_dispatch:
```

For daily checks change the cron expression to `'23 6 * * *'`. For monthly checks on the first day use `'23 6 1 * *'`. GitHub schedules can be delayed or occasionally dropped during high load; the time is not an exact delivery guarantee.

**GitHub disables scheduled workflows in public repositories after 60 days without repository activity.** Check the Actions page periodically and re-enable the workflow if needed. See GitHub's [schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) and [Pages custom-workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

If a download, calculation or validation fails, the deployment job does not run and the existing published site remains available. Inspect the failed step on the Actions page, then rerun after resolving the cause. Temporary HTTP 429/5xx/network failures are retried up to three attempts per download. Responses are downloaded and checked before replacing cached inputs. The manifest is written last; checksum checks stop a build if local file replacement was interrupted.

Queries pin WDI source 2, OECD MSTI structure version 1.3 and OECD RDS GERD sector/field version 1.0. API/schema changes, a newly unclassified OECD aggregate/economy, or unexpectedly incomplete responses can require a code update. Current WDI queries request all rows in one page; the build explicitly rejects a multi-page or truncated response instead of silently plotting a partial sample. For actual pagination, increase `per_page` appropriately or implement retrieval of every page. Very small/degenerate samples and label-layout failures likewise stop publication. Source sector/field totals that differ from their breakdowns are retained in the reconciliation audit; this is distinct from a failed extraction or export check. The independent sector/field validation must match the build timestamp before packaging.

## Run the same pipeline locally

From `figures/world-rd-income/`, with Python 3.12, the packages in `requirements.txt`, and Node.js 24 installed:

```powershell
node test_explorer.js
node test_breakdown.js
python -m unittest test_nominal_rd.py test_sector_field_rd.py
python download_data.py --refresh
python reproduce_figures.py
python verify_sector_field.py
python verify_basque.py
python verify_breakdown.py
node test_explorer.js --built
node test_breakdown.js --built
python industry_sources.py --refresh
python industry_data.py
python verify_industry.py
python broad_sector_sources.py --refresh
python broad_sectors.py
python verify_broad_sectors.py
node test_broad_sector.js --built
python broad_sector_figures.py
python build_site.py --destination ../../_site
python verify_broad_site.py --site ../../_site
```

Choose an empty destination for the final command. The packaged site's `index.html` can be opened locally; its chart remains self-contained. The ZIP download is a companion file. Running these commands locally validates the build; deployment and GitHub-specific configuration are verified by the first successful Actions run.
## Funding/research extension

The existing weekly refresh also archives the OECD funding and research-type dataflows, Eustat funding/cost tables (including exact POST bodies, metadata and PC-Axis precision sources), and the reviewed ONS publication editions in `official_sources.py`. It regenerates the databases, workbook sheets, five stacked-chart figure families and scrolling dashboard. `verify_breakdown.py` and `test_breakdown.js --built` run before packaging/deployment, including direct ONS/Eustat checks. Basque constant-2020 PPP inputs use Spain's paired OECD funding totals; ONS research conversions use the UK's paired totals. No missing factors or research types are filled forward. A changed OECD base year or ONS worksheet layout fails validation. New ONS editions require reviewed mappings; see `OFFICIAL_DATA.md`.
