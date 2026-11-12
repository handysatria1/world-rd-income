'use strict';
const assert=require('assert/strict');
const chart=require('./absorptive_capacity_chart.js');
const data={current_vintage:'FY2027',group_averages:[]};
for(const vintage of ['FY2027','FY2020'])for(const code of ['HIC','UMC','LMC','MIC','LIC'])
  data.group_averages.push({classification_vintage:vintage,income_group_code:code,metric:'rd',mean_of_country_means:1});
assert.deepEqual(chart.rowsFor(data,'rd','current',false).map(r=>r.income_group_code),['HIC','UMC','LMC','LIC']);
assert.deepEqual(chart.rowsFor(data,'rd','current',true).map(r=>r.income_group_code),['HIC','MIC','LIC']);
assert.deepEqual(chart.rowsFor(data,'rd','FY2020',false).map(r=>r.classification_vintage),Array(4).fill('FY2020'));
console.log('Absorptive-capacity group display and classification-vintage checks passed.');
