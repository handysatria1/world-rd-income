"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),core=require("./rd_industry_core.js");
const row={iso:"AAA",year:2022,stackAvailable:true,totalUSD:100,totalLocal:100,shares:[50,null,null,null,null,null],intensity:[5,null,null,null,null,null],perWorker:[10,null,null,null,null,null],gvaShares:[10,20,20,20,20,10],employmentShares:[10,20,20,20,20,10],productivity:[100,null,null,null,null,null],exportShares:[70,null,null,null,null,null]};
const data={rows:[row,{...row,iso:"BBB",year:2021}]};
assert.equal(core.select(data,["AAA"],"2023","composition")[0].row,null);
assert.equal(core.select(data,["AAA","BBB"],"common","composition")[0].year,null);
assert.deepEqual(core.select(data,["BBB","AAA"],"latest","composition").map(r=>r.year),[2021,2022]);
assert.equal(core.available({...row,stackAvailable:false},"composition"),false);
assert.equal(core.available({...row,intensity:Array(6).fill(null)},"intensity"),false);
assert.equal(core.available(row,"productivity","share",1),false);
assert.equal(core.available({...row,totalUSD:null},"composition","share"),true);
assert.equal(core.available({...row,totalUSD:null},"composition","amount"),false);
if(process.argv.includes("--built")){
  const built=JSON.parse(fs.readFileSync("data/rd_industry_explorer.json","utf8"));
  const examples=core.select(built,built.defaults,"2022","composition");
  assert.equal(examples.find(r=>r.iso==="SGP").available,true);
  assert.equal(examples.find(r=>r.iso==="SGP").row.status,"reported_total_only");
  assert.equal(examples.find(r=>r.iso==="SGP").row.remainingShare,100);
  assert(examples.find(r=>r.iso==="ES-PV").row.remainingShare<100);
  const singapore=core.select(built,["SGP"],"2023","composition")[0];
  assert.equal(singapore.row.source,"SGP_RIE");
  assert.equal(singapore.row.assignedLocal[2],2316260000);
  assert(singapore.row.complete.every(v=>v===false));
  assert.equal(core.available(singapore.row,"intensity"),false);
  assert.equal(singapore.row.nativeRows.length,16);
  assert.equal(core.select(built,["SGP"],"latest","composition")[0].year,Math.max(...built.rows.filter(r=>r.iso==="SGP"&&r.stackAvailable).map(r=>r.year)));
  for(const r of built.rows){
    r.intensity.forEach((v,i)=>{if(v!==null)assert.equal(r.complete[i],true);});
    if(r.status==="negative_reconciliation_remainder")assert.equal(core.available(r,"composition"),false);
  }
}
console.log("R&D selection, missingness, common years and complete-group checks passed.");
