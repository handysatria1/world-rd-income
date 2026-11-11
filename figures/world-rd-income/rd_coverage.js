"use strict";
const RDCoverage=(()=>{
  const catalog=JSON.parse(document.getElementById('rd-coverage-data').textContent);
  const label=c=>c+' · '+(catalog.labels[c]||c);
  function describe(r,i){
    const g=data.groups[i],d=catalog.rows[[r.iso,r.year,g.id].join('/')];
    if(!d)return {title:g.label,lines:['No industry observation in this economy/year.'],detail:null};
    const lines=[d.coverage.toUpperCase()+' sector coverage',
      'Assigned R&D: '+r.currency+' '+fmt(r.assignedLocal[i]==null?null:r.assignedLocal[i]/1e6,3)+' million',
      fmt(r.shares[i],2)+'% of reported total business R&D — NOT percent coverage of this sector.',d.reason,
      'Included: '+(d.included.map(t=>(t.weight<0?'minus ':'')+label(t.code)).join('; ')||'No allocatable public components.'),
      (d.native?'Unallocated native branches (not a known missing-sector list): ':'Not covered: ')+(d.missing.map(t=>label(t.code)+' — '+t.reason+(t.flags?' ['+t.flags+']':'')).join('; ')||'None.'),
      'Scope: '+d.scope+'. Source: '+(data.sources[d.source]||d.source)+'.',
      'Selected source flags: '+(d.flags||'none reported')+'.',
      d.coverage==='complete'?'Whole-group ratios can be calculated when exact same-year denominators exist.':'Whole-group R&D/GVA and R&D per worker are unavailable for this partial group.'];
    return {title:countries.get(r.iso).name+' · '+r.year+' · '+g.id,lines,detail:d};
  }
  function contents(target,info,full=false){
    target.replaceChildren();const title=document.createElement('strong');title.textContent=info.title;target.append(title);
    for(const value of info.lines){const p=document.createElement('p');p.textContent=value;target.append(p);}
    if(full&&info.detail){const h=document.createElement('h3');h.textContent='Selected source expression and locators';target.append(h);
      for(const t of info.detail.included){const p=document.createElement('p');p.textContent=(t.weight<0?'− ': '+ ')+label(t.code)+': '+fmt(t.amountLocal,2)+' local-currency units · '+t.file+' · '+t.locator;target.append(p);}
      for(const t of info.detail.missing.filter(t=>t.file)){const p=document.createElement('p');p.textContent=label(t.code)+' · '+t.file+' · '+t.locator+(t.flags?' · '+t.flags:'');target.append(p);}
    }
  }
  function inspect(r,i){const box=document.getElementById('coverage-inspector');box.hidden=false;contents(document.getElementById('coverage-detail'),describe(r,i),true);}
  function bind(node,r,i){
    const info=describe(r,i),tip=document.getElementById('coverage-tooltip');
    node.dataset.rdIso=r.iso;node.dataset.rdYear=r.year;node.dataset.rdGroup=data.groups[i].id;
    node.setAttribute('tabindex','0');node.setAttribute('role','button');node.setAttribute('aria-label',info.title+' · '+info.lines[0]+'. Activate for coverage details.');
    node.querySelector('title').textContent=[info.title,...info.lines].join('\n');
    const show=e=>{contents(tip,info);tip.hidden=false;const b=node.getBoundingClientRect();if(typeof positionDashboardTooltip==='function')positionDashboardTooltip(tip,e.clientX??b.x,e.clientY??b.y);else{tip.style.left=Math.max(8,Math.min(e.clientX??b.x,window.innerWidth-tip.offsetWidth-12))+'px';tip.style.top=Math.max(8,Math.min((e.clientY??b.y)+16,window.innerHeight-tip.offsetHeight-12))+'px';}};
    node.addEventListener('pointerenter',show);node.addEventListener('focus',show);
    for(const event of ['pointerleave','blur'])node.addEventListener(event,()=>tip.hidden=true);
    node.addEventListener('click',()=>{tip.hidden=true;inspect(r,i);});
    node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();tip.hidden=true;inspect(r,i);}if(e.key==='Escape')tip.hidden=true;});
  }
  return {describe,bind,inspect};
})();
