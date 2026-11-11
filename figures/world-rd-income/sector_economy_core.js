/* Exact-year selection and medians, shared by browser and independent checks. */
(function(root) {
  "use strict";
  function series(row, kind) {return row[kind === "exports" ? "exports" : kind === "employment" ? "employment" : "productivity"];}
  function available(row, kind, unit) {
    const s=series(row,kind);
    return (kind==="comparison" ? s.comparisonStatus : s.status)==="available" &&
      (!(kind==="exports"&&unit==="amount") || s.total!==null);
  }
  function select(data, selected, mode, kind, unit="share") {
    const eligible=iso=>data.rows.filter(r=>r.iso===iso&&available(r,kind,unit));
    let common=null;
    if(mode==="common"&&selected.length) {
      const years=eligible(selected[0]).map(r=>r.year).filter(y=>selected.every(iso=>eligible(iso).some(r=>r.year===y)));
      if(years.length)common=Math.max(...years);
    }
    return selected.map(iso=>{
      const years=eligible(iso).map(r=>r.year);
      const year=mode==="common"?common:mode==="latest"?(years.length?Math.max(...years):null):Number(mode);
      const raw=data.rows.find(r=>r.iso===iso&&r.year===year);
      const row=raw&&available(raw,kind,unit)?series(raw,kind):null;
      return {iso,year,row,reason:row?"":year===null?"No complete year for this selection":raw?(kind==="comparison"?series(raw,kind).comparisonStatus:series(raw,kind).status)==="available"?"Currency conversion missing":kind==="comparison"?series(raw,kind).comparisonStatus:series(raw,kind).status:"No observation for requested year"};
    });
  }
  function median(values) {const a=values.filter(v=>v!==null&&Number.isFinite(v)).sort((a,b)=>a-b),n=a.length;return n?(a[Math.floor((n-1)/2)]+a[Math.floor(n/2)])/2:null;}
  const api={select,median};if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.SectorEconomy=api;
})(typeof globalThis!=="undefined"?globalThis:this);
