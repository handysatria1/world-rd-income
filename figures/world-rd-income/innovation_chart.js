'use strict';
window.InnovationChart=(()=>{
  const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
  const titles={researchers:'Researchers in R&D',patents:'Patent applications',publications:'Scientific and technical journal articles'};
  let result=null,filename='innovation';
  const fmt=v=>v==null?'Missing':v.toLocaleString('en',{maximumFractionDigits:2});
  const short=v=>v>=1e6?+(v/1e6).toFixed(1)+'m':v>=1e3?+(v/1e3).toFixed(1)+'k':+v.toFixed(2);
  function node(tag,attrs={},text){const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;return n;}
  function text(svg,x,y,s,attrs={}){const n=node('text',{x,y,fill:'#172f42','font-size':14,...attrs},s);svg.append(n);return n;}
  function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
  function render(data,shared){
    const metric=shared.kind,patents=$('innovation-patent-mode').value;
    result=IncomeCore.countryObservations(data,{...shared,metric,patents});
    const rows=result.rows,title=titles[metric],unit=data.indicators[metric].unit;
    const period=shared.year==='latest'?'Latest available · reporting years may differ':shared.year==='common'?(result.commonYear==null?'No common year for all selected economies':`Latest common year · ${result.commonYear}`):`Year · ${shared.year}`;
    const definition=metric==='patents'?(patents==='total'?'Residents and nonresidents':patents==='nonresident'?'Nonresidents':'Residents'):'';
    filename=`innovation-${metric}-${shared.year}${metric==='patents'?'-'+patents:''}`;
    $('innovation-heading').textContent=title+' by economy';
    $('innovation-patent-control').hidden=metric!=='patents';
    $('innovation-note').textContent=metric==='researchers'?'Researchers in R&D per million people (full-time equivalent), not total headcount.':metric==='patents'?'Applications filed at each economy’s patent office. Resident and nonresident totals require both series in the same year.':'Scientific and technical journal articles reported in the World Bank series.';
    $('innovation-inspector').textContent='Select an economy’s row to see its observation, source and reporting notes.';
    $('innovation-export-status').textContent='';
    const width=1120,top=116,step=40,bottom=top+Math.max(1,rows.length)*step,height=Math.max(420,bottom+88),left=288,plot=550;
    const max=Math.max(1,...rows.map(r=>r.value??0))*1.08;
    const svg=node('svg',{id:'innovation-svg',xmlns:NS,width,height,viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':title+' by economy','font-family':'Arial, sans-serif'});
    svg.append(node('rect',{width,height,fill:'white'}));
    text(svg,24,32,title,{'font-size':23,'font-weight':700});
    text(svg,24,58,period+(definition?' · '+definition:''));
    text(svg,24,80,unit,{'font-size':13,fill:'#526777'});
    text(svg,24,104,'Economy',{'font-size':12,'font-weight':700});text(svg,985,104,'Value',{'text-anchor':'end','font-size':12,'font-weight':700});text(svg,1094,104,'Year',{'text-anchor':'end','font-size':12,'font-weight':700});
    for(let i=0;i<=4;i++){const x=left+plot*i/4;svg.append(node('line',{x1:x,y1:top,x2:x,y2:bottom,stroke:'#dce5ea'}));text(svg,x,bottom+20,short(max*i/4),{'text-anchor':'middle','font-size':12});}
    rows.forEach((r,i)=>{
      const y=top+i*step;
      const description=`${r.economy} (${r.iso}) · ${r.year??'No reporting year'}\n${title}${definition?' · '+definition:''}: ${fmt(r.value)} ${unit}\n${r.missing_reason||r.method}\n${r.group_label} · ${r.classification}\nIndicator: ${r.indicator}\nSource: ${r.source_file}; record(s): ${r.source_record}; input value(s): ${r.source_values}\nFlags: ${r.flags.replaceAll(';','').trim()?r.flags:'none'}\nNotes: ${r.notes.replaceAll(';','').trim()?r.notes:'none'}\nWDI updated: ${r.api_lastupdated}; retrieved: ${r.retrieved_utc}`;
      const g=node('g',{tabindex:0,role:'button','aria-label':description,'data-iso':r.iso});g.append(node('title',{},description));
      g.append(node('rect',{x:12,y:y+1,width:1096,height:step-2,fill:i%2?'#f4f8fa':'white','fill-opacity':.7}));
      const name=text(g,24,y+25,r.economy,{'font-size':14});
      if(r.value!=null){g.append(node('rect',{x:left,y:y+8,width:Math.max(1,r.value/max*plot),height:24,fill:'#176181'}));}
      else text(g,left+8,y+25,'No data',{'font-size':13,fill:'#526777'});
      text(g,985,y+25,fmt(r.value),{'text-anchor':'end'});text(g,1094,y+25,r.year??'—',{'text-anchor':'end'});
      const inspect=()=>{$('innovation-inspector').textContent=description;};
      for(const event of ['pointerenter','focus','click'])g.addEventListener(event,inspect);
      g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect();}});
      svg.append(g);
      name.dataset.economyLabel='true';
    });
    if(!rows.length)text(svg,24,top+28,'Select economies above to compare their observations.');
    text(svg,24,height-33,'Handy Satria · World Bank WDI · '+(metric==='researchers'?'UNESCO UIS':metric==='patents'?'WIPO':'NSF'),{'font-size':12});
    text(svg,24,height-13,'Missing is not zero. Exact years are not replaced. Source observations: 2000–2025.',{'font-size':12});
    $('innovation-chart').replaceChildren(svg);
    for(const label of svg.querySelectorAll('[data-economy-label]')){
      const full=label.textContent;
      if(label.getComputedTextLength()>left-42){
        let split=full.lastIndexOf(' ',Math.floor(full.length/2));if(split<1)split=Math.floor(full.length/2);
        label.textContent='';label.setAttribute('y',+label.getAttribute('y')-8);
        for(const [j,line]of[full.slice(0,split),full.slice(split).trim()].entries()){
          const span=node('tspan',{x:24,dy:j?16:0},line);label.append(span);
          if(span.getComputedTextLength()>left-42){span.setAttribute('textLength',left-42);span.setAttribute('lengthAdjust','spacingAndGlyphs');}
        }
      }
    }
    const observed=rows.filter(r=>r.value!=null).length;
    $('innovation-status').textContent=`${observed} of ${rows.length} selected economies have data. `+(shared.year==='common'?'Latest common year requires an observation for every selected economy, including any selected region. ':shared.year==='latest'?'Each economy uses its most recent available observation. ':'Only observations in the selected year are shown. ')+(rows.some(r=>r.geography_type==='region')?'Basque Country has no separate observations in these WDI series. ':'')+'Open “Select economies” to add, remove or reorder countries.';
    const columns=['economy','year','value','unit','availability','missing_reason','indicator','method','flags','notes'],table=$('innovation-table');
    table.tHead.replaceChildren();table.tBodies[0].replaceChildren();const head=table.tHead.insertRow();
    for(const key of columns){const th=document.createElement('th');th.textContent=key.replaceAll('_',' ');head.append(th);}
    for(const row of rows){const tr=table.tBodies[0].insertRow();for(const key of columns)tr.insertCell().textContent=key==='value'?fmt(row[key]):row[key]??'—';}
    $('innovation-definitions').replaceChildren();
    for(const key of metric==='patents'?(patents==='total'?['patents','patentsNonresident']:[patents==='nonresident'?'patentsNonresident':'patents']):[metric]){
      const m=data.indicators[key],p=document.createElement('p');p.textContent=`${m.label} (${m.code}; ${m.unit}). ${m.definition} Source: ${m.organization}. WDI updated: ${m.updated}; retrieved ${m.retrieved}.`;$('innovation-definitions').append(p);
    }
    $('innovation-csv-download').disabled=!rows.length;
  }
  function initialize(){
    const serialize=()=>new XMLSerializer().serializeToString($('innovation-svg'));
    $('innovation-svg-download').onclick=()=>save(new Blob([serialize()],{type:'image/svg+xml;charset=utf-8'}),filename+'.svg');
    $('innovation-csv-download').onclick=()=>{if(!result?.rows.length)return;const keys=Object.keys(result.rows[0]),q=v=>'"'+String(v??'').replaceAll('"','""')+'"';save(new Blob(['\ufeff'+[keys,...result.rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),filename+'.csv');};
    $('innovation-png-download').onclick=async()=>{
      const svg=$('innovation-svg'),name=filename,url=URL.createObjectURL(new Blob([serialize()],{type:'image/svg+xml'}));
      try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement('canvas');canvas.width=svg.viewBox.baseVal.width*2;canvas.height=svg.viewBox.baseVal.height*2;canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('PNG encoding failed');save(blob,name+'.png');$('innovation-export-status').textContent='PNG ready.';}catch(error){$('innovation-export-status').textContent=error.message;}finally{URL.revokeObjectURL(url);}
    };
  }
  return {initialize,render,get result(){return result;}};
})();
