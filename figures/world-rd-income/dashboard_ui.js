/* Presentation layer only: calculations and source observations stay in their view modules. */
(function(root){
  'use strict';
  const FRAME_EXCLUDES=new Set(['kind','year','gdpYear','sectorYear','search']);
  const MAIN_CONTROLS=['shared-year','sample-scope','income-vintage','income-filter','combine-middle','income-year-a','income-year-b','income-stat','income-sample','patent-mode','innovation-patent-mode','innovation-scale','capacity-metric','capacity-vintage','capacity-combine','capacity-period','capacity-year','capacity-from','capacity-to'];
  const GROUPS={snapshot:'Overview',income:'Country comparisons',rd:'Industry analysis',data:'Data & methods'};
  function readConfig(search){
    try{const raw=new URLSearchParams(search).get('config');if(!raw||raw.length>12000)return null;
      const value=JSON.parse(raw);if(value?.v!==1||!Array.isArray(value.ids)||value.ids.length>16)return null;
      if(!value.ids.every(id=>typeof id==='string'&&/^[A-Z0-9-]{2,8}$/.test(id)))return null;
      return value;
    }catch{return null;}
  }
  function controls(doc,main=false){
    return [...doc.querySelectorAll('select[id],input[id]')].filter(el=>main?MAIN_CONTROLS.includes(el.id):!FRAME_EXCLUDES.has(el.id)&&!el.id.startsWith('official-')&&el.type!=='search'&&el.type!=='button');
  }
  function capture(doc,main=false){return Object.fromEntries(controls(doc,main).map(el=>[el.id,el.type==='checkbox'?el.checked:el.value]));}
  function apply(doc,values,main=false){
    if(!values||typeof values!=='object'||Array.isArray(values))return [];
    const changed=[];
    for(const el of controls(doc,main)){
      if(!Object.hasOwn(values,el.id))continue;const value=values[el.id];
      if(el.type==='checkbox'){if(typeof value==='boolean'&&el.checked!==value){el.checked=value;changed.push(el);}}
      else if(typeof value==='string'&&value.length<=300&&(el.tagName!=='SELECT'||[...el.options].some(o=>o.value===value))&&el.value!==value){el.value=value;changed.push(el);}
    }return changed;
  }
  const api={readConfig,capture,apply};
  if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
  const $=id=>document.getElementById(id);
  let options,pending,initialized=false,presentation=false,refreshQueued=false;
  const docs=new WeakSet();
  const element=(doc,tag,cls,text)=>{const n=doc.createElement(tag);if(cls)n.className=cls;if(text)n.textContent=text;return n;};
  function text(el,value){if(el&&el.textContent!==value)el.textContent=value;}
  function visibleFrame(){return [...document.querySelectorAll('#view-host iframe')].find(f=>!f.hidden);}
  function group(id,section){return id==='snapshot'?'snapshot':['snapshot','income','national'].includes(section)?'income':['rd','economy'].includes(section)?'rd':'data';}
  function addDetails(doc,target,label,cls='ui-advanced'){
    if(!target||target.closest('.'+cls))return;
    const details=element(doc,'details',cls),summary=element(doc,'summary','',label);
    target.before(details);details.append(summary,target);return details;
  }
  function enhance(doc){
    if(!docs.has(doc)){
      docs.add(doc);
      if(doc!==document){const link=doc.createElement('link');link.rel='stylesheet';link.href='dashboard_ui.css';doc.head.append(link);doc.body.classList.add('ui-frame');}
      if(doc!==document){
        const national=doc.querySelector('section.controls[aria-label="Chart controls"]');
        if(national){
          addDetails(doc,national,'Advanced options · income basis, R&D period & chart settings');
          const metric=doc.getElementById('metric');if(metric){const label=metric.parentElement;label.firstChild.textContent='GDP per capita basis';
            const help=element(doc,'p','ui-basis-help','Current-price measures include price changes over time. Constant-2021 PPP adjusts for those price changes. PPP dollars are not market-exchange-rate US dollars.');label.append(help);}
        }
        for(const setting of doc.querySelectorAll('section.settings'))addDetails(doc,setting,'Advanced chart options');
        const research=doc.getElementById('research-layout');if(research)addDetails(doc,research.closest('section'),'Advanced chart options · layout, measure & industry filters');
        const official=doc.getElementById('official-table');if(official)addDetails(doc,official.closest('section'),'Official published industries · source tables','ui-data');
        const inspector=doc.getElementById('inspector');if(inspector)addDetails(doc,inspector,'Selected observation','ui-observation');
        const table=doc.getElementById('single-table');if(table){const wrap=addDetails(doc,table,'View plotted data','ui-data');wrap?.setAttribute('id','ui-plotted-data');}
      }
      for(const el of doc.querySelectorAll('details.methodology > summary'))if(el.textContent==='Definitions and sources')text(el,'Methods & coverage');
      doc.addEventListener('keydown',event=>{if(event.key==='Escape'&&presentation)setPresentation(false);});
      const observer=new MutationObserver(()=>schedule());observer.observe(doc.querySelector('main'),{childList:true,subtree:true});
    }
    doc.body.classList.toggle('ui-presentation',presentation);
    doc.documentElement.style.setProperty('--ui-viewport',innerHeight+'px');
    for(const details of doc.querySelectorAll('details')){
      const summary=details.querySelector(':scope > summary');if(!summary)continue;
      if(details.id!=='ui-plotted-data'&&/^(Data table|View plotted data)/.test(summary.textContent)){
        const count=details.querySelectorAll('table tbody tr').length;
        const unit=doc.getElementById('data-table')&&details.contains(doc.getElementById('data-table'))?'economies':'rows';
        text(summary,`View plotted data · ${count} ${unit}`);
        details.classList.add('ui-data');
      }
    }
    const explorer=doc.defaultView.RDExplorer;
    if(explorer&&!['snapshot','compare'].includes(explorer.view))text(doc.querySelector('#ui-plotted-data > summary'),`View plotted data · ${doc.querySelectorAll('#data-table tbody tr').length} rows`);
    if(doc.getElementById('ui-missing-data'))doc.getElementById('ui-missing-data').hidden=!['snapshot','compare'].includes(explorer?.view);
    if(explorer&&['snapshot','compare'].includes(explorer.view)&&explorer.result){
      const result=explorer.result,rows=result.rows,latest=result.latest;
      const years=[...new Set(rows.map(r=>r.end.gdpYear))].sort((a,b)=>a-b);
      const period=latest?(result.common?'latest common year':'latest available'):explorer.view==='compare'?`${doc.getElementById('fromYear').value}–${doc.getElementById('toYear').value}`:doc.getElementById('gdpYear').value;
      text(doc.getElementById('chart-title'),'R&D intensity and income · '+period);
      const metric=doc.getElementById('metric'),basis=metric.selectedOptions[0]?.textContent;
      const subtitle=doc.getElementById('selection-description');
      if(!subtitle.dataset.uiOriginal||!subtitle.textContent.startsWith('GDP per capita · '))subtitle.dataset.uiOriginal=subtitle.textContent;
      const original=subtitle.dataset.uiOriginal;
      text(subtitle,`GDP per capita · ${basis}. ${latest?(years.length?`Observation years: ${years[0]}${years.length>1?'–'+years.at(-1):''}; actual years shown for each economy.`:'No shared observations for this selection.'):original}`);
      const dataSummary=doc.querySelector('#ui-plotted-data > summary');text(dataSummary,`View plotted data · ${rows.length} economies`);
      let notice=doc.getElementById('ui-missing-data');
      if(!notice){notice=element(doc,'p','ui-notice');notice.id='ui-missing-data';doc.getElementById('coverage-note').before(notice);}
      const excluded=result.audit.filter(r=>!r.end.eligible||r.start&&!r.start.eligible).length;
      notice.hidden=!excluded;
      text(notice,`${excluded} economies are not plotted because required observations are missing${explorer.view==='compare'?' at one or both endpoints':''}. ${metric.value==='pppConstant'?'Constant-2021 PPP has no separate Basque Country observation. ':''}Expand Coverage and exclusions below to see the reasons. Missing data are never replaced with another year or price basis.`);
      for(const stat of doc.querySelectorAll('#stats .stat')){
        if(stat.querySelector('.ui-info'))continue;
        const label=stat.textContent;
        const explanation=/R²/.test(label)?'R² describes the fit of R&D intensity against the logarithm of GDP per capita. It is not evidence of causation.':/Spearman/.test(label)?'Spearman rho measures the rank association between GDP per capita and R&D intensity, from −1 to +1. Association is not causation.':/regression/.test(label)?'Number of economies used in the fitted statistics. Regional comparisons such as Basque Country are excluded to avoid overlap.':/coverage/.test(label)?'Economies with every requested R&D year reported. An incomplete window is not treated as zero.':'Number of economies with the observations required for this chart. Missing values are excluded.';
        const button=element(doc,'button','ui-info','i');button.type='button';button.setAttribute('aria-label','Explain '+label);button.setAttribute('aria-expanded','false');button.title=explanation;
        button.onclick=()=>{let note=doc.getElementById('ui-stat-note');if(!note){note=element(doc,'p','ui-stat-note');note.id='ui-stat-note';note.setAttribute('role','status');doc.getElementById('stats').after(note);}note.hidden=note.textContent===explanation&&!note.hidden;text(note,explanation);for(const info of doc.querySelectorAll('#stats .ui-info'))info.setAttribute('aria-expanded',String(info===button&&!note.hidden));};stat.append(button);
      }
    }
  }
  function schedule(){if(refreshQueued)return;refreshQueued=true;requestAnimationFrame(()=>{refreshQueued=false;refresh();});}
  function refresh(){
    if(!initialized)return;
    enhance(document);
    const frame=visibleFrame();if(frame?.contentDocument?.querySelector('main'))enhance(frame.contentDocument);
    const id=$('view').value,section=options.sectionFor(id),selected=group(id,section);
    for(const b of document.querySelectorAll('nav.tabs [data-section]'))b.setAttribute('aria-pressed',String(b.dataset.section===selected));
    text($('ui-view-label'),$('view').selectedOptions[0]?.textContent||'Explore the data');
    const visible=frame?.contentDocument;
    const metric=visible?.getElementById('metric');
    const year=$('shared-year-label').hidden?'':$('shared-year').selectedOptions[0]?.textContent;
    text($('ui-context'),[year,metric&&!metric.parentElement.hidden?metric.selectedOptions[0]?.textContent:''].filter(Boolean).join(' · '));
  }
  function setPresentation(value){
    presentation=value;
    document.body.classList.toggle('ui-presentation',value);
    for(const frame of document.querySelectorAll('#view-host iframe'))if(frame.contentDocument?.body){frame.contentDocument.documentElement.style.setProperty('--ui-viewport',innerHeight+'px');frame.contentDocument.body.classList.toggle('ui-presentation',value);}
    text($('ui-present'),value?'Exit presentation':'Presentation mode');$('ui-present').setAttribute('aria-pressed',String(value));
    if(value){window.scrollTo({top:0,behavior:'instant'});$('ui-present').focus();}
  }
  function state(){
    const frame=visibleFrame(),win=frame?.contentWindow,doc=frame?.contentDocument;
    return {v:1,ids:options.getIds(),controls:capture(document,true),frame:doc?{file:new URL(frame.src).pathname.split('/').pop(),kind:win.dashboardSourceState?.kind,controls:capture(doc),sector:doc.querySelector('[data-sector][aria-pressed="true"]')?.dataset.sector}:null};
  }
  async function share(){
    const url=new URL(location.href);url.search='';url.searchParams.set('config',JSON.stringify(state()));
    url.hash=$('view').value;history.replaceState(null,'',url);
    try{await navigator.clipboard.writeText(url.href);$('ui-share-link').hidden=true;text($('ui-share-status'),'Link copied. It includes the selected economies, years, measures and chart settings.');}
    catch{const field=$('ui-share-link');field.hidden=false;field.value=url.href;field.focus();field.select();text($('ui-share-status'),'Copy this link to share the current view.');}
  }
  async function initialize(config){
    if(initialized)return;options=config;pending=readConfig(location.search);initialized=true;
    const nav=document.querySelector('nav.tabs');
    nav.replaceChildren();for(const [key,label] of Object.entries(GROUPS)){const b=element(document,'button','',label);b.type='button';b.dataset.section=key;b.onclick=()=>root.Dashboard.navigate(({snapshot:'snapshot',income:'compare',rd:'research',data:'sources'})[key]);nav.append(b);}
    const toolbar=element(document,'section','ui-toolbar');toolbar.setAttribute('aria-label','Presentation and sharing');
    const heading=element(document,'div','ui-toolbar-heading');const label=element(document,'p','ui-view-label');label.id='ui-view-label';const context=element(document,'p','ui-context');context.id='ui-context';heading.append(label,context);
    const actions=element(document,'div','ui-actions');
    for(const [id,label,action] of [['ui-present','Presentation mode',()=>setPresentation(!presentation)],['ui-share','Share this view',share],['ui-reset','Reset view',()=>{const url=new URL(location.href);url.search='';url.hash='snapshot';history.replaceState(null,'',url);location.reload();}]]){const b=element(document,'button','',label);b.id=id;b.type='button';b.onclick=action;if(id==='ui-present')b.setAttribute('aria-pressed','false');actions.append(b);}
    toolbar.append(heading,actions);$('shared-controls').before(toolbar);
    const status=element(document,'p','ui-share-status');status.id='ui-share-status';status.setAttribute('role','status');const link=element(document,'input','ui-share-link');link.id='ui-share-link';link.readOnly=true;link.hidden=true;link.setAttribute('aria-label','Shareable view link');toolbar.after(status,link);
    if(pending){const valid=new Set(root.Dashboard.data.countries.map(c=>c.iso));options.setIds([...new Set(pending.ids.filter(id=>valid.has(id)))]);apply(document,pending.controls,true);options.chips();}
    window.addEventListener('resize',schedule);
    enhance(document);refresh();
  }
  async function frameUpdated(win){
    if(!initialized||!win.document.querySelector('main'))return;
    const saved=pending?.frame;
    if(saved&&saved.file===win.location.pathname.split('/').pop()&&saved.kind===win.dashboardSourceState?.kind){
      pending.frame=null;
      const changed=apply(win.document,saved.controls);
      if(changed.length)changed.at(-1).dispatchEvent(new win.Event('change',{bubbles:true}));
      if(typeof saved.sector==='string')for(const b of win.document.querySelectorAll('[data-sector]'))if(b.dataset.sector===saved.sector&&b.getAttribute('aria-pressed')!=='true')b.click();
    }
    enhance(win.document);refresh();
  }
  root.DashboardUI={...api,initialize,frameUpdated,refresh,setPresentation,state};
})(typeof window!=='undefined'?window:globalThis);
