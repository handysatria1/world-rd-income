/* Pure calculations shared by the offline browser and Node verification. */
(function (root) {
  "use strict";
  const SOURCE_NAMES = {oecd: "OECD MSTI", wdi: "UNESCO UIS via World Bank WDI", eustat: "Eustat (Basque Country)", ons: "ONS (UK; publication/GDP vintage break at 2022)"};
  const regressionRows = rows => rows.filter(r => r.country.regressionEligible !== false);
  const range = (start, end) => Array.from({length: Math.max(0, end - start + 1)}, (_, i) => start + i);
  function checkYears(data, start, end) {
    if (!Number.isInteger(start) || !Number.isInteger(end) || start > end || start < data.firstYear || end > data.lastYear)
      throw new Error(`Choose an ordered year range within ${data.firstYear}–${data.lastYear}.`);
  }
  function pickSource(country, years) {
    const count = source => years.filter(y => country.rd[source]?.[y] != null).length;
    const providers = country.rdProviders || Object.keys(SOURCE_NAMES).filter(s => country.rd[s]);
    return providers.reduce((best, source) => count(source) > count(best) ? source : best, providers[0]);
  }
  function rdSummary(country, start, end, source) {
    const requested = range(start, end);
    source = source || pickSource(country, requested);
    const years = requested.filter(y => country.rd[source]?.[y] != null);
    return {source, sourceName: SOURCE_NAMES[source], years, start, end,
      missing: requested.filter(y => !years.includes(y)), complete: years.length === requested.length,
      value: years.length ? years.reduce((s, y) => s + country.rd[source][y].v, 0) / years.length : null,
      flags: years.map(y => `${y}: ${country.rd[source][y].flags || "unflagged"}`).join("; ")};
  }
  function endpoint(country, gdpYear, start, end, strict, source) {
    const rd = rdSummary(country, start, end, source);
    const nominal = country.gdp.nominal[gdpYear]?.v ?? null;
    const ppp = country.gdp.ppp[gdpYear]?.v ?? null;
    const reasons = [];
    if (rd.value === null) reasons.push(`No R&D in ${start}–${end}`);
    else if (strict && !rd.complete) reasons.push(`Incomplete R&D in ${start}–${end}`);
    if (nominal === null) reasons.push(`Missing ${gdpYear} current-US$ GDP`);
    if (ppp === null) reasons.push(`Missing ${gdpYear} PPP GDP`);
    return {gdpYear, nominal, ppp, rd, reasons, eligible: !reasons.length};
  }
  function snapshot(data, options) {
    checkYears(data, options.rdStart, options.rdEnd);
    checkYears(data, options.gdpYear, options.gdpYear);
    const audit = data.countries.map(country => ({country,
      end: endpoint(country, options.gdpYear, options.rdStart, options.rdEnd, options.strict)}));
    return {audit, rows: audit.filter(r => r.end.eligible), rdStart: options.rdStart, rdEnd: options.rdEnd};
  }
  function comparison(data, options) {
    checkYears(data, options.from, options.to);
    if (options.from === options.to) throw new Error("Choose two different GDP years for a comparison.");
    checkYears(data, options.rdStart, options.rdEnd);
    const shift = options.timing === "aligned" ? options.from - options.to : 0;
    const earlyStart = options.rdStart + shift, earlyEnd = options.rdEnd + shift;
    checkYears(data, earlyStart, earlyEnd);
    const years = [...new Set([...range(earlyStart, earlyEnd), ...range(options.rdStart, options.rdEnd)])];
    const audit = data.countries.map(country => {
      // A single provider across both endpoints prevents source-switch artefacts.
      const source = pickSource(country, years);
      return {country,
        start: endpoint(country, options.from, earlyStart, earlyEnd, options.strict, source),
        end: endpoint(country, options.to, options.rdStart, options.rdEnd, options.strict, source)};
    });
    return {audit, rows: audit.filter(r => r.start.eligible && r.end.eligible), earlyStart, earlyEnd,
      startEligible: audit.filter(r => r.start.eligible).length, endEligible: audit.filter(r => r.end.eligible).length};
  }
  function latestSnapshot(data, options, common=false) {
    const years=range(data.firstYear,data.lastYear).reverse();
    const at=(country,year)=>endpoint(country,year,year,year,false);
    const commonYear=common&&data.countries.length?years.find(y=>data.countries.every(c=>at(c,y).eligible)):null;
    const audit=data.countries.map(country=>{
      const year=common?commonYear:years.find(y=>at(country,y).eligible);
      const end=at(country,year??data.lastYear);
      if(year==null){end.eligible=false;end.reasons.push(common?'No common exact year across the selected economies':'No year with R&D and both income measures');}
      return {country,end};
    });
    return {audit,rows:audit.filter(r=>r.end.eligible),latest:true,common,commonYear};
  }
  function history(data, iso, from, to) {
    checkYears(data, from, to);
    const country = data.countries.find(c => c.iso === iso);
    if (!country) throw new Error("Choose a country to see its history.");
    const years = range(from, to), source = pickSource(country, years);
    return {country, source, sourceName: SOURCE_NAMES[source], rows: years.map(year => ({year,
      nominal: country.gdp.nominal[year]?.v ?? null, ppp: country.gdp.ppp[year]?.v ?? null,
      rd: country.rd[source][year]?.v ?? null, flags: country.rd[source][year]?.flags || "",
      note: country.rd[source][year]?.note || "",
      rdNominalUSD: country.rdNominal?.usd[source]?.[year]?.v ?? null,
      rdNominalMissing: country.rdNominal?.usd[source]?.[year]?.missingReason || "",
      rdNominalEUR: country.rdNominal?.localEustat?.[year]?.v ?? null,
      rdNominalPPP: country.rdNominal?.pppEustat?.[year]?.v ?? null,
      gdpNominalNote: country.gdp.nominal[year]?.note || "", gdpPPPNote: country.gdp.ppp[year]?.note || "",
      gdpNominalFlags: country.gdp.nominal[year]?.flags || "", gdpPPPFlags: country.gdp.ppp[year]?.flags || "",
      gdpTotalUSD: country.gdpTotalUSD?.[year]?.v ?? null,
      gdpTotalFlags: country.gdpTotalUSD?.[year]?.flags || "",
      gdpTotalNote: country.gdpTotalUSD?.[year]?.note || "",
      rdNominalLocalOECD: country.rdNominal?.localOECD[year]?.v ?? null,
      rdNominalLocalFlags: country.rdNominal?.localOECD[year]?.flags || "",
      rdNominalLocalNote: country.rdNominal?.localOECD[year]?.note || "",
      rdNominalUSDOECD: country.rdNominal?.usd.oecd[year]?.v ?? null,
      rdNominalUSDWDI: country.rdNominal?.usd.wdi[year]?.v ?? null,
      rdNominalUSDUIS: country.rdNominal?.usd.uis[year]?.v ?? null,
      rdNominalUISFlags: country.rdNominal?.usd.uis[year]?.flags || "",
      rdNominalUISNote: country.rdNominal?.usd.uis[year]?.note || ""}))};
  }
  function sectorField(data, iso, year, basis) {
    checkYears(data, year, year);
    const dataset = data.sectorField, country = data.countries.find(c => c.iso === iso);
    if (!country) throw new Error("Choose an economy for the sector/field breakdown.");
    if (!dataset.bases[basis]) throw new Error("Choose a valid GERD unit and price basis.");
    const index = Object.fromEntries(dataset.columns.map((key, i) => [key, i])), cells = new Map();
    for (const row of dataset.rows) {
      if (row[index.iso3] !== iso || row[index.year] !== year || row[index.basis] !== basis) continue;
      const record = Object.fromEntries(dataset.columns.map((key, i) => [key, row[i]]));
      cells.set(`${record.sector_code}|${record.field_code}`, record);
    }
    const flagKeys = dataset.columns.filter(key => key.includes("STATUS"));
    const classification = dataset.areaClassifications?.[iso] || {};
    const sectors = Object.fromEntries((classification.sectors || dataset.defaultSectors || Object.keys(dataset.sectors)).map(k => [k,dataset.sectors[k]]));
    const fields = Object.fromEntries((classification.fields || dataset.defaultFields || Object.keys(dataset.fields)).map(k => [k,dataset.fields[k]]));
    const rows = [];
    for (const [field, label] of Object.entries(fields)) {
      for (const [sector, sectorLabel] of Object.entries(sectors)) {
        const cell = cells.get(`${sector}|${field}`);
        const sourceFile = cell?.source_file || (country.geographyType === "region" ? "" : dataset.sourceFile);
        const source = dataset.sources?.[sourceFile] || (sourceFile === dataset.sourceFile ? dataset.source : {});
        const conversion = dataset.sources?.[cell?.conversion_source_file] || {};
        const flags = Object.fromEntries(flagKeys.map(key => [key, cell?.[key] || ""]));
        const flagText = flagKeys.filter(key => flags[key]).map(key => {
          const book = key === "CONF_STATUS" ? "CL_CONF_STATUS" : key.startsWith("AUX") ? "CL_AUX_OBS_STATUS" : "CL_OBS_STATUS";
          return `${key}=${flags[key]}: ${dataset.flagLabels[book][flags[key]]}`;
        }).join("; ");
        rows.push({iso3:iso, economy:dataset.areaNames[iso] || country.name, year, sector_code:sector, sector:sectorLabel,
          field_code:field, field:label, sector_level:sector === "_T" ? "total" : sector === "BES_PNP" ? "combined_group" : "component",
          field_level:field === "_T" ? "total" : dataset.fieldGroups[field] ? "combined_group" : "component",
          field_parent:dataset.fieldParents[field] || "", basis, unit_code:dataset.bases[basis].unit,
          price_code:dataset.bases[basis].price, unit_and_price:dataset.bases[basis].label,
          currency_code:cell?.currency_code || "", base_year:cell?.base_year || "",
          amount:cell?.amount ?? null, amount_scale:"units", availability:cell?.availability || "not_returned",
          source_value:cell?.source_value ?? "", source_unit_multiplier:cell?.source_unit_multiplier ?? null,
          source_decimals:cell?.source_decimals ?? null, ...flags, flag_descriptions:flagText,
          source_file:sourceFile, source_url:source.url || "", retrieved_utc:source.retrieved_utc || "",
          value_status:cell?.value_status || (cell ? "reported" : ""), conversion_divisor:cell?.conversion_divisor || "",
          conversion_source_file:cell?.conversion_source_file || "", conversion_source_url:conversion.url || "",
          conversion_retrieved_utc:conversion.retrieved_utc || "", conversion_method:cell?.conversion_method || "",
          source_field_label:cell?.source_field_label || "", source_sector_label:cell?.source_sector_label || "",
          source_status:cell?.source_status || "",
          source_currency:country.geographyType === "region" ? "EUR" : cell?.currency_code || ""});
      }
    }
    return {country, year, basis, rows, sectors, fields, sourceCells:cells.size, available:rows.filter(r => r.amount !== null).length};
  }
  function ols(points) {
    if (points.length < 3 || points.some(p => !Number.isFinite(p.x) || p.x <= 0 || !Number.isFinite(p.y))) return null;
    const xs = points.map(p => Math.log(p.x)), ys = points.map(p => p.y), n = points.length;
    const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    const xx = xs.reduce((a, v) => a + (v - mx) ** 2, 0);
    const yy = ys.reduce((a, v) => a + (v - my) ** 2, 0);
    if (xx <= 0 || yy <= 0) return null;
    const xy = xs.reduce((a, v, i) => a + (v - mx) * (ys[i] - my), 0);
    return {n, intercept: my - xy / xx * mx, slope: xy / xx, r2: Math.max(0, Math.min(1, xy * xy / (xx * yy)))};
  }
  const api = {range, checkYears, pickSource, rdSummary, snapshot, latestSnapshot, comparison, history, sectorField, ols, regressionRows, SOURCE_NAMES};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RDCore = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
