# Frozen analysed study

The **Analysed study** tab (`#analysis`) publishes the latest `Global/` delivery from `World_RD_Income_Paper_2026-11-11`, including its policy brief and methods companion. Earlier Korea-centred revisions are not substituted for this global successor.

## Identity and reproducibility

`analysis/2026-11-11/snapshot.json` pins the portable study ZIP by SHA-256. `analysis_site.py` checks that hash and all 237 manifest payload hashes before publishing anything. The package contains frozen inputs, raw supplementary responses, pinned analytical scripts, reports, papers and workbooks. It is intentionally versioned independently from live-data builds. A weekly refresh republishes the same frozen study, not recalculated results against newer inputs.

The dashboard exposes country scatterplots (including internet use and government effectiveness), all 36 published conditional associations with intervals and samples, 120 comparable-intensity pairs, and 19 manufacturing standardisations. Each view includes a searchable data table and CSV/SVG exports. Original analytical CSVs preserve additional provenance and flags; documents, workbooks and the full portable package are downloadable.

The study's government-effectiveness indicator is **`GOV_WGI_GE.EST`, source 3, estimate units**. It can be negative. It is not the requested `GOV_WGI_GE_SC` 0–100 score, a percentile rank, or a converted equivalent. Internet use is `IT.NET.USER.ZS`, percent of population. Main observations are matched 2022; HCI uses 2020, and prior rents retain their actual years. Missing values remain missing.

## Interpretation and controls

- The default national sample contains 83 economies; Basque Country is excluded from national fits. Available samples differ by indicator.
- The study's sample control optionally uses dashboard-selected economies and its income filter, but does not recalculate published correlations, reference weights or ranks. Selected pair mode requires both members. Search only filters displayed rows.
- The scatter uses log PPP income, but displays levels and units. No regression or causal coefficient is estimated by the integration.
- Pair eligibility requires both an absolute intensity gap ≤0.15 pp and a relative gap ≤10% of the pair mean. Pairs overlap.
- Manufacturing standardisation is BERD / manufacturing GVA, not GERD/GDP or BERD / total GVA. Partial Singapore and Basque allocations are not completed.
- Model diagnostics, correlations and accounting counterfactuals are descriptive, not causal returns or efficiency rankings. Read the original research audit.

## Build and check

```sh
python -m unittest test_analysis_site.py
python analysis_site.py --destination /path/to/site
```

The ordinary `build_site.py` includes the study automatically through `dashboard_site.py`, and includes its source inputs and published files in the research ZIP. The full Pages artifact must still pass the existing 1 GB limit. For exact snapshot restoration, use the checksum-pinned Pages release workflow as documented in `AUTOMATION.md`.
