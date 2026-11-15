# R&D and Economic Development: editorial release

The approved dashboard-wide wording uses British English and neutral institutional
language. The main heading is **R&D and Economic Development**. Bibliographic
titles and official indicator definitions remain unchanged.

This is not a data refresh. Preserve all three GDP options, exact economy/year
joins, flags, source qualifications, missing-data rules, unweighted means,
income-group colours and symbols, existing downloads and static figures.

## Controlled publication

The source tree contains unpublished selectable-period capacity and enriched
snapshot functionality. Do **not** build the publication from those templates
wholesale. `stage_wording_release.py` applies only editorial differences since
commit `09a40142195e2f907659e4cb2552f352e34ec521` to that release's validated
`pages-site.zip`, whose SHA-256 is checked before extraction.

```text
python figures/world-rd-income/stage_wording_release.py --archive BASE/pages-site.zip --destination STAGE
python figures/world-rd-income/test_wording_release.py --archive BASE/pages-site.zip --site STAGE
```

The helper retains generated attributes, release download URLs and embedded data.
Fixed-period capacity text is explicitly applied in the helper because those
published strings do not exist in the selectable-period source. Published means
remain for **2000–2025**, with equal country weights and no imputation.

## Validation

- All ten Node regression suites (analytical, classification, UI and captions).
- `test_dashboard_ui_browser.py --url URL --baseline-url BASE_URL`: 31 routes;
  identical table values, flags and order; closed allowlist of approved headings;
  one approved source-map documentation correction; share/presentation/mobile.
- `test_source_captions_browser.py --url URL`: 31 routes, provider links,
  attribution switching, local redraws, SVG/PNG downloads and narrow layouts.
- `test_constant_ppp_browser.py --url URL`: three unchanged GDP options, exact
  WDI observations, cohorts, endpoints, history gaps, nominal R&D and CSV export.
- `test_wording_browser.py --url URL --baseline-url BASE_URL`: longer replacement
  SVG labels stay in bounds; 27 generated CSV exports are byte-identical.
- `test_wording_release.py`: only 18 presentation files change; every other file
  and all eight embedded JSON observation blocks are byte-identical.

Archive the staged site, checksum and validation report in a GitHub release,
then dispatch `publish-world-rd-snapshot.yml` with its tag and checksum. Verify the
completed workflow and live heading. Existing code/data download archives are
deliberately retained; the editorial source changes are available in Git history.
