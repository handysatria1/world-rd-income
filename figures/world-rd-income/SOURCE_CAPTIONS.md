# Chart and table source captions

Every dashboard chart has a visible **Source:** footer and every table has a
source note immediately below its scrollable area. Provider names are linked.
Source footers are part of the SVG, so SVG/PNG downloads and printing retain
them. Notes identify calculated statistics rather than attributing them to a
provider as published aggregates.

`source_captions.js` resolves sources by view, indicator, selected source and
the provenance of the displayed rows. It distinguishes OECD GERD from
UNESCO UIS/WDI GERD; WIPO is cited for patent applications, not R&D expenditure.
Income-group notes cite the World Bank classification. Detailed value-added
tables cite their selected provider separately; China NBS native industries
and Eustat regional innovation context have their own notes. Source years,
classification vintage and period means follow the active controls.

The view bridge refreshes captions after asynchronous loads. A scoped DOM
observer covers local chart/table redraws, without changing observations,
missingness, fits or the selection. Captions are idempotent and do not accumulate
when controls change. Existing titles, source-cell tooltips, provider flags,
downloadable provenance and detailed methods remain available.

Run `node test_source_captions.js` for provider/metric/period and wrapping tests.
Browser verification should exercise all dashboard routes, local controls,
source switching, empty selections and exported figures.

For the optional end-to-end test, install Playwright in a development environment
(`pip install playwright`; use `playwright install chromium` on Linux), serve a
built site, then run `python test_source_captions_browser.py --url http://127.0.0.1:8765/`.
Windows uses the installed Microsoft Edge browser. This test does not refresh
source data or modify the website.
