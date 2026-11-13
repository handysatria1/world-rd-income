/* Run with node test_explorer.js. Fixtures exercise missingness/source changes. */
"use strict";
const assert = require("node:assert/strict");
const core = require("./explorer_core.js");

// Exercise the actual snapshot marker/legend renderers without a browser dependency.
{
  const vm = require('node:vm'), fs = require('node:fs');
  const source = fs.readFileSync(require('node:path').join(__dirname, 'explorer.js'), 'utf8');
  const node = tag => ({tag, children:[], style:{}, attrs:{},
    appendChild(child){this.children.push(child);return child;},
    append(child){this.children.push(child);},
    replaceChildren(){this.children=[];},
    setAttribute(key,value){this.attrs[key]=value;}});
  const legend = node('div');
  const context = vm.createContext({
    document:{createElement:node, createElementNS:(ns,tag)=>node(tag), createTextNode:text=>({textContent:text})},
    $:()=>legend, NS:'http://www.w3.org/2000/svg', view:'snapshot',
    shared:{combine:false, vintage:'current', income:{currentVintage:'FY2027'}},
    incomeFor:iso=>({code:iso})
  });
  vm.runInContext(source.slice(source.indexOf('  const incomeStyles'), source.indexOf('  const names')) +
    source.slice(source.indexOf('  function element('), source.indexOf('  function text(')) +
    source.slice(source.indexOf('  function incomeMarker('), source.indexOf('  function scatter(')), context);
  const rows = ['HIC','HIC','UMC','LMC','LIC','UNK'].map(iso=>({country:{iso}}));
  context.rows=rows;vm.runInContext('incomeLegend(rows)',context);
  const labels = () => legend.children.slice(0,-1).map(item=>item.children[1].textContent);
  assert.deepEqual(labels(), ['High income (n=2)','Upper-middle income (n=1)','Lower-middle income (n=1)','Low income (n=1)','Unclassified / region (n=1)']);
  const markers = legend.children.slice(0,-1).map(item=>item.children[0].children[0]);
  assert.deepEqual(markers.map(m=>m.tag), ['circle','rect','path','path','path']);
  assert.deepEqual(markers.map(m=>m.attrs.fill), ['#2878df','#f06432','#10b981','#f0a000','#687787']);
  assert.equal(markers[2].attrs.d.split(' L').length,3); // lower-middle triangle
  assert.equal(markers[3].attrs.d.split(' L').length,4); // low-income diamond
  context.rows=[rows[2]];vm.runInContext('incomeLegend(rows)',context);
  assert.deepEqual(labels(), ['High income (n=0)','Upper-middle income (n=1)','Lower-middle income (n=0)','Low income (n=0)']);
  context.shared.combine=true;context.shared.vintage='FY2020';context.rows=[{country:{iso:'MIC'}}];
  vm.runInContext('incomeLegend(rows)',context);
  assert.deepEqual(labels(), ['High income (n=0)','Middle income (n=1)','Low income (n=0)']);
  assert.match(legend.children.at(-1).textContent,/FY2020/);
  context.rows=[];vm.runInContext('incomeLegend(rows)',context);
  assert.ok(labels().every(label=>label.endsWith('(n=0)')));
  console.log('Snapshot income colors, marker shapes and dynamic group counts passed.');
}

const observations = values => Object.fromEntries(Object.entries(values).map(([year,v])=>[year,{v,flags:"",note:""}]));
function country(iso, oecd, wdi, missingPPP=false) {
  return {iso,name:iso,rd:{oecd:observations(oecd),wdi:observations(wdi)},gdp:{
    nominal:observations({2010:100,2023:200}),ppp:observations(missingPPP?{2010:150}:{2010:150,2023:300})}};
}
const a=country("A",{2007:1,2008:1,2009:1,2020:2,2022:4},{2020:20,2021:30,2022:40});
const b=country("B",{2009:0,2020:0,2022:2},{2021:50,2022:99});
const c=country("C",{2020:2,2021:3,2022:4},{},true);
const d=country("D",{},{});
const data={firstYear:2000,lastYear:2025,countries:[a,b,c,d]};
const options={rdStart:2020,rdEnd:2022,gdpYear:2023,strict:false,from:2010,to:2023,timing:"aligned"};
const snapshot=core.snapshot(data,options);
assert.deepEqual(snapshot.rows.map(r=>r.country.iso),["A","B"]);
assert.equal(snapshot.rows[0].end.rd.source,"wdi");
assert.equal(snapshot.rows[0].end.rd.value,30);
assert.equal(snapshot.rows[1].end.rd.source,"oecd"); // OECD tie-break
assert.equal(snapshot.rows[1].end.rd.value,1); // observed zero retained, missing 2021 excluded
assert.deepEqual(snapshot.rows[1].end.rd.missing,[2021]);
assert.equal(snapshot.audit[2].end.reasons[0],"Missing 2023 PPP GDP");
assert.deepEqual(core.snapshot(data,{...options,strict:true}).rows.map(r=>r.country.iso),["A"]);

const comparison=core.comparison(data,options);
assert.deepEqual([comparison.earlyStart,comparison.earlyEnd],[2007,2009]);
assert.deepEqual(comparison.rows.map(r=>r.country.iso),["A","B"]);
assert.equal(comparison.rows[0].start.rd.source,"oecd");
assert.equal(comparison.rows[0].end.rd.source,"oecd"); // one provider across endpoints, despite snapshot preferring WDI
assert.equal(comparison.rows[0].start.rd.value,1);
assert.equal(comparison.rows[0].end.rd.value,3);
assert.equal(core.comparison(data,{...options,strict:true}).rows.length,0);
const fixed=core.comparison(data,{...options,timing:"fixed"});
assert.equal(fixed.rows[0].end.rd.source,"wdi");
assert.equal(fixed.rows[0].start.rd.value,fixed.rows[0].end.rd.value);

const history=core.history(data,"B",2020,2022);
assert.deepEqual(history.rows.map(r=>r.rd),[0,null,2]); // no fill or interpolation
assert.equal(history.source,"oecd");
// Nominal totals follow the selected intensity provider, without filling GDP gaps.
b.gdpTotalUSD={2020:{v:1e9},2021:{v:2e9}};
b.rdNominal={usd:{oecd:{2020:{v:0},2022:{v:null,missingReason:"Missing same-year GDP"}},
  wdi:{2022:{v:99e6}},uis:{2020:{v:5e6}}},localOECD:{2020:{v:123e6}}};
const nominalHistory=core.history(data,"B",2020,2022);
assert.deepEqual(nominalHistory.rows.map(r=>r.rdNominalUSD),[0,null,null]);
assert.equal(nominalHistory.rows[2].rdNominalUSDWDI,99e6); // alternative retained, never silently substituted
assert.equal(nominalHistory.rows[2].gdpTotalUSD,null);
assert.equal(nominalHistory.rows[0].rdNominalLocalOECD,123e6);
assert.throws(()=>core.snapshot(data,{...options,rdStart:2024}),/ordered year range/);
assert.throws(()=>core.comparison(data,{...options,from:2000}),/ordered year range/);
assert.throws(()=>core.comparison(data,{...options,from:2023}),/different GDP years/);
assert.throws(()=>core.history(data,"UNKNOWN",2010,2025),/Choose a country/);
const fit=core.ols([{x:Math.exp(1),y:1},{x:Math.exp(2),y:3},{x:Math.exp(3),y:5}]);
assert.ok(Math.abs(fit.slope-2)<1e-12 && Math.abs(fit.intercept+1)<1e-12 && Math.abs(fit.r2-1)<1e-12);
assert.ok(Math.abs(core.spearman([{x:1,y:3},{x:2,y:1},{x:3,y:2}]).rho+.5)<1e-12);
assert.ok(Math.abs(core.spearman([{x:1,y:1},{x:1,y:2},{x:2,y:2}]).rho-.5)<1e-12);
assert.equal(core.spearman([{x:1,y:1},{x:2,y:1},{x:3,y:1}]),null);
assert.equal(core.ols([{x:1,y:1},{x:2,y:2}]),null);
assert.equal(core.ols([{x:1,y:2},{x:2,y:2},{x:3,y:2}]),null);
assert.equal(core.ols([{x:0,y:1},{x:2,y:2},{x:3,y:4}]),null);
// Joint cells are selected exactly, with totals retained and three kinds of absence.
data.sectorField={columns:["iso3","year","sector_code","field_code","basis","amount","source_value","currency_code","base_year","availability","OBS_STATUS","CONF_STATUS"],
  rows:[["A",2023,"_T","_T","XDC_V",999,"0.000999","EUR","","available","",""],
        ["A",2023,"HES","FORD1","XDC_V",0,"0","EUR","","available","",""],
        ["A",2023,"HES","FORD2","XDC_V",null,"","EUR","","confidential_or_restricted","","C"],
        ["A",2023,"HES","FORD1","USD_PPP_Q",44,"0.000044","USD","2020","available","",""],
        ["A",2022,"HES","FORD2","XDC_V",33,"0.000033","EUR","","available","",""]],
  fields:{_T:"Total",FORD1:"Natural sciences",FORD2:"Engineering"},sectors:{_T:"Total",HES:"Higher education"},
  fieldGroups:{},fieldParents:{},areaNames:{A:"A"},bases:{XDC_V:{unit:"XDC",price:"V",label:"Current national currency"},USD_PPP_Q:{unit:"USD_PPP",price:"Q",label:"Constant PPP"}},
  flagLabels:{CL_OBS_STATUS:{},CL_CONF_STATUS:{C:"Confidential"}},sourceFile:"source.csv",source:{url:"https://example.org/source",retrieved_utc:"2026-11-11"}};
const cells=core.sectorField(data,"A",2023,"XDC_V");
assert.equal(cells.rows.length,6);
assert.equal(cells.available,2);
assert.equal(cells.rows.find(r=>r.field_code==="_T"&&r.sector_code==="_T").amount,999); // never reconstructed
assert.equal(cells.rows.find(r=>r.field_code==="FORD1"&&r.sector_code==="HES").amount,0);
assert.equal(cells.rows.find(r=>r.field_code==="FORD2"&&r.sector_code==="HES").amount,null); // no prior-year fallback
assert.match(cells.rows.find(r=>r.CONF_STATUS).flag_descriptions,/Confidential/);
assert.equal(cells.rows.filter(r=>r.availability==="not_returned").length,3);
assert.equal(core.sectorField(data,"A",2023,"USD_PPP_Q").rows.find(r=>r.amount!==null).base_year,"2020");
assert.equal(core.sectorField(data,"A",2025,"XDC_V").sourceCells,0);
console.log("Explorer checks passed: windows, missingness, source selection, paired cohorts, history gaps, nominal provenance, sector/field selection, OLS and tied-rank Spearman.");

// Regions keep their own provider even in an empty window and never enter a
// country regression merely because they are selected or highlighted.
const region={...country("ES-PV",{},{}),geographyType:"region",regressionEligible:false,rdProviders:["eustat"],
  rd:{oecd:{},wdi:{},eustat:observations({2020:2,2022:3})}};
assert.equal(core.pickSource(region,[2025]),"eustat");
assert.equal(core.rdSummary(region,2025,2025).value,null);
assert.deepEqual(core.regressionRows([{country:a},{country:region}]).map(r=>r.country.iso),["A"]);

if(process.argv.includes("--built")) {
  const built=JSON.parse(require("node:fs").readFileSync(require("node:path").join(__dirname,"data/explorer_history.json"),"utf8"));
  const opts={rdStart:2020,rdEnd:2024,gdpYear:2025,strict:false,from:2010,to:2025,timing:"aligned"};
  const snap=core.snapshot(built,opts),comp=core.comparison(built,opts),b=snap.rows.find(r=>r.country.iso==="ES-PV");
  assert.ok(b && b.end.rd.complete && comp.rows.some(r=>r.country.iso==="ES-PV"));
  assert.equal(b.end.rd.source,"eustat");
  assert.ok(!core.regressionRows(snap.rows).some(r=>r.country.iso==="ES-PV"));
  const hist=core.history(built,"ES-PV",2000,2025);
  for(const row of hist.rows) {
    const inputs=built.basqueAnnual.find(r=>r.year===row.year);
    assert.equal(row.rd,inputs.rd_percent_gdp_derived);
    assert.equal(row.rdNominalUSD,inputs.gerd_usd_derived);
    assert.equal(row.rdNominalPPP,inputs.gerd_ppp_derived);
    assert.equal(row.nominal,inputs.gdp_per_capita_usd_derived);
    assert.equal(row.ppp,inputs.gdp_per_capita_ppp_derived);
    for(const [basis,key] of [["XDC_V","gerd_eur_reported"],["USD_V","gerd_usd_derived"],["USD_PPP_V","gerd_ppp_derived"]]) {
      const sf=core.sectorField(built,"ES-PV",row.year,basis);
      assert.equal(sf.rows.length,24);
      assert.equal(sf.rows.find(r=>r.sector_code==="_T"&&r.field_code==="_T").amount,inputs[key]);
      assert.ok(!sf.rows.some(r=>r.sector_code==="BES"||r.sector_code==="PNP"||r.field_code==="FORD5"));
      assert.ok(sf.rows.filter(r=>r.amount!==null).every(r=>r.source_file.startsWith("eustat_")&&r.value_status===(basis==="XDC_V"?"reported":"derived")));
    }
    assert.equal(core.sectorField(built,"ES-PV",row.year,"USD_PPP_Q").available,0);
  }
  // Income toggle has the same paired cohort; missing 2025 R&D must not be carried forward.
  assert.deepEqual(core.snapshot(built,{...opts,metric:"ppp"}).rows.map(r=>r.country.iso),snap.rows.map(r=>r.country.iso));
  const last=built.basqueAnnual.at(-1);
  if(last.gerd_eur_reported===null)assert.ok(!core.snapshot(built,{...opts,rdStart:2025,rdEnd:2025}).rows.some(r=>r.country.iso==="ES-PV"));
  const stats=JSON.parse(require("node:fs").readFileSync(require("node:path").join(__dirname,"data/validation_report.json"),"utf8"));
  for(const metric of ["nominal","ppp"]) {
    const fit=core.ols(core.regressionRows(snap.rows).map(r=>({x:r.end[metric],y:r.end.rd.value})));
    const expected=stats.models.find(r=>r.figure===`world_2025_${metric}`);
    assert.equal(fit.n,expected.n);assert.ok(Math.abs(fit.r2-expected.r_squared)<1e-12);
    assert.equal(snap.rows.length,expected.plotted_n);
  }
  console.log("Built-data checks passed: Basque Country in all four views, source-specific grids, year-matched conversions, missingness and regression exclusion.");
}
