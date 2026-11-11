/* Pure year-selection logic shared by the chart and Node verification. */
(function (root) {
  "use strict";
  function select(data, selected, mode, metric = "share") {
    const usable = r => r.status === "available" && (metric === "share" || (r.totalUSD !== null && r.amounts.every(v => v !== null)));
    const index = new Map(data.rows.map(r => [r.iso + ":" + r.year, r]));
    const years = iso => data.rows.filter(r => r.iso === iso && usable(r)).map(r => r.year);
    let common = null;
    if (mode === "common" && selected.length) {
      const candidates = years(selected[0]).filter(y => selected.every(iso => usable(index.get(iso + ":" + y) || {})));
      common = candidates.length ? Math.max(...candidates) : null;
    }
    return selected.map(iso => {
      const available = years(iso);
      const year = mode === "latest" ? (available.length ? Math.max(...available) : null) : mode === "common" ? common : Number(mode);
      const row = year === null ? null : index.get(iso + ":" + year);
      return {iso, year, row: row && usable(row) ? row : null,
        reason: year === null ? (mode === "common" ? "No common complete year" : "No complete observations") : !row || row.status !== "available" ? "Incomplete sector coverage" : "Missing same-year USD conversion"};
    });
  }
  const api = {select};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BroadSector = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
