'use strict';
(()=>{
const data=JSON.parse(document.getElementById('research-data').textContent),$=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
let state={ids:data.defaults,year:'latest',names:Object.fromEntries(data.countries.map(c=>[c.iso,c.name]))},selected=[],exported=[],changes=[],sector='Manufacturing';
const byKey=new Map(),audit=new Map(data.coverage.map(r=>[r.iso3+'/'+r.year,r]));
const loaded=new Map();let request=0;
for(const r of data.rows){const key=r.iso3+'/'+r.year;if(!byKey.has(key))byKey.set(key,[]);byKey.get(key).push(r);}
const fmt=v=>v==null?'Missing':Number(v).toLocaleString('en',{maximumFractionDigits:2}),short=v=>v>=1e6?(v/1e6).toFixed(1)+'m':v>=1e3?(v/1e3).toFixed(1)+'k':+v.toFixed(2);
function n(tag,attrs={},value){const e=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(value!=null)e.textContent=value;return e;}
function txt(svg,x,y,value,attrs={}){svg.append(n('text',{x,y,fill:'#172f42','font-size':12,...attrs},value));}
function wrap(svg,x,y,value,width=32){const lines=[''];for(const word of value.split(' ')){if((lines.at(-1)+' '+word).length>width)lines.push(word);else lines[lines.length-1]+=(lines.at(-1)?' ':'')+word;}lines.forEach((s,i)=>txt(svg,x,y+i*15,s,{'text-anchor':'middle','font-size':12}));}
function bind(node,row,metric){const m=metric.startsWith('berd')?'BERD':metric.startsWith('gva')?'GVA':'Employment',d=row.details[m],unit=metric.endsWith('_share_percent')?'% of total':metric.endsWith('_assigned_usd')?'current US$':metric==='employment_assigned_persons'?'persons':metric==='berd_percent_gva'?'% of GVA':'US$ per person';const info=`${row.economy} · ${row.year} · ${row.group_id} ${row.research_group}\n${metric}: ${fmt(row[metric])} ${unit}.\nCoverage: ${row[m==='BERD'?'berd_coverage':m==='GVA'?'gva_coverage':'employment_coverage']}\nSource: ${row[m==='BERD'?'berd_source':m==='GVA'?'gva_source':'employment_source']}\nExpression: ${d.expression}\nMissing source codes / ISIC classes: ${d.missing||'none listed; see native coverage note'}\n${d.note}\nSource-cell locators: research_group_components.csv; match ${row.iso3}/${row.year}/${row.group_id}/${m}.\n${m==='BERD'?'Assigned BERD share is a fraction of reported total BERD, not expenditure coverage of this sector.':''}`;
const full=info+'\nSource flags: '+(row[m==='BERD'?'berd_flags':m==='GVA'?'gva_flags':'employment_flags']||'none reported')+'.'+(m==='BERD'?'\nOriginal amount: '+fmt(row.berd_assigned_local)+' '+row.berd_currency+'; scope: '+row.berd_scope+'.':'');
inspect(node,full);}
function inspect(node,full){node.append(n('title',{},full));node.setAttribute('tabindex',0);node.setAttribute('role','button');node.setAttribute('aria-label',full);for(const event of ['pointerenter','focus','click'])node.addEventListener(event,()=>{$('research-detail').textContent=full;});node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('research-detail').textContent=full;}});}
function drawBar(svg,x,y,w,h,color,row,metric,partial){const rect=n('rect',{x,y,width:w,height:Math.max(.7,h),fill:color});svg.append(rect);if(row)bind(rect,row,metric);if(partial)svg.append(n('rect',{x,y,width:w,height:Math.max(.7,h),fill:'url(#research-partial)','pointer-events':'none'}));}
function usable(rows){if(!rows?.length)return false;const layout=$('research-layout').value,metric=$('research-metric').value;
 if(layout==='comparison')return ['berd_share_percent','gva_share_percent','employment_share_percent'].every(k=>rows.some(r=>r[k]!=null));
 return rows.some(r=>(layout!=='single'||r.group_id===$('research-group').value)&&r[metric]!=null);
}
function render(){
  $('research-detail').textContent='Select a bar to see its coverage and sources.';
 const layout=$('research-layout').value,paired=ResearchGroups.pairedLayouts.includes(layout),history=layout==='history',mode=$('research-measure').value,groups=paired?ResearchGroups.groups(data.groups,sector):data.groups;
 $('research-measure-label').hidden=!paired;$('research-sectors').hidden=!paired;$('research-history').hidden=!history;$('research-metric-label').hidden=paired||layout==='comparison';$('research-group-label').hidden=layout!=='single';$('research-changes-csv').hidden=!history;
 $('research-chart').classList.toggle('paired',paired);changes=[];
 const economy=$('research-economy'),previous=economy.value;economy.replaceChildren(...state.ids.map(iso=>new Option(state.names[iso]||iso,iso)));economy.value=state.ids.includes(previous)?previous:state.ids.includes('USA')?'USA':state.ids[0]||'';
  $('research-layout-help').textContent=history?'Years are shown in chronological order. Changes compare the first and last selected years; the year filter above does not apply.':paired?'Ranked by GVA in each panel. Latest and common years require both GVA and BERD for at least one selected industry.':'Choose an indicator to compare industries. Ratios are shown only where the whole group is covered.';
 if(history){const years=[...new Set(['a','b','c'].map(k=>+$('research-year-'+k).value))].sort((a,b)=>a-b);selected=economy.value?years.map(year=>({iso:economy.value,year,rows:byKey.get(economy.value+'/'+year)||[]})):[];}
 else selected=ResearchGroups.select(byKey,state.ids,state.year,paired?rows=>ResearchGroups.usable(rows,groups,mode):usable);
 selected=selected.map(a=>({...a,rows:a.rows.filter(r=>groups.some(g=>g.id===r.group_id))}));
 exported=selected.flatMap(a=>a.rows.length?a.rows.map(({details,...r})=>r):groups.map(g=>({...Object.fromEntries((data.columns||[]).map(k=>[k,null])),iso3:a.iso,economy:state.names[a.iso]||a.iso,year:a.year,group_id:g.id,research_group:g.label,sector:g.sector,berd_coverage:'unavailable',gva_coverage:'unavailable',employment_coverage:'unavailable'}))).map(r=>({...r,year_selection:history?'exact historical years':state.year,view_layout:layout,display_measure:paired?mode:$('research-metric').value,sector_filter:paired?sector:'all',data_build_utc:data.builtUTC}));
 if(paired){const result=ResearchCompare.render({data,state,selected,groups,layout,mode,sector,host:$('research-chart'),n,txt,drawBar,inspect});changes=result.changes;$('research-chart').replaceChildren(result.svg);finish();return;}
 const metric=$('research-metric').value,panels=layout==='panels',width=1600,height=panels?1770:layout==='comparison'?1000:700;
 $('research-metric').disabled=layout==='comparison';$('research-group').disabled=layout!=='single';
 const svg=n('svg',{xmlns:NS,width,height,viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'Sixteen research group comparison','font-family':'Arial, sans-serif'});svg.append(n('rect',{width,height,fill:'white'}));
 const defs=n('defs'),pattern=n('pattern',{id:'research-partial',width:8,height:8,patternUnits:'userSpaceOnUse'});pattern.append(n('path',{d:'M0,8 L8,0',stroke:'white','stroke-width':2,'stroke-opacity':.65}));defs.append(pattern);svg.append(defs);
  txt(svg,24,32,'16 industry groups · '+(layout==='comparison'?'GVA, BERD and employment shares':$('research-metric').selectedOptions[0].text),{'font-size':22,'font-weight':700});
  txt(svg,24,60,(state.year==='latest'?'Latest available years':state.year==='common'?'Latest common year':'Reporting year '+state.year)+' · Hatched = partial coverage; — = missing.',{'font-size':14});
 if(layout==='comparison'){
  const left=65,top=130,h=410,w=1150,slot=w/Math.max(1,selected.length),bw=Math.min(44,slot*.25);
  for(let i=0;i<=4;i++){const y=top+h-i*h/4;svg.append(n('line',{x1:left,y1:y,x2:left+w,y2:y,stroke:'#dce5ea'}));txt(svg,left-10,y+4,i*25+'%',{'text-anchor':'end'});}
  selected.forEach((a,i)=>{const center=left+(i+.5)*slot;
   ['gva','berd','employment'].forEach((prefix,j)=>{const x=center+(j-1.5)*(bw+3),key=prefix+'_share_percent',known=a.rows.filter(r=>r[key]!=null);let bottom=top+h;
    if(!known.length){txt(svg,x+bw/2,top+h/2,'—',{'text-anchor':'middle'});}else{
      let sum=0;for(const r of known){const v=r[key],bh=v/100*h;bottom-=bh;sum+=v;drawBar(svg,x,bottom,bw,bh,data.groups.find(g=>g.id===r.group_id).color,r,key,r[prefix+'_coverage']!=='complete');}
      if(sum<=100.00001&&100-sum>.001){const bh=(100-sum)/100*h;bottom-=bh;const rect=n('rect',{x,y:bottom,width:bw,height:bh,fill:'#d1d8dc'});rect.append(n('title',{},'Unallocated / reconciliation: '+fmt(100-sum)+'% of denominator.'));svg.append(rect);}
    }txt(svg,x+bw/2,top+h+19,['GVA','R&D','Jobs'][j],{'text-anchor':'middle','font-size':10});
   });wrap(svg,center,top+h+44,state.names[a.iso]||a.iso,Math.max(8,Math.floor(slot/7)));txt(svg,center,top+h+101,a.year??'No usable year',{'text-anchor':'middle','font-size':11});
  });
  data.groups.forEach((g,i)=>{svg.append(n('rect',{x:1255,y:110+i*42,width:13,height:13,fill:g.color}));const words=(g.id+' · '+g.label).split(' '),lines=[''];for(const word of words){if((lines.at(-1)+' '+word).length>43)lines.push(word);else lines[lines.length-1]+=(lines.at(-1)?' ':'')+word;}lines.forEach((line,j)=>txt(svg,1277,121+i*42+j*14,line,{'font-size':11}));});
  txt(svg,24,814,'Denominators differ: GVA and employment = A–T totals; BERD = reported industry R&D total, which can include U.',{'font-size':13});
  txt(svg,24,838,'Grey = unallocated / reconciliation. Groups 14 and 15 span KIS and LIS; values are calculated from original industry data.',{'font-size':13});
 }else{
  const groups=panels?data.groups:data.groups.filter(g=>g.id===$('research-group').value),columns=panels?4:1,pw=(width-40)/columns,ph=390;
  const factor=['berd_assigned_usd','gva_assigned_usd'].includes(metric)?1e9:metric==='employment_assigned_persons'?1e6:1;
  groups.forEach((g,p)=>{const x0=20+p%columns*pw,y0=110+Math.floor(p/columns)*ph,left=x0+65,top=y0+48,w=pw-86,h=215;
    wrap(svg,x0+pw/2,y0,g.id+' · '+g.label,panels?34:90);const values=selected.map(a=>a.rows.find(r=>r.group_id===g.id)?.[metric]??null),max=Math.max(1,...values.filter(v=>v!=null).map(v=>v/factor))*1.18;
    for(let i=0;i<=4;i++){const y=top+h-h*i/4;svg.append(n('line',{x1:left,y1:y,x2:left+w,y2:y,stroke:'#dce5ea'}));txt(svg,left-7,y+4,short(max*i/4),{'text-anchor':'end','font-size':10});}
    const slot=w/Math.max(1,selected.length);selected.forEach((a,i)=>{const r=a.rows.find(r=>r.group_id===g.id),v=values[i],x=left+(i+.18)*slot,bw=slot*.64;
      if(v!=null){const bh=v/factor/max*h,coverage=metric.startsWith('berd')?'berd_coverage':metric.startsWith('gva')?'gva_coverage':'employment_coverage';drawBar(svg,x,top+h-bh,bw,bh,g.color,r,metric,r[coverage]!=='complete');txt(svg,x+bw/2,top+h-bh-6,short(v/factor),{'text-anchor':'middle','font-size':10});}else txt(svg,x+bw/2,top+h/2,'—',{'text-anchor':'middle'});
      txt(svg,x+bw/2,top+h+20,a.iso,{'text-anchor':'middle','font-size':panels?9:12});txt(svg,x+bw/2,top+h+36,a.year??'—',{'text-anchor':'middle','font-size':9});
    });
  });
 }
 txt(svg,24,height-65,'Handy Satria · OECD TiVA / TiM / RDS; Eustat; A*STAR RIE. All currency conversions use exact same-year inputs.',{'font-size':13});
 txt(svg,24,height-43,'Basque R&D: companies + PNPI. Singapore RIE: S&T only. Whole-group ratios require complete coverage; native allocations remain partial.',{'font-size':12});
 txt(svg,24,height-21,'Group 16 = R–T. U and unresolved mixed branches remain outside assigned groups. Original data, flags and class bridge are downloadable.',{'font-size':12});
 $('research-chart').replaceChildren(svg);finish();
}
function finish(){
 $('research-status').textContent=selected.length?selected.map(a=>(state.names[a.iso]||a.iso)+': '+(a.year??'no usable year')+(a.rows.length?'':' · missing')).join(' · '):'Choose an economy in the shared controls.';
 $('research-changes-csv').disabled=!changes.length;
 const table=$('research-table'),cols=exported.length?Object.keys(exported[0]):['economy','year','group_id'];table.tHead.replaceChildren();table.tBodies[0].replaceChildren();const h=table.tHead.insertRow();for(const c of cols){const th=document.createElement('th');th.textContent=c.replaceAll('_',' ');h.append(th);}for(const r of exported){const tr=table.tBodies[0].insertRow();for(const c of cols)tr.insertCell().textContent=r[c]??'—';}
}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function serialized(){return new XMLSerializer().serializeToString($('research-chart').querySelector('svg'));}
$('research-svg').onclick=()=>save(new Blob([serialized()],{type:'image/svg+xml;charset=utf-8'}),'research-groups.svg');
function csv(rows,name){if(!rows.length)return;const keys=Object.keys(rows[0]),q=v=>'"'+String(v??'').replaceAll('"','""')+'"';save(new Blob(['\ufeff'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),name);}
$('research-csv').onclick=()=>csv(exported,'research-groups-joined.csv');$('research-changes-csv').onclick=()=>csv(changes,'research-groups-endpoint-changes.csv');
$('research-png').onclick=async()=>{const url=URL.createObjectURL(new Blob([serialized()],{type:'image/svg+xml'}));try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('PNG encoding failed');save(blob,'research-groups.png');$('research-export-status').textContent='PNG ready.';}catch(e){$('research-export-status').textContent=e.message;}finally{URL.revokeObjectURL(url);}};
for(const g of data.groups){$('research-group').add(new Option(g.id+' · '+g.label,g.id));const row=$('research-classification').tBodies[0].insertRow();for(const v of [g.id,g.sector,g.label,g.codes.join(' + ')])row.insertCell().textContent=v;}
for(const [k,value]of [['a',2000],['b',2010],['c',2022]]){for(let y=2000;y<=2025;y++)$('research-year-'+k).add(new Option(y,y));$('research-year-'+k).value=value;}
for(const id of ['research-layout','research-metric','research-group','research-measure','research-economy','research-year-a','research-year-b','research-year-c'])$(id).onchange=render;
document.querySelectorAll('[data-sector]').forEach(b=>b.onclick=()=>{sector=b.dataset.sector;document.querySelectorAll('[data-sector]').forEach(c=>c.setAttribute('aria-pressed',c===b));render();});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(ResearchGroups.pairedLayouts.includes($('research-layout').value))render();},120);});
$('research-build').textContent='Build: '+data.builtUTC;render();
if(typeof dashboardBridge!=='undefined')dashboardBridge.register({async set(value){const token=++request;
 await Promise.all(value.ids.filter(iso=>data.partitions?.[iso]).map(iso=>{if(!loaded.has(iso))loaded.set(iso,(async()=>{try{for(const r of await loadDashboardJSON(data.partitions[iso])){const key=r.iso3+'/'+r.year;if(!byKey.has(key))byKey.set(key,[]);byKey.get(key).push(r);}}catch(error){loaded.delete(iso);throw error;}})());return loaded.get(iso);}));if(token!==request)return;state=value;render();},get rows(){return selected;},get exported(){return exported;},get changes(){return changes;}});
})();
