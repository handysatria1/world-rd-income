"use strict";
const data=JSON.parse(document.getElementById("sector-data").textContent),el=id=>document.getElementById(id),ns="http://www.w3.org/2000/svg";
const countries=new Map(data.countries.map(c=>[c.iso,c]));let selected=data.defaults.slice(),current=[],csvRows=[];
const titles={employment:"Employment by broad sector",comparison:"GVA and employment shares by broad sector",sector:"Gross value added per employed person by sector",economy:"Gross value added per employed person by economy",exports:"Goods exports by manufacturing technology group"};
const fmt=(v,d=0)=>v===null||v===undefined?"Missing":Number(v).toLocaleString("en",{minimumFractionDigits:d,maximumFractionDigits:d});
function node(tag,attrs={},value){const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(value!==undefined)n.textContent=value;return n;}
function text(svg,x,y,value,attrs={}){svg.append(node("text",{x,y,fill:"#172f42","font-family":"Arial, sans-serif","font-size":13,...attrs},value));}
function line(svg,x1,y1,x2,y2,attrs={}){svg.append(node("line",{x1,y1,x2,y2,stroke:"#dce5ea",...attrs}));}
const measure=document.createElement("canvas").getContext("2d");
function name(svg,x,y,value,width=90){const words=value.split(" "),lines=[""];for(const w of words){let i=lines.length-1;if((lines[i]+" "+w).length>Math.floor(width/6)&&lines[i])lines.push(w);else lines[i]=(lines[i]+" "+w).trim();}const fitted=lines.length>2?[lines[0],lines.slice(1).join(" ")]:lines;measure.font="11px Arial";fitted.forEach((s,i)=>text(svg,x,y+15*i,s,{"text-anchor":"middle","font-size":Math.min(11,11*width/Math.max(1,measure.measureText(s).width))}));}
function choose(){el("selection").replaceChildren();selected.forEach((iso,i)=>{const chip=document.createElement("span");chip.className="chip";chip.append(countries.get(iso).display);for(const[label,action,disabled]of[["←",()=>{[selected[i-1],selected[i]]=[selected[i],selected[i-1]];},i===0],["→",()=>{[selected[i+1],selected[i]]=[selected[i],selected[i+1]];},i===selected.length-1],["×",()=>{selected=selected.filter(v=>v!==iso);},false]]){const b=document.createElement("button");b.textContent=label;b.disabled=disabled;b.setAttribute("aria-label",(label==="×"?"Remove ":label==="←"?"Move left ":"Move right ")+countries.get(iso).display);b.onclick=()=>{action();choose();render();};chip.append(b);}el("selection").append(chip);});choices();}
function choices(){el("choices").replaceChildren();const q=el("search").value.trim().toLowerCase();for(const c of [...data.countries].sort((a,b)=>a.name.localeCompare(b.name))){if(!(c.name+" "+c.display+" "+c.iso).toLowerCase().includes(q))continue;const label=document.createElement("label"),box=document.createElement("input");box.type="checkbox";box.checked=selected.includes(c.iso);box.disabled=!box.checked&&selected.length>=16;box.onchange=()=>{selected=box.checked?[...selected,c.iso]:selected.filter(v=>v!==c.iso);choose();render();};label.append(box,c.name+(c.region?" (region)":""));el("choices").append(label);}}
function axis(svg,x,y,w,h,max){for(let i=0;i<=4;i++){const v=max*i/4,py=y+h-h*i/4;line(svg,x,py,x+w,py);text(svg,x-8,py+4,fmt(v,max<10?1:0),{"text-anchor":"end","font-size":10});}}
function bar(svg,x,y,w,h,color,tip){const n=node("rect",{x,y,width:w,height:Math.max(0,h),fill:color});n.append(node("title",{},tip));svg.append(n);}
function render(){
  const kind=el("kind").value,mode=el("year").value,unit=el("unit").value,digits=Number(el("decimals").value),panels=["sector","economy"].includes(kind),groups=kind==="exports"?data.exportGroups:data.groups;
  el("unit").disabled=panels||kind==="comparison";current=SectorEconomy.select(data,selected,mode,kind,unit);
  const width=panels?Math.max(1380,kind==="sector"?selected.length*180+240:1380):Math.max(1150,selected.length*(kind==="comparison"?185:130)+330);
  const rows=kind==="economy"?Math.max(1,Math.ceil(selected.length/3)):2,height=panels?155+rows*320+110:700;
  const svg=node("svg",{xmlns:ns,width,height,viewBox:`0 0 ${width} ${height}`,role:"img","aria-labelledby":"chart-title chart-desc"});svg.append(node("title",{id:"chart-title"},el("title-input").value),node("desc",{id:"chart-desc"},"Sector comparisons with actual years, sources and complete values in the accompanying table."),node("rect",{width,height,fill:"white"}));
  text(svg,24,33,el("title-input").value,{"font-size":Math.min(22,(width-48)/Math.max(1,el("title-input").value.length)*1.7),"font-weight":700});
  const years=mode==="latest"?"Latest complete year per economy":mode==="common"?"Latest common complete year":"Reporting year: "+mode;
  const units=panels?"current US$ thousand per employed person":kind==="comparison"?"share of six-sector total (%)":unit==="share"?"share of total (%)":kind==="employment"?"million employed persons":"current US$ billion";
  text(svg,24,59,years+" · "+units+(panels?" · individual panel scales":""),{fill:"#526777"});
  if(panels){
    const count=kind==="sector"?6:selected.length,pw=(width-40)/3,ph=320;
    for(let p=0;p<count;p++){
      const x=22+(p%3)*pw,y=105+Math.floor(p/3)*ph,left=x+47,top=y+25,w=pw-70,h=185;
      const values=kind==="sector"?current.map(r=>r.row?.amounts[p]??null):current[p]?.row?.amounts??Array(6).fill(null);
      const median=kind==="sector"?SectorEconomy.median(values):current[p]?.row?.total??null;
      const max=Math.max(1,...values.filter(v=>v!==null),median??0)*1.22;axis(svg,left,top,w,h,max);
      text(svg,x+pw/2,y,kind==="sector"?groups[p].label:countries.get(current[p].iso).display+" · "+(current[p].year??"—"),{"text-anchor":"middle","font-size":14,"font-weight":700});
      const slot=w/Math.max(1,values.length);
      values.forEach((v,i)=>{const center=left+slot*(i+.5);if(v!==null){const bh=v/max*h;bar(svg,center-slot*.32,top+h-bh,slot*.64,bh,kind==="sector"?groups[p].color:groups[i].color,fmt(v,2)+" thousand USD/person");text(svg,center,top+h-bh-5,fmt(v,digits),{"text-anchor":"middle","font-size":11});}else text(svg,center,top+h/2,"—",{"text-anchor":"middle"});name(svg,center,top+h+18,kind==="sector"?countries.get(current[i].iso).display:groups[i].id,slot-3);if(kind==="sector")text(svg,center,top+h+52,current[i].year??"—",{"text-anchor":"middle","font-size":10});});
      if(median!==null){const my=top+h-median/max*h;line(svg,left,my,left+w,my,{stroke:"#b54831","stroke-dasharray":"6 4","stroke-width":2});text(svg,left,top+h+78,(kind==="sector"?"Selected-economy median: ":"Economy total GVA/person: ")+fmt(median,1),{fill:"#a13a24","font-size":11});}
    }
  }else{
    const left=65,top=145,h=365,w=width-365,share=kind==="comparison"||unit==="share",divisor=kind==="employment"?1e6:1e9;
    const max=share?100:Math.max(1,...current.filter(r=>r.row).map(r=>r.row.total/divisor))*1.12;axis(svg,left,top,w,h,max);
    const slot=w/Math.max(1,current.length);
    current.forEach((item,i)=>{const center=left+slot*(i+.5),r=item.row,sets=kind==="comparison"?2:1;
      if(r){for(let k=0;k<sets;k++){
        const bw=slot*(sets===2?.35:.72),bx=sets===2?center+(k===0?-bw-3:3):center-bw/2,bc=bx+bw/2;
        const values=kind==="comparison"?(k===0?r.gvaShares:r.employmentShares):share?r.shares:r.amounts.map(v=>v/divisor);
        const perc=kind==="comparison"?values:r.shares;let bottom=top+h;
        values.forEach((v,j)=>{const bh=v/max*h;bottom-=bh;bar(svg,bx,bottom,bw,bh,groups[j].color,`${countries.get(item.iso).name} · ${item.year} · ${groups[j].label}: ${fmt(perc[j],2)}%`);if(bh>=13)text(svg,bc,bottom+bh/2+4,fmt(perc[j],digits)+"%",{"text-anchor":"middle","font-size":bh<19?10:12,fill:"white"});});
        const total=kind==="comparison"?(k===0?(r.totalGVA===null?"FX missing":"$"+fmt(r.totalGVA/1e9)+"bn"):fmt(r.totalPersons/1e6,2)+"m"):kind==="employment"?fmt(r.total/1e6,2)+" million":r.total===null?r.currency+" "+fmt(r.totalLocal/1e9,1)+"bn":"US$ "+fmt(r.total/1e9,1)+"bn";
        if(sets===2){text(svg,bc,top-31,total.replace(/bn$|m$/,""),{"text-anchor":"middle","font-size":12});text(svg,bc,top-15,k===0?"billion USD":"million persons",{"text-anchor":"middle","font-size":10});text(svg,bc,top+h+17,k===0?"GVA":"Employment",{"text-anchor":"middle","font-size":10});}else text(svg,bc,top-17,total,{"text-anchor":"middle","font-size":12});
      }}else text(svg,center,top+h/2,"No complete data",{"text-anchor":"middle","font-size":11});
      name(svg,center,top+h+42,countries.get(item.iso).display,slot-8);text(svg,center,top+h+80,(item.year??"—")+(item.iso==="ES-PV"&&item.year===2025&&kind==="exports"?" (p)":""),{"text-anchor":"middle","font-size":11});
    });
    [...groups].reverse().forEach((g,i)=>{const x=left+w+22,y=top+20+i*52;bar(svg,x,y-11,13,13,g.color,g.label);const words=g.label.split(" ");if(g.label.length>27){text(svg,x+21,y,words.slice(0,-1).join(" "));text(svg,x+21,y+17,words.at(-1));}else text(svg,x+21,y,g.label);});
  }
  if(kind==="economy")data.groups.forEach((g,i)=>text(svg,24+(i%3)*(width-48)/3,height-113+Math.floor(i/3)*17,g.id+": "+g.label,{"font-size":11}));
  text(svg,24,height-72,"Handy Satria · Sources: OECD TiM 2025 / TiVA 2025 / BTiGE; Eustat; WDI exchange rates.",{"font-size":12,fill:"#526777"});
  text(svg,24,height-50,panels?"Nominal GVA/person, not PPP or hourly productivity. "+(kind==="sector"?"Sector medians: unweighted selected available economies.":"Dashed line: economy total GVA divided by total persons."):kind==="exports"?"Goods exports; custom manufacturing groups. Other/unallocated = reported goods total minus both groups.":"Six-sector denominator: sections A–T; persons rather than FTEs. Totals above stacks. Regional Basque data from Eustat.",{"font-size":12,fill:"#526777"});
  text(svg,24,height-28,kind==="exports"?"C33 services outside BTiGE goods scope; Eustat native groups reclassified. (p) Provisional.":"Actual observation years shown. Missing values are not zero. Different latest years are not a common-year comparison.",{"font-size":11,fill:"#526777"});
  el("chart").replaceChildren(svg);
  const good=current.filter(r=>r.row),missing=current.filter(r=>!r.row),observed=[...new Set(good.map(r=>r.year))].sort();
  el("status").textContent=`${good.length} of ${selected.length} economies have complete data. `+(observed.length?"Year(s): "+observed.join(", ")+". ":"")+(observed.length>1?"Different reporting years are shown. ":"");
  el("missing").hidden=!missing.length;el("missing").textContent=missing.map(r=>countries.get(r.iso).display+": "+r.reason).join("; ");for(const id of["svg","png","csv","print"])el(id).disabled=!good.length;
  table(kind,groups);
}
function table(kind,groups){
  const columns=["Economy","Year","Sector",...(kind==="comparison"?["GVA share %","Employment share %"]:kind==="employment"?["Persons","Employment share %"]:kind==="exports"?["Exports US$ billion","Goods share %"]:["GVA/person US$ thousand","GVA US$ billion","Persons"]),"Source / status"];
  const head=document.createElement("tr");for(const label of columns){const th=document.createElement("th");th.textContent=label;head.append(th);}el("table-head").replaceChildren(head);el("table-body").replaceChildren();
  csvRows=[["iso3","economy","year","group","group_label","chart_kind","value","value_unit","share_percent","gva_share_percent","employment_share_percent","gva_usd","persons","total","total_unit","sector_median_usd_thousand","source","obs_status","coverage","note","value_status","build_utc","year_selection"]];
  const medians=data.groups.map((_,i)=>SectorEconomy.median(current.map(r=>r.row?.amounts[i]??null)));
  for(const item of current)groups.forEach((g,i)=>{const r=item.row,prod=["sector","economy"].includes(kind),v=r?.amounts?.[i]??null,values=[countries.get(item.iso).name,item.year??"—",g.label,...(kind==="comparison"?[fmt(r?.gvaShares[i],2),fmt(r?.employmentShares[i],2)]:kind==="employment"?[fmt(v),fmt(r?.shares[i],2)]:kind==="exports"?[fmt(v===null?null:v/1e9,3),fmt(r?.shares[i],2)]:[fmt(v,2),fmt(r?.gvaUSD[i]===null||!r?null:r.gvaUSD[i]/1e9,3),fmt(r?.persons[i])]),r?r.source:item.reason];const tr=document.createElement("tr");for(const value of values){const td=document.createElement("td");td.textContent=value;tr.append(td);}el("table-body").append(tr);
    csvRows.push([item.iso,countries.get(item.iso).name,item.year??"",g.id,g.label,kind,v??"",kind==="employment"?"persons":kind==="exports"?"USD":"USD thousand/person",r?.shares?.[i]??"",r?.gvaShares?.[i]??"",r?.employmentShares?.[i]??"",r?.gvaUSD?.[i]??"",kind==="employment"?v??"":r?.persons?.[i]??"",r?.total??"",kind==="employment"?"persons":kind==="exports"?"USD":"USD thousand/person",prod?medians[i]??"":"",r?.source??"",r?.flags??"",r?"available":item.reason,r?.note??"","derived; source cells in full workbook",data.builtUTC,el("year").value]);});
  el("table-note").textContent="Full-precision plotted values are available in CSV; source cells, units, flags and calculation inputs are in the Excel workbook.";
}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function svgText(){return new XMLSerializer().serializeToString(el("chart").querySelector("svg"));}
const filename=()=>"sector-"+el("kind").value+"-"+el("year").value;
el("svg").onclick=()=>save(new Blob([svgText()],{type:"image/svg+xml;charset=utf-8"}),filename()+".svg");
el("png").onclick=async()=>{el("download-status").textContent="Preparing PNG…";const url=URL.createObjectURL(new Blob([svgText()],{type:"image/svg+xml;charset=utf-8"}));try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement("canvas");canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext("2d").drawImage(image,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png"));if(!blob)throw new Error("PNG encoding failed");save(blob,filename()+".png");el("download-status").textContent="PNG ready.";}catch(e){el("download-status").textContent="PNG export failed: "+e.message;}finally{URL.revokeObjectURL(url);}};
el("csv").onclick=()=>{const q=v=>'"'+String(v).replaceAll('"','""')+'"';save(new Blob(["\ufeff"+csvRows.map(row=>row.map(q).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"}),filename()+".csv");};
el("print").onclick=()=>window.print();el("clear").onclick=()=>{selected=[];choose();render();};el("reset").onclick=()=>{selected=data.defaults.slice();el("year").value=el("kind").value==="exports"?"2024":"2022";choose();render();};el("search").addEventListener("input",choices);
for(let y=2025;y>=2000;y--){const o=document.createElement("option");o.value=y;o.textContent=y;el("year").append(o);}el("year").value="2022";
el("kind").addEventListener("change",()=>{el("title-input").value=titles[el("kind").value];el("year").value=el("kind").value==="exports"?"2024":"2022";render();});
for(const id of["year","unit","decimals"])el(id).addEventListener("change",render);el("title-input").addEventListener("input",render);choose();render();
