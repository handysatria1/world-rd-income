"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),bd=require("./breakdown_core.js");
const columns=["iso3","year","breakdown","sector_code","category_code","basis","amount","currency_code","base_year"];
const fixture={firstYear:2000,lastYear:2025,countries:[{iso:"AAA",name:"A",rd:{oecd:{2020:{v:1},2021:{v:3}},wdi:{}}}],
  breakdowns:{columns,rows:[],bases:{USD_PPP_Q:{}},partitions:{funding:["GOV","BES","PNP"]},categories:{funding:{GOV:"Government",BES:"Business",PNP:"Non-profit"}},sectors:{_T:"Total"},sources:{}}};
function cell(y,c,n,currency="USD"){return ["AAA",y,"funding","_T",c,"USD_PPP_Q",n,currency,"2020"];}
fixture.breakdowns.rows=[cell(2020,"_T",100),cell(2021,"_T",300),cell(2020,"GOV",50),cell(2021,"GOV",30),cell(2020,"BES",40),cell(2021,"BES",240)];
const opts={rdStart:2020,rdEnd:2021,basis:"USD_PPP_Q",chart:"funding_share",shareMode:"ratio",countries:["AAA"],strict:false};
let r=bd.select(fixture,opts).rows[0];
assert.deepEqual(r.years,[2020,2021]);assert.equal(r.parts[0].share,20);assert.equal(r.intensity,2);assert.equal(r.residual,20);
assert.equal(r.parts[2].amount,null);assert.deepEqual(r.missingCategories,["PNP"]);
assert.equal(bd.select(fixture,{...opts,shareMode:"annual"}).rows[0].parts[0].share,30);
const amount=bd.select(fixture,{...opts,chart:"funding_amount",shareMode:"annual"});
assert.equal(amount.rows[0].parts[0].share,20);assert.equal(amount.opts.shareMode,"ratio");
assert.equal(bd.exportRows(fixture,amount)[0].composition_method,"ratio of sums on common years");
// All segments must use a common year set, never independent means.
fixture.breakdowns.rows.pop();r=bd.select(fixture,opts).rows[0];
assert.deepEqual(r.years,[2020]);assert.equal(r.total,100);assert.equal(r.intensity,1);
assert.equal(bd.select(fixture,{...opts,strict:true}).rows[0].total,null);
fixture.countries[0].rd.oecd={2021:{v:3}};
assert.equal(bd.select(fixture,opts).rows[0].intensity,null); // no partial-year overlay
fixture.breakdowns.rows=[cell(2020,"_T",0),cell(2020,"GOV",0)];
r=bd.select(fixture,opts).rows[0];assert.equal(r.parts[0].amount,0);assert.equal(r.parts[0].share,null);assert.equal(r.residualShare,null);
fixture.breakdowns.rows=[cell(2020,"_T",100),cell(2020,"GOV",120)];
r=bd.select(fixture,opts).rows[0];assert.equal(r.parts[0].share,120);assert.equal(r.residual,-20); // never force 100%
fixture.breakdowns.rows=[cell(2020,"_T",100),cell(2021,"_T",100,"EUR"),cell(2020,"GOV",50),cell(2021,"GOV",50,"EUR")];
assert.match(bd.select(fixture,opts).rows[0].reason,/Incompatible/);
console.log("Common-year, missing-category, averaging, intensity, zero and currency fixtures passed.");
if(process.argv.includes("--built")){
  const data=JSON.parse(fs.readFileSync("data/explorer_history.json","utf8"));
  const examples=JSON.parse(fs.readFileSync("data/rd_breakdown_examples.json","utf8"));
  // Subtracting trillion-dollar totals loses a few floating-point ulps near zero.
  // Scale that bound by the operands, not the small accounting residual.
  const close=(a,b,scale=0)=>{assert.equal(a===null,b===null);if(a!==null)assert.ok(Math.abs(a-b)<=Math.max(1e-6,Math.abs(b)*1e-12,16*Number.EPSILON*Math.abs(scale)),`${a} vs ${b}`);};
  for(const [name,expected] of Object.entries(examples)){
    const selected=bd.select(data,{...opts,rdEnd:2024,countries:expected.map(r=>r.iso),chart:expected[0].chart,sector:expected[0].sector});
    for(const [i,r] of selected.rows.entries()){
      const e=expected[i];assert.deepEqual(r.years,e.years);close(r.total,e.total);close(r.intensity,e.intensity);close(r.residual,e.residual,r.total||0);close(r.residualShare,e.residual_share);
      for(const [j,p] of r.parts.entries()){assert.equal(p.code,e.parts[j].code);close(p.amount,e.parts[j].amount);close(p.share,e.parts[j].share);}
    }
    const exported=bd.exportRows(data,selected);
    assert.equal(exported.length,expected.reduce((s,r)=>s+r.parts.length,0));
    for(const row of exported){for(const cell of JSON.parse(row.annual_cells))assert.ok(cell.source_url.startsWith("https://"));}
    if(selected.performers)for(const row of exported){assert.equal(row.category_dimension,"sector_of_performance");assert.equal(row.performer_code,row.category_code);}
    console.log(`Independent Python vs JavaScript: ${name} passed.`);
  }
  const regional=bd.select(data,{...opts,rdEnd:2024,chart:"performer_share",countries:["ES-PV"]}).rows[0];
  assert.deepEqual(regional.parts.map(p=>p.code),["GOV","BES_PNP","HES"]);
  const strict=bd.select(data,{...opts,rdEnd:2024,strict:true,countries:["SGP"]});assert.equal(strict.rows[0].total,null);
  const research=bd.select(data,{...opts,rdEnd:2024,chart:"research_share",sector:"BES",countries:["GBR","ES-PV"]});
  assert.deepEqual(research.rows[0].years,[2022,2023,2024]);
  assert.deepEqual(research.rows[0].missingCategories,[]);
  assert.equal(research.rows[1].sector,"BES_PNP");
  assert.deepEqual(research.rows[1].missingCategories,["BR","AR","ED"]);
  assert.ok(research.rows[1].parts.find(p=>p.code==="CAP_EX_NEC").amount>0);
  for(const p of research.rows[0].parts)assert.ok(p.annual.every(c=>c.source_file.startsWith("ons_berd_")));
  const ukFunding=bd.select(data,{...opts,rdEnd:2024,chart:"funding_amount",countries:["GBR"]}).rows[0];
  close(ukFunding.intensity,(2.96+2.81+2.73+2.72+2.71)/5);
  assert.ok(ukFunding.intensitySource.startsWith("ONS"));
  assert.ok(ukFunding.intensityAnnual.every(r=>r.sources[0].file.startsWith("ons_")));
  assert.equal(bd.select(data,{...opts,rdEnd:2024,strict:true,chart:"research_share",sector:"GOV",countries:["GBR"]}).rows[0].total,null);
  console.log("Official-source checks passed: ONS capital separation and intensity, Eustat partial categories, UK government missingness.");
}
