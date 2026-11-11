'use strict';
const ResearchCompare=(()=>{
  const labels={economies:'Value added and business R&D by economy',industries:'Value added and business R&D by industry',history:'Value added and business R&D over time'};
  const number=v=>v===0?'0':Math.abs(v)<.01?v.toExponential(1):Number(v).toLocaleString('en',{maximumFractionDigits:2});
  function render({data,state,selected,groups,layout,mode,sector,host,n,txt,drawBar,inspect}){
    const measures=ResearchGroups.measures(mode),width=Math.max(560,Math.min(1500,host.clientWidth)),columns=width>=1100?2:1,pw=(width-40)/columns;
    const labelWidth=Math.min(245,pw*.43),rowHeight=69,panels=layout==='industries'?groups.map(g=>({title:g.id+' · '+g.label,subtitle:'Separate observation years shown',items:selected.map(a=>({label:(state.names[a.iso]||a.iso)+' · '+ResearchGroups.yearLabel(a),row:a.rows.find(r=>r.group_id===g.id)}))})):selected.map(a=>({title:state.names[a.iso]||a.iso,subtitle:ResearchGroups.yearLabel(a),items:groups.map(g=>({label:g.id+' · '+g.label,row:a.rows.find(r=>r.group_id===g.id)}))}));
    const count=layout==='industries'?selected.length:groups.length,ph=110+Math.max(1,count)*rowHeight,plotBottom=140+Math.ceil(panels.length/columns)*ph;
    const history=layout==='history',changeHeight=history?100+Math.ceil(2/columns)*(110+groups.length*48):0,height=Math.max(360,plotBottom+changeHeight+160);
    const svg=n('svg',{xmlns:'http://www.w3.org/2000/svg',width,height,viewBox:`0 0 ${width} ${height}`,role:'img','aria-label':labels[layout],'font-family':'Arial, sans-serif'});
    svg.append(n('rect',{width,height,fill:'white'}));
    const defs=n('defs'),pattern=n('pattern',{id:'research-partial',width:8,height:8,patternUnits:'userSpaceOnUse'});pattern.append(n('path',{d:'M0,8 L8,0',stroke:'white','stroke-width':2,'stroke-opacity':.7}));defs.append(pattern);svg.append(defs);
    function lines(x,y,value,maxWidth,size=12,color='#172f42'){
      const max=Math.max(10,Math.floor(maxWidth/(size*.53))),out=[''];
      for(const word of value.split(' ')){if((out.at(-1)+' '+word).trim().length>max&&out.at(-1))out.push(word);else out[out.length-1]+=(out.at(-1)?' ':'')+word;}
      out.forEach((v,i)=>txt(svg,x,y+i*(size+3),v,{'font-size':size,fill:color}));return out.length*(size+3);
    }
    txt(svg,20,30,labels[layout],{'font-size':20,'font-weight':700});
    txt(svg,20,55,(sector==='all'?'All '+data.groups.length+' groups':sector)+' · '+(mode==='share'?'% of each metric’s total':'Current US$ billion'),{'font-size':14});
    measures.forEach((m,i)=>{svg.append(n('rect',{x:20+i*115,y:72,width:16,height:12,fill:m.color}));txt(svg,42+i*115,83,m.label,{'font-size':12});});
    lines(20,108,'Ranked by GVA. Scales vary by panel. Hatching = partial coverage; — = missing; 0 = reported zero.',width-40,12,'#526777');
    if(!panels.length)txt(svg,20,180,'Choose at least one economy in the shared controls.');
    panels.forEach((panel,p)=>{
      const x=20+p%columns*pw,y=145+Math.floor(p/columns)*ph,left=x+labelWidth,w=pw-labelWidth-70;
      lines(x,y,panel.title,pw-25,15);txt(svg,x,y+40,panel.subtitle,{'font-size':12,fill:'#526777'});
      const items=ResearchGroups.rank(panel.items,measures[0].key),values=items.flatMap(a=>measures.map(m=>a.row?.[m.key]/m.factor)).filter(ResearchGroups.finite);
      const max=Math.max(.01,...values)*1.08,min=Math.min(0,...values)*1.08,scale=v=>left+(v-min)/(max-min)*w,zero=scale(0),top=y+65;
      for(let k=0;k<=4;k++){
        const v=min+(max-min)*k/4,x1=scale(v);svg.append(n('line',{x1,y1:top-4,x2:x1,y2:top+items.length*rowHeight-8,stroke:'#e3eaed'}));
        txt(svg,x1,top+items.length*rowHeight+10,number(v),{'font-size':10,'text-anchor':'middle',fill:'#526777'});
      }
      items.forEach((item,i)=>{
        const y1=top+i*rowHeight;lines(x,y1+17,item.label,labelWidth-16,12);
        measures.forEach((m,j)=>{
          const raw=item.row?.[m.key],value=ResearchGroups.finite(raw)?raw/m.factor:null,by=y1+6+j*23,partial=value!=null&&item.row[m.prefix+'_coverage']!=='complete';
          if(value!=null){
            const end=scale(value);drawBar(svg,Math.min(zero,end),by,Math.max(.9,Math.abs(end-zero)),14,m.color,item.row,m.key,partial);
            txt(svg,end+5,by+11,number(value)+(partial?'*':''),{'font-size':11,fill:m.color});
          }else{
            const missing=n('rect',{x:zero,y:by,width:30,height:16,fill:'transparent'});svg.append(missing);
             inspect(missing,(item.label)+' · '+m.label+'\nNo assignable observation in the selected source year. See official native industries for unresolved classifications.');
            txt(svg,zero+4,by+12,'—',{'font-size':12,fill:m.color,'pointer-events':'none'});
          }
        });
      });
    });
    const changes=[];
    if(history&&selected.length===1)txt(svg,20,plotBottom+25,'Choose at least two distinct years to calculate endpoint changes.');
    if(history&&selected.length>1){
      const first=selected[0],last=selected.at(-1),start=plotBottom+20,changeUnit=mode==='share'?'percentage points':'% change in current US$';
      txt(svg,20,start,`Change from ${first.year} to ${last.year}`,{'font-size':18,'font-weight':700});
      lines(20,start+23,mode==='share'?'Last share − first share, in percentage points. Same total denominators as the bars above.':'(Last − first) / first × 100. Nominal US$ changes include prices and exchange rates; they are not real growth.',width-40,12,'#526777');
      const ranked=ResearchGroups.rank(groups.map(g=>({g,row:last.rows.find(r=>r.group_id===g.id)})),measures[0].key);
      measures.forEach((m,p)=>{
        const x=20+p%columns*pw,y=start+85+Math.floor(p/columns)*(110+groups.length*48),left=x+labelWidth,w=pw-labelWidth-100;
        txt(svg,x,y,m.label+' · '+changeUnit,{'font-size':14,'font-weight':700});
        const entries=ranked.map(({g})=>{const a=first.rows.find(r=>r.group_id===g.id),b=last.rows.find(r=>r.group_id===g.id),d=ResearchGroups.change(a,b,m.prefix,mode);return {g,a,b,d};});
        const values=entries.map(e=>e.d.value).filter(ResearchGroups.finite),min=Math.min(0,...values),max=Math.max(0,...values),span=max-min||1,scale=v=>left+(v-min)/span*w,zero=scale(0);
        svg.append(n('line',{x1:zero,y1:y+18,x2:zero,y2:y+25+groups.length*48,stroke:'#9bafb9'}));
        entries.forEach(({g,a,b,d},i)=>{
          const by=y+25+i*48;
          lines(x,by+14,g.id+' · '+g.label,labelWidth-16,11);
          const record={iso3:first.iso,economy:state.names[first.iso]||first.iso,group_id:g.id,research_group:g.label,metric:m.prefix,measure:mode,first_year:first.year,last_year:last.year,first_value:d.start,last_value:d.end,input_unit:mode==='share'?'percent of total':'current USD',change:d.value,change_unit:d.unit,reason:d.reason};
          for(const [tag,row]of [['first',a],['last',b]])for(const k of ['coverage','source','flags','scope'])record[tag+'_'+k]=row?.[m.prefix+'_'+k]??'';
          for(const [tag,row]of [['first',a],['last',b]])record[tag+'_source_expression']=row?.details[m.prefix==='gva'?'GVA':'BERD']?.expression??'';
           record.source_file=(data.groups.length===6?'research_six_group':'research_group')+'_joined.csv; corresponding components CSV; exact iso3/year/group_id/metric';record.build_utc=data.builtUTC;changes.push(record);
          const info=Object.entries(record).map(([k,v])=>k.replaceAll('_',' ')+': '+(v??'unavailable')).join('\n');
          if(d.value!=null){
            const end=scale(d.value),bar=n('rect',{x:Math.min(zero,end),y:by+3,width:Math.max(.9,Math.abs(end-zero)),height:19,fill:m.color});svg.append(bar);inspect(bar,info);
            txt(svg,left+w+8,by+17,(d.value>0?'+':'')+number(d.value)+(mode==='share'?' pp':'%'),{'font-size':11});
          }else{
            const reason=d.reason==='Incomplete endpoint coverage'?'Partial endpoint':d.reason==='Missing endpoint'?'Missing endpoint':d.reason.startsWith('Percentage')?'Zero / negative baseline':'Source / scope differs';
            const target=n('rect',{x:left,y:by,width:pw-labelWidth-20,height:28,fill:'#f3f6f8'});svg.append(target);inspect(target,info);txt(svg,left+5,by+18,'— '+reason,{'font-size':11,fill:'#526777','pointer-events':'none'});
          }
        });
      });
    }
    let footer=height-133;
    for(const text of ['Handy Satria · Official agencies and OECD. Latest GVA and R&D years selected independently; same-year currency inputs.',
      'BERD is assigned business R&D, not total national R&D. Basque: companies + PNPI; Singapore RIE: S&T only.',
      history?'Changes require complete endpoints with matching source and scope. Source flags remain in the inspector and CSV.':'GVA shares: A–T total. BERD shares: reported industry R&D total, including any unallocated activities.',
       (data.groups.length===6?'Six sectors cover A–T.':'Group 16 = R–T.')+' Partial sums are hatched. Hover, focus or tap a bar for its source expression and flags.'])footer+=lines(20,footer,text,width-40,11,'#526777')+4;
    return {svg,changes};
  }
  return {render};
})();
