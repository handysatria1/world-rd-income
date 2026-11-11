"use strict";
const data = JSON.parse(document.getElementById("broad-data").textContent);
const el = id => document.getElementById(id), ns = "http://www.w3.org/2000/svg";
const countries = new Map(data.countries.map(c => [c.iso, c]));
let selected = data.defaults.slice(), current = [];
const format = (v, digits = 0) => v === null || v === undefined ? "Missing" : Number(v).toLocaleString("en", {minimumFractionDigits: digits, maximumFractionDigits: digits});
function node(tag, attrs = {}, text) {const n = document.createElementNS(ns, tag); for (const [k,v] of Object.entries(attrs)) n.setAttribute(k,v); if (text !== undefined) n.textContent = text; return n;}
function text(svg, x, y, value, attrs = {}) {svg.append(node("text", {x,y,fill:"#172f42","font-family":"Arial, sans-serif","font-size":14,...attrs},value));}
const measure = document.createElement("canvas").getContext("2d");
function fittedSize(value, width, size) {measure.font=`${size}px Arial`;return Math.min(size, size*width/Math.max(1,measure.measureText(String(value)).width));}
function nameLines(value, width) {measure.font="12px Arial";const words=value.split(" "),lines=[""];for(const word of words){const i=lines.length-1,next=(lines[i]+" "+word).trim();if(lines[i]&&measure.measureText(next).width>width)lines.push(word);else lines[i]=next;}return lines.length<=2?lines:[lines[0],lines.slice(1).join(" ")];}
function choose() {
  el("selection").replaceChildren();
  selected.forEach((iso,i) => {const chip=document.createElement("span");chip.className="chip";chip.append(countries.get(iso).display);
    for(const [label,action,disabled] of [["←",()=>{[selected[i-1],selected[i]]=[selected[i],selected[i-1]];},i===0],["→",()=>{[selected[i+1],selected[i]]=[selected[i],selected[i+1]];},i===selected.length-1],["×",()=>{selected=selected.filter(c=>c!==iso);},false]]) {const b=document.createElement("button");b.textContent=label;b.disabled=disabled;b.setAttribute("aria-label",(label==="×"?"Remove ":label==="←"?"Move left ":"Move right ")+countries.get(iso).display);b.onclick=()=>{action();choose();render();};chip.append(b);}el("selection").append(chip);});
  choices();
}
function choices() {
  el("choices").replaceChildren();const query=el("search").value.trim().toLowerCase();
  for(const c of [...data.countries].sort((a,b)=>a.name.localeCompare(b.name))) {if(!(c.name+" "+c.display+" "+c.iso).toLowerCase().includes(query))continue;const label=document.createElement("label"),box=document.createElement("input");box.type="checkbox";box.checked=selected.includes(c.iso);box.disabled=!box.checked&&selected.length>=16;box.onchange=()=>{selected=box.checked?[...selected,c.iso]:selected.filter(v=>v!==c.iso);choose();render();};label.append(box,c.name+(c.region?" (region)":""));el("choices").append(label);}
}
function render() {
  const mode=el("year").value, metric=el("metric").value, digits=Number(el("decimals").value);
  current=BroadSector.select(data,selected,mode,metric);
  const share=metric==="share", width=Math.max(1060,selected.length*125+370), height=650, left=65, top=135, plotHeight=350, plotWidth=width-390;
  const svg=node("svg",{xmlns:ns,width,height,viewBox:`0 0 ${width} ${height}`,role:"img","aria-labelledby":"chart-title chart-description"});
  svg.append(node("title",{id:"chart-title"},el("title-input").value),node("desc",{id:"chart-description"},"Stacked gross value added by six sectors. Actual observation years, sources and numerical values are in the accompanying table."),node("rect",{width,height,fill:"white"}));
  text(svg,24,32,el("title-input").value,{"font-size":fittedSize(el("title-input").value,width-48,22)*.95,"font-weight":700});
  const caption=mode==="latest"?"Latest available complete year by economy":mode==="common"?"Latest common complete year" : "Reporting year: "+mode;
  text(svg,24,58,caption+" · "+(share?"shares of grouped GVA":"current US$ billion"),{fill:"#526777"});
  const max=share?100:Math.max(1,...current.filter(r=>r.row).map(r=>r.row.totalUSD/1e9))*1.08;
  for(let i=0;i<=5;i++) {const v=max*i/5,y=top+plotHeight-v/max*plotHeight;svg.append(node("line",{x1:left,y1:y,x2:left+plotWidth,y2:y,stroke:"#dce5ea"}));text(svg,left-9,y+4,format(v,share?0:0)+(share?"%":""),{"text-anchor":"end","font-size":11,fill:"#526777"});}
  current.forEach((item,index)=>{const c=countries.get(item.iso),slot=plotWidth/Math.max(1,current.length),x=left+slot*index+slot*.06,barWidth=slot*.88,center=x+barWidth/2;let bottom=top+plotHeight;
    if(item.row) {const r=item.row;
      text(svg,center,94,r.totalUSD===null?r.currency+" "+format(r.totalLocal/1e9,1):"US$ "+format(r.totalUSD/1e9),{"text-anchor":"middle","font-size":13});text(svg,center,112,r.totalUSD===null?"billion · FX missing":"billion",{"text-anchor":"middle","font-size":12});
      data.groups.forEach((g,j)=>{const value=share?r.shares[j]:r.amounts[j]/1e9,h=value/max*plotHeight;bottom-=h;const rect=node("rect",{x,y:bottom,width:barWidth,height:Math.max(0,h),fill:g.color});rect.append(node("title",{},`${c.name} · ${item.year} · ${g.label}: ${format(r.shares[j],2)}%; US$ ${format(r.amounts[j]===null?null:r.amounts[j]/1e9,3)} billion`));svg.append(rect);if(h>=12&&barWidth>=40)text(svg,center,bottom+h/2+3.5,format(r.shares[j],digits)+"%",{"text-anchor":"middle","font-size":h<17?10:12,fill:j===5?"#212121":"white"});});
    } else text(svg,center,top+plotHeight/2,"No complete data",{"text-anchor":"middle","font-size":12,fill:"#617480"});
    nameLines(c.display,slot-8).forEach((line,i)=>text(svg,center,top+plotHeight+24+i*16,line,{"text-anchor":"middle","font-size":fittedSize(line,slot-8,12)}));text(svg,center,top+plotHeight+62,(item.year??"—")+(item.row?.note?" (p)":""),{"text-anchor":"middle","font-size":12});text(svg,center,top+plotHeight+80,item.iso==="ES-PV"?"Eustat · region":"OECD TiVA",{"text-anchor":"middle","font-size":11,fill:"#526777"});
  });
  [...data.groups].reverse().forEach((g,i)=>{const x=left+plotWidth+26,y=top+22+i*50;svg.append(node("rect",{x,y:y-12,width:13,height:13,fill:g.color}));const words=g.label.split(" ");if(g.label.length>28){text(svg,x+22,y,words.slice(0,-1).join(" "),{"font-size":13});text(svg,x+22,y+17,words.at(-1),{"font-size":13});}else text(svg,x+22,y,g.label,{"font-size":13});});
  text(svg,24,615,"Handy Satria · Sources: OECD TiVA 2025; Eustat A38; WDI exchange rates.",{"font-size":12,fill:"#526777"});
  text(svg,24,635,"User-supplied grouping; GVA at basic prices, excluding net product taxes and section U. (p) Provisional.",{"font-size":11,fill:"#526777"});
  el("chart").replaceChildren(svg);
  const good=current.filter(r=>r.row),missing=current.filter(r=>!r.row),years=[...new Set(good.map(r=>r.year))].sort();
  el("status").textContent=`${good.length} of ${selected.length} selected economies have complete data. `+(years.length?"Year(s): "+years.join(", ")+". ":"")+(years.length>1?"Latest-year bars use different reporting years. ":"")+good.filter(r=>r.row.note).map(r=>countries.get(r.iso).display+": "+r.row.note+".").join(" ");
  el("missing").hidden=missing.length===0;el("missing").textContent=missing.map(r=>countries.get(r.iso).display+": "+r.reason).join("; ");
  for(const id of ["svg","png","csv","print"])el(id).disabled=!good.length;
  const head=document.createElement("tr");for(const label of ["Economy / year / source","Total US$ bn",...data.groups.map(g=>g.label)]){const th=document.createElement("th");th.textContent=label;head.append(th);}el("table-head").replaceChildren(head);el("table-body").replaceChildren();
  for(const item of current){const tr=document.createElement("tr"),values=[countries.get(item.iso).name+" · "+(item.year??"—")+" · "+(item.row?data.sources[item.row.source]:item.reason)+(item.row?.note?" · "+item.row.note:""),item.row?format(item.row.totalUSD===null?null:item.row.totalUSD/1e9,3):"Missing",...data.groups.map((_,i)=>item.row?format(item.row.shares[i],2)+"%":"Missing")];for(const value of values){const td=document.createElement("td");td.textContent=value;tr.append(td);}el("table-body").append(tr);}
}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function svgText(){return new XMLSerializer().serializeToString(el("chart").querySelector("svg"));}
el("svg").onclick=()=>save(new Blob([svgText()],{type:"image/svg+xml;charset=utf-8"}),"gva-broad-sectors.svg");
el("png").onclick=async()=>{el("download-status").textContent="Preparing PNG…";const url=URL.createObjectURL(new Blob([svgText()],{type:"image/svg+xml;charset=utf-8"}));try{const image=new Image();image.src=url;await image.decode();const canvas=document.createElement("canvas");canvas.width=image.width*2;canvas.height=image.height*2;canvas.getContext("2d").drawImage(image,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png"));if(!blob)throw new Error("PNG encoding failed");save(blob,"gva-broad-sectors.png");el("download-status").textContent="PNG ready.";}catch(error){el("download-status").textContent="PNG export failed: "+error.message;}finally{URL.revokeObjectURL(url);}};
el("csv").onclick=()=>{const rows=[["economy_code","economy","year","source","group","group_label","gva_usd","share_percent","grouped_total_usd","coverage","note","grouped_total_source_currency","source_currency","obs_status","valuation","value_status","build_utc","year_selection","chart_measure"]];for(const item of current)for(let i=0;i<data.groups.length;i++)rows.push([item.iso,countries.get(item.iso).name,item.year??"",item.row?.source??"",data.groups[i].id,data.groups[i].label,item.row?.amounts[i]??"",item.row?.shares[i]??"",item.row?.totalUSD??"",item.row?"available":item.reason,item.row?.note??"",item.row?.totalLocal??"",item.row?.currency??"",item.row?.flags??"","current basic prices",item.iso==="ES-PV"?"derived_sum_and_currency_conversion":"derived_sum_of_provider_USD",data.builtUTC,el("year").value,el("metric").value]);const quote=v=>'"'+String(v).replaceAll('"','""')+'"';save(new Blob(["\ufeff"+rows.map(r=>r.map(quote).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"}),"gva-broad-sectors-plotted.csv");};
el("print").onclick=()=>window.print();el("reset").onclick=()=>{selected=data.defaults.slice();choose();render();};el("clear").onclick=()=>{selected=[];choose();render();};el("search").addEventListener("input",choices);
for(let y=2025;y>=2000;y--){const o=document.createElement("option");o.value=y;o.textContent=y;el("year").append(o);}
for(const id of ["year","metric","decimals"])el(id).addEventListener("change",render);el("title-input").addEventListener("input",render);choose();render();
if(typeof dashboardBridge!=='undefined')dashboardBridge.register({set({ids,year,names}){selected=ids;for(const iso of ids)if(!countries.has(iso))countries.set(iso,{iso,name:names[iso],display:names[iso]});el('year').value=year;choose();render();},get rows(){return current;}});
