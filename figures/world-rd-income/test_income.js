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

// Scale conversion requires the denominator from the observation year, including for year selection.
individuals.countries[0].series.population={2000:{v:2e6,record:70},2021:{v:0,record:71},2022:{v:null,record:72}};
individuals.countries[1].series.population={2000:{v:3e6,record:80},2021:{v:4e6,record:81}};
countries=core.countryObservations(individuals,{...one,scale:'total'});
assert.deepEqual(countries.rows.map(r=>[r.year,r.value]),[[2021,12],[2000,0]]);
assert.equal(core.countryObservations(individuals,{...one,scale:'total',year:'common'}).commonYear,2000);
r=core.countryObservations(individuals,{...one,scale:'total',year:2022}).rows[1];
assert.equal(r.value,null);assert.match(r.missing_reason,/population/);assert.equal(r.population_source_record,'72');
assert.equal(core.countryObservations(individuals,{...one,metric:'patents',patents:'nonresident',scale:'perMillion',year:2021}).rows[1].value,null);
r=core.countryObservations(individuals,{...one,metric:'patents',patents:'total',scale:'perMillion',year:2000}).rows[0];
assert.equal(r.value,10/3);assert.equal(r.raw_value,10);assert.equal(r.population,3e6);assert.equal(r.population_year,2000);assert.equal(r.source_values,'4;6');assert.match(r.method,/resident \+ nonresident/);
const region=individuals.countries[2];
region.series={researchersTotal:{2023:{v:50,record:'Eustat cell',provenance:{method:'reported Eustat FTE total'}},2024:{v:60}},population:{2023:{v:2e6,flags:'MIDYEAR_PROXY',provenance:{method:'midyear proxy',source_values:'1900000;2100000'}}}};
region.indicatorMetadata={researchersTotal:{code:'Eustat',source_file:'eustat.json',organization:'Eustat'}};
r=core.countryObservations(individuals,{...one,ids:['R'],scale:'total'}).rows[0];
assert.equal(r.year,2024);assert.equal(r.value,60);assert.equal(r.population_used,false);assert.equal(r.source_file,'eustat.json');
r=core.countryObservations(individuals,{...one,ids:['R'],scale:'perMillion'}).rows[0];
assert.equal(r.year,2023);assert.equal(r.value,25);assert.equal(r.raw_unit,'researchers (FTE)');assert.equal(r.source_record,'Eustat cell');assert.equal(r.population_flags,'MIDYEAR_PROXY');assert.equal(r.population_source_values,'1900000;2100000');
r=core.countryObservations(individuals,{...one,ids:['R'],scale:'perMillion',year:2025}).rows[0];assert.equal(r.value,null);assert.equal(r.indicator,'Eustat');assert.equal(r.source_file,'eustat.json');
for(const v of [-1,0,NaN,Infinity,null]){region.series.population[2023].v=v;assert.equal(core.countryMeasurement(region,'researchers',2023,'resident','perMillion').value,null);}
region.contextIndicators={pctPatents:{metadata:{label:'PCT',unit:'per GDP'},series:{2022:{v:1.3,record:'Hoja1!I6'},2023:{v:null,record:'Hoja1!J6'}}}};
assert.equal(core.regionalContext(individuals,{ids:['R'],metric:'patents',year:'latest'})[0].year,2022);
assert.equal(core.regionalContext(individuals,{ids:['R'],metric:'patents',year:2023})[0].value,null);
assert.equal(core.regionalContext(individuals,{ids:['R'],metric:'patents',year:'common'})[0].year,null);
assert.equal(core.countryObservations(individuals,{...one,ids:['R'],metric:'patents'}).rows[0].value,null);
assert.equal(core.aggregate(individuals,{...opts,ids:['R']}).rows[0].n,0);
console.log('Population conversions, denominator-aware years, native regional totals and non-equivalent context checks passed.');
