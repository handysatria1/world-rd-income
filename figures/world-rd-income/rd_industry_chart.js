"use strict";
const data=JSON.parse(document.getElementById("rd-industry-data").textContent),el=id=>document.getElementById(id),ns="http://www.w3.org/2000/svg";
const countries=new Map(data.countries.map(c=>[c.iso,c]));let selected=data.defaults.slice(),current=[],csvRows=[],nativeCsvRows=[];
const titles={composition:"Industry R&D by broad sector",comparison:"GVA and business R&D · sector shares",intensity:"Business R&D as a share of sector GVA",perWorker:"Business R&D per employed person",productivity:"Sector R&D intensity and labour productivity",trade:"Manufacturing R&D and goods-export shares"};
const fmt=(v,d=1)=>v===null||v===undefined?"Missing":Number(v).toLocaleString("en",{minimumFractionDigits:d,maximumFractionDigits:d});
const short=s=>s.replaceAll("_"," "),bn=v=>v==null?null:v/1e9;
function node(tag,attrs={},value){const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(value!==undefined)n.textContent=value;return n;}
function text(svg,x,y,value,attrs={}){svg.append(node("text",{x,y,fill:"#172f42","font-family":"Arial, sans-serif","font-size":13,...attrs},value));}
function line(svg,x1,y1,x2,y2,attrs={}){svg.append(node("line",{x1,y1,x2,y2,stroke:"#dce5ea",...attrs}));}
function bar(svg,x,y,w,h,color,tip,partial=false,coverage=null){if(!Number.isFinite(h))return;const n=node("rect",{x,y,width:w,height:Math.max(0,h),fill:color});n.append(node("title",{},tip));svg.append(n);if(coverage)RDCoverage.bind(n,...coverage);if(partial)svg.append(node("rect",{x,y,width:w,height:Math.max(0,h),fill:"url(#partial)","pointer-events":"none"}));}
function name(svg,x,y,value,width=110){const words=value.split(" "),lines=[""];for(const w of words){let i=lines.length-1;if((lines[i]+" "+w).length>Math.floor(width/6)&&lines[i])lines.push(w);else lines[i]=(lines[i]+" "+w).trim();}lines.forEach((s,i)=>text(svg,x,y+14*i,s,{"text-anchor":"middle","font-size":11}));}
function choose(){el("selection").replaceChildren();selected.forEach((iso,i)=>{const chip=document.createElement("span");chip.className="chip";chip.append(countries.get(iso).display);for(const[label,action,disabled]of[["←",()=>{[selected[i-1],selected[i]]=[selected[i],selected[i-1]];},i===0],["→",()=>{[selected[i+1],selected[i]]=[selected[i],selected[i+1]];},i===selected.length-1],["×",()=>{selected=selected.filter(v=>v!==iso);},false]]){const b=document.createElement("button");b.textContent=label;b.disabled=disabled;b.setAttribute("aria-label",(label==="×"?"Remove ":label==="←"?"Move left ":"Move right ")+countries.get(iso).display);b.onclick=()=>{action();choose();render();};chip.append(b);}el("selection").append(chip);});choices();}
function choices(){el("choices").replaceChildren();const q=el("search").value.trim().toLowerCase();for(const c of [...data.countries].sort((a,b)=>a.name.localeCompare(b.name))){if(!(c.name+" "+c.display+" "+c.iso).toLowerCase().includes(q))continue;const label=document.createElement("label"),box=document.createElement("input");box.type="checkbox";box.checked=selected.includes(c.iso);box.disabled=!box.checked&&selected.length>=16;box.onchange=()=>{selected=box.checked?[...selected,c.iso]:selected.filter(v=>v!==c.iso);choose();render();};label.append(box,c.name+(c.region?" (region)":""));el("choices").append(label);}}
function axis(svg,x,y,w,h,max){for(let i=0;i<=4;i++){const v=max*i/4,py=y+h-h*i/4;line(svg,x,py,x+w,py);text(svg,x-9,py+4,fmt(v,max<10?1:0),{"text-anchor":"end","font-size":11});}}
function legend(svg,x,y){[...data.groups,{id:"UNALLOC",label:"Unallocated / reconciliation",color:"#cbd2d9"}].forEach((g,i)=>{bar(svg,x,y+i*40,14,14,g.color,g.label);text(svg,x+22,y+12+i*40,g.id+" · "+g.label,{"font-size":11});});bar(svg,x,y+292,25,16,"#526777","Partial group",true);text(svg,x+34,y+305,"Hatching: partial sector coverage",{"font-size":11});}
function render(){
  el('coverage-tooltip').hidden=true;el('coverage-inspector').hidden=true;
  const kind=el("kind").value,mode=el("year").value,unit=el("unit").value,digits=Number(el("decimals").value),group=Number(el("group").value),panels=["intensity","perWorker","trade"].includes(kind);
  const horizontal=kind==='comparison'&&el('comparison-layout').value==='horizontal';
  el('comparison-layout-label').hidden=kind!=='comparison';el('unit').closest('label').hidden=kind!=='composition';el('group').closest('label').hidden=kind!=='productivity';el('chart').classList.toggle('horizontal',horizontal);
  el("unit").disabled=kind!=="composition";el("group").disabled=kind!=="productivity";
  current=RDIndustry.select(data,selected,mode,horizontal?'pairedShares':kind,unit,group);
  const width=horizontal?1250:Math.max(1450,selected.length*(kind==="comparison"?210:kind==="trade"?160:130)+420),height=horizontal?Math.max(580,current.length*106+350):panels?(kind==="trade"?650:880):740;
  const svg=node("svg",{xmlns:ns,width,height,viewBox:`0 0 ${width} ${height}`,role:"img","aria-labelledby":"chart-title chart-desc"});svg.append(node("title",{id:"chart-title"},el("title-input").value),node("desc",{id:"chart-desc"},"Reported-year industry R&D comparisons. Hatched segments are partial groups; grey is unallocated. Missing values and unavailable ratios are not zero."),node("rect",{width,height,fill:"white"}));
  const defs=node("defs"),pattern=node("pattern",{id:"partial",width:8,height:8,patternUnits:"userSpaceOnUse"});pattern.append(node("path",{d:"M-2,2 L2,-2 M0,8 L8,0 M6,10 L10,6",stroke:"white","stroke-opacity":.55,"stroke-width":2}));defs.append(pattern);svg.append(defs);
  text(svg,24,34,el("title-input").value,{"font-size":22,"font-weight":700});
  const units=horizontal?'GVA: % of A–T total · BERD: % of reported industry R&D total':kind==="intensity"?"BERD / whole-sector GVA (%) · complete groups only":kind==="perWorker"?"current US$ per whole-sector employed person · complete groups only":kind==="productivity"?data.groups[group].label+" · complete R&D group only":kind==="trade"?"R&D share of reported BERD versus export share of all goods (%)":kind==="comparison"?"R&D / GVA / employment: each uses its own total denominator (%)":unit==="share"?"share of reported industry R&D total (%)":"current US$ billion";
  text(svg,24,60,(mode==="latest"?"Latest usable years":mode==="common"?"Latest common usable year":"Reporting year: "+mode)+" · "+units,{fill:"#526777"});
  if(horizontal){
    const left=235,top=115,w=970;
    for(let k=0;k<=4;k++){const x=left+w*k/4;line(svg,x,top-15,x,top+current.length*106-10);text(svg,x,top-26,k*25+'%',{'text-anchor':'middle','font-size':12});}
    current.forEach((a,i)=>{
      const y=top+i*106,r=a.row;name(svg,83,y+20,countries.get(a.iso).display,150);text(svg,83,y+61,a.year??'No usable year',{'text-anchor':'middle','font-size':11});
      for(const [j,key,label]of [[0,'gvaShares','GVA'],[1,'shares','BERD']]){
        const by=y+j*35,good=j===0?r?.gvaShares.every(RDIndustry.finite):r?.stackAvailable;
        text(svg,left-14,by+20,label,{'text-anchor':'end','font-size':12});
        if(!good){text(svg,left+10,by+20,'— Missing '+label+' for this year',{'font-size':12,fill:'#526777'});continue;}
        const values=j===0?r[key]:[...r.shares,r.remainingShare];let x=left;
        values.forEach((v,k)=>{if(!RDIndustry.finite(v)||v<0)return;const bw=v/100*w,g=data.groups[k],partial=j===1&&k<6&&!r.complete[k],tip=(g?.label??'Unallocated / reconciliation')+': '+fmt(v,3)+'%';
          bar(svg,x,by,bw,27,g?.color??'#cbd2d9',tip,partial,j===1&&k<6?[r,k]:null);
          if(bw>45)text(svg,x+bw/2,by+18,fmt(v,digits)+'%',{'text-anchor':'middle','font-size':11,fill:k===6?'#172f42':'white'});x+=bw;
        });
      }
    });
    const legendY=top+current.length*106+20;
    [...data.groups,{id:'UNALLOC',label:'Unallocated / reconciliation',color:'#cbd2d9'}].forEach((g,i)=>{const x=24+i%3*410,y=legendY+Math.floor(i/3)*25;bar(svg,x,y,14,14,g.color,g.label);text(svg,x+22,y+12,g.id+' · '+g.label,{'font-size':11});});
    bar(svg,434,legendY+50,20,14,'#526777','Partial coverage',true);text(svg,462,legendY+62,'Hatched = partial activity coverage',{'font-size':11});
  }else if(panels){
    const trade=kind==="trade",count=trade?2:6,columns=trade?2:3,pw=(width-40)/columns,ph=330;
    for(let p=0;p<count;p++){
      const x=24+(p%columns)*pw,y=105+Math.floor(p/columns)*ph,left=x+60,top=y+25,w=pw-85,h=190;
      text(svg,x+pw/2,y,data.groups[p].label,{"text-anchor":"middle","font-size":14,"font-weight":700});
      const values=current.flatMap(a=>trade?[a.row?.stackAvailable?a.row.shares[p]:null,a.row?.exportShares[p]??null]:[a.row?.[kind][p]??null]);
      const max=trade?100:Math.max(1,...values.filter(RDIndustry.finite))*1.2;axis(svg,left,top,w,h,max);const slot=w/Math.max(1,current.length);
      current.forEach((a,i)=>{const center=left+slot*(i+.5),vs=trade?[a.row?.stackAvailable?a.row.shares[p]:null,a.row?.exportShares[p]??null]:[a.row?.[kind][p]??null];
        vs.forEach((v,j)=>{const bw=slot*(trade?.32:.65),bx=center+(trade?(j===0?-bw-2:2):-bw/2),partial=trade&&j===0&&!a.row?.complete[p];if(v!=null){const bh=v/max*h;bar(svg,bx,top+h-bh,bw,bh,j===1?"#97734d":data.groups[p].color,fmt(v,3)+(partial?" · partial R&D group":""),partial,j===0&&a.row?[a.row,p]:null);text(svg,bx+bw/2,top+h-bh-5,fmt(v,digits)+(partial?"*":""),{"text-anchor":"middle","font-size":10});}else text(svg,bx+bw/2,top+h/2,"—",{"text-anchor":"middle"});});
        name(svg,center,top+h+18,countries.get(a.iso).display,slot-5);text(svg,center,top+h+61,a.year??"—",{"text-anchor":"middle","font-size":10});});
    }
    if(kind==="trade")text(svg,24,height-140,"Paired bars: sector colour = assigned R&D; brown = goods exports. * / hatching = partial R&D group. Missing R&D does not hide available exports.",{"font-size":12});
  }else if(kind==="productivity"){
    const left=100,top=115,w=width-240,h=420,points=current.filter(a=>a.available),xmax=Math.max(1,...points.map(a=>a.row.intensity[group]))*1.25,ymax=Math.max(1,...points.map(a=>a.row.productivity[group]))*1.25;
    axis(svg,left,top,w,h,ymax);for(let i=0;i<=4;i++){const x=left+w*i/4;line(svg,x,top,x,top+h);text(svg,x,top+h+22,fmt(xmax*i/4),{"text-anchor":"middle"});}
    points.forEach(a=>{const x=left+a.row.intensity[group]/xmax*w,y=top+h-a.row.productivity[group]/ymax*h,c=node("circle",{cx:x,cy:y,r:7,fill:data.groups[group].color});c.append(node("title",{},countries.get(a.iso).name+": "+fmt(a.row.intensity[group],3)+"% R&D/GVA; "+fmt(a.row.productivity[group],3)+" thousand USD/person"));svg.append(c);text(svg,x+12,y-10,countries.get(a.iso).display+" · "+a.year,{"font-size":12});});
    text(svg,left+w/2,top+h+50,"Business R&D / sector GVA (%)",{"text-anchor":"middle"});text(svg,left,top-18,"GVA per employed person · current US$ thousand",{"font-size":12});text(svg,24,height-125,"Descriptive comparison. R&D intensity and productivity share GVA in their formulas; this plot does not establish a causal relationship.",{"font-size":12});
  }else{
    const compare=kind==="comparison",share=compare||unit==="share",left=65,top=145,h=360,w=width-420,slot=w/Math.max(1,current.length);
    const max=share?100:Math.max(1,...current.filter(a=>a.available).map(a=>a.row.totalUSD/1e9))*1.15;axis(svg,left,top,w,h,max);
    current.forEach((a,i)=>{const r=a.row,center=left+slot*(i+.5),sets=compare?3:1,bw=slot*(compare?.25:.68);
      for(let k=0;k<sets;k++){
        const bx=compare?center+(k-1.5)*(bw+4)+2:center-bw/2,good=k===0?r?.stackAvailable&&(share||r.totalUSD!==null):r?.[k===1?"gvaShares":"employmentShares"].every(RDIndustry.finite);
        if(good){const values=k===0?[...(share?r.shares:r.assigned.map(bn)),share?r.remainingShare:bn(r.remainingUSD)]:r[k===1?"gvaShares":"employmentShares"];let bottom=top+h;
          values.forEach((v,j)=>{if(v===null)return;const bh=v/max*h;bottom-=bh;const g=data.groups[j],partial=k===0&&j<6&&!r.complete[j];bar(svg,bx,bottom,bw,bh,g?.color??"#cbd2d9",(g?.label??"Unallocated / reconciliation")+": "+fmt(v,3)+(partial?" · partial group":""),partial,k===0&&j<6?[r,j]:null);if(bh>17)text(svg,bx+bw/2,bottom+bh/2+4,fmt(v,digits)+(share?"%":""),{"text-anchor":"middle","font-size":11,fill:j===6?"#172f42":"white"});});
        }else text(svg,bx+bw/2,top+h/2,"—",{"text-anchor":"middle"});
        if(compare)text(svg,bx+bw/2,top+h+18,["R&D","GVA","Jobs"][k],{"text-anchor":"middle","font-size":10});
      }
      if(!compare&&r?.totalLocal!=null)text(svg,center,top-15,r.totalUSD==null?r.currency+" "+fmt(r.totalLocal/1e9)+"bn":"US$ "+fmt(r.totalUSD/1e9)+"bn",{"text-anchor":"middle","font-size":12});
      name(svg,center,top+h+43,countries.get(a.iso).display,slot-7);text(svg,center,top+h+83,a.year??"—",{"text-anchor":"middle","font-size":11});if(a.iso==="ES-PV")text(svg,center,top+h+99,"companies + PNPI",{"text-anchor":"middle","font-size":10});
    });legend(svg,left+w+22,top);
  }
  text(svg,24,height-77,"Handy Satria · Sources: OECD RDS BERD / TiVA / TiM / BTiGE; A*STAR RIE; Eustat; World Bank WDI.",{"font-size":12,fill:"#526777"});
  text(svg,24,height-53,"Basque: companies + PNPI. Singapore RIE: S&T R&D only. Native branch allocations are partial, with mixed branches unallocated.",{"font-size":12,fill:"#526777"});
  text(svg,24,height-29,kind==="trade"?"MHT: C20,21,26–30. LMT: C10–19,22–25,31–33; goods exports exclude C33. Different denominators; no export/R&D ratio.":"Unallocated is not Other production. Missing is not zero. Complete-group ratios use exact economy/year/group joins.",{"font-size":12,fill:"#526777"});
  el("chart").replaceChildren(svg);
  const good=current.filter(a=>a.available),years=[...new Set(current.filter(a=>a.row).map(a=>a.year))].sort();
  el("status").textContent=`${good.length} of ${selected.length} economies meet this chart’s R&D data requirements. `+(years.length?"Selected year(s): "+years.join(", ")+". ":"")+(years.length>1?"Different reporting years are shown. ":"")+"Partial groups are never used as full-group ratios.";
  const notes=current.filter(a=>!a.available||a.row?.classifiedShare<99.999).map(a=>countries.get(a.iso).display+": "+(!a.available?short(a.reason)+"; required R&D data unavailable":fmt(a.row.classifiedShare)+"% assigned; "+short(a.row.status)));
  el("missing").hidden=!notes.length;el("missing").textContent=notes.join("; ");const drawable=horizontal?current.some(a=>a.row?.stackAvailable||a.row?.gvaShares.every(RDIndustry.finite)):good.length;for(const id of["svg","png","print"])el(id).disabled=!drawable;el("csv").disabled=!current.some(a=>a.row);table();nativeTable();
}
function nativeTable(){
  el("native-body").replaceChildren();
  nativeCsvRows=[["iso3","economy","year","activity_code","activity_label","amount_local","currency","partial_group","aggregation_eligible","mapping_note","source","source_file","source_locator","source_flags","build_utc"]];
  for(const a of current)for(const r of a.row?.nativeRows??[]){
    appendRow(el("native-body"),[countries.get(a.iso).name,a.year,r.label,fmt(r.amountLocal==null?null:r.amountLocal/1e6,3),r.currency,r.eligible?r.group+" (partial)":"Unallocated / parent / total",r.note+(r.flags?" Flags: "+r.flags:""),data.sources[r.source]+" · "+r.sourceFile+" · "+r.locator]);
    nativeCsvRows.push([a.iso,countries.get(a.iso).name,a.year,r.code,r.label,r.amountLocal,r.currency,r.group,r.eligible,r.note,r.source,r.sourceFile,r.locator,r.flags,data.builtUTC]);
  }
  el("native-section").hidden=nativeCsvRows.length===1;el("native-csv").disabled=nativeCsvRows.length===1;
}
function appendRow(target,values){const tr=document.createElement("tr");for(const value of values){const td=document.createElement("td");td.textContent=value;tr.append(td);}target.append(tr);}
function table(){
  const columns=["Economy","Year","Group","Assigned R&D · US$ bn","Group coverage","R&D share %","GVA · US$ bn","Employed persons","GVA/person · US$ thousand","R&D/GVA %","R&D/worker · US$","Goods exports · US$ bn","Source / status"];
  const head=document.createElement("tr");for(const label of columns){const th=document.createElement("th");th.textContent=label;head.append(th);}el("table-head").replaceChildren(head);el("table-body").replaceChildren();el("context-body").replaceChildren();
  csvRows=[["iso3","economy","year","group","assigned_rd_usd","assigned_rd_local","currency","group_coverage","assigned_rd_share_percent","gva_usd","gva_share_percent","employed_persons","employment_share_percent","gva_per_person_usd_thousand","rd_percent_sector_gva","rd_usd_per_sector_worker","goods_exports_usd","goods_exports_share_percent","reported_industry_rd_usd","unallocated_rd_usd","industry_rd_scope","industry_rd_source","coverage_status","rd_flags","rd_total_flags","gva_source","gva_flags","employment_source","employment_flags","exports_source","exports_flags","gerd_oecd_usd","gerd_wdi_usd","gerd_eustat_usd","gdp_per_capita_current_usd","build_utc","year_selection","source_table"]];
  for(const a of current){const r=a.row;data.groups.forEach((g,i)=>{
    appendRow(el("table-body"),[countries.get(a.iso).name,a.year??"—",g.id,fmt(bn(r?.assigned[i]),3),r?.groupCoverage[i]??"unavailable",fmt(r?.shares[i],2),fmt(bn(r?.gvaUSD[i]),3),fmt(r?.persons[i],0),fmt(r?.productivity[i],2),fmt(r?.intensity[i],2),fmt(r?.perWorker[i],0),fmt(bn(r?.exportUSD[i]),3),data.sources[r?.source]??short(a.reason)]);
    const e=r?.economicSources??{},c=r?.context??{};
    csvRows.push([a.iso,countries.get(a.iso).name,a.year??"",g.id,r?.assigned[i],r?.assignedLocal[i],r?.currency,r?.groupCoverage[i],r?.shares[i],r?.gvaUSD[i],r?.gvaShares[i],r?.persons[i],r?.employmentShares[i],r?.productivity[i],r?.intensity[i],r?.perWorker[i],r?.exportUSD[i],r?.exportShares[i],r?.totalUSD,r?.remainingUSD,r?.scope,r?.source,r?.status,r?.flags,r?.totalFlags,e.gva_source,e.gva_flags,e.employment_source,e.employment_flags,e.exports_source,e.exports_flags,c.gerd_oecd_usd,c.gerd_wdi_usd,c.gerd_eustat_usd,c.gdp_per_capita_current_usd,data.builtUTC,el("year").value,"rd_economy_joined.csv; match iso3/year/group"]);
  });const c=r?.context??{};appendRow(el("context-body"),[countries.get(a.iso).name,a.year??"—",fmt(bn(r?.totalUSD),3),(r?.scope??"—")+" / "+fmt(r?.classifiedShare)+"%",...["oecd","wdi","eustat"].map(s=>fmt(bn(c["gerd_"+s+"_usd"]),3)+" / "+fmt(c["rd_percent_gdp_"+s],2)),fmt(c.gdp_per_capita_current_usd,0)]);}
}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function svgText(){return new XMLSerializer().serializeToString(el("chart").querySelector("svg"));}
const filename=()=>"rd-industry-"+el("kind").value+"-"+el("year").value;
el("svg").onclick=()=>save(new Blob([svgText()],{type:"image/svg+xml;charset=utf-8"}),filename()+".svg");
el("png").onclick=async()=>{el("download-status").textContent="Preparing PNG…";const url=URL.createObjectURL(new Blob([svgText()],{type:"image/svg+xml;charset=utf-8"}));try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement("canvas");canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext("2d").drawImage(image,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png"));if(!blob)throw new Error("PNG encoding failed");save(blob,filename()+".png");el("download-status").textContent="PNG ready.";}catch(e){el("download-status").textContent="PNG export failed: "+e.message;}finally{URL.revokeObjectURL(url);}};
function saveCsv(rows,name){const q=v=>'"'+String(v??"").replaceAll('"','""')+'"';save(new Blob(["\ufeff"+rows.map(row=>row.map(q).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"}),name);}
el("csv").onclick=()=>saveCsv(csvRows,filename()+".csv");el("native-csv").onclick=()=>saveCsv(nativeCsvRows,"rd-industry-native-"+el("year").value+".csv");
el("print").onclick=()=>window.print();el("clear").onclick=()=>{selected=[];choose();render();};el("reset").onclick=()=>{selected=data.defaults.slice();el("year").value=String(data.defaultYear);choose();render();};el("search").addEventListener("input",choices);
for(let y=2025;y>=2000;y--){const o=document.createElement("option");o.value=y;o.textContent=y;el("year").append(o);}el("year").value=String(data.defaultYear);
data.groups.forEach((g,i)=>{const o=document.createElement("option");o.value=i;o.textContent=g.label;el("group").append(o);});
el("coverage-note").textContent="Singapore: RIE 2023 adds partial MHT, LMT, KIS and LIS values. RIE totals fill 2014–2022; those years have no industry split. Original OECD detail is retained through 2013. Use 2023 to see the workbook’s industry values.";
el('comparison-layout').addEventListener('change',()=>{titles.comparison=el('comparison-layout').value==='horizontal'?'GVA and business R&D · sector shares':'R&D, GVA and employment shares';el('title-input').value=titles.comparison;render();});
el("kind").addEventListener("change",()=>{el("title-input").value=titles[el("kind").value];render();});for(const id of["year","unit","group","decimals"])el(id).addEventListener("change",render);el("title-input").addEventListener("input",render);choose();render();
el('coverage-close').onclick=()=>el('coverage-inspector').hidden=true;
if(typeof dashboardBridge!=='undefined')dashboardBridge.register({set({ids,year,kind,names}){selected=ids;for(const iso of ids)if(!countries.has(iso))countries.set(iso,{iso,name:names[iso],display:names[iso]});if(el('kind').value!==kind){el('kind').value=kind;el('title-input').value=titles[kind];}el('year').value=year;choose();render();},get rows(){return current;}});
