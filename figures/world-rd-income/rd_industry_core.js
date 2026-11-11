"use strict";
const RDIndustry=(()=>{
  const finite=v=>typeof v==="number"&&Number.isFinite(v);
  function available(r,kind,unit="share",group=0){
    if(!r)return false;
    if(kind==="intensity"||kind==="perWorker")return r[kind].some(finite);
    if(kind==="productivity")return finite(r.intensity[group])&&finite(r.productivity[group]);
    if(kind==="trade")return r.stackAvailable&&r.shares.slice(0,2).some((v,i)=>finite(v)&&finite(r.exportShares[i]));
    if(kind==="comparison")return r.stackAvailable&&r.gvaShares.every(finite)&&r.employmentShares.every(finite);
    return r.stackAvailable&&(unit==="share"||finite(r.totalUSD));
  }
  function select(data,ids,mode,kind,unit="share",group=0){
    const byISO=new Map(ids.map(iso=>[iso,data.rows.filter(r=>r.iso===iso).sort((a,b)=>b.year-a.year)]));
    let common=null;
    if(mode==="common"&&ids.length)common=byISO.get(ids[0]).find(r=>ids.every(iso=>byISO.get(iso).some(s=>s.year===r.year&&available(s,kind,unit,group))))?.year??null;
    return ids.map(iso=>{
      const rows=byISO.get(iso),year=mode==="common"?common:mode==="latest"?(rows.find(r=>available(r,kind,unit,group))??rows.find(r=>finite(r.totalLocal)))?.year??null:Number(mode);
      const row=rows.find(r=>r.year===year)??null;
      return {iso,year,row,available:available(row,kind,unit,group),reason:row?.status??(mode==="common"?"no common year with required data":"no industry observations")};
    });
  }
  return {finite,available,select};
})();
if(typeof module!=="undefined")module.exports=RDIndustry;
