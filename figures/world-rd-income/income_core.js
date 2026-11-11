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
  const api={labels,symbols,classify,value,aggregate};
  if(typeof module!=='undefined')module.exports=api;else root.IncomeCore=api;
})(typeof globalThis!=='undefined'?globalThis:this);
