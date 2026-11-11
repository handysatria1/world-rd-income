/* Pure income classification and paired-year statistics; shared with verification. */
(function(root){
  'use strict';
  const labels={HIC:'High income',UMC:'Upper-middle income',LMC:'Lower-middle income',LIC:'Low income',MIC:'Middle income',UNK:'Unclassified / region'};
  const symbols={HIC:'●',UMC:'■',LMC:'◆',LIC:'▲',MIC:'◆',UNK:'×'};
  function classify(data,iso,vintage='current',combine=false){
    const c=data.countries.find(c=>c.iso===iso);
    let code=(vintage==='current'?c?.current:c?.history?.[vintage])||'UNK';
    if(combine&&['UMC','LMC'].includes(code))code='MIC';
    return {code,label:labels[code],symbol:symbols[code],vintage:vintage==='current'?data.currentVintage:vintage};
  }
  function value(country,metric,year,patentMode='resident'){
    if(metric==='patents'&&patentMode==='total'){
      const a=country.series.patents?.[year]?.v,b=country.series.patentsNonresident?.[year]?.v;
      return a==null||b==null?null:a+b;
    }
    return country.series[metric==='patents'&&patentMode==='nonresident'?'patentsNonresident':metric]?.[year]?.v??null;
  }
  function countryMeasurement(country,metric,year,patents='resident',scale=metric==='researchers'?'perMillion':'total'){
    const nativeTotal=metric==='researchers'&&!!country.series.researchersTotal&&(country.series.researchersTotal[year]?.v!=null||country.series.researchers?.[year]?.v==null);
    const rawMetric=nativeTotal?'researchersTotal':metric,raw=value(country,rawMetric,year,patents);
    const population=country.series.population?.[year]?.v??null;
    const conversion=metric==='researchers'&&!nativeTotal?scale==='total':scale==='perMillion';
    const v=raw==null||conversion&&!(Number.isFinite(population)&&population>0)?null:!conversion?raw:scale==='total'?raw*population/1e6:raw/population*1e6;
    return {value:v,raw,rawMetric,population,conversion,nativeTotal};
  }
  function sourceDetails(data,c,keys,year){
    const cells=keys.map(k=>c.series[k]?.[year]),meta=keys.map(k=>c.indicatorMetadata?.[k]||data.indicators[k]||{});
    const join=(key,fallback,separator=';')=>keys.map((k,i)=>cells[i]?.provenance?.[key]??fallback(k,cells[i],meta[i])).join(separator);
    return {indicator:join('indicator',(k,cell,m)=>m.code||k,' + '),source_file:join('source_file',(k,cell,m)=>m.source_file||k+'.json'),
      source_record:join('source_record',(k,cell)=>cell?.record??'not returned'),source_values:join('source_values',(k,cell)=>cell?.v??'missing'),
      flags:join('flags',(k,cell)=>cell?.flags||''),notes:join('notes',(k,cell)=>cell?.note||''),
      source_url:join('source_url',(k,cell,m)=>m.url||''),source_organization:join('source_organization',(k,cell,m)=>m.organization||''),
      api_lastupdated:join('api_lastupdated',(k,cell,m)=>m.updated||''),retrieved_utc:join('retrieved_utc',(k,cell,m)=>m.retrieved||'')};
  }
  function countryObservations(data,opts){
    const byISO=new Map(data.countries.map(c=>[c.iso,c]));
    const countries=(opts.ids??data.countries.map(c=>c.iso)).map(iso=>byISO.get(iso)).filter(Boolean);
    const metric=opts.metric,patents=opts.patents||'resident',requested=String(opts.year),scale=opts.scale||(metric==='researchers'?'perMillion':'total');
    const keys=metric==='patents'?(patents==='total'?['patents','patentsNonresident']:[patents==='nonresident'?'patentsNonresident':'patents']):[metric];
    const measurement=(c,y)=>countryMeasurement(c,metric,y,patents,scale);
    const available=c=>[...new Set([...keys,...(metric==='researchers'?['researchersTotal']:[])].flatMap(k=>Object.keys(c.series[k]||{})))].map(Number).filter(y=>y>=2000&&y<=2025&&measurement(c,y).value!=null).sort((a,b)=>b-a);
    const years=countries.map(available);
    const commonYear=years[0]?.find(y=>countries.every(c=>measurement(c,y).value!=null))??null;
    const rows=countries.map((c,i)=>{
      const year=requested==='latest'?(years[i][0]??null):requested==='common'?commonYear:+requested;
      const m=measurement(c,year),v=year==null?null:m.value,classification=classify(data,c.iso,opts.vintage,opts.combine);
      const source=sourceDetails(data,c,m.nativeTotal?['researchersTotal']:keys,year),pop=sourceDetails(data,c,['population'],year);
      const missing=v!=null?'':requested==='common'?'No common year for all selected economies':year==null?'No complete observations in 2000–2025':m.raw!=null&&m.conversion?'Missing or nonpositive same-year population':'No observation in exact year';
      const method=m.conversion?(scale==='total'?'derived total = source rate × same-year population / 1,000,000':`derived rate = ${metric==='patents'&&patents==='total'?'(resident + nonresident)':'source total'} / same-year population × 1,000,000`):c.series[m.rawMetric]?.[year]?.provenance?.method||(metric==='patents'&&patents==='total'?'derived resident + nonresident':'reported WDI value');
      return {iso:c.iso,economy:c.name,geography_type:c.region?'region':'economy',metric,requested_year:requested,year,value:v,
        unit:metric==='researchers'?(scale==='total'?'researchers (FTE)':'per million people'):scale==='perMillion'?(metric==='patents'?'applications':'articles')+' per million people':data.indicators[metric].unit,scale,availability:v==null?'missing':'available',missing_reason:missing,
        latest_available_year:years[i][0]??null,patent_definition:metric==='patents'?patents:'',method,
        classification:classification.vintage,group_label:classification.label,
        ...source,raw_value:m.raw,raw_unit:m.nativeTotal?'researchers (FTE)':data.indicators[metric].unit,
        population:m.population,population_year:m.population==null?null:year,population_used:m.conversion,
        population_method:c.series.population?.[year]?.provenance?.method||'reported WDI population',
        ...Object.fromEntries(Object.entries(pop).map(([k,v])=>['population_'+k,v])),built_utc:data.builtUTC||''};
    });
    return {rows,commonYear,metric};
  }
  function regionalContext(data,opts,commonYear=null){
    const keys=opts.metric==='patents'?['pctPatents']:opts.metric==='publications'?['internationalPublications','topCitedShare']:[];
    return (opts.ids||[]).flatMap(iso=>{
      const c=data.countries.find(c=>c.iso===iso);
      return keys.filter(k=>c?.contextIndicators?.[k]).map(k=>{
        const {metadata:m,series}=c.contextIndicators[k],years=Object.keys(series).map(Number).filter(y=>series[y].v!=null).sort((a,b)=>b-a);
        const year=opts.year==='latest'?years[0]??null:opts.year==='common'?commonYear:+opts.year,cell=series[year];
        return {iso,economy:c.name,metric:k,label:m.label,requested_year:opts.year,year,value:cell?.v??null,unit:m.unit,
          availability:cell?.v!=null?'available':'missing',missing_reason:cell?.v!=null?'':year==null?'No common comparison year':'No observation in exact year',
          definition:m.definition,method:cell?.provenance?.method||'reported Eustat EIS 2025 ratio',indicator:m.code,
          source_file:m.source_file,source_record:cell?.record||'not returned',source_values:cell?.v??null,flags:cell?.flags||'',notes:cell?.note||'',
          source_url:m.url,display_url:m.display_url,source_organization:m.organization,source_updated:m.updated,retrieved_utc:m.retrieved,built_utc:data.builtUTC};
      });
    });
  }
  function aggregate(data,opts){
    const codes=opts.combine?['HIC','MIC','LIC']:['HIC','UMC','LMC','LIC'];
    const rows=[],audit=[];
    for(const metric of ['rd','researchers','patents','publications'])for(const code of codes){
      if(opts.groups?.length&&!opts.groups.includes(code))continue;
      const members=data.countries.filter(c=>!c.region&&(!opts.ids||opts.ids.includes(c.iso))&&classify(data,c.iso,opts.vintage,opts.combine).code===code);
      const eligible=members.filter(c=>opts.sample!=='paired'||opts.years.every(y=>value(c,metric,y,opts.patents)!=null));
      for(const year of opts.years){
        const observed=eligible.filter(c=>value(c,metric,year,opts.patents)!=null);
        const values=observed.map(c=>value(c,metric,year,opts.patents));
        const method=opts.stat==='auto'?(['rd','researchers'].includes(metric)?'mean':'sum'):opts.stat;
        const sorted=[...values].sort((a,b)=>a-b),n=values.length;
        const v=!n?null:method==='sum'?values.reduce((a,b)=>a+b,0):method==='median'?(sorted[Math.floor((n-1)/2)]+sorted[Math.floor(n/2)])/2:values.reduce((a,b)=>a+b,0)/n;
        rows.push({metric,group:code,group_label:labels[code],year,value:v,method,n,eligible:members.length,
          included:observed.map(c=>c.iso).join(';'),missing:members.filter(c=>!observed.includes(c)).map(c=>c.iso).join(';'),
          classification:opts.vintage==='current'?data.currentVintage:opts.vintage,sample:opts.sample,patent_definition:opts.patents});
        for(const c of members){const raw=value(c,metric,year,opts.patents),included=observed.includes(c);
          const keys=metric==='patents'?(opts.patents==='total'?['patents','patentsNonresident']:[opts.patents==='nonresident'?'patentsNonresident':'patents']):[metric];
          audit.push({iso:c.iso,economy:c.name,metric,year,group:code,classification:opts.vintage==='current'?data.currentVintage:opts.vintage,
            value:raw,included,exclusion:included?'':raw==null?'No observation in exact year':'Missing comparison-year observation (paired sample)',
            method:metric==='patents'&&opts.patents==='total'?'derived resident + nonresident':'reported WDI value',
            indicator:keys.map(k=>data.indicators[k].code).join(' + '),source_file:keys.map(k=>k+'.json').join(';'),
            source_record:keys.map(k=>c.series[k]?.[year]?.record??'not returned').join(';'),
            flags:keys.map(k=>c.series[k]?.[year]?.flags||'').join(';'),notes:keys.map(k=>c.series[k]?.[year]?.note||'').join(';')});
        }
      }
    }
    return {rows,audit};
  }
  const api={labels,symbols,classify,value,aggregate,countryObservations,countryMeasurement,regionalContext};
  if(typeof module!=='undefined')module.exports=api;else root.IncomeCore=api;
})(typeof globalThis!=='undefined'?globalThis:this);
