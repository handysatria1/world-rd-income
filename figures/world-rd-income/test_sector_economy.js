"use strict";
const assert=require("node:assert/strict"),{select,median}=require("./sector_economy_core.js");
const make=(iso,year,n,status="available")=>({iso,year,employment:{status,total:n},exports:{status,total:n},productivity:{status,comparisonStatus:status,amounts:[n]}});
const d={rows:[make("A",2021,1),make("A",2022,2),make("B",2021,4),make("B",2022,null,"missing")]};
assert.deepEqual(select(d,["B","A"],"latest","employment").map(r=>r.year),[2021,2022]);
assert.deepEqual(select(d,["B","A"],"common","sector").map(r=>r.year),[2021,2021]);
assert.equal(select(d,["B"],"2022","employment")[0].row,null);
assert.deepEqual(select(d,[],"common","employment"),[]);
assert.equal(median([null,1,2,9,10]),5.5);assert.equal(median([3,1,2]),2);assert.equal(median([]),null);
const fx={rows:[make("A",2024,null)]};assert.equal(select(fx,["A"],"2024","exports","amount")[0].row,null);assert.ok(select(fx,["A"],"2024","exports","share")[0].row);
if(process.argv.includes("--built")){
  const data=require("./data/sector_economy_explorer.json");
  for(const kind of["employment","comparison","sector","economy","exports"]){const chosen=select(data,data.defaults,kind==="exports"?"2024":"2022",kind);assert.equal(chosen.filter(r=>r.row).length,6);}
  assert.ok(select(data,data.defaults,"2024","sector").filter(r=>r.row).length<6);
  const pairs=select(data,data.defaults,"common","sector");assert.equal(new Set(pairs.map(r=>r.year)).size,1);assert.ok(pairs.every(r=>r.row));
}
console.log("Sector-economy exact-year, missingness and median checks passed.");
