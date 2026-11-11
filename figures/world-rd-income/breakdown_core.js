/* Common-year accounting for the offline funding/research charts. */
(function(root) {
  "use strict";
  const core = typeof module !== "undefined" && module.exports ? require("./explorer_core.js") : root.RDCore;
  const mean = values => values.length ? values.reduce((a,b)=>a+b,0)/values.length : null;
  function select(data, opts) {
    // Amount-bar labels must match the drawn segments, regardless of the share-chart setting.
    if(opts.chart.endsWith("amount"))opts={...opts,shareMode:"ratio"};
    core.checkYears(data,opts.rdStart,opts.rdEnd);
    const ds=data.breakdowns, kind=opts.chart.startsWith("research")?"research":"funding";
    if(!ds.bases[opts.basis])throw new Error("Select an expenditure price basis.");
    const performers=opts.chart.startsWith("performer"), requested=core.range(opts.rdStart,opts.rdEnd);
    const index=Object.fromEntries(ds.columns.map((k,i)=>[k,i])), cells=new Map();
    for(const values of ds.rows){
      if(values[index.breakdown]!==kind||values[index.basis]!==opts.basis||!opts.countries.includes(values[index.iso3])||!requested.includes(values[index.year]))continue;
      const r=Object.fromEntries(ds.columns.map((k,i)=>[k,values[i]]));
      cells.set([r.iso3,r.year,r.sector_code,r.category_code].join("|"),r);
    }
    const rows=opts.countries.map(iso=>{
      const country=data.countries.find(c=>c.iso===iso);
      if(!country)throw new Error(`Unknown economy: ${iso}`);
      const sector=kind==="research"?(iso==="ES-PV"&&opts.sector==="BES"?"BES_PNP":opts.sector):"_T";
      const categories=performers?(iso==="ES-PV"?["GOV","BES_PNP","HES"]:["GOV","BES","HES","PNP"]):ds.partitions[kind];
      const labels=performers?ds.sectors:ds.categories[kind];
      const get=(year,category)=>cells.get([iso,year,performers?category:sector,performers?"_T":category].join("|"));
      const present=categories.filter(c=>requested.some(y=>get(y,c)?.amount!=null));
      const candidate=requested.filter(y=>get(y,"_T")?.amount!=null&&present.every(c=>get(y,c)?.amount!=null));
      let years=present.length?candidate:[];
      const compatible=new Set(years.flatMap(y=>["_T",...present].map(c=>{const r=get(y,c);return [r.currency_code,r.base_year].join(":");})));
      const incompatible=compatible.size>1;
      if(incompatible||(opts.strict&&years.length!==requested.length))years=[];
      const total=mean(years.map(y=>get(y,"_T").amount));
      const parts=categories.map(code=>{
        const annual=years.map(y=>get(y,code)).filter(Boolean);
        const available=years.length>0&&years.every(y=>get(y,code)?.amount!=null);
        const amount=available?mean(years.map(y=>get(y,code).amount)):null;
        const share=amount===null||years.some(y=>get(y,"_T").amount<=0)?null:
          opts.shareMode==="annual"?mean(years.map(y=>get(y,code).amount/get(y,"_T").amount*100)):amount/total*100;
        return {code,label:labels[code],amount,share,annual};
      });
      const used=parts.filter(p=>p.amount!==null), residual=total===null?null:total-used.reduce((s,p)=>s+p.amount,0);
      const residualShare=total===null||years.some(y=>get(y,"_T").amount<=0)?null:100-used.reduce((s,p)=>s+p.share,0);
      const intensityCountry=ds.officialIntensity?.[iso]?{...country,rd:{...country.rd,ons:ds.officialIntensity[iso]},rdProviders:[...(country.rdProviders||Object.keys(country.rd)),"ons"]}:country;
      const source=core.pickSource(intensityCountry,years), intensityYears=years.filter(y=>intensityCountry.rd[source]?.[y]!=null);
      const intensity=years.length&&intensityYears.length===years.length?mean(years.map(y=>intensityCountry.rd[source][y].v)):null;
      const intensityFiles=source==="eustat"?["eustat_rd_total.json","eustat_gdp_total.json"]:[source==="oecd"?"msti_gerd_percent_gdp_history.csv":"wb_rd_history.json"];
      const intensityAnnual=intensityYears.map(year=>{const obs=intensityCountry.rd[source][year];return {year,...obs,sources:(source==="ons"?[obs.source_file]:intensityFiles).map(file=>({file,...data.sources?.[file]}))};});
      const missingCategories=parts.filter(p=>p.amount===null).map(p=>p.code);
      const reason=incompatible?"Incompatible currencies or base years in the window":!present.length?"No breakdown observations in this window":!years.length?"No eligible common-year window":"";
      return {country,sector,kind,years,missingYears:requested.filter(y=>!years.includes(y)),parts,total,residual,residualShare,
        intensity,intensitySource:core.SOURCE_NAMES[source],intensityYears,intensityAnnual,missingCategories,reason,
        totalAnnual:years.map(y=>get(y,"_T")),currency:years.length?get(years[0],"_T").currency_code:"",
        baseYear:years.length?get(years[0],"_T").base_year:"",
        methodologyNotes:[...new Set(years.flatMap(y=>["_T",...present].map(c=>get(y,c)?.methodology_note).filter(Boolean)))]};
    });
    if(opts.chart.endsWith("amount")&&new Set(rows.filter(r=>r.years.length).map(r=>r.currency+":"+r.baseYear)).size>1)
      throw new Error("Amount comparisons require a shared currency and price base. Select PPP dollars or one economy.");
    return {rows,kind,performers,opts};
  }
  function exportRows(data,result) {
    const ds=data.breakdowns, opts=result.opts;
    const provenance=annual=>JSON.stringify(annual.map(r=>({...r,source_url:ds.sources[r.source_file]?.url||"",
      retrieved_utc:ds.sources[r.source_file]?.retrieved_utc||"",conversion_source_url:ds.sources[r.conversion_source_file]?.url||""})));
    return result.rows.flatMap(r=>r.parts.map(p=>({economy:r.country.name,code:r.country.iso,chart:opts.chart,
      breakdown:r.kind,category_dimension:result.performers?"sector_of_performance":r.kind==="funding"?"source_of_funds":"type_of_research",
      performer_code:result.performers?p.code:r.sector,category_code:p.code,category:p.label,basis:opts.basis,
      currency:r.currency,base_year:r.baseYear,window_start:opts.rdStart,window_end:opts.rdEnd,
      years_used:r.years.join(";"),missing_years:r.missingYears.join(";"),category_available:p.amount!==null,
      mean_annual_amount:p.amount,reported_mean_total:r.total,share_percent:p.share,
      composition_method:opts.shareMode==="annual"?"mean annual shares":"ratio of sums on common years",
      residual_amount:r.residual,residual_share_percent:r.residualShare,missing_categories:r.missingCategories.join(";"),
      intensity_percent_gdp:r.intensity,intensity_source:r.intensitySource,intensity_years:r.intensityYears.join(";"),
      intensity_annual_inputs:JSON.stringify(r.intensityAnnual),
      exclusion_reason:r.reason,methodology_notes:r.methodologyNotes.join(" | "),regional_proxy:r.country.iso==="ES-PV"&&opts.basis==="USD_PPP_Q"?"Spain national implied constant-2020 PPP conversion":"",
      annual_cells:provenance(p.annual),annual_totals:provenance(r.totalAnnual),
      regional_conversion_inputs:JSON.stringify(r.country.iso==="ES-PV"&&opts.basis==="USD_PPP_Q"?ds.conversions.filter(c=>r.years.includes(c.year)):[]),
      national_conversion_inputs:JSON.stringify(r.country.iso==="GBR"&&r.kind==="research"&&r.sector==="BES"?(ds.officialConversions||[]).filter(c=>r.years.includes(c.year)&&c.basis===opts.basis):[])})));
  }
  const api={select,exportRows};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.RDBreakdowns=api;
})(typeof globalThis!=="undefined"?globalThis:this);
