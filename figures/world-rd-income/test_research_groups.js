'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),core=require('./research_group_core.js');
const groups=[{id:'03',sector:'Manufacturing'},{id:'10',sector:'Services'},{id:'16',sector:'Services'}];
const row={iso3:'AAA',year:2000,group_id:'03',gva_assigned_usd:100,berd_assigned_usd:10,gva_share_percent:20,berd_share_percent:10,gva_coverage:'complete',berd_coverage:'complete',gva_source:'OECD_TIVA',berd_source:'OECD_RDS',berd_scope:'BERD'};
const end={...row,year:2022,gva_assigned_usd:150,berd_assigned_usd:0,gva_share_percent:25,berd_share_percent:0};
assert.deepEqual(core.groups(groups,'Services').map(g=>g.id),['10','16']);
assert.equal(core.change(row,end,'gva','amount').value,50);
assert.equal(core.change(row,end,'gva','share').value,5);
assert.equal(core.change(row,end,'berd','amount').value,-100);
assert.equal(core.change({...row,berd_assigned_usd:0},end,'berd','amount').value,null);
assert.equal(core.change({...row,berd_share_percent:0},end,'berd','share').value,0);
for(const invalid of [null,{...end,berd_coverage:'partial'},{...end,berd_source:'OTHER'},{...end,berd_scope:'GERD'},{...end,iso3:'BBB'},{...end,group_id:'04'},{...end,year:1999}])assert.equal(core.change(row,invalid,'berd','amount').value,null);
assert.equal(core.usable([{...row,gva_assigned_usd:null},{...end,berd_assigned_usd:null}],groups,'amount'),false);
assert.equal(core.usable([end],groups,'amount'),true); // A reported zero is usable.
const ranked=core.rank([{id:'missing',row:{}},{id:'zero',row:{gva_assigned_usd:0}},{id:'largest',row:end},{id:'first',row},{id:'negative',row:{gva_assigned_usd:-2}}],'gva_assigned_usd');
assert.deepEqual(ranked.map(r=>r.id),['largest','first','zero','negative','missing']);
const byKey=new Map([['AAA/2000',[row]],['AAA/2022',[end]],['BBB/2000',[{...row,iso3:'BBB'}]]]);
const accept=rows=>core.usable(rows,groups,'amount');
assert.deepEqual(core.select(byKey,['AAA','BBB'],'latest',accept).map(r=>r.year),[2022,2000]);
assert.deepEqual(core.select(byKey,['AAA','BBB'],'common',accept).map(r=>r.year),[2000,2000]);
assert.equal(core.select(byKey,['AAA'],'2010',accept)[0].rows.length,0);
assert.equal(core.select(byKey,['AAA','ZZZ'],'common',accept)[0].year,null);
if(process.argv.includes('--built')){
  const data=JSON.parse(fs.readFileSync('data/research_group_explorer.json','utf8')),index=new Map();
  for(const r of data.rows){const k=r.iso3+'/'+r.year;if(!index.has(k))index.set(k,[]);index.get(k).push(r);}
  assert.equal(core.groups(data.groups,'Manufacturing').length,5);assert.equal(core.groups(data.groups,'Services').length,7);
  let checked=0,withheld=0;
  for(const iso of data.countries.map(c=>c.iso))for(const g of data.groups){
    const a=index.get(iso+'/2000')?.find(r=>r.group_id===g.id),b=index.get(iso+'/2022')?.find(r=>r.group_id===g.id);
    for(const mode of ['share','amount'])for(const m of core.measures(mode)){
      const actual=core.change(a,b,m.prefix,mode);
      if(actual.value===null){withheld++;continue;}
      assert.equal(a[m.prefix+'_coverage'],'complete');assert.equal(b[m.prefix+'_coverage'],'complete');assert.equal(a[m.prefix+'_source'],b[m.prefix+'_source']);
      const expected=mode==='share'?b[m.key]-a[m.key]:100*(b[m.key]/a[m.key]-1);
      assert(Math.abs(actual.value-expected)<1e-8);checked++;
    }
  }
  console.log(`${checked} archived endpoint changes independently checked; ${withheld} unavailable/incomparable endpoints withheld.`);
}
console.log('Research groups: ranking, exact/common years, pairing, missingness, zero baselines and endpoint units passed.');
