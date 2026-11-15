# Research-presentation interface

`dashboard_ui.js` and `dashboard_ui.css` add a presentation layer without changing
source observations, country sampling, fits, aggregation or income-group marks.

- Four entry points: Overview, Country comparisons, Industry analysis, Data & methods.
- The view, year and economy selection remain accessible; secondary chart controls
  live under **Advanced options**. No analytical capability is removed.
- Snapshot titles identify R&D intensity and income, with the actual GDP price
  basis beneath them. Sample/fit statistics have keyboard-operable explanations.
- Plotted tables are collapsed, with a current row/economy count. Missing-data
  messages point to the unchanged coverage/exclusion audit.
- Source provider links remain beneath each chart/table. Detailed calculation
  notes move to **Methods & coverage**; SVG exports retain the note in a `desc`.
- **Presentation mode** hides filters, inspectors, tables and download buttons,
  retaining figures, titles, legends, visible source captions and coverage notes.
  Exit with the toolbar button or Escape, including from within a view iframe.
- **Share this view** stores a versioned configuration in the URL (not on a server).
  It includes ordered selected economies, global filters and the active frame's
  chart controls, including PPP basis, R&D windows, comparison years and industry
  filters. Clipboard failure exposes a selectable link. Data revisions can still
  change a view; cite the archived data release for reproducible observations.
- **Reset view** clears the shared configuration and reloads the default Overview.

Shared configurations are bounded and validated against known controls/options.
They do not execute code or populate markup. Unknown series, country IDs and
unavailable controls are ignored. Legacy hash links such as `#snapshot` still work.

Run `node test_dashboard_ui.js` and the optional Playwright test
`python test_dashboard_ui_browser.py --url http://127.0.0.1:8767/` against a built
site. Existing calculation, constant-PPP and source-caption suites remain in use.
Use `--baseline-url` on the UI browser test to compare every displayed table's
headings, values, flags and ordering with an earlier deployment across all routes.
