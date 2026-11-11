'use strict';
window.IncomeChart=(()=>{
  const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg',colors=['#176181','#bd6b35'];
  let result=null,data=null;
  const fmt=v=>v==null?'Missing':v.toLocaleString('en',{maximumFractionDigits:2});
  const short=v=>v>=1e6?(v/1e6).toFixed(1)+'m':v>=1e3?(v/1e3).toFixed(1)+'k':+v.toFixed(2);
  function node(tag,attrs={},text){const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;return n;}
  function text(svg,x,y,s,attrs={}){svg.append(node('text',{x,y,fill:'#172f42','font-size':13,...attrs},s));}
  function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
  function csv(rows,name){if(!rows.length)return;const keys=Object.keys(rows[0]),q=v=>'"'+String(v??'').replaceAll('"','""')+'"';save(new Blob(['\ufeff'+[keys,...rows.map(r=>keys.map(k=>r[k]))].map(r=>r.map(q).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),name);}
  function render(input,shared){
    $('income-inspector').textContent='Hover, focus or tap a bar for its values, sample and classification.';
    data=input;const years=[+$('income-year-a').value,+$('income-year-b').value];
    if(years[0]===years[1])throw new Error('Choose two different comparison years.');
    const opts={years,vintage:shared.vintage,combine:shared.combine,ids:shared.ids,groups:shared.groups,
      stat:$('income-stat').value,sample:$('income-sample').value,patents:$('patent-mode').value};
    result=IncomeCore.aggregate(data,opts);
    const svg=node('svg',{id:'income-svg',xmlns:NS,width:1240,height:900,viewBox:'0 0 1240 900',role:'img','aria-label':'Four-panel income-group innovation comparison','font-family':'Arial, sans-serif'});
    svg.append(node('rect',{width:1240,height:900,fill:'white'}));
    text(svg,28,32,'Innovation by World Bank income group',{'font-size':23,'font-weight':700});
    text(svg,28,58,`${years.join(' versus ')} · fixed ${shared.vintage==='current'?data.currentVintage:shared.vintage} classification · ${opts.sample==='paired'?'paired economy samples per indicator':'available economies in each year'}`);
    years.forEach((year,i)=>{svg.append(node('rect',{x:950+i*120,y:24,width:16,height:16,fill:colors[i]}));text(svg,974+i*120,38,year);});
    ['rd','researchers','patents','publications'].forEach((metric,p)=>{
      const rows=result.rows.filter(r=>r.metric===metric),groups=[...new Set(rows.map(r=>r.group))],x0=24+(p%2)*614,y0=100+Math.floor(p/2)*365,left=x0+78,top=y0+52,w=500,h=220;
      const max=Math.max(1,...rows.map(r=>r.value??0))*1.18;
      const title=metric==='patents'?`Patent applications · ${opts.patents==='total'?'resident + nonresident':opts.patents}`:data.indicators[metric].label;
      text(svg,x0+14,y0+8,title,{'font-size':17,'font-weight':700});
      text(svg,x0+14,y0+30,`${rows[0]?.method||'No groups'} · ${data.indicators[metric].unit}`,{'font-size':12,fill:'#526777'});
      for(let i=0;i<=4;i++){const y=top+h-i*h/4;svg.append(node('line',{x1:left,y1:y,x2:left+w,y2:y,stroke:'#dce5ea'}));text(svg,left-9,y+4,short(max*i/4),{'text-anchor':'end','font-size':11});}
      groups.forEach((code,g)=>{
        const slot=w/Math.max(1,groups.length),center=left+(g+.5)*slot,bw=Math.min(42,slot*.3);
        years.forEach((year,i)=>{
          const row=rows.find(r=>r.group===code&&r.year===year),x=center+(i-.5)*(bw+3)-bw/2;
          const description=`${IncomeCore.labels[code]} · ${year}\n${title}: ${fmt(row.value)} ${data.indicators[metric].unit}\n${row.method}; n=${row.n} of ${row.eligible} economies in selected group.\nIncluded: ${row.included||'none'}\nMissing / excluded: ${row.missing||'none'}\nClassification: ${row.classification}; ${row.sample} sample.`;
          if(row.value==null){text(svg,x+bw/2,top+h-6,'—',{'text-anchor':'middle'});text(svg,x+bw/2,top+h+17,'n=0',{'text-anchor':'middle','font-size':10});return;}
          const bh=row.value/max*h,rect=node('rect',{x,y:top+h-bh,width:bw,height:Math.max(.8,bh),fill:colors[i],tabindex:0,role:'button','aria-label':description,'data-metric':metric,'data-group':code,'data-year':year});
          rect.append(node('title',{},description));svg.append(rect);
          for(const event of ['pointerenter','focus','click'])rect.addEventListener(event,()=>{$('income-inspector').textContent=description;});
          rect.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('income-inspector').textContent=description;}});
          text(svg,x+bw/2,top+h-bh-7,short(row.value),{'text-anchor':'middle','font-size':11});
          text(svg,x+bw/2,top+h+17,'n='+row.n,{'text-anchor':'middle','font-size':10});
        });
        const label=code==='HIC'?['High','income']:code==='UMC'?['Upper-middle','income']:code==='LMC'?['Lower-middle','income']:code==='MIC'?['Middle','income']:['Low','income'];
        label.forEach((s,i)=>text(svg,center,top+h+38+i*15,s,{'text-anchor':'middle','font-size':12}));
      });
      if(!groups.length)text(svg,left+w/2,top+h/2,'No classified groups in this selection',{'text-anchor':'middle'});
    });
    text(svg,28,847,'Handy Satria · World Bank WDI: UNESCO UIS, WIPO and NSF source series. Exact years only; missing is not zero.',{'font-size':12});
    text(svg,28,868,'Means are unweighted across economies. Sums cover observed economies only. Sample sizes differ between indicators.',{'font-size':12});
    $('income-chart').replaceChildren(svg);
    $('income-status').textContent=`${result.rows.length} group-year statistics. ${data.currentVintage} is based on 2025 Atlas-method GNI per capita. Regional and unclassified economies are excluded from group statistics. Indicator vintages are listed below.`;
    const table=$('income-table'),columns=['metric','group_label','year','value','method','n','eligible','classification','included','missing'];
    table.tHead.replaceChildren();table.tBodies[0].replaceChildren();const h=table.tHead.insertRow();for(const key of columns){const th=document.createElement('th');th.textContent=key.replaceAll('_',' ');h.append(th);}
    for(const r of result.rows){const tr=table.tBodies[0].insertRow();for(const key of columns){const td=tr.insertCell();td.textContent=key==='value'?fmt(r[key]):r[key];}}
  }
  function initialize(input){
    data=input;for(const id of ['income-year-a','income-year-b'])for(let y=2000;y<=2025;y++){const o=new Option(y,y);$(id).add(o);}
    $('income-year-a').value='2000';$('income-year-b').value='2013';
    for(const m of Object.values(data.indicators)){const p=document.createElement('p');p.textContent=`${m.label} (${m.code}; ${m.unit}). ${m.definition} Source: ${m.organization}. WDI updated: ${m.updated}; retrieved ${m.retrieved}.`;$('income-definitions').append(p);}
    const serialize=()=>new XMLSerializer().serializeToString($('income-svg'));
    $('income-svg-download').onclick=()=>save(new Blob([serialize()],{type:'image/svg+xml;charset=utf-8'}),'income-group-comparison.svg');
    $('income-csv-download').onclick=()=>csv(result.rows,'income-group-statistics.csv');
    $('income-audit-download').onclick=()=>csv(result.audit,'income-group-country-inputs.csv');
    $('income-png-download').onclick=async()=>{const url=URL.createObjectURL(new Blob([serialize()],{type:'image/svg+xml'}));try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement('canvas');canvas.width=2480;canvas.height=1800;canvas.getContext('2d').drawImage(image,0,0,2480,1800);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw new Error('PNG encoding failed');save(blob,'income-group-comparison.png');$('income-export-status').textContent='PNG ready.';}catch(error){$('income-export-status').textContent=error.message;}finally{URL.revokeObjectURL(url);}};
  }
  return {initialize,render,get result(){return result;}};
})();
