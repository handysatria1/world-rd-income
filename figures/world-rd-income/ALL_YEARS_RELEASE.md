# All-years CSV download

Adds **Download all years (CSV)** beside the existing national-view CSV download.
The complete 2000–2025 panel contains 219 economies × 26 years = 5,694 rows,
including 211 entirely missing economy/year rows. Missing numbers are blank;
observed zeros and the original numeric precision are retained.

## Contents and interpretation

- Economy code/name, geography type, parent economy and year.
- Annual R&D intensity (% of GDP), selected provider, flags, notes and source-selection rule.
- GDP per capita in current US dollars, current international dollars (PPP),
  and constant 2021 international dollars (PPP), each with source, flags, notes
  and the source record where present in the embedded dataset.
- Separate annual R&D observations, flags and notes for every provider.
- Regional qualifications and the embedded data-build timestamp.

The main R&D value uses the existing single-year source rule: a provider with
an observation wins, with existing provider priority breaking ties. Sources may
change between years. This differs from the trends chart's one-provider rule
over its whole selected period; neither chart calculations nor exports change.
GDP uses exact-year observations without filling or nearest-year substitution.
Basque constant-2021 PPP values remain blank; current-price regional conversions
retain their Spain-proxy qualifications. The export ignores chart and sample
filters and leaves the current chart state unchanged.

## Controlled publication

Base: `snapshot-2026-11-15-professional-wording`, archive SHA-256
`c38591479e41fd33dcdfeb9d3007dfa8cdfa2fa94c81cb563ed8f49326c9644e`.

`stage_all_years_release.py` applies only the feature diff from source commit
`46a99613ddba54f7683bc2350ff2b7a676629379` to embedded `view-national.html`.
All other 667 website files, existing downloads and embedded JSON remain
byte-identical. This is not a data refresh or a full source-template rebuild.
Unpublished enriched-snapshot/period-selection functionality is not deployed.
Published capacity means remain fixed at 2000–2025.

Validation passed on the staged snapshot:

- All 11 Node suites, including new annual-export edge-case fixtures.
- Actual browser CSV: all 5,694 rows checked against the embedded annual values,
  providers, flags, notes and source records; missingness, numeric precision,
  filter independence, chart-state preservation, desktop/mobile downloads.
- All 31 routes: identical baseline table values, flags and ordering; UI,
  share links, presentation/reset and mobile checks.
- All three GDP bases and exact WDI observations.
- Source captions, SVG/PNG exports and narrow-screen notes across all routes.
- 27 existing generated CSV exports byte-identical to the prior publication.
- File-set and byte-preservation audit.

Run browser suites sequentially to avoid local server/browser resource contention.
Package using the staging script's `--package` option after validation; publish
the checksummed archive using `publish-world-rd-snapshot.yml`, not the full-refresh
workflow.
