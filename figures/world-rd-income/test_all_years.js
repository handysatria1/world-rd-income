/* Run with node test_all_years.js. */
"use strict";
const assert = require('node:assert/strict');
const core = require('./explorer_core.js');
const data = {firstYear:2000,lastYear:2002,builtUTC:'fixture',countries:[
  {iso:'AAA',name:'Fixture',rd:{oecd:{2000:{v:0,flags:'P',note:'zero'}},wdi:{2000:{v:4},2001:{v:1.23456789012345,flags:'E',note:'alternate'}}},gdp:{nominal:{2000:{v:0},2002:{v:123.456789012345,flags:'F',note:'exact',sourceRecord:'record'}}}},
  {iso:'ES-PV',name:'Region',geographyType:'region',parentEconomy:'ESP',note:'Regional qualification',rdProviders:['eustat'],rd:{eustat:{2000:{v:2}},custom:{2001:{v:9,flags:'C',note:'retained'}}},gdp:{nominal:{},ppp:{}}}
]};
const before = JSON.stringify(data), rows = core.allAnnualRows(data);
assert.equal(rows.length,6);
const [zero, switched, missing, region] = rows;
assert.equal(zero.rd_intensity_percent_gdp,0);
assert.equal(zero.rd_source_code,'oecd');
assert.equal(zero.rd_wdi_percent_gdp,4);
assert.equal(zero.rd_flags,'P');
assert.equal(zero.rd_notes,'zero');
assert.equal(zero.gdp_per_capita_current_usd,0);
assert.equal(switched.rd_source_code,'wdi');
assert.equal(switched.rd_intensity_percent_gdp,1.23456789012345);
assert.equal(switched.rd_notes,'alternate');
assert.equal(switched.gdp_per_capita_current_usd,null); // No nearest-year substitution.
assert.equal(missing.rd_intensity_percent_gdp,null);
assert.equal(missing.gdp_per_capita_current_usd,123.456789012345);
assert.equal(missing.gdp_per_capita_current_usd_source_record,'record');
assert.equal(missing.gdp_per_capita_current_usd_flags,'F');
assert.equal(missing.gdp_per_capita_current_usd_notes,'exact');
assert.equal(region.geography_type,'region');
assert.equal(region.parent_economy,'ESP');
assert.equal(region.geography_notes,'Regional qualification');
assert.equal(region.gdp_per_capita_ppp_constant_2021_international_dollars,null);
assert.equal(rows[4].rd_custom_percent_gdp,9);
assert.equal(rows[4].rd_custom_flags,'C');
assert.equal(rows[4].rd_custom_notes,'retained');
for(const row of rows) {
  assert.deepEqual(Object.keys(row),Object.keys(zero));
  assert.equal(row.data_build_utc,'fixture');
  assert.match(row.rd_source_selection,/Source may vary/);
}
assert.equal(JSON.stringify(data),before);
console.log('All-years fixtures passed: complete panel, zeros, exact-year joins, provider ties/switches, alternatives, provenance, missingness and non-mutation.');
