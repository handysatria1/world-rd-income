(function () {
  "use strict";
  const data = JSON.parse(document.getElementById("history-data").textContent);
  const core = window.RDCore;
  const $ = id => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const TEAL = "#146b88", INK = "#172d3d", MUTED = "#536574", GRID = "#e1e7ec";
  const names = {KOR: "Korea", RUS: "Russia", HKG: "Hong Kong", MAC: "Macao", TUR: "Türkiye"};
  const priority = new Set("ES-PV NLD DNK CHN KOR GBR USA SGP IND IDN BRA RUS MEX ZAF ISR CHE LUX IRL JPN DEU AUS FRA SWE MAC QAT NOR HKG SAU".split(" "));
  const controls = ["metric", "gdpYear", "fromYear", "toYear", "scale", "rdMode", "rdStart", "rdEnd", "timing", "strict", "labels", "country", "sectorYear", "gerdBasis", "breakdownBasis", "breakdownSector", "shareMode", "breakdownPercentages"];
  const exampleEconomies = ["USA","CHN","KOR","GBR","SGP","ES-PV"];
  let breakdownEconomies = [...exampleEconomies];
  let view = "snapshot", current = null, exported = [];
  const fmt = (v, digits = 2) => v == null || !Number.isFinite(v) ? "—" : v.toLocaleString("en-US", {maximumFractionDigits: digits, minimumFractionDigits: digits});
  const short = v => v >= 1e12 ? `${+(v / 1e12).toFixed(1)}tn` : v >= 1e9 ? `${+(v / 1e9).toFixed(1)}bn` : v >= 1e6 ? `${+(v / 1e6).toFixed(1)}m` : v >= 1000 ? `${+(v / 1000).toFixed(1)}k` : `${+v.toFixed(2)}`;
  const unit = () => $("metric").value === "nominal" ? "current US dollars" : "current international dollars (PPP)";
  const rdWindow = (start, end) => start === end ? `${start}` : `${start}–${end}`;
  function element(tag, attrs = {}, text, parent) {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    if (text != null) node.textContent = text;
    if (parent) parent.appendChild(node);
    return node;
  }
  function text(parent, x, y, content, attrs = {}) {
    return element("text", {x, y, fill: MUTED, "font-size": 12, ...attrs}, content, parent);
  }
  function line(parent, x1, y1, x2, y2, attrs = {}) {
    return element("line", {x1, y1, x2, y2, stroke: GRID, ...attrs}, null, parent);
  }
  function niceStep(value) {
    const power = 10 ** Math.floor(Math.log10(value || 1)), scaled = value / power;
    return (scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10) * power;
  }
  function options() {
    const end = +$("rdEnd").value;
    return {metric: $("metric").value, gdpYear: +$("gdpYear").value,
      rdStart: $("rdMode").value === "custom" ? +$("rdStart").value : end - +$("rdMode").value + 1,
      rdEnd: end, strict: $("strict").checked, from: +$("fromYear").value, to: +$("toYear").value,
      timing: $("timing").value, scale: $("scale").value};
  }
  function setView(value) {
    view = value;
    if (["history", "sector"].includes(view) && !$("country").value) $("country").value = "GBR";
    render();
  }
  function reset() {
    const defaults = {metric: "nominal", gdpYear: "2025", fromYear: "2010", toYear: "2025",
      scale: "linear", rdMode: "5", rdStart: "2020", rdEnd: "2024", timing: "aligned", country: "", sectorYear:"2023", gerdBasis:"XDC_V",
      breakdownBasis:"USD_PPP_Q",breakdownSector:"",shareMode:"ratio"};
    for (const [id, value] of Object.entries(defaults)) $(id).value = value;
    $("strict").checked = false; $("labels").checked = true; $("search").value = "";
    $("breakdownPercentages").checked = true;
    breakdownEconomies=[...exampleEconomies];
    view = "snapshot"; render();
  }
  function layoutControls() {
    document.querySelectorAll("[data-view]").forEach(b => b.setAttribute("aria-pressed", b.dataset.view === view));
    $("gdp-year-control").hidden = view !== "snapshot";
    document.querySelectorAll(".range-control").forEach(n => { n.hidden = !["compare", "history"].includes(view); });
    $("rd-controls").hidden = ["history", "sector"].includes(view);
    $("timing-control").hidden = view !== "compare";
    $("rd-start-control").hidden = $("rdMode").value !== "custom";
    $("scale-control").hidden = ["history", "sector", "breakdown"].includes(view);
    $("search").parentElement.hidden = ["history", "sector", "breakdown"].includes(view);
    $("metric").parentElement.hidden = ["sector", "breakdown"].includes(view);
    $("breakdown-controls").hidden = view !== "breakdown";
    $("breakdown-dashboard").hidden = view !== "breakdown";
    for(const id of ["single-chart","single-table","inspector"])$(id).hidden = view === "breakdown";
    $("country").parentElement.hidden = view === "breakdown";
    $("example").hidden = view === "breakdown";
    $("labels").parentElement.hidden = view === "breakdown";
    $("export-svg").hidden = true;
    $("sector-year-control").hidden = view !== "sector";
    $("gerd-basis-control").hidden = view !== "sector";
    $("export").textContent = view === "sector" ? "Download selected cells CSV" : "Download plotted CSV";
    $("history-button").hidden = ["history", "breakdown"].includes(view);
    $("history-button").disabled = !$("country").value;
  }
  function stat(label, value, target = $("stats")) {
    const node = document.createElement("div"); node.className = "stat";
    const strong = document.createElement("strong"), span = document.createElement("span");
    strong.textContent = value; span.textContent = label; node.append(strong, span); target.appendChild(node);
  }
  function details(row, endpoint = "end") {
    const e = row[endpoint], c = row.country;
    return `${c.name} (${c.iso})\nGDP ${e.gdpYear}: ${fmt(e[$("metric").value])} ${unit()}\n` +
      `R&D mean: ${fmt(e.rd.value, 4)}% of GDP · window ${rdWindow(e.rd.start, e.rd.end)}\n` +
      `Reported years: ${e.rd.years.join(", ") || "none"} (${e.rd.years.length}/${e.rd.end - e.rd.start + 1})\n` +
      `Missing years: ${e.rd.missing.join(", ") || "none"}\nSource: ${e.rd.sourceName}\nFlags: ${e.rd.flags || "none reported"}` +
      (c.note ? `\n${c.note}\nGDP flags: ${c.gdp[$("metric").value][e.gdpYear]?.flags || ""}` : "") +
      (e.reasons.length ? `\nExcluded: ${e.reasons.join("; ")}` : "");
  }
  function tooltip(node, content, onClick) {
    element("title", {}, content, node);
    node.setAttribute("tabindex", "0"); node.setAttribute("role", "button");
    node.setAttribute("aria-label", content);
    const show = event => {
      const tip = $("tooltip"); tip.textContent = content; tip.hidden = false;
      const rect = node.getBoundingClientRect();
      const x = event.clientX ?? rect.x, y = event.clientY ?? rect.y;
      tip.style.left = `${Math.max(8, Math.min(x + 16, window.innerWidth - tip.offsetWidth - 10))}px`;
      tip.style.top = `${Math.max(8, Math.min(y + 14, window.innerHeight - tip.offsetHeight - 10))}px`;
    };
    node.addEventListener("pointerenter", show); node.addEventListener("focus", show);
    node.addEventListener("pointerleave", () => { $("tooltip").hidden = true; });
    node.addEventListener("blur", () => { $("tooltip").hidden = true; });
    node.addEventListener("click", () => { $("tooltip").hidden = true; onClick(); });
    node.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } });
  }
  function inspect(iso) { $("country").value = iso; render(); }
  function countryInfo() {
    const iso = $("country").value;
    if (!iso || !current || view === "history") return;
    const row = current.audit.find(r => r.country.iso === iso);
    if (!row) return;
    $("inspector").textContent = row.start ? `${details(row, "start")}\n\n${details(row)}` : details(row);
  }
  function axes(svg, xs, ys, log) {
    const bounds = {left: 78, right: 1205, top: 34, bottom: 578};
    const xmax = log ? Math.max(...xs) * 1.15 : Math.ceil(Math.max(...xs) * 1.10 / niceStep(Math.max(...xs) / 6)) * niceStep(Math.max(...xs) / 6);
    const xmin = log ? Math.min(...xs) * .8 : 0;
    const ymax = Math.max(1, Math.ceil(Math.max(...ys) * 1.16 / niceStep(Math.max(...ys) / 7)) * niceStep(Math.max(...ys) / 7));
    const x = value => bounds.left + (log ? Math.log(value / xmin) / Math.log(xmax / xmin) : value / xmax) * (bounds.right - bounds.left);
    const y = value => bounds.bottom - value / ymax * (bounds.bottom - bounds.top);
    const xticks = [];
    if (log) {
      for (let p = Math.floor(Math.log10(xmin)); p <= Math.ceil(Math.log10(xmax)); p++)
        for (const factor of [1, 2, 5]) { const v = factor * 10 ** p; if (v >= xmin && v <= xmax) xticks.push(v); }
    } else for (let v = 0, step = niceStep(xmax / 7); v <= xmax * 1.001; v += step) xticks.push(v);
    for (const v of xticks) { line(svg, x(v), bounds.top, x(v), bounds.bottom); text(svg, x(v), bounds.bottom + 26, short(v), {"text-anchor": "middle"}); }
    const ystep = niceStep(ymax / 7);
    for (let v = 0; v <= ymax * 1.001; v += ystep) { line(svg, bounds.left, y(v), bounds.right, y(v)); text(svg, bounds.left - 12, y(v) + 4, short(v), {"text-anchor": "end"}); }
    line(svg, bounds.left, bounds.top, bounds.left, bounds.bottom, {stroke: "#aabdc9"});
    line(svg, bounds.left, bounds.bottom, bounds.right, bounds.bottom, {stroke: "#aabdc9"});
    text(svg, (bounds.left + bounds.right) / 2, bounds.bottom + 65, `GDP per capita (${unit()})${log ? " · logarithmic display" : ""}`, {"text-anchor": "middle", fill: INK, "font-size": 14});
    text(svg, 22, (bounds.top + bounds.bottom) / 2, "Mean R&D expenditure (% of GDP)", {"text-anchor": "middle", fill: INK, "font-size": 14, transform: `rotate(-90 22 ${(bounds.top + bounds.bottom) / 2})`});
    return {x, y, xmax, ymax, ...bounds};
  }
  function trend(svg, rows, endpoint, options, coordinates, faded) {
    const points = core.regressionRows(rows).map(r => ({x: r[endpoint][options.metric], y: r[endpoint].rd.value}));
    const fit = core.ols(points); if (!fit) return null;
    const min = Math.min(...points.map(p => p.x)), max = Math.max(...points.map(p => p.x));
    let d = "", drawing = false;
    for (let i = 0; i <= 160; i++) {
      const value = min * (max / min) ** (i / 160), prediction = fit.intercept + fit.slope * Math.log(value);
      if (prediction < 0 || prediction > coordinates.ymax) { drawing = false; continue; }
      d += `${drawing ? "L" : "M"}${coordinates.x(value)},${coordinates.y(prediction)} `; drawing = true;
    }
    element("path", {d, class: "trend", opacity: faded ? .4 : .9, "stroke-dasharray": faded ? "8 6" : "3 5"}, null, svg);
    return fit;
  }
  function addLabels(svg, entries, markerBoxes, bounds) {
    if (!$("labels").checked) return;
    const occupied = [], overlap = (a, b) => a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y;
    const ordered = [...entries].sort((a, b) => (b.row.country.iso === $("country").value) - (a.row.country.iso === $("country").value) ||
      Number(priority.has(b.row.country.iso)) - Number(priority.has(a.row.country.iso)) || a.neighbours - b.neighbours || a.y - b.y);
    for (const e of ordered) {
      if (e.neighbours >= 5 && !priority.has(e.row.country.iso) && e.row.country.iso !== $("country").value) continue;
      const label = text(e.group, 0, 0, (names[e.row.country.iso] || e.row.country.name) + (e.row.end.rd.complete ? "" : "*"), {class: "country-label", id: `label-${e.row.country.iso}`});
      let placed = false;
      for (const [dx, dy, anchor] of [[10,-10,"start"],[10,20,"start"],[-10,-10,"end"],[-10,20,"end"],[15,4,"start"],[-15,4,"end"],[26,4,"start"],[-26,4,"end"],[0,-17,"middle"],[0,28,"middle"]]) {
        label.setAttribute("x", e.x + dx); label.setAttribute("y", e.y + dy); label.setAttribute("text-anchor", anchor);
        const b = label.getBBox(), box = {x: b.x - 3, y: b.y - 3, width: b.width + 6, height: b.height + 6};
        if (box.x < bounds.left + 2 || box.x + box.width > bounds.right - 2 || box.y < bounds.top + 2 || box.y + box.height > bounds.bottom - 2) continue;
        if ([...occupied, ...markerBoxes].some(other => overlap(box, other))) continue;
        occupied.push(box); placed = true;
        if (Math.hypot(dx, dy) > 20) line(e.group, e.x, e.y, e.x + dx * .7, e.y + dy * .7, {stroke: TEAL, opacity: .4, "stroke-width": .7});
        break;
      }
      if (!placed) label.remove();
    }
  }
  function scatter(result, opts) {
    const rows = result.rows;
    if (!rows.length) { $("charts").innerHTML = '<p class="empty">No economies meet this selection. Try another year or allow reported-year averages.</p>'; return; }
    const svg = element("svg", {class: "chart", viewBox: "0 0 1240 670", role: "img", "aria-label": $("chart-title").textContent}, null, $("charts"));
    const endpoints = rows.flatMap(r => r.start ? [r.start, r.end] : [r.end]);
    const c = axes(svg, endpoints.map(e => e[opts.metric]), endpoints.map(e => e.rd.value), opts.scale === "log");
    const defs = element("defs", {}, null, svg);
    const arrow = element("marker", {id: "movement-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 5, markerHeight: 5, orient: "auto-start-reverse"}, null, defs);
    element("path", {d: "M 0 0 L 10 5 L 0 10 z", fill: TEAL}, null, arrow);
    if (view === "compare") trend(svg, rows, "start", opts, c, true);
    trend(svg, rows, "end", opts, c, false);
    const entries = [], markerBoxes = [];
    for (const row of rows) {
      const group = element("g", {class: "economy", "data-iso": row.country.iso, "data-name": row.country.name.toLowerCase()}, null, svg);
      const x = c.x(row.end[opts.metric]), y = c.y(row.end.rd.value), chosen = row.country.iso === $("country").value;
      if (row.start) {
        const sx = c.x(row.start[opts.metric]), sy = c.y(row.start.rd.value);
        line(group, sx, sy, x, y, {stroke: TEAL, opacity: chosen ? .9 : .25, "stroke-width": chosen ? 2 : 1, "marker-end": "url(#movement-arrow)"});
        const start = element("rect", {x: sx - 4, y: sy - 4, width: 8, height: 8, fill: "white", stroke: TEAL, opacity: .65, class: "point", "data-endpoint": "start"}, null, group);
        tooltip(start, details(row, "start"), () => inspect(row.country.iso));
        markerBoxes.push({x:sx-6,y:sy-6,width:12,height:12});
      }
      if (chosen) element("circle", {cx:x,cy:y,r:11,fill:"none",stroke:TEAL,"stroke-width":1,opacity:.4}, null, group);
      const point = element("circle", {cx:x,cy:y,r:chosen?6:4.5,fill:row.end.rd.complete?TEAL:"white",stroke:TEAL,"stroke-width":1.3,class:"point","data-endpoint":"end"}, null, group);
      tooltip(point, details(row), () => inspect(row.country.iso));
      markerBoxes.push({x:x-6,y:y-6,width:12,height:12});
      entries.push({row, group, x, y});
    }
    for (const e of entries) e.neighbours = entries.filter(other => other !== e && Math.hypot(e.x-other.x,e.y-other.y)<34).length;
    addLabels(svg, entries, markerBoxes, c);
  }
  function annualChart(result, key, title) {
    const heading = document.createElement("h3"); heading.className = "history-title"; heading.textContent = title; $("charts").appendChild(heading);
    const values = result.rows.filter(r => r[key] != null);
    if (!values.length) { const p=document.createElement("p");p.className="empty";p.textContent="No available observations for this series and range.";$("charts").appendChild(p);return; }
    const svg = element("svg", {class:"chart",viewBox:"0 0 1240 300",role:"img","aria-label":title}, null, $("charts"));
    const a=result.rows[0].year,b=result.rows.at(-1).year,left=78,right=1205,top=22,bottom=244;
    const step=niceStep(Math.max(...values.map(r=>r[key]))/4),max=Math.max(step,Math.ceil(Math.max(...values.map(r=>r[key]))*1.12/step)*step);
    const x=year=>left+(year-a)/Math.max(1,b-a)*(right-left),y=value=>bottom-value/max*(bottom-top);
    for(let v=0;v<=max*1.001;v+=step){line(svg,left,y(v),right,y(v));text(svg,left-12,y(v)+4,key==="rd"?fmt(v,1):short(v),{"text-anchor":"end"});}
    const yearStep=Math.max(1,Math.ceil((b-a)/10));
    for(let year=a;year<=b;year+=yearStep){line(svg,x(year),top,x(year),bottom);text(svg,x(year),bottom+26,year,{"text-anchor":"middle"});}
    if((b-a)%yearStep)text(svg,x(b),bottom+26,b,{"text-anchor":"middle"});
    let d="",drawing=false;
    for(const row of result.rows){if(row[key]==null){drawing=false;continue;}d+=`${drawing?"L":"M"}${x(row.year)},${y(row[key])} `;drawing=true;}
    element("path",{d,fill:"none",stroke:TEAL,"stroke-width":2},null,svg);
    for(const row of values){
      const point=element("circle",{cx:x(row.year),cy:y(row[key]),r:4,fill:TEAL,class:"point","data-year":row.year},null,svg);
      const content=`${result.country.name} · ${row.year}\nGDP per capita: ${fmt(row[$("metric").value])} ${unit()}\nAnnual R&D: ${fmt(row.rd,4)}% of GDP\nR&D source: ${result.sourceName}\nFlags: ${row.flags||"unflagged"}${row.note?"\n"+row.note:""}`+
        `\nNominal R&D (derived): ${fmt(row.rdNominalUSD)} current US$\nCalculation: ${result.source === "eustat" ? data.nominalRD.basqueMethod : data.nominalRD.formula}\nTotal GDP: ${fmt(row.gdpTotalUSD)} current US$\nGDP flags: ${row.gdpTotalFlags||"unflagged"}${row.gdpTotalNote?"\n"+row.gdpTotalNote:""}${row.rdNominalMissing?"\n"+row.rdNominalMissing:""}` +
        (result.source === "eustat" ? `\nReported R&D: ${fmt(row.rdNominalEUR)} EUR\nDerived PPP R&D: ${fmt(row.rdNominalPPP)} current international dollars (Spain national PPP proxy)\nGDP/person flags: ${row.gdpNominalFlags}; ${row.gdpPPPFlags}` : "");
      tooltip(point,content,()=>{$("inspector").textContent=content;});
    }
  }
  function table(rows, columns, target = $("data-table")) {
    const head=target.tHead,body=target.tBodies[0];head.replaceChildren();body.replaceChildren();
    const header=document.createElement("tr");
    for(const col of columns){const th=document.createElement("th");th.textContent=col.label;header.appendChild(th);}head.appendChild(header);
    for(const record of rows){const tr=document.createElement("tr");tr.dataset.iso=record.code||"";tr.dataset.name=(record.economy||"").toLowerCase();
      if(record.code===$("country").value)tr.className="selected";
      for(const col of columns){const td=document.createElement("td"),value=record[col.key];td.textContent=col.format?col.format(value):value==null?"—":String(value);tr.appendChild(td);}
      if(!["history","sector","breakdown"].includes(view))tr.addEventListener("click",()=>inspect(record.code));body.appendChild(tr);
    }
  }
  function plottedTable(result,opts) {
    exported=result.rows.map(r=>({economy:r.country.name,code:r.country.iso,rd_source:r.end.rd.sourceName,
      geography_type:r.country.geographyType||"economy",parent_economy:r.country.parentEconomy||"",regression_included:r.country.regressionEligible!==false,regional_note:r.country.note||"",
      ...(r.start?{start_gdp_year:r.start.gdpYear,start_gdp:r.start[opts.metric],start_rd:r.start.rd.value,start_rd_window:rdWindow(r.start.rd.start,r.start.rd.end),start_rd_years:r.start.rd.years.join(";"),start_rd_flags:r.start.rd.flags}:{}),
      gdp_year:r.end.gdpYear,gdp_unit:unit(),gdp:r.end[opts.metric],rd:r.end.rd.value,rd_window:rdWindow(r.end.rd.start,r.end.rd.end),rd_years:r.end.rd.years.join(";"),rd_missing:r.end.rd.missing.join(";"),rd_flags:r.end.rd.flags,
      ...(r.start?{gdp_change:r.end[opts.metric]-r.start[opts.metric],gdp_change_percent:(r.end[opts.metric]/r.start[opts.metric]-1)*100,rd_change_pp:r.end.rd.value-r.start.rd.value}:{}),
      gdp_status:r.country.gdp[opts.metric][r.end.gdpYear]?.flags||"",gdp_footnote:r.country.gdp[opts.metric][r.end.gdpYear]?.note||""}));
    const columns=[{key:"economy",label:"Economy"},{key:"code",label:"Code"}];
    if(view==="compare")columns.push({key:"start_gdp",label:`GDP ${opts.from}`,format:v=>fmt(v)},{key:"start_rd",label:"Earlier R&D (%)",format:v=>fmt(v,4)});
    columns.push({key:"gdp",label:`GDP ${view==="compare"?opts.to:opts.gdpYear}`,format:v=>fmt(v)},{key:"rd",label:"R&D mean (%)",format:v=>fmt(v,4)});
    if(view==="compare")columns.push({key:"gdp_change_percent",label:"GDP change (%)",format:v=>fmt(v,1)},{key:"rd_change_pp",label:"R&D change (pp)",format:v=>fmt(v,3)},{key:"start_rd_years",label:"Earlier R&D years"});
    columns.push({key:"rd_years",label:"Reported R&D years"},{key:"rd_source",label:"R&D source"});table(exported,columns);
    $("table-title").textContent="Plotted data";
    $("table-description").textContent=`Income in ${unit()}. Search filters this table and highlights points; it does not change the sample or regression. CSV includes windows, missing years and flags.`;
    const excluded=result.audit.filter(r=>!r.end.eligible||(r.start&&!r.start.eligible));
    $("audit-section").hidden=false;$("audit-title").textContent=`Coverage and exclusions · ${excluded.length} of ${data.countries.length} audited economies excluded`;
    const tbody=$("audit-table").tBodies[0];tbody.replaceChildren();
    for(const r of excluded){const tr=document.createElement("tr");const reasons=r.start?[...r.start.reasons.map(s=>`${opts.from}: ${s}`),...r.end.reasons.map(s=>`${opts.to}: ${s}`)]:r.end.reasons;
      for(const v of [r.country.name,r.country.iso,reasons.join("; ")]){const td=document.createElement("td");td.textContent=v;tr.appendChild(td);}tbody.appendChild(tr);}
  }
  function applySearch() {
    const query=["history","sector","breakdown"].includes(view)?"":$("search").value.trim().toLowerCase();
    const matches=node=>!query||(node.dataset.name||"").includes(query)||(node.dataset.iso||"").toLowerCase().includes(query);
    document.querySelectorAll(".economy").forEach(node=>node.classList.toggle("dimmed",!matches(node)));
    $("data-table").tBodies[0].querySelectorAll("tr").forEach(row=>{row.hidden=!matches(row);});
  }
  function sectorMatrix(result) {
    const dataset=data.sectorField, scroll=document.createElement("div"), matrix=document.createElement("table");
    scroll.className="table-scroll sector-matrix";matrix.setAttribute("aria-label","GERD by field and sector, millions");
    const head=document.createElement("thead"), header=document.createElement("tr");
    for(const label of ["Field of R&D · millions",...Object.values(result.sectors)]){const th=document.createElement("th");th.textContent=label;th.scope="col";header.appendChild(th);}
    head.appendChild(header);matrix.appendChild(head);
    const body=document.createElement("tbody"), markers={confidential_or_restricted:"C",included_elsewhere:"I",missing_source_value:"M",missing_conversion_factor:"M",not_returned:"—"};
    for(const [field,label] of Object.entries(result.fields)){
      const tr=document.createElement("tr"), th=document.createElement("th");th.scope="row";
      th.textContent=label+(dataset.fieldGroups[field]?" (combined group)":"");tr.appendChild(th);
      if(field==="_T"||dataset.fieldGroups[field])tr.className="aggregate";
      for(const sector of Object.keys(result.sectors)){
        const row=result.rows.find(r=>r.field_code===field&&r.sector_code===sector),td=document.createElement("td"),button=document.createElement("button");
        button.type="button";button.className="matrix-cell";
        button.textContent=row.amount===null?markers[row.availability]:fmt(row.amount/1e6,3)+(row.flag_descriptions?" *":"");
        const detail=`${row.economy} · ${row.year}\n${row.sector} · ${row.field}\n${row.unit_and_price}\nAmount: ${fmt(row.amount,2)} units · ${row.currency_code||"currency not supplied"}${row.base_year?" · base year "+row.base_year:""}\nAvailability: ${row.availability}\n${row.flag_descriptions||"No source flags"}\nValue status: ${row.value_status || "not returned"}\nSource: ${row.source_file || "none"}\n${row.source_url}\n${row.conversion_method}`;
        button.title=detail;button.setAttribute("aria-label",detail);button.addEventListener("click",()=>{$("inspector").textContent=detail;});
        td.appendChild(button);tr.appendChild(td);
      }
      body.appendChild(tr);
    }
    matrix.appendChild(body);scroll.appendChild(matrix);$("charts").appendChild(scroll);
  }
  const breakdownColors={GOV:"#4779b5",BES:"#e08c32",HES:"#64a46c",PNP:"#b874a3",ROW:"#8a77b0",BES_PNP:"#ca9847",BR:"#4779b5",AR:"#e08c32",ED:"#64a46c",CAP_EX_NEC:"#b874a3"};
  const breakdownLabels={GOV:"Government",BES:"Business",HES:"Higher education",PNP:"Private non-profit",ROW:"Rest of the world",BES_PNP:"Business + private non-profit",BR:"Basic research",AR:"Applied research",ED:"Experimental development",CAP_EX_NEC:"Capital, not elsewhere recorded"};
  function breakdownChart(result, panel, spec) {
    const $=id=>panel.querySelector(`[data-role="${id}"]`);
    const opts=result.opts, percentage=opts.chart.endsWith("share"), overlay=["funding_amount","performer_amount"].includes(opts.chart);
    $("chart-title").textContent=`${spec.title} · ${rdWindow(opts.rdStart,opts.rdEnd)}`;
    const basis=data.breakdowns.bases[opts.basis].label;
    $("selection-description").textContent=`${basis} · ${percentage?(opts.shareMode==="annual"?"Mean annual shares":"Ratio of sums on common years"):"Mean annual expenditure, billions"}${result.kind==="research"?" · Performer: "+data.breakdowns.sectors[opts.sector]:""}.`;
    stat("Selected economies",result.rows.length,$("stats"));stat("Bars with observations",result.rows.filter(r=>r.years.length).length,$("stats"));
    stat("Full requested year coverage",result.rows.filter(r=>r.years.length===opts.rdEnd-opts.rdStart+1).length,$("stats"));
    $("legend").replaceChildren();$("legend").className="legend breakdown-legend";
    const codes=[...new Set(result.rows.flatMap(r=>r.parts.map(p=>p.code)))];
    for(const code of [...codes,"residual"]){const span=document.createElement("span"),swatch=document.createElement("i");swatch.style.background=breakdownColors[code]||"#d1d8df";span.append(swatch,document.createTextNode(breakdownLabels[code]||"Unallocated difference (derived)"));$("legend").appendChild(span);}
    if(overlay){const span=document.createElement("span");span.textContent="● R&D intensity · right axis";$("legend").appendChild(span);}
    const width=Math.max(1000,result.rows.length*145+170), left=85,right=width-90,top=50,bottom=440;
    const svg=element("svg",{class:"chart",viewBox:`0 0 ${width} 555`,role:"img","aria-label":$("chart-title").textContent,"font-family":"system-ui, sans-serif"},null,$("charts"));
    const amounts=result.rows.map(r=>percentage?Math.max(100,r.parts.reduce((s,p)=>s+(p.share||0),0)):Math.max(r.total||0,r.parts.reduce((s,p)=>s+(p.amount||0),0))/1e9);
    const max=percentage?Math.max(100,...amounts)*1.04:Math.max(1,...amounts)*1.15, step=percentage?20:niceStep(max/5);
    const y=v=>bottom-v/max*(bottom-top);
    for(let v=0;v<=max;v+=step){line(svg,left,y(v),right,y(v));text(svg,left-12,y(v)+4,short(v),{"text-anchor":"end"});}
    text(svg,left,25,percentage?"Share of reported expenditure (%)":"Mean annual expenditure (billions)",{fill:INK,"font-size":14});
    let iy;
    if(overlay){const imax=Math.max(1,...result.rows.map(r=>r.intensity||0))*1.25;iy=v=>bottom-v/imax*(bottom-top);
      for(let v=0,st=niceStep(imax/5);v<=imax;v+=st){text(svg,right+12,iy(v)+4,fmt(v,1)+"%",{fill:TEAL});}
      text(svg,right,25,"GERD / GDP (%)",{"text-anchor":"end",fill:TEAL,"font-size":14});}
    const band=(right-left)/Math.max(1,result.rows.length),barWidth=Math.min(86,band*.62);
    result.rows.forEach((r,i)=>{
      const x=left+band*(i+.5), country=names[r.country.iso]||r.country.name;
      const detail=`${country} (${r.country.iso})\nYears: ${r.years.join(", ")||"none"}\nMissing years: ${r.missingYears.join(", ")||"none"}\nMissing categories: ${r.missingCategories.join(", ")||"none"}\nMean reported total: ${fmt(r.total)}\nAccounting difference: ${fmt(r.residual)}\nIntensity: ${fmt(r.intensity,3)}% (${r.intensitySource})`;
      const labelShare=(code,share,start,value)=>{
        if(!opts.showPercentages||share===null||value<=0)return;
        const upper=y(start+value),lower=y(start),label=fmt(share,1)+"%";
        if(lower-upper<20||barWidth<label.length*7+8)return;
        let middle=(upper+lower)/2;
        if(overlay&&r.intensity!==null&&Math.abs(iy(r.intensity)-middle)<15){
          const alternatives=[upper+10,lower-10];
          middle=alternatives.find(v=>Math.abs(iy(r.intensity)-v)>=15);
          if(middle===undefined)return;
        }
        text(svg,x,middle+4,label,{class:"segment-percentage","data-iso":r.country.iso,"data-category":code,"data-share":share,
          "text-anchor":"middle",fill:["BES","HES","BES_PNP","AR","ED","residual"].includes(code)?INK:"white","font-size":12,"pointer-events":"none"});
      };
      let stacked=0;
      for(const p of r.parts){const value=percentage?p.share:p.amount===null?null:p.amount/1e9;if(value===null)continue;
        const rect=element("rect",{x:x-barWidth/2,y:y(stacked+value),width:barWidth,height:Math.max(0,y(stacked)-y(stacked+value)),fill:breakdownColors[p.code],"data-iso":r.country.iso,"data-category":p.code},null,svg);
        tooltip(rect,`${detail}\n${p.label}: ${fmt(p.amount)} units · ${fmt(p.share,3)}%`,()=>{$("inspector").textContent=detail+"\n"+p.label+": "+fmt(p.amount)+" units; "+fmt(p.share,3)+"%";});
        labelShare(p.code,p.share,stacked,value);
        stacked+=value;
      }
      const residual=percentage?r.residualShare:r.residual===null?null:r.residual/1e9;
      if(residual>0){const rect=element("rect",{x:x-barWidth/2,y:y(stacked+residual),width:barWidth,height:y(stacked)-y(stacked+residual),fill:"#d1d8df"},null,svg);tooltip(rect,detail+"\nGrey: reported total minus known segments; not a measured category.",()=>{$("inspector").textContent=detail;});labelShare("residual",r.residualShare,stacked,residual);}
      if(!r.years.length)text(svg,x,bottom-25,"No data",{"text-anchor":"middle","font-size":13});
      else if(!percentage)text(svg,x,y(Math.max(stacked,(r.total||0)/1e9))-12,fmt(r.total/1e9,r.total<1e10?2:1),{"text-anchor":"middle",fill:INK});
      if(overlay&&r.intensity!==null){const point=element("circle",{cx:x,cy:iy(r.intensity),r:5.5,fill:TEAL,stroke:"white","stroke-width":1.5},null,svg);tooltip(point,detail,()=>{$("inspector").textContent=detail;});}
      const words=country==="United States"?["United States"]:country==="United Kingdom"?["United Kingdom"]:country.split(/(?<=\S)\s+(?=\S)/);
      // Wrap long country names into at most two readable lines.
      const lines=country.length<=18?[country]:[words.slice(0,Math.ceil(words.length/2)).join(" "),words.slice(Math.ceil(words.length/2)).join(" ")];
      lines.forEach((s,j)=>text(svg,x,bottom+27+j*17,s,{"text-anchor":"middle",fill:TEAL,"font-weight":400}));
      const yearLabel=r.years.length?(r.years.length===1?String(r.years[0]):`${r.years[0]}–${r.years.at(-1)}${r.years.at(-1)-r.years[0]+1===r.years.length?"":" · gaps"}`):"No eligible years";
      text(svg,x,bottom+66,yearLabel,{"text-anchor":"middle","font-size":10});
       if(r.years.length)text(svg,x,bottom+83,`${r.years.length}/${opts.rdEnd-opts.rdStart+1} years${r.missingCategories.length?" · partial categories":""}`,{"text-anchor":"middle","font-size":10});
       if(result.kind==="research"&&r.country.iso==="ES-PV")text(svg,x,bottom+100,r.sector==="BES_PNP"?"Business + PNP · types unavailable":"Types unavailable; capital only",{"text-anchor":"middle","font-size":9});
    });
    const notes=result.rows.map(r=>`${names[r.country.iso]||r.country.name}: ${r.reason||("years "+r.years.join(", "))}${r.missingCategories.length?"; unreported/unusable categories: "+r.missingCategories.map(c=>breakdownLabels[c]).join(", "):""}${r.residual!==null&&Math.abs(r.residual)>1?"; signed total-minus-components difference "+fmt(r.residual,0)+" units":""}.`);
    if(overlay)for(const r of result.rows)if(r.years.length&&r.intensity===null)notes.push(`${names[r.country.iso]||r.country.name}: intensity omitted; missing matching intensity years ${r.years.filter(y=>!r.intensityYears.includes(y)).join(", ")} (${r.intensitySource}).`);
    if(result.rows.some(r=>r.country.iso==="ES-PV"))notes.push(result.kind==="research"?"Basque Country: Eustat reports total and capital costs; basic/applied/experimental types are unavailable. Grey is unclassified current costs. Business + PNP performers remain combined. PPP amounts use Spanish national proxies.":"Basque Country: business + private non-profit performers are combined. "+(opts.basis==="USD_PPP_Q"?"Constant-2020 PPP uses a derived Spanish national conversion proxy.":opts.basis==="USD_PPP_V"?"Current PPP uses Spain's GDP-PPP proxy.":""));
    for(const r of result.rows)for(const note of r.methodologyNotes)notes.push(`${r.country.name}: ${note}`);
    if(result.kind==="research"&&["GOV","BES"].includes(opts.sector)&&result.rows.some(r=>r.country.iso==="GBR"))notes.push(opts.sector==="GOV"?"UK government 2024 types unavailable: ONS GovERD Table 10 measures net spending, not government-performed R&D.":"UK business 2020–2021 types have no comparable redesigned-survey series; ONS 2022–2024 publication vintages show current research costs and separate capital. Older vintages can differ from revised performer totals.");
    if(overlay&&result.rows.some(r=>r.intensitySource.startsWith("ONS")))notes.push("UK intensity: one ONS provider across the bar years, with indicative 2018–2021 values from the 2023 publication and 2022–2024 from the 2024 publication; GDP/methodology vintage break at 2022.");
    notes.push(`Expenditure: OECD RDS / Eustat / ONS. Intensity: OECD MSTI / WDI / Eustat / ONS, potentially different vintages. Build: ${data.builtUTC}.`);
    $("coverage-note").textContent=notes.join("\n");$("coverage-note").className="metadata breakdown-note";
    $("inspector").textContent="Select a segment or intensity marker for details. All segments in a bar share the displayed years; grey is an accounting gap, not an assigned funding/research category.";
    $("percentage-note").textContent=`${opts.showPercentages?"Segment labels show percentages where space permits.":"Segment percentage labels are hidden."} ${percentage&&opts.shareMode==="annual"?"Percentages are mean annual shares.":"Percentages are each category's share of the reported mean total."} Small segments: hover or open “All sector percentages and plotted data” below. Grey is a derived accounting difference.`;
    const rows=window.RDBreakdowns.exportRows(data,result);
    table(rows,[{key:"economy",label:"Economy"},{key:"category",label:result.performers?"Performing sector":result.kind==="funding"?"Funding source":"Research type / capital"},{key:"years_used",label:"Years used"},{key:"mean_annual_amount",label:"Mean annual amount (units)",format:v=>fmt(v,1)},{key:"share_percent",label:"Share (%)",format:v=>fmt(v,3)},{key:"intensity_percent_gdp",label:"Intensity (%)",format:v=>fmt(v,3)}],$("data-table"));
    $("table-description").textContent="All reported category percentages, including segments too small to label. CSV includes annual input cells, totals, flags, conversions and source URLs. Missing categories remain blank, not zero.";
    $("export-svg").disabled=!result.rows.length;
    $("export").disabled=!rows.length;
    $("export").addEventListener("click",()=>downloadCSV(rows,`gerd-${spec.id}-${opts.rdStart}-${opts.rdEnd}-${opts.basis}.csv`));
    $("export-svg").addEventListener("click",()=>downloadBreakdownSVG(panel,result,spec));
    return rows;
  }
  function breakdownDashboard(opts) {
    core.checkYears(data,opts.rdStart,opts.rdEnd);
    const specs=[
      {id:"funding_amount",chart:"funding_amount",title:"Who funds R&D? Amounts + intensity"},
      {id:"funding_share",chart:"funding_share",title:"Who funds R&D? Sector percentages"},
      {id:"performer_amount",chart:"performer_amount",title:"Who performs R&D? Amounts + intensity"},
      {id:"performer_share",chart:"performer_share",title:"Who performs R&D? Sector percentages"},
      {id:"research_gov_share",chart:"research_share",sector:"GOV",title:"Government-performed R&D · research-type percentages"},
      {id:"research_business_share",chart:"research_share",sector:"BES",title:"Business-performed R&D · research-type percentages"},
      {id:"research_gov_amount",chart:"research_amount",sector:"GOV",title:"Government-performed R&D · research-type amounts"},
      {id:"research_business_amount",chart:"research_amount",sector:"BES",title:"Business-performed R&D · research-type amounts"}
    ];
    const extra=$("breakdownSector").value;
    if(extra)for(const mode of ["share","amount"])specs.push({id:`research_${extra}_${mode}`,chart:`research_${mode}`,sector:extra,
      title:`${data.breakdowns.sectors[extra]} · research-type ${mode==="share"?"percentages":"amounts"}`});
    const panels=specs.map(spec=>{
      const panel=$("breakdown-panel-template").content.firstElementChild.cloneNode(true);
      panel.id="breakdown-"+spec.id;panel.dataset.panel=spec.id;$("breakdown-panels").appendChild(panel);
      try {
        const result=window.RDBreakdowns.select(data,{...opts,countries:breakdownEconomies,chart:spec.chart,sector:spec.sector||"_T",
          basis:$("breakdownBasis").value,shareMode:$("shareMode").value,showPercentages:$("breakdownPercentages").checked});
        return {...spec,result,exported:breakdownChart(result,panel,spec)};
      } catch(error) {
        panel.querySelector('[data-role="chart-title"]').textContent=spec.title;
        const message=panel.querySelector('[data-role="error"]');message.hidden=false;message.textContent=error.message;
        panel.querySelectorAll("button").forEach(button=>{button.disabled=true;});
        panel.querySelectorAll("details").forEach(details=>{details.hidden=true;});
        return {...spec,error:error.message,exported:[]};
      }
    });
    return {panels,opts};
  }
  function downloadCSV(rows,filename) {
    if(!rows.length)return;
    const keys=Object.keys(rows[0]),escape=value=>'"'+String(value??"").replaceAll('"','""')+'"';
    const csv=[keys.map(escape).join(","),...rows.map(row=>keys.map(key=>escape(row[key])).join(","))].join("\r\n");
    const url=URL.createObjectURL(new Blob(["\ufeff"+csv],{type:"text/csv;charset=utf-8"}));
    const a=document.createElement("a");a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();
    window.addEventListener("pagehide",()=>URL.revokeObjectURL(url),{once:true});
  }
  function downloadBreakdownSVG(panel,result,spec) {
    const $=id=>panel.querySelector(`[data-role="${id}"]`),chart=$("charts").querySelector("svg");if(!chart)return;
    const width=chart.viewBox.baseVal.width,height=chart.viewBox.baseVal.height,legend=[...$("legend").children];
    const top=90+Math.ceil(legend.length/3)*22,notes=[$("selection-description").textContent,$("percentage-note").textContent,
      "Common years within each bar; missing categories are not zero. Grey = reported total minus known components.",...$("coverage-note").textContent.split("\n")];
    const lines=[];for(const note of notes){let line="";for(const word of note.split(/\s+/)){if((line+word).length>Math.floor(width/7)){lines.push(line);line="";}line+=(line?" ":"")+word;}if(line)lines.push(line);}
    const fullHeight=top+height+lines.length*18+25,svg=element("svg",{xmlns:NS,viewBox:`0 0 ${width} ${fullHeight}`,width,height:fullHeight,"font-family":"system-ui, sans-serif"});
    element("rect",{width,height:fullHeight,fill:"white"},null,svg);
    text(svg,30,32,$("chart-title").textContent,{"font-size":20,fill:INK});
    legend.forEach((item,i)=>{const x=30+(i%3)*(width-60)/3,y=60+Math.floor(i/3)*22,swatch=item.querySelector("i");if(swatch)element("rect",{x,y:y-11,width:12,height:12,fill:swatch.style.background},null,svg);text(svg,x+18,y,item.textContent,{"font-size":12});});
    const group=element("g",{transform:`translate(0 ${top})`},null,svg);for(const node of chart.childNodes)group.appendChild(node.cloneNode(true));
    lines.forEach((note,i)=>text(svg,30,top+height+15+i*18,note,{"font-size":11}));
    const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)],{type:"image/svg+xml"})),opts=result.opts;
    const a=document.createElement("a");a.href=url;a.download=`gerd-${spec.id}-${opts.rdStart}-${opts.rdEnd}-${opts.basis}.svg`;a.click();
    window.addEventListener("pagehide",()=>URL.revokeObjectURL(url),{once:true});
  }
  function render() {
    layoutControls();$("error").hidden=true;$("tooltip").hidden=true;$("stats").replaceChildren();$("charts").replaceChildren();
    $("breakdown-panels").replaceChildren();
    $("inspector").textContent="Hover over or click a point to inspect its values, reporting years and source.";
    const opts=options();
    try {
      $("legend").className="legend";$("coverage-note").className="metadata";
      if(view==="breakdown") {
        $("breakdown-countries").replaceChildren();
        for(const iso of breakdownEconomies){const button=document.createElement("button");button.type="button";button.textContent=(names[iso]||data.countries.find(c=>c.iso===iso).name)+" ×";button.setAttribute("aria-label","Remove "+iso);button.addEventListener("click",()=>{breakdownEconomies=breakdownEconomies.filter(c=>c!==iso);render();});$("breakdown-countries").appendChild(button);}
        current=breakdownDashboard(opts);exported=current.panels.flatMap(panel=>panel.exported);$("audit-section").hidden=true;
      } else if(view==="sector") {
        current=core.sectorField(data,$("country").value,+$("sectorYear").value,$("gerdBasis").value);
        const dataset=data.sectorField, currencies=[...new Set(current.rows.map(r=>r.currency_code).filter(Boolean))], bases=[...new Set(current.rows.map(r=>r.base_year).filter(Boolean))];
        $("chart-title").textContent=`${current.country.name} · GERD by sector × field · ${current.year}`;
        $("selection-description").textContent=`${dataset.bases[current.basis].label} · matrix in millions · currency: ${currencies.join(", ")||"no source rows"}${bases.length?" · base year: "+bases.join(", "):""}.`;
        if(current.country.geographyType==="region")$("selection-description").textContent+=current.basis==="USD_PPP_V"?" Derived from EUR using Spain's national GDP-PPP proxy.":current.basis==="USD_V"?" Derived from EUR using the same-year official exchange rate.":current.basis==="XDC_V"?" Reported Eustat expenditure in EUR.":" No Basque constant-price series is supplied.";
        stat("Available cells",current.available);stat("Source cells returned",current.sourceCells);stat("Confidential cells",current.rows.filter(r=>r.availability==="confidential_or_restricted").length);
        stat("Economies in this dataset",dataset.summary.economies);
        $("legend").textContent="C: confidential/restricted · I: included elsewhere · M: explicit missing value · —: not returned · *: source flags (select a cell). Zero means an observed zero.";
        sectorMatrix(current);
        $("coverage-note").textContent=`Source cells and explicitly labelled currency conversions; no reconstructed totals. Totals and combined groups overlap their components: do not add all rows or columns. Breakdowns may not add to source totals; the downloadable reconciliation audit records this. Available years across the dataset: ${dataset.summary.first_available_year}–${dataset.summary.last_available_year}. ${dataset.areaNotes?.[current.country.iso] || ""}`;
        $("inspector").textContent="Select a matrix cell for its currency, price basis, base year, availability and source flags. The sector identifies the performer of R&D, not its funder.";
        exported=current.rows;
        table(exported,[{key:"sector",label:"Performing sector"},{key:"field",label:"Field"},{key:"amount",label:"GERD (units)",format:v=>fmt(v,2)},{key:"currency_code",label:"Currency"},{key:"base_year",label:"Base year"},{key:"availability",label:"Availability"},{key:"flag_descriptions",label:"Source flags"}]);
        $("table-title").textContent="Selected sector/field cells";$("table-description").textContent="CSV amounts are in units and retain all seven source flag fields. Absent combinations are explicitly marked not_returned. No other year or price basis is substituted.";$("audit-section").hidden=true;
      } else if(view==="history") {
        current=core.history(data,$("country").value,opts.from,opts.to);
        $("chart-title").textContent=`${current.country.name} · ${opts.from}–${opts.to}`;
        $("selection-description").textContent="Annual GDP per capita, R&D intensity and derived nominal R&D totals. Gaps are left visible; no missing years are filled.";
        stat(`GDP ${opts.from}`,fmt(current.rows[0][opts.metric],0));stat(`GDP ${opts.to}`,fmt(current.rows.at(-1)[opts.metric],0));
        stat("GDP years reported",current.rows.filter(r=>r[opts.metric]!=null).length);stat("R&D years reported",current.rows.filter(r=>r.rd!=null).length);
        stat("Nominal R&D years derived",current.rows.filter(r=>r.rdNominalUSD!=null).length);
        $("legend").textContent=`R&D source for the whole displayed history: ${current.sourceName}.`;
        annualChart(current,opts.metric,`GDP per capita · ${unit()}`);annualChart(current,"rd","Annual R&D expenditure · % of GDP");
        annualChart(current,"rdNominalUSD","Nominal R&D expenditure · derived current US dollars (total)");
        if(current.source==="eustat")annualChart(current,"rdNominalPPP","R&D expenditure · derived current international dollars (Spain GDP-PPP proxy)");
        $("coverage-note").textContent="Nominal US$ totals are derived from the displayed provider's annual R&D share × same-year World Bank total GDP / 100. Input vintages and GDP denominators can differ. Each series displays its own available years. OECD reported national-currency amounts and provider alternatives are included in the table/CSV and full database.";
        if(current.source==="eustat")$("coverage-note").textContent=`Eustat reports current EUR amounts. USD and PPP totals divide these by same-year Spanish WDI exchange/PPP factors. R&D intensity is derived from Eustat expenditure / same-year Eustat GDP. ${current.country.note} ${current.country.rd.eustat[2025]?"":"The 2025 advance R&D release contains growth rates only; no annual level is inferred. "}See Basque annual conversions for all inputs.`;
        $("inspector").textContent=`${current.country.name} (${current.country.iso})\nR&D provider chosen by most annual observations in ${opts.from}–${opts.to}: ${current.sourceName}.\nHover over a year for values and source flags.`;
        exported=current.rows.map(r=>({economy:current.country.name,code:current.country.iso,year:r.year,gdp_current_usd:r.nominal,gdp_current_international_dollars_ppp:r.ppp,rd_percent_gdp:r.rd,rd_source:current.sourceName,rd_flags:r.flags,rd_note:r.note,
          rd_nominal_usd_derived:r.rdNominalUSD,rd_nominal_method:current.source==="eustat"?data.nominalRD.basqueMethod:data.nominalRD.formula,rd_nominal_missing_reason:r.rdNominalMissing,gdp_total_usd_input:r.gdpTotalUSD,gdp_total_flags:r.gdpTotalFlags,gdp_total_note:r.gdpTotalNote,
          gdp_usd_flags:r.gdpNominalFlags,gdp_ppp_flags:r.gdpPPPFlags,gdp_usd_note:r.gdpNominalNote,gdp_ppp_note:r.gdpPPPNote,
          rd_eustat_eur_reported:r.rdNominalEUR,rd_eustat_ppp_derived:r.rdNominalPPP,
          ...(current.source==="eustat"?Object.fromEntries(Object.entries(data.basqueAnnual.find(a=>a.year===r.year)||{}).map(([k,v])=>["basque_"+k,v])):{}),
          rd_nominal_local_oecd_reported:r.rdNominalLocalOECD,rd_local_unit:"current national currency (OECD XDC), units",rd_local_flags:r.rdNominalLocalFlags,rd_local_note:r.rdNominalLocalNote,
          rd_nominal_usd_oecd_derived:r.rdNominalUSDOECD,rd_nominal_usd_wdi_derived:r.rdNominalUSDWDI,rd_nominal_usd_uis_derived:r.rdNominalUSDUIS,rd_uis_flags:r.rdNominalUISFlags,rd_uis_note:r.rdNominalUISNote}));
        table(exported,[{key:"year",label:"Year"},{key:"gdp_current_usd",label:"GDP/person (current US$)",format:v=>fmt(v)},{key:"gdp_current_international_dollars_ppp",label:"GDP/person (current international $, PPP)",format:v=>fmt(v)},{key:"rd_percent_gdp",label:"Annual R&D (% GDP)",format:v=>fmt(v,4)},{key:"rd_nominal_usd_derived",label:"Nominal R&D (derived US$)",format:v=>fmt(v,0)},...(current.source==="eustat"?[{key:"rd_eustat_eur_reported",label:"Eustat R&D (reported EUR)",format:v=>fmt(v,0)},{key:"rd_eustat_ppp_derived",label:"R&D (derived PPP, Spain proxy)",format:v=>fmt(v,0)}]:[{key:"rd_nominal_local_oecd_reported",label:"OECD R&D (reported national currency)",format:v=>fmt(v,0)}]),{key:"rd_flags",label:"R&D flags"}]);
        $("table-title").textContent=`${current.country.name}: annual history`;$("table-description").textContent="A dash means missing, not zero. National-currency amounts are units, not millions, and cannot be compared across currencies. CSV includes separate OECD/WDI/direct-UIS US$ estimates. Data include later historical revisions.";$("audit-section").hidden=true;
      } else {
        current=view==="compare"?core.comparison(data,opts):core.snapshot(data,opts);
        const fitRows=core.regressionRows(current.rows),endFit=core.ols(fitRows.map(r=>({x:r.end[opts.metric],y:r.end.rd.value})));
        $("chart-title").textContent=view==="compare"?`Country positions · ${opts.from} → ${opts.to}`:`R&D intensity and income · GDP ${opts.gdpYear}`;
        $("selection-description").textContent=view==="compare"?`Earlier R&D: ${rdWindow(current.earlyStart,current.earlyEnd)} · Later R&D: ${rdWindow(opts.rdStart,opts.rdEnd)} · ${opts.timing==="fixed"?"R&D held fixed; horizontal movement only":"R&D window shifts with GDP year"}.`:`R&D ${rdWindow(opts.rdStart,opts.rdEnd)} · ${opts.strict?"Every requested R&D year required":"Mean of reported R&D years"} · ${unit()}.`;
        stat(view==="compare"?"Economies at both endpoints":"Economies plotted",current.rows.length);
        stat("Complete R&D coverage",current.rows.filter(r=>r.end.rd.complete&&(!r.start||r.start.rd.complete)).length);
        stat("Economies in regression",fitRows.length);
        if(view==="compare") {const fit=core.ols(fitRows.map(r=>({x:r.start[opts.metric],y:r.start.rd.value})));stat(`R² · ${opts.from}`,fit?fmt(fit.r2,3):"—");}
        stat(`R² · ${view==="compare"?opts.to:opts.gdpYear}`,endFit?fmt(endFit.r2,3):"—");
        $("legend").innerHTML=(view==="compare"?`<span><b class="key">□ → ●</b>${opts.from} → ${opts.to}; faint dashed fit = earlier year</span>`:"")+ '<span><b class="key">●</b>All R&D years reported</span><span><b class="key">○</b>Incomplete R&D window</span><span>Dotted curve: R&D = a + b ln(GDP)</span>';
        scatter(current,opts);plottedTable(current,opts);
        $("coverage-note").textContent=view==="compare"?`${current.startEligible} economies eligible at the earlier endpoint; ${current.endEligible} at the later endpoint; ${current.rows.length} in the common comparison. Both fits use that same common sample. The CSV records the selected R&D provider and actual reporting years.`:`${current.rows.length} of ${data.countries.length} audited economies have R&D and both income measures for this selection. Missing values are excluded; hollow points and * labels mark incomplete R&D coverage.`;
        if(!endFit)$("coverage-note").textContent+=" Regression unavailable: fewer than three valid points or no variation.";
        if(current.rows.some(r=>r.country.regressionEligible===false))$("coverage-note").textContent+=" Basque Country is a regional comparison point, excluded from both country fits because it overlaps Spain. Its PPP income uses Spain's national GDP-PPP factor as a proxy.";
        countryInfo();
      }
      $("export").disabled=!exported.length;applySearch();
    } catch(error) {
      current=null;exported=[];$("error").textContent=error.message;$("error").hidden=false;
      $("chart-title").textContent="Adjust the year selection";$("selection-description").textContent="";$("legend").textContent="";$("coverage-note").textContent="";
      $("charts").replaceChildren();$("stats").replaceChildren();table([],[]);$("table-description").textContent="";$("audit-section").hidden=true;$("export").disabled=true;
    }
  }
  for(const id of ["gdpYear","fromYear","toYear","rdStart","rdEnd","sectorYear"])
    for(const year of core.range(data.firstYear,data.lastYear)){const option=document.createElement("option");option.value=year;option.textContent=year;$(id).appendChild(option);}
  for(const country of data.countries){const option=document.createElement("option");option.value=country.iso;option.textContent=`${country.name} (${country.iso})`;$("country").appendChild(option);}
  for(const [code,basis] of Object.entries(data.sectorField.bases)){const option=document.createElement("option");option.value=code;option.textContent=basis.label;$("gerdBasis").appendChild(option);}
  for(const [code,basis] of Object.entries(data.breakdowns.bases)){const option=document.createElement("option");option.value=code;option.textContent=basis.label;$("breakdownBasis").appendChild(option);}
  for(const country of data.countries){const option=document.createElement("option");option.value=country.iso;option.textContent=`${country.name} (${country.iso})`;$("breakdownAdd").appendChild(option);}
  $("breakdownAdd").value="NLD";
  $("breakdown-add").addEventListener("click",()=>{const iso=$("breakdownAdd").value;if(!breakdownEconomies.includes(iso))breakdownEconomies.push(iso);render();});
  $("breakdown-examples").addEventListener("click",()=>{breakdownEconomies=[...exampleEconomies];render();});
  for(const id of controls)$(id).addEventListener("change",render);
  $("search").addEventListener("input",applySearch);
  document.querySelectorAll("[data-view]").forEach(button=>button.addEventListener("click",()=>setView(button.dataset.view)));
  $("history-button").addEventListener("click",()=>setView("history"));
  $("reset").addEventListener("click",reset);
  $("example").addEventListener("click",()=>{reset();view="compare";render();});
  $("export").addEventListener("click",()=>{
    downloadCSV(exported,view==="sector"?`gerd-sector-field-${$("country").value}-${$("sectorYear").value}-${$("gerdBasis").value}.csv`:`rd-income-${view}-${$("metric").value}.csv`);
  });
  $("refresh-status").textContent=`Historical data retrieved (UTC): ${data.retrievalDates.join(", ")} · Build: ${data.builtUTC}`;
  $("source-details").textContent=`Archive range: ${data.firstYear}–${data.lastYear}. WDI dataset-level update dates: ${Object.entries(data.datasetDates).map(([k,v])=>`${k}: ${v||"not supplied"}`).join("; ")}. These are not individual observation revision dates. Exact response URLs, timestamps, SHA-256 checksums and source flags are retained in the downloadable build.`;
  // Expose the pure model and current selection for reproducible browser verification.
  window.RDExplorer={data,core,get view(){return view;},get result(){return current;},get exported(){return exported;},render};
  reset();
})();
