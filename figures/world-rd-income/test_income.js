'use strict';
const assert=require('assert/strict'),core=require('./income_core.js'),national=require('./explorer_core.js');
const country=(iso,current,values,region=false)=>({iso,name:iso,current,region,history:{FY2001:'LIC'},series:Object.fromEntries(['rd','researchers','patents','publications'].map(k=>[k,Object.fromEntries(values.map((v,i)=>[2000+i*13,{v,record:i+1}]))]))});
const data={currentVintage:'FY2027',indicators:Object.fromEntries(['rd','researchers','patents','patentsNonresident','publications'].map(k=>[k,{code:k}])),countries:[country('A','HIC',[0,4]),country('B','HIC',[2,null]),country('C','LMC',[1,3]),country('D','UMC',[3,5]),country('R','HIC',[100,100],true)]};
const opts={years:[2000,2013],vintage:'current',combine:false,sample:'paired',stat:'auto',patents:'resident'};
let result=core.aggregate(data,opts),r=result.rows.find(r=>r.metric==='rd'&&r.group==='HIC'&&r.year===2000);
assert.equal(r.value,0);assert.equal(r.n,1);assert.equal(r.eligible,2);assert.equal(r.included,'A');assert.equal(r.missing,'B');
assert.equal(result.rows.find(r=>r.group==='LIC').value,null);
r=core.aggregate(data,{...opts,sample:'available'}).rows.find(r=>r.metric==='rd'&&r.group==='HIC'&&r.year===2000);assert.equal(r.value,1);assert.equal(r.n,2);
r=core.aggregate(data,{...opts,combine:true}).rows.find(r=>r.metric==='rd'&&r.group==='MIC'&&r.year===2000);assert.equal(r.value,2);assert.equal(r.n,2);
assert.equal(core.classify(data,'A','FY2001').code,'LIC');assert.equal(core.classify(data,'absent').code,'UNK');
assert.equal(core.aggregate(data,{...opts,ids:[]}).rows[0].n,0);
assert.equal(core.value(data.countries[0],'patents',2000,'total'),null);data.countries[0].series.patentsNonresident={2000:{v:5}};assert.equal(core.value(data.countries[0],'patents',2000,'total'),5);
const nd={firstYear:2000,lastYear:2002,countries:[{iso:'A',rd:{wdi:{2000:{v:1},2002:{v:2}}},gdp:{nominal:{2000:{v:100},2001:{v:110}},ppp:{2000:{v:200},2001:{v:220}}}},{iso:'B',rd:{wdi:{2002:{v:3}}},gdp:{nominal:{2002:{v:100}},ppp:{2002:{v:200}}}}]};
assert.deepEqual(national.latestSnapshot(nd,{}).rows.map(r=>r.end.gdpYear),[2000,2002]);assert.equal(national.latestSnapshot(nd,{},true).rows.length,0);
console.log('Income sampling, missingness, classification and latest-year checks passed.');

// Individual observations retain order, zeros and source detail; year selection never drops a country.
const individuals={builtUTC:'build-date',currentVintage:'FY2027',indicators:{
  researchers:{code:'SP.POP.SCIE.RD.P6',unit:'per million people',updated:'update-date',retrieved:'retrieval-date',url:'source-url'},
  patents:{code:'IP.PAT.RESD',unit:'applications'},patentsNonresident:{code:'IP.PAT.NRES',unit:'applications'}
},countries:[
  {iso:'A',name:'Alpha',current:'HIC',history:{FY2001:'LIC'},series:{researchers:{2000:{v:0,record:10,flags:'E',note:'estimated'},2022:{v:5,record:11}},patents:{2000:{v:0,record:20},2022:{v:10,record:21}},patentsNonresident:{2000:{v:0,record:30},2021:{v:8,record:31},2022:{v:null,record:32}}}},
  {iso:'B',name:'Beta',current:'LMC',history:{},series:{researchers:{2000:{v:2,record:40},2021:{v:3,record:41}},patents:{2000:{v:4,record:50}},patentsNonresident:{2000:{v:6,record:60}}}},
  {iso:'R',name:'Region',region:true,history:{},series:{}}
]};
const one={ids:['B','A'],metric:'researchers',year:'latest',vintage:'current'};
let countries=core.countryObservations(individuals,one);
assert.deepEqual(countries.rows.map(r=>[r.iso,r.year,r.value]),[['B',2021,3],['A',2022,5]]);
countries=core.countryObservations(individuals,{...one,year:'common'});
assert.equal(countries.commonYear,2000);assert.deepEqual(countries.rows.map(r=>r.value),[2,0]);
r=countries.rows[1];assert.equal(r.source_record,'10');assert.equal(r.flags,'E');assert.equal(r.notes,'estimated');assert.equal(r.unit,'per million people');assert.equal(r.source_url,'source-url');assert.equal(r.api_lastupdated,'update-date');assert.equal(r.retrieved_utc,'retrieval-date');assert.equal(r.built_utc,'build-date');
countries=core.countryObservations(individuals,{...one,year:'2021'});
assert.equal(countries.rows[1].value,null);assert.equal(countries.rows[1].year,2021);assert.equal(countries.rows[1].missing_reason,'No observation in exact year');
countries=core.countryObservations(individuals,{...one,ids:['A','B','R'],year:'common'});
assert.equal(countries.commonYear,null);assert.equal(countries.rows.length,3);assert(countries.rows.every(r=>r.value===null&&r.year===null&&r.missing_reason.includes('No common year')));
assert.equal(countries.rows[2].geography_type,'region');
assert.equal(core.countryObservations(individuals,{...one,ids:['R']}).rows[0].year,null);
assert.deepEqual(core.countryObservations(individuals,{...one,ids:[]}).rows,[]);
assert.equal(core.countryObservations(individuals,{...one,ids:['A'],year:'common'}).commonYear,2022);
assert.equal(core.countryObservations(individuals,{...one,vintage:'FY2001'}).rows[1].group_label,'Low income');
countries=core.countryObservations(individuals,{...one,metric:'patents',patents:'total'});
assert.deepEqual(countries.rows.map(r=>[r.year,r.value]),[[2000,10],[2000,0]]);
r=countries.rows[1];assert.equal(r.source_record,'20;30');assert.equal(r.source_values,'0;0');assert.equal(r.indicator,'IP.PAT.RESD + IP.PAT.NRES');assert.equal(r.method,'derived resident + nonresident');
assert.equal(core.countryObservations(individuals,{...one,metric:'patents',patents:'total',year:'common'}).commonYear,2000);
r=core.countryObservations(individuals,{...one,metric:'patents',patents:'total',year:2022}).rows[1];assert.equal(r.value,null);assert.equal(r.source_values,'10;missing');assert.equal(r.source_record,'21;32');
r=core.countryObservations(individuals,{...one,metric:'patents',patents:'nonresident'}).rows[1];assert.equal(r.year,2021);assert.equal(r.value,8);assert.equal(r.indicator,'IP.PAT.NRES');
console.log('Country selection, exact/latest/common years, zeros, patent components and provenance checks passed.');
