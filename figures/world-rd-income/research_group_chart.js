'use strict';
(()=>{
const data=JSON.parse(document.getElementById('research-data').textContent),$=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
let state={ids:data.defaults,year:'latest',names:Object.fromEntries(data.countries.map(c=>[c.iso,c.name]))},selected=[],exported=[];
const byKey=new Map(),audit=new Map(data.coverage.map(r=>[r.iso3+'/'+r.year,r]));
const loaded=new Map();let request=0;
for(const r of data.rows){const key=r.iso3+'/'+r.year;if(!byKey.has(key))byKey.set(key,[]);byKey.get(key).push(r);}
const fmt=v=>v==null?'Missing':Number(v).toLocaleString('en',{maximumFractionDigits:2}),short=v=>v>=1e6?(v/1e6).toFixed(1)+'m':v>=1e3?(v/1e3).toFixed(1)+'k':+v.toFixed(2);
function n(tag,attrs={},value){const e=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(value!=null)e.textContent=value;return e;}
function txt(svg,x,y,value,attrs={}){svg.append(n('text',{x,y,fill:'#172f42','font-size':12,...attrs},value));}
function wrap(svg,x,y,value,width=32){const lines=[''];for(const word of value.split(' ')){if((lines.at(-1)+' '+word).length>width)lines.push(word);else lines[lines.length-1]+=(lines.at(-1)?' ':'')+word;}lines.forEach((s,i)=>txt(svg,x,y+i*15,s,{'text-anchor':'middle','font-size':12}));}
function bind(node,row,metric){const m=metric.startsWith('berd')?'BERD':metric.startsWith('gva')?'GVA':'Employment',d=row.details[m];const info=`${row.economy} · ${row.year} · ${row.group_id} ${row.research_group}\n${metric}: ${fmt(row[metric])} (CSV unit amounts).\nCoverage: ${row[m==='BERD'?'berd_coverage':m==='GVA'?'gva_coverage':'employment_coverage']}\nSource: ${row[m==='BERD'?'berd_source':m==='GVA'?'gva_source':'employment_source']}\nExpression: ${d.expression}\nMissing source codes / ISIC classes: ${d.missing||'none listed; see native coverage note'}\n${d.note}\nSource-cell locators: research_group_components.csv; match ${row.iso3}/${row.year}/${row.group_id}/${m}.\n${m==='BERD'?'Assigned BERD share is a fraction of reported total BERD, not expenditure coverage of this sector.':''}`;
const full=info+'\nSource flags: '+(row[m==='BERD'?'berd_flags':m==='GVA'?'gva_flags':'employment_flags']||'none reported')+'.';
node.append(n('title',{},full));node.setAttribute('tabindex',0);node.setAttribute('role','button');node.setAttribute('aria-label',full);for(const event of ['pointerenter','focus','click'])node.addEventListener(event,()=>{$('research-detail').textContent=full;});node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('research-detail').textContent=full;}});}
function drawBar(svg,x,y,w,h,color,row,metric,partial){const rect=n('rect',{x,y,width:w,height:Math.max(.7,h),fill:color});svg.append(rect);if(row)bind(rect,row,metric);if(partial)svg.append(n('rect',{x,y,width:w,height:Math.max(.7,h),fill:'url(#research-partial)','pointer-events':'none'}));}
function usable(rows){if(!rows?.length)return false;const layout=$('research-layout').value,metric=$('research-metric').value;
 if(layout==='comparison')return ['berd_share_percent','gva_share_percent','employment_share_percent'].every(k=>rows.some(r=>r[k]!=null));
 return rows.some(r=>(layout!=='single'||r.group_id===$('research-group').value)&&r[metric]!=null);
}
function render(){
 $('research-detail').textContent='Hover, focus or tap a segment for coverage, source expressions and flags.';
 const years=Array.from({length:26},(_,i)=>2025-i),common=state.year==='common'?years.find(y=>state.ids.length&&state.ids.every(iso=>usable(byKey.get(iso+'/'+y)))):null;
 selected=state.ids.map(iso=>{const year=state.year==='latest'?years.find(y=>usable(byKey.get(iso+'/'+y))):state.year==='common'?common:+state.year;return {iso,year:year??null,rows:byKey.get(iso+'/'+year)||[]};});
 exported=selected.flatMap(a=>a.rows.length?a.rows.map(({details,...r})=>({...r,year_selection:state.year})):data.groups.map(g=>({...Object.fromEntries((data.columns||[]).map(k=>[k,null])),iso3:a.iso,economy:state.names[a.iso]||a.iso,year:a.year,group_id:g.id,research_group:g.label,sector:g.sector,berd_coverage:'unavailable',gva_coverage:'unavailable',employment_coverage:'unavailable',year_selection:state.year})));
 const layout=$('research-layout').value,metric=$('research-metric').value,panels=layout==='panels',width=1600,height=panels?1770:layout==='comparison'?1000:700;
 $('research-metric').disabled=layout==='comparison';$('research-group').disabled=layout!=='single';
 const svg=n('svg',{xmlns:NS,width,height,viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':'Sixteen research group comparison','font-family':'Arial, sans-serif'});svg.append(n('rect',{width,height,fill:'white'}));
 const defs=n('defs'),pattern=n('pattern',{id:'research-partial',width:8,height:8,patternUnits:'userSpaceOnUse'});pattern.append(n('path',{d:'M0,8 L8,0',stroke:'white','stroke-width':2,'stroke-opacity':.65}));defs.append(pattern);svg.append(defs);
 txt(svg,24,32,'16 research groups · '+(layout==='comparison'?'GVA, BERD and employment shares':$('research-metric').selectedOptions[0].text),{'font-size':22,'font-weight':700});
 txt(svg,24,60,(state.year==='latest'?'Latest usable years':state.year==='common'?'Latest common usable year':'Reporting year '+state.year)+' · Hatched = partial coverage; missing is not zero.',{'font-size':14});
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
  txt(svg,24,838,'Grey = unallocated / reconciliation. Groups 14 and 15 cross the earlier KIS/LIS boundary; amounts are rebuilt from source cells.',{'font-size':13});
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
 $('research-chart').replaceChildren(svg);$('research-status').textContent=selected.map(a=>(state.names[a.iso]||a.iso)+': '+(a.year??'no usable year')).join(' · ');
 const table=$('research-table'),cols=exported.length?Object.keys(exported[0]):['economy','year','group_id'];table.tHead.replaceChildren();table.tBodies[0].replaceChildren();const h=table.tHead.insertRow();for(const c of cols){const th=document.createElement('th');th.textContent=c.replaceAll('_',' ');h.append(th);}for(const r of exported){const tr=table.tBodies[0].insertRow();for(const c of cols)tr.insertCell().textContent=r[c]??'—';}
}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function serialized(){return new XMLSerializer().serializeToString($('research-chart').querySelector('svg'));}
$('research-svg').onclick=()=>save(new Blob([serialized()],{type:'image/svg+xml;charset=utf-8'}),'research-groups.svg');
$('research-csv').onclick=()=>{if(!exported.length)return;const keys=Object.keys(exported[0]),q=v=>'"'+String(v??'').replaceAll('"','""')+'"';save(new Blob(['\ufeff'+[keys,...exported.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'research-groups-joined.csv');};
$('research-png').onclick=async()=>{const url=URL.createObjectURL(new Blob([serialized()],{type:'image/svg+xml'}));try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('PNG encoding failed');save(blob,'research-groups.png');$('research-export-status').textContent='PNG ready.';}catch(e){$('research-export-status').textContent=e.message;}finally{URL.revokeObjectURL(url);}};
for(const g of data.groups){$('research-group').add(new Option(g.id+' · '+g.label,g.id));const row=$('research-classification').tBodies[0].insertRow();for(const v of [g.id,g.sector,g.label,g.codes.join(' + ')])row.insertCell().textContent=v;}
for(const id of ['research-layout','research-metric','research-group'])$(id).onchange=render;
$('research-build').textContent='Build: '+data.builtUTC;render();
if(typeof dashboardBridge!=='undefined')dashboardBridge.register({async set(value){const token=++request;
 await Promise.all(value.ids.filter(iso=>data.partitions?.[iso]).map(iso=>{if(!loaded.has(iso))loaded.set(iso,(async()=>{try{for(const r of await loadDashboardJSON(data.partitions[iso])){const key=r.iso3+'/'+r.year;if(!byKey.has(key))byKey.set(key,[]);byKey.get(key).push(r);}}catch(error){loaded.delete(iso);throw error;}})());return loaded.get(iso);}));if(token!==request)return;state=value;render();},get rows(){return selected;},get exported(){return exported;}});
})();
