# Worldwide R&D and income

**[Open the interactive dashboard](https://handysatria1.github.io/world-rd-income/)**

Explore worldwide R&D intensity, income, funding, performing sectors and research types over **2000–2025**, including Basque Country. Choose years, 3-/5-year averages or custom windows, compare historical positions, and download each chart as CSV or SVG.

- [Current complete research package](https://handysatria1.github.io/world-rd-income/world-rd-income.zip): exact source responses, provenance, data, workbook, figures, code and validation reports.
- [Archived validated releases](https://github.com/handysatria1/world-rd-income/releases).
- [Methodology and coverage](figures/world-rd-income/README.md).
- [Official Eustat/ONS data and limitations](figures/world-rd-income/OFFICIAL_DATA.md).
- [Automation and reproduction](figures/world-rd-income/AUTOMATION.md).
- [Refresh/deployment runs](https://github.com/handysatria1/world-rd-income/actions).

## Suggested reference

If you use this dashboard, code, derived datasets or figures, please cite:

> Handy Satria. (2026). *Worldwide R&D and income explorer, 2000–2025* [Interactive dashboard and reproducible research software]. https://handysatria1.github.io/world-rd-income/

[BibTeX](CITATION.bib) · [Citation metadata (CFF)](CITATION.cff). GitHub also provides **Cite this repository** in the sidebar. For reproducibility, record the archived release tag or commit, data build timestamp and access date. Acknowledge the original data providers for the observations used; their details are preserved in the downloads.

## Updates

GitHub Actions checks the configured official sources every **Monday at 06:23 UTC**, validates the rebuilt outputs, and publishes successful builds to GitHub Pages. You can also run **Update worldwide R&D charts** manually. New ONS publication editions require reviewed mappings. See the automation guide for schedule limitations and maintenance.

The public branch tracks source code. Generated datasets, the self-contained offline HTML, chart downloads and reproducibility archives are published through the website and releases.

## Reproduce

Use Python 3.12 and Node.js 24. After cloning this repository:

```sh
cd figures/world-rd-income
python -m pip install -r requirements.txt
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
python build_site.py --destination ../../_site
```

Use an empty destination for packaging. For an exact archived vintage, extract its `world-rd-income.zip` and use its included code and raw inputs, omitting `download_data.py --refresh`. Missing observations, source flags, source vintages and reported-versus-derived distinctions are retained; country/region coverage varies by chart and year. Data attribution and source-specific licences are documented in the methodology and included source archives.
