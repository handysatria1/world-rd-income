'use strict';
(function(root){
  const labels={HIC:'High income',UMC:'Upper-middle income',LMC:'Lower-middle income',MIC:'Middle income',LIC:'Low income',UNK:'Unclassified'};
  const colors={HIC:'#176181',UMC:'#4f8c7b',LMC:'#d38b32',MIC:'#8965a8',LIC:'#bd6b35'};
  const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg';
  const fmt=v=>v==null?'Missing':Number(v).toLocaleString('en',{maximumFractionDigits:2});
  const node=(tag,attrs={},text)=>{const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;return n;};
  function rowsFor(data,metric,vintage,combine){
    const chosen=vintage==='current'?data.current_vintage:vintage;
    const codes=combine?['HIC','MIC','LIC']:['HIC','UMC','LMC','LIC'];
    return codes.map(code=>data.group_averages.find(r=>r.classification_vintage===chosen&&r.income_group_code===code&&r.metric===metric)).filter(Boolean);
  }
  function classification(country,vintage,combine){
    const code=vintage==='current'?country.current_income_code:(country.history?.[vintage]||'UNK');
    return combine&&['UMC','LMC'].includes(code)?'MIC':code;
  }
  function periodFor(data,mode,year,from,to){
    const first=data.first_year,last=data.last_year;
    let start,end;
    if(mode==='single')start=end=Number(year);
    else if(mode==='last5'){end=last;start=Math.max(first,last-4);}
    else{start=Number(from);end=Number(to);}
    if(!Number.isInteger(start)||!Number.isInteger(end)||start<first||end>last||start>end)
      throw new Error(`Choose an ordered period within ${first}–${last}.`);
    return {start,end,years:Array.from({length:end-start+1},(_,i)=>start+i),
      label:start===end?String(start):`${start}–${end}`};
  }
  function calculateAverages(data,income,metric,vintage,combine,start,end){
    const incomeCountries=new Map((income?.countries||[]).map(country=>[country.iso,country]));
    const countries=data.countries.map(country=>{
      const source=incomeCountries.get(country.iso3),observations=[];
      for(let year=start;year<=end;year++){
        const value=source?.series?.[metric]?.[String(year)]?.v;
        if(value!=null&&Number.isFinite(Number(value)))observations.push([year,Number(value)]);
      }
      const n=observations.length;
      return {...country,average:n?observations.reduce((sum,row)=>sum+row[1],0)/n:null,
        n_years:n,first_year:n?observations[0][0]:null,last_year:n?observations[n-1][0]:null,
        income_group:labels[classification(country,vintage,combine)]||labels.UNK};
    });
    const codes=combine?['HIC','MIC','LIC']:['HIC','UMC','LMC','LIC'];
    const groups=codes.map(code=>{
      const members=countries.filter(country=>classification(country,vintage,combine)===code);
      const observed=members.filter(country=>country.average!=null);
      return {income_group_code:code,income_group:labels[code],
        mean_of_country_means:observed.length?observed.reduce((sum,country)=>sum+country.average,0)/observed.length:null,
        economies_with_data:observed.length,economies_in_group:members.length,
        coverage_percent:members.length?100*observed.length/members.length:null,
        included_iso3:observed.map(country=>country.iso3).sort().join(';'),
        missing_iso3:members.filter(country=>country.average==null).map(country=>country.iso3).sort().join(';')};
    });
    return {countries,groups};
  }
  function drawChart(rows,metric){
    const width=1100,left=300,plotWidth=590,rowHeight=58,top=58,height=top+rows.length*rowHeight+24;
    const observed=rows.map(r=>r.mean_of_country_means).filter(Number.isFinite);
    let minimum=Math.min(0,...observed),maximum=Math.max(0,...observed);
    if(minimum===maximum){maximum=minimum+1;}
    const pad=(maximum-minimum)*.1;minimum-=pad;maximum+=pad;
    const xFor=v=>left+(v-minimum)/(maximum-minimum)*plotWidth,zero=xFor(0);
    const svg=node('svg',{id:'capacity-svg',xmlns:NS,width,height,viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':metric.label+' average by World Bank income group','font-family':'Arial, sans-serif'});
    svg.append(node('rect',{width,height,fill:'white'}));
    svg.append(node('text',{x:20,y:30,fill:'#172f42','font-size':18,'font-weight':700},metric.label));
    svg.append(node('text',{x:left,y:30,fill:'#526777','font-size':13},metric.unit));
    for(let i=0;i<=4;i++){
      const value=minimum+(maximum-minimum)*i/4,x=xFor(value);
      svg.append(node('line',{x1:x,y1:top-12,x2:x,y2:height-18,stroke:'#dce5ea'}));
      svg.append(node('text',{x,y:height-2,fill:'#526777','font-size':11,'text-anchor':'middle'},fmt(value)));
    }
    svg.append(node('line',{x1:zero,y1:top-12,x2:zero,y2:height-18,stroke:'#647986','stroke-width':1.5}));
    rows.forEach((row,i)=>{
      const y=top+i*rowHeight,value=row.mean_of_country_means,group=row.income_group_code;
      svg.append(node('text',{x:20,y:y+23,fill:'#172f42','font-size':14},row.income_group));
      if(value==null){svg.append(node('text',{x:left+10,y:y+23,fill:'#526777','font-size':13},'No observations'));return;}
      const x=xFor(value),rectX=Math.min(zero,x),barWidth=Math.max(1,Math.abs(x-zero));
      svg.append(node('rect',{x:rectX,y:y+4,width:barWidth,height:28,rx:3,fill:colors[group]||'#176181'}));
      const positive=value>=0,labelX=positive?Math.min(left+plotWidth-5,x+7):Math.max(left+5,x-7);
      svg.append(node('text',{x:labelX,y:y+24,fill:'#172f42','font-size':12,'text-anchor':positive?'start':'end'},fmt(value)));
      svg.append(node('text',{x:left+plotWidth+18,y:y+23,fill:'#526777','font-size':12},`${row.economies_with_data}/${row.economies_in_group} economies`));
    });
    return svg;
  }
  function fillTable(tableId,rows,columns){
    const table=$(tableId);table.tHead.replaceChildren();table.tBodies[0].replaceChildren();
    const header=table.tHead.insertRow();
    for(const col of columns){const th=document.createElement('th');th.textContent=col.label;header.append(th);}
    for(const row of rows){const tr=table.tBodies[0].insertRow();for(const col of columns){const td=tr.insertCell(),value=row[col.key];td.textContent=col.format?col.format(value,row):value??'—';}}
  }
  function render(data,state){
    const key=$('capacity-metric').value||data.metrics[0].key;
    const metric=data.metrics.find(item=>item.key===key)||data.metrics[0];
    const vintage=$('capacity-vintage').value||'current',combine=$('capacity-combine').checked;
    const mode=$('capacity-period').value||'range';
    $('capacity-year-control').hidden=mode!=='single';
    $('capacity-from-control').hidden=mode!=='range';
    $('capacity-to-control').hidden=mode!=='range';
    $('capacity-error').hidden=true;
    let period;
    try{period=periodFor(data,mode,$('capacity-year').value,$('capacity-from').value,$('capacity-to').value);}
    catch(error){$('capacity-error').textContent=error.message;$('capacity-error').hidden=false;
      $('capacity-chart').replaceChildren();fillTable('capacity-groups-table',[],[]);fillTable('capacity-country-table',[],[]);
      $('capacity-status').textContent='';$('capacity-country-note').textContent='';return;}
    const calculated=calculateAverages(data,state.income,metric.key,vintage,combine,period.start,period.end);
    const groups=calculated.groups;
    $('capacity-heading').textContent=`${metric.label} · ${period.label} · ${metric.unit}`;
    $('capacity-chart').replaceChildren(drawChart(groups,metric));
    fillTable('capacity-groups-table',groups,[
      {key:'income_group',label:'World Bank income group'},
      {key:'mean_of_country_means',label:'Average of country means',format:fmt},
      {key:'economies_with_data',label:'Countries with data'},
      {key:'economies_in_group',label:'Countries classified'},
      {key:'coverage_percent',label:'Coverage',format:v=>v==null?'—':fmt(v)+'%'},
    ]);
    const countryRows=calculated.countries.map(country=>({
      economy:country.economy,iso3:country.iso3,income_group:country.income_group,
      average:country.average,n_years:country.n_years,
      years:country.n_years?`${country.first_year}–${country.last_year}`:'—'}));
    fillTable('capacity-country-table',countryRows,[
      {key:'economy',label:'Economy'},{key:'iso3',label:'ISO3'},
      {key:'income_group',label:'World Bank income group'},
      {key:'average',label:`Country mean (${metric.unit})`,format:fmt},
      {key:'n_years',label:'Observed years'}, {key:'years',label:'First–last observed year'},
    ]);
    const populatedGroups=groups.filter(row=>row.economies_with_data>0).length;
    const shownVintage=vintage==='current'?data.current_vintage:vintage;
    $('capacity-status').textContent=`Period: ${period.label}. Classification: ${shownVintage}${combine?' · middle-income economies combined':''}. Country means use only non-missing annual observations; group averages weight each country mean equally. ${populatedGroups} of ${groups.length} displayed income groups have observations. `+
      'Researchers are FTE per million people; R&D is expenditure as % of GDP; WGI estimate is separate from the 0–100 score; journal articles are annual counts.';
    $('capacity-country-note').textContent=`${data.countries.length} country-level means for ${metric.label} in ${period.label}. Each mean and its observed-year count/range are shown; the integrated country CSV remains the fixed 2000–2025 reference. The selected income vintage changes group labels, not country values.`;
  }
  function initialize(data){
    for(const metric of data.metrics)$('capacity-metric').add(new Option(`${metric.label} (${metric.unit})`,metric.key));
    $('capacity-vintage').add(new Option(`Current · ${data.current_vintage}`,'current'));
    for(const vintage of data.classification_vintages){
      if(vintage!==data.current_vintage)$('capacity-vintage').add(new Option(`${vintage} · fixed membership`,vintage));
    }
    for(let year=data.first_year;year<=data.last_year;year++){
      $('capacity-year').add(new Option(year,year));
      $('capacity-from').add(new Option(year,year));
      $('capacity-to').add(new Option(year,year));
    }
    $('capacity-year').value=data.last_year;
    $('capacity-from').value=data.first_year;
    $('capacity-to').value=data.last_year;
    $('capacity-metric').value=data.metrics[0].key;
  }
  const api={initialize,render,rowsFor,periodFor,calculateAverages};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AbsorptiveCapacityChart=api;
})(typeof window!=='undefined'?window:globalThis);
