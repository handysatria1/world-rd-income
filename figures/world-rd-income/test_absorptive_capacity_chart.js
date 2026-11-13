'use strict';
const assert=require('assert/strict');
const chart=require('./absorptive_capacity_chart.js');
const data={current_vintage:'FY2027',group_averages:[]};
for(const vintage of ['FY2027','FY2020'])for(const code of ['HIC','UMC','LMC','MIC','LIC'])
  data.group_averages.push({classification_vintage:vintage,income_group_code:code,metric:'rd',mean_of_country_means:1});
assert.deepEqual(chart.rowsFor(data,'rd','current',false).map(r=>r.income_group_code),['HIC','UMC','LMC','LIC']);
assert.deepEqual(chart.rowsFor(data,'rd','current',true).map(r=>r.income_group_code),['HIC','MIC','LIC']);
assert.deepEqual(chart.rowsFor(data,'rd','FY2020',false).map(r=>r.classification_vintage),Array(4).fill('FY2020'));
const capacity={first_year:2000,last_year:2025,current_vintage:'FY2027',countries:[
  {iso3:'AAA',economy:'Alpha',current_income_code:'HIC',history:{FY2020:'HIC'}},
  {iso3:'AAB',economy:'Alpha B',current_income_code:'HIC',history:{FY2020:'HIC'}},
  {iso3:'BBB',economy:'Beta',current_income_code:'UMC',history:{FY2020:'UMC'}},
  {iso3:'CCC',economy:'Gamma',current_income_code:'LMC',history:{FY2020:'LMC'}},
  {iso3:'DDD',economy:'Delta',current_income_code:'LIC',history:{FY2020:'LIC'}}
]};
const income={countries:[
  {iso:'AAA',series:{rd:{2020:{v:0},2021:{v:null},2022:{v:4}}}},
  {iso:'AAB',series:{rd:{2020:{v:20}}}},
  {iso:'BBB',series:{rd:{2021:{v:8}}}},
  {iso:'CCC',series:{rd:{2021:{v:12}}}},
  {iso:'DDD',series:{rd:{}}}
]};
const result=chart.calculateAverages(capacity,income,'rd','current',false,2020,2022);
assert.equal(result.countries[0].average,2);assert.equal(result.countries[0].n_years,2);
assert.equal(result.countries[0].first_year,2020);assert.equal(result.countries[0].last_year,2022);
assert.equal(result.groups.find(r=>r.income_group_code==='HIC').mean_of_country_means,11);
assert.equal(result.groups.find(r=>r.income_group_code==='LIC').mean_of_country_means,null);
const combined=chart.calculateAverages(capacity,income,'rd','current',true,2020,2022);
assert.equal(combined.groups.find(r=>r.income_group_code==='MIC').mean_of_country_means,10);
assert.deepEqual(chart.periodFor(capacity,'single',2022).years,[2022]);
assert.deepEqual(chart.periodFor(capacity,'last5').years,[2021,2022,2023,2024,2025]);
assert.throws(()=>chart.periodFor(capacity,'range',null,2023,2022),/ordered period/);
console.log('Absorptive-capacity group display and classification-vintage checks passed.');
console.log('Selectable averages preserve missing years and equally weight country means.');
