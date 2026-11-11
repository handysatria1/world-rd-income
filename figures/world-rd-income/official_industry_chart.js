'use strict';
const OfficialIndustries=(()=>{
  const $=id=>document.getElementById(id);let data=null,state=null,selected=[],pending=null;
  const format=v=>v==null?'Not published / suppressed':Number(v).toLocaleString('en',{maximumFractionDigits:3});
  function render(){
    if(!data||!state)return;
    const economy=$('official-economy'),previous=economy.value;
    economy.replaceChildren(...state.ids.map(iso=>new Option(state.names[iso]||iso,iso)));
    economy.value=state.ids.includes(previous)?previous:state.ids.includes('SGP')?'SGP':state.ids[0]||'';
    const iso=economy.value,metric=$('official-metric').value,source=$('official-source'),old=source.value;
    const common=state.year==='common'?[...new Set(data.rows.filter(r=>r.metric===metric&&r.amount_local!==null).map(r=>r.year))].sort((a,b)=>b-a).find(y=>state.ids.length&&state.ids.every(id=>data.rows.some(r=>r.iso3===id&&r.metric===metric&&r.year===y&&r.amount_local!==null))):null;
    const available=data.rows.filter(r=>r.iso3===iso&&r.metric===metric&&(state.year==='latest'||r.year===(state.year==='common'?common:Number(state.year))));
    const names={'SingStat M354861':'SingStat · manufacturing industries','SingStat M355181':'SingStat · manufacturing clusters','SingStat M015731':'SingStat · national accounts','SGP_RIE':'A*STAR · RIE 2023','EUSTAT_NATIVE':'Eustat · companies + PNPI'};
    const sources=[...new Set(available.map(r=>r.source))];source.replaceChildren(...sources.map(s=>new Option(names[s]||s,s)));source.value=sources.includes(old)?old:sources[0]||'';
    const candidates=available.filter(r=>r.source===source.value),year=Math.max(...candidates.map(r=>r.year));
    selected=candidates.filter(r=>r.year===year);
    $('official-status').textContent=selected.length?`${state.names[iso]||iso} · ${metric} · ${year} · ${selected[0].scope}. Values in million ${selected[0].currency}; converted US$ use that observation year’s exchange rate.`:'No verified source-native observations for this economy / year selection.';
    $('official-note').textContent=[...new Set(selected.map(r=>r.note).filter(Boolean))].join(' ');
    const body=$('official-table').tBodies[0];body.replaceChildren();
    for(const r of selected){
      const tr=body.insertRow();for(const value of [r.activity_label,r.activity_code,r.year,r.amount_local==null?r.flags||'Not published':format(r.amount_local/1e6),format(r.amount_usd==null?null:r.amount_usd/1e6),r.flags||'—',r.source_locator])tr.insertCell().textContent=value;
      const cell=tr.insertCell(),link=document.createElement('a');link.href=r.source_url;link.textContent=r.source;link.target='_blank';link.rel='noopener';cell.append(link);
    }
    $('official-csv').disabled=!selected.length;
  }
  async function set(value){
    state=value;
    if(!pending)pending=fetch('government_industry_explorer.json').then(r=>{if(!r.ok)throw new Error('Official industry dataset unavailable');return r.json();}).then(d=>data=d).catch(e=>{pending=null;throw e;});
    await pending;render();
  }
  for(const id of ['official-economy','official-metric','official-source'])$(id).onchange=render;
  $('official-csv').onclick=()=>{
    if(!selected.length)return;const keys=Object.keys(selected[0]),q=v=>'"'+String(v??'').replaceAll('"','""')+'"';
    const blob=new Blob(['\ufeff'+[keys,...selected.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='official-published-industries.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  return {set,get exported(){return selected;}};
})();
