'use strict';
const ResearchGroups=(()=>{
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const pairedLayouts=['economies','industries','history'];
  function groups(all,sector){return all.filter(g=>sector==='all'||g.sector===sector);}
  function measures(mode){return ['gva','berd'].map(prefix=>({prefix,key:prefix+(mode==='share'?'_share_percent':'_assigned_usd'),factor:mode==='share'?1:1e9,label:prefix==='gva'?'GVA':'Assigned BERD',color:prefix==='gva'?'#167d9a':'#d37132'}));}
  function usable(rows,selectedGroups,mode){return rows?.some(r=>selectedGroups.some(g=>g.id===r.group_id)&&measures(mode).every(m=>finite(r[m.key])))??false;}
  function select(byKey,ids,mode,accept){
    const years=[...new Set([...byKey.values()].map(rows=>rows[0]?.year).filter(finite))].sort((a,b)=>b-a);
    const common=mode==='common'?years.find(y=>ids.length&&ids.every(iso=>accept(byKey.get(iso+'/'+y)))):null;
    return ids.map(iso=>{const year=mode==='latest'?years.find(y=>accept(byKey.get(iso+'/'+y))):mode==='common'?common:Number(mode);return {iso,year:year??null,rows:byKey.get(iso+'/'+year)||[]};});
  }
  function rank(items,key){return [...items].sort((a,b)=>{
    const x=a.row?.[key],y=b.row?.[key];
    return finite(x)&&finite(y)?y-x:finite(x)?-1:finite(y)?1:0;
  });}
  function change(first,last,prefix,mode){
    const key=prefix+(mode==='share'?'_share_percent':'_assigned_usd'),a=first?.[key],b=last?.[key],unit=mode==='share'?'percentage points':'percent';
    let reason='';
    if(!finite(a)||!finite(b))reason='Missing endpoint';
    else if(first.iso3!==last.iso3||first.group_id!==last.group_id||first.year>=last.year)reason='Endpoints must match economy and group, in chronological order';
    else if(first[prefix+'_coverage']!=='complete'||last[prefix+'_coverage']!=='complete')reason='Incomplete endpoint coverage';
    else if(!first[prefix+'_source']||first[prefix+'_source']!==last[prefix+'_source']||(prefix==='berd'&&first.berd_scope!==last.berd_scope))reason='Source or scope differs between endpoints';
    else if(mode!=='share'&&a<=0)reason='Percentage change needs a positive starting value';
    return {value:reason?null:mode==='share'?b-a:(b-a)/a*100,unit,reason,start:a??null,end:b??null};
  }
  return {finite,pairedLayouts,groups,measures,usable,select,rank,change};
})();
if(typeof module!=='undefined')module.exports=ResearchGroups;
