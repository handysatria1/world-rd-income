"use strict";
const assert = require("node:assert/strict"), fs = require("node:fs");
const {select} = require("./broad_sector_core.js");
const row = (iso, year, extra={}) => ({iso,year,status:"available",totalUSD:100,amounts:[30,70],...extra});
const data={rows:[row("A",2020),row("A",2022),row("B",2020),row("B",2021),row("B",2022,{status:"missing_components"}),row("C",2022,{totalUSD:null,amounts:[null,null]})]};
assert.deepEqual(select(data,["B","A"],"latest").map(r=>[r.iso,r.year]),[["B",2021],["A",2022]]);
assert.deepEqual(select(data,["A","B"],"common").map(r=>r.year),[2020,2020]);
assert.equal(select(data,["B"],"2022")[0].row,null); // Explicit years never silently fall back.
assert.equal(select(data,["A","C"],"common")[1].year,2022); // Shares do not need currency conversion.
assert.ok(select(data,["A","C"],"common","usd").every(r=>r.row===null));
assert.deepEqual(select(data,[],"common"),[]);
if(process.argv.includes("--built")) {
  const built=JSON.parse(fs.readFileSync(__dirname+"/data/broad_sector_explorer.json","utf8"));
  const latest=select(built,built.defaults,"latest"), common=select(built,built.defaults,"common");
  assert.ok(latest.every(r=>r.row));assert.equal(new Set(common.map(r=>r.year)).size,1);
  assert.ok(common.every(r=>r.row && Math.abs(r.row.shares.reduce((a,b)=>a+b,0)-100)<1e-9));
  assert.equal(select(built,["CHN"],"2025")[0].row,null);
  console.log("Built example:",latest.map(r=>({iso:r.iso,year:r.year,totalUSD:r.row.totalUSD})));
}
console.log("Broad-sector selection checks passed.");
