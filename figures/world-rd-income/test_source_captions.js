'use strict';
const assert=require('node:assert/strict');
const captions=require('./source_captions.js');
const labels=spec=>spec.items.map(s=>s.label).join('; ');
let spec=captions.describe({page:'national',kind:'snapshot',ids:['USA','IDN','ES-PV'],rows:[{end:{rd:{source:'oecd'}}},{end:{rd:{source:'wdi'}}},{end:{rd:{source:'eustat'}}}],period:'GDP years: 2025; R&D periods: 2020–2024.'});
assert.match(labels(spec),/OECD MSTI/);assert.match(labels(spec),/World Bank WDI \/ UNESCO UIS/);assert.match(labels(spec),/Eustat/);assert.match(labels(spec),/income classifications/);
assert.doesNotMatch(labels(spec),/WIPO/); // Do not copy the example's unsupported GERD attribution.
assert.match(spec.note,/2020–2024/);
spec=captions.describe({page:'dashboard',kind:'patents',patents:'total',population:true,vintage:'FY2020',period:'2022'});
assert.match(labels(spec),/IP.PAT.RESD/);assert.match(labels(spec),/IP.PAT.NRES/);assert.match(labels(spec),/SP.POP.TOTL/);assert.match(spec.note,/FY2020/);
spec=captions.describe({page:'dashboard',kind:'patents',patents:'nonresident'});
assert.doesNotMatch(labels(spec),/IP.PAT.RESD/);assert.match(labels(spec),/IP.PAT.NRES/);
for(const metric of ['rd','researchers','internetUsers','bachelorAttainment','humanCapitalIndex','governmentEffectiveness','governmentEffectivenessEstimate','publications']){
  spec=captions.describe({page:'dashboard',kind:'capacity',metric,period:'2015–2024'});
  assert.match(spec.note,/equally weighted country means/);assert.match(spec.note,/2015–2024/);
  assert.ok(spec.items.every(s=>s.label&&s.url));
}
spec=captions.describe({page:'detail',target:'export-rows'});assert.match(labels(spec),/UNIDO CIP/);assert.doesNotMatch(labels(spec),/OECD/);
spec=captions.describe({page:'detail',target:'gva-rows',detailSource:'UNIDO_INDSTAT'});assert.match(labels(spec),/UNIDO INDSTAT/);assert.doesNotMatch(labels(spec),/OECD/);
spec=captions.describe({page:'detail',target:'nbs-rows'});assert.match(labels(spec),/China NBS/);
const rows=[{rows:[{gva_source:'OECD_TIVA',berd_source:'ONS_BERD'},{gva_source:'EUSTAT_A38',berd_source:'SGP_RIE'}]}];
spec=captions.describe({page:'research',rows,currency:true});
for(const name of ['TiVA','ONS','Eustat','A*STAR','exchange rates'])assert.ok(labels(spec).includes(name));
assert.equal(new Set(spec.items.map(s=>s.label)).size,spec.items.length);
assert.deepEqual(captions.industrySources(['no observations']),[]);
spec=captions.describe({page:'research',target:'research-classification'});assert.match(labels(spec),/compiled by Handy Satria/);
spec=captions.describe({page:'research',target:'official-table',officialSources:[{label:'Published ONS workbook',url:'https://www.ons.gov.uk/'}]});assert.match(labels(spec),/Published ONS workbook/);
const parts=[{text:'Source: ',bold:true},{text:'A long provider name with a link',url:'https://example.org/'},{text:'. Author’s calculations.'}];
const wrapped=captions.wrapParts(parts,25,text=>text.length);
assert.equal(wrapped.flat().map(p=>p.text).join('').replace(/\s+/g,' '),parts.map(p=>p.text).join(''));
assert.ok(wrapped.every(line=>line.reduce((sum,p)=>sum+p.text.length,0)<=26));
assert.ok(wrapped.flat().filter(p=>p.url).every(p=>p.url==='https://example.org/'));
console.log('Source captions: provider attribution, metrics, years, source-specific tables, calculated statistics and linked line wrapping passed.');
