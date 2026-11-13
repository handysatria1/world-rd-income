/* Visible, linked source notes for dashboard figures, tables and figure exports. */
(function(root){
  'use strict';
  const NS='http://www.w3.org/2000/svg';
  const source=(label,url)=>({label,url});
  const providers={
    wdi:source('World Bank WDI','https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators'),
    msti:source('OECD MSTI (GERD)','https://www.oecd.org/en/data/datasets/main-science-and-technology-indicators.html'),
    rds:source('OECD RDS (R&D statistics)','https://www.oecd.org/en/data/datasets/research-and-development-statistics.html'),
    uis:source('UNESCO UIS (R&D)','https://databrowser.uis.unesco.org/resources/bulk'),
    eustat:source('Eustat (Basque Country)','https://en.eustat.eus/estadisticas/tema_312/opt_1/tipo_1/temas.html'),
    ons:source('UK ONS','https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/researchanddevelopmentexpenditure'),
    tiva:source('OECD TiVA 2025 (value added)','https://www.oecd.org/en/topics/sub-issues/trade-in-value-added.html'),
    tim:source('OECD TiM 2025 (employment)','https://www.oecd.org/en/topics/sub-issues/trade-in-employment.html'),
    btige:source('OECD BTiGE (goods exports)','https://www.oecd.org/en/data/datasets/bilateral-trade-in-goods-by-industry-and-end-use-category.html'),
    rie:source('A*STAR National RIE Survey (Singapore R&D)','https://www.a-star.edu.sg/news/national-survey-of-rie'),
    stan:source('OECD STAN 2025','https://www.oecd.org/en/data/datasets/structural-analysis-database.html'),
    na:source('OECD annual national accounts, Table 6','https://data-explorer.oecd.org/'),
    unido:source('UNIDO INDSTAT Rev.4','https://stat.unido.org/data/table?dataset=indstat&revision=4'),
    nbs:source('China NBS, 2023 input–output table','CHINA_GVA.md'),
    groups:source('World Bank income classifications','https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups'),
    wgi:source('World Bank Worldwide Governance Indicators','https://www.worldbank.org/en/publication/worldwide-governance-indicators')
  };
  const indicatorCodes={rd:'GB.XPD.RSDV.GD.ZS',researchers:'SP.POP.SCIE.RD.P6',patents:'IP.PAT.RESD',patentsNonresident:'IP.PAT.NRES',publications:'IP.JRN.ARTC.SC',internetUsers:'IT.NET.USER.ZS',humanCapitalIndex:'HD.HCI.OVRL',bachelorAttainment:'SE.TER.CUAT.BA.ZS',population:'SP.POP.TOTL'};
  const origins={rd:'UNESCO UIS',researchers:'UNESCO UIS',patents:'WIPO',patentsNonresident:'WIPO',publications:'NSF',internetUsers:'ITU',bachelorAttainment:'UNESCO UIS'};
  function indicator(key){
    if(key.startsWith('governmentEffectiveness'))return providers.wgi;
    const code=indicatorCodes[key];
    return code?source(`World Bank WDI${origins[key]?' / '+origins[key]:''} (${code})`,'https://data.worldbank.org/indicator/'+code):providers.wdi;
  }
  function unique(items){return items.filter((item,i)=>item&&items.findIndex(other=>other?.label===item.label&&other?.url===item.url)===i);}
  function sourceTokens(rows){
    const values=[];
    for(const row of rows||[]){
      for(const key of ['source','gva_source','berd_source','employment_source','exports_source'])if(row?.[key])values.push(row[key]);
      if(row?.economicSources)values.push(...Object.values(row.economicSources));
      if(row?.row)values.push(...sourceTokens([row.row]));
      if(row?.rows)values.push(...sourceTokens(row.rows));
    }
    return values;
  }
  function industrySources(tokens){
    return unique(tokens.flatMap(value=>{
      const s=String(value).toUpperCase(),found=[];
      if(/TIVA/.test(s))found.push(providers.tiva);
      if(/\bTIM\b|OECD_TIM/.test(s))found.push(providers.tim);
      if(/BTIGE/.test(s))found.push(providers.btige);
      if(/OECD_RDS|OECD RDS/.test(s))found.push(providers.rds);
      if(/STAN/.test(s))found.push(providers.stan);
      if(/OECD_NA/.test(s))found.push(providers.na);
      if(/EUSTAT/.test(s))found.push(providers.eustat);
      if(/(^|[^A-Z])ONS(_|[^A-Z]|$)/.test(s))found.push(providers.ons);
      if(/SGP_RIE|A\*STAR|RIE_SURVEY/.test(s))found.push(providers.rie);
      return found;
    }));
  }
  function describe(c){
    let items=[],note="Author’s calculations. Observation years and coverage are shown in the figure/table; missing values are not filled.";
    const kind=c.kind||'snapshot',target=c.target||'',rows=c.rows||[],basque=c.ids?.includes('ES-PV');
    if(c.page==='dashboard'){
      if(target==='innovation-regional-table')return {items:[source('Eustat European Innovation Scoreboard 2025','https://en.eustat.eus/estadisticas/tema_20/opt_1/tipo_1/temas.html')],note:'Published regional indicators; definitions and observation years differ from the country series above.'};
      const metrics=kind==='income'?['rd','researchers','patents','publications']:[c.metric||kind];
      items=metrics.map(indicator);
      if(kind==='income'&&c.patents==='nonresident')items=metrics.map(key=>indicator(key==='patents'?'patentsNonresident':key));
      if(kind==='income'&&c.patents==='total')items.push(indicator('patentsNonresident'));
      if(kind==='patents'&&c.patents==='nonresident')items=[indicator('patentsNonresident')];
      if(kind==='patents'&&c.patents==='total')items.push(indicator('patentsNonresident'));
      if(c.population)items.push(indicator('population'));
      if(basque&&kind==='researchers')items.push(source('Eustat (researchers and population)','https://en.eustat.eus/elementos/tbl0010998_i.html'));
      items.push(providers.groups);
      note=(kind==='capacity'?'Author’s calculations: country means of available annual observations, then equally weighted country means within each income group. ':kind==='income'?'Author’s calculations: selected group statistic from observed country values, not official World Bank aggregates. ':'Author’s calculations where totals, rates or component sums are derived. ')+
        (c.period?'Period: '+c.period+'. ':'')+(c.vintage?'Income classification: '+c.vintage+'. ':'')+'Exact observation years only; missing values are not filled.';
    }else if(c.page==='national'){
      if(['snapshot','compare','history'].includes(kind)){
        const codes=unique(rows.flatMap(r=>[r.end?.rd?.source,r.start?.rd?.source,r.source]).filter(Boolean).map(code=>source(code,code))).map(s=>s.label);
        if(!codes.length&&c.nationalSource)codes.push(c.nationalSource);
        if(c.table)codes.push(...(c.alternativeSources||[]));
        const rd=codes.map(code=>({oecd:providers.msti,wdi:source('World Bank WDI / UNESCO UIS (GERD)','https://data.worldbank.org/indicator/GB.XPD.RSDV.GD.ZS'),uis:providers.uis,eustat:providers.eustat,ons:providers.ons})[code]).filter(Boolean);
        const title=c.title||'';
        if(kind!=='history'||!/Annual R&D expenditure/.test(title))items.push(source('World Bank WDI (GDP and conversion inputs)','https://data.worldbank.org/indicator/'+(c.ppp?'NY.GDP.PCAP.PP.CD':'NY.GDP.PCAP.CD')));
        if(kind!=='history'||!/GDP per capita/.test(title)||c.table)items.push(...rd);
        if(basque||codes.includes('eustat'))items.push(providers.eustat);
        if(kind!=='history')items.push(providers.groups);
        if(c.table&&c.snapshotIndicators)items.push(indicator('humanCapitalIndex'),indicator('researchers'),indicator('bachelorAttainment'),source('World Bank WDI / UNIDO CIP (manufactured-export technology share)','https://data.worldbank.org/indicator/TX.MNF.TECH.ZS.UN'),...industrySources(sourceTokens(c.indicatorRows||[])));
        note='Author’s calculations: reported-year R&D averages and fitted statistics; currency totals, where shown, use same-year inputs. '+(c.period||'Reporting years are shown in the chart/table.')+' No missing years are substituted.';
      }else{
        items=[providers.rds];
        if(basque)items.push(providers.eustat);
        if(kind==='breakdown'&&c.ids?.includes('GBR'))items.push(providers.ons);
        items.push(source('World Bank WDI (currency / PPP inputs)','https://data.worldbank.org/indicator/PA.NUS.FCRF'));
        note='Author’s calculations: category sums, period averages, shares and same-year currency conversions where applicable. '+(c.period||'Reporting years are shown.')+' Source flags and missing categories are retained.';
      }
    }else if(c.page==='detail'){
      if(target==='export-rows')items=[source('World Bank WDI / UNIDO CIP (TX.MNF.TECH.ZS.UN)','https://data.worldbank.org/indicator/TX.MNF.TECH.ZS.UN')];
      else if(target==='nbs-rows')items=[providers.nbs];
      else items=[({OECD_NA:providers.na,OECD_STAN:providers.stan,UNIDO_INDSTAT:providers.unido,OECD_TIVA_CHN:providers.tiva})[c.detailSource]||providers.na];
      note=target==='nbs-rows'?'Published native product sectors and Excel cells; not relabelled as ISIC divisions.':target==='export-rows'?'Published share of manufactured exports; exact reporting years shown.':'Author’s scaling to unit amounts. Provider USD values are retained; source-specific coverage and valuation apply.';
    }else if(c.page==='sources'){
      items=[source('Archived provider requests, source files and checksums','source_inventory.csv')];note='Source documentation compiled by Handy Satria; follow the linked provider and methodology references.';
    }else if(target==='research-classification'){
      items=[source('Industry classification and correspondence compiled by Handy Satria','RESEARCH_GROUPS.md')];note='Analytical grouping of ISIC Rev.4 activities; not a new official statistical classification.';
    }else if(target==='official-table'){
      items=c.officialSources||[];note='Published source-native industries. Author’s same-year currency conversions where USD amounts are shown; unresolved mappings are not assigned to comparison groups.';
    }else{
      items=industrySources(sourceTokens(rows));
      // With no observations, name the view’s documented inputs rather than imply a zero.
      if(!items.length)items=c.page==='gva'?[providers.tiva]:c.page==='economy'?[kind==='exports'?providers.btige:providers.tim]:[providers.rds,providers.tiva];
      if(c.currency)items.push(source('World Bank WDI (same-year exchange rates)','https://data.worldbank.org/indicator/PA.NUS.FCRF'));
      note='Author’s calculations: industry regrouping, shares and derived ratios where shown. Actual source years, flags and partial coverage are retained; no missing observations are imputed.';
    }
    if(!items.length)items=[source('Dataset methods and source-cell references','sources.html')];
    return {items:unique(items),note};
  }
  function parts(spec){return [{text:'Source: ',bold:true},...spec.items.flatMap((s,i)=>[{text:s.label,url:s.url},{text:i===spec.items.length-1?'. ':'; '}]),{text:spec.note}];}
  function wrapParts(input,width,measure=text=>text.length*7){
    const lines=[[]];let used=0;
    for(const part of input)for(const word of part.text.match(/\S+\s*|\s+/g)||[]){
      const size=measure(word);
      if(used+size>width&&lines.at(-1).length){lines.push([]);used=0;}
      const text=used===0?word.trimStart():word;if(!text)continue;
      lines.at(-1).push({...part,text});used+=measure(text);
    }
    return lines;
  }
  const figures=new WeakMap(),tables=new Map();let observer,main;
  function context(element){
    const $=id=>document.getElementById(id),value=id=>$(id)?.value;
    const filename=location.pathname.split('/').pop(),pages={'view-national.html':'national','view-rd.html':'rd','view-gva.html':'gva','view-economy.html':'economy','view-research.html':'research','view-research-six.html':'research','view-detail.html':'detail','view-sources.html':'sources'};
    const state=root.dashboardSourceState||(root.Dashboard?.data?root.Dashboard.selection:{});
    const api=root.dashboardAPI,c={page:pages[filename]||'dashboard',kind:state.kind,ids:state.ids,table:element.tagName.toLowerCase()==='table',target:element.id||element.querySelector('tbody')?.id,
      title:element.previousElementSibling?.textContent||element.getAttribute('aria-label')||'',rows:api?.rows?.rows||api?.rows||[],ppp:value('metric')==='ppp',vintage:state.vintage==='current'?state.income?.currentVintage:state.vintage};
    if(!Array.isArray(c.rows))c.rows=[];
    if(c.page==='dashboard'){
      c.kind=element.closest('#capacity-panel')?'capacity':element.closest('#income-panel')?'income':state.kind;
      c.metric=c.kind==='capacity'?value('capacity-metric'):c.kind;
      c.patents=value(c.kind==='income'?'patent-mode':'innovation-patent-mode');c.population=!['income','capacity'].includes(c.kind)&&(value('innovation-scale')==='perMillion'||c.kind==='researchers');
      if(c.kind==='capacity'){
        const mode=value('capacity-period'),data=root.Dashboard?.data;
        c.period=!mode?'2000–2025 (fixed reference)':mode==='single'?value('capacity-year'):mode==='last5'?`${Math.max(2000,(data?.lastYear||2025)-4)}–${data?.lastYear||2025}`:`${value('capacity-from')}–${value('capacity-to')}`;
        c.vintage=value('capacity-vintage')==='current'?data?.currentVintage:value('capacity-vintage');
      }else c.period=c.kind==='income'?`${value('income-year-a')} and ${value('income-year-b')}`:state.year==='latest'?'latest available (actual years shown)':state.year==='common'?'latest common year (shown)':state.year;
    }else if(c.page==='national'){
      const result=root.RDExplorer?.result;c.kind=root.RDExplorer?.view||state.kind;c.nationalSource=result?.source;
      c.alternativeSources=Object.entries(result?.country?.rd||{}).filter(([,values])=>Object.keys(values).length).map(([key])=>key);
      c.snapshotIndicators=root.RDExplorer?.data?.snapshotIndicators;
      if(c.snapshotIndicators)c.indicatorRows=c.snapshotIndicators.rows.filter(row=>(state.ids||[]).includes(row.iso3));
      if(c.kind==='history')c.period=`Years: ${value('fromYear')}–${value('toYear')}.`;
      else if(c.kind==='snapshot'||c.kind==='compare'){
        const endpoints=(result?.rows||[]).flatMap(r=>[r.start,r.end].filter(Boolean));
        const years=[...new Set(endpoints.map(e=>e.gdpYear))].sort((a,b)=>a-b);
        const windows=[...new Set(endpoints.map(e=>e.rd.start===e.rd.end?String(e.rd.start):`${e.rd.start}–${e.rd.end}`))];
        c.period=years.length?`GDP observation years: ${years.length>3?years[0]+'–'+years.at(-1)+' (vary by economy)':years.join(', ')}; R&D periods: ${windows.length>3?'vary by economy (see table)':windows.join(', ')}.`:'';
      }else c.period=c.kind==='sector'?`Year: ${value('sectorYear')}.`:`R&D period ends ${value('rdEnd')}; window: ${value('rdMode')==='custom'?value('rdStart')+'–'+value('rdEnd'):value('rdMode')+' year(s)'}.`;
    }else if(c.page==='detail')c.detailSource=value('gva-source');
    else{
      c.kind=value('kind')||state.kind;c.currency=c.page!=='economy'||c.kind!=='employment';
      if(c.page==='research'&&element.id!=='research-table'){
        c.rows=api?.rows||[];
        if(element.id==='official-table')c.officialSources=unique([...element.querySelectorAll('tbody a')].map(a=>source(a.textContent,a.href)));
      }
    }
    return c;
  }
  function annotateFigure(svg,spec){
    const signature=JSON.stringify(spec),previous=figures.get(svg);if(previous?.signature===signature)return;
    if(previous){svg.querySelector('[data-source-caption]')?.remove();svg.setAttribute('viewBox',previous.viewBox);if(previous.height!=null)svg.setAttribute('height',previous.height);}
    const viewBox=svg.getAttribute('viewBox'),box=viewBox?.split(/[\s,]+/).map(Number);if(!box||box.length!==4||!box.every(Number.isFinite))return;
    const [x,y,width,height]=box,originalHeight=svg.getAttribute('height');
    const n=(tag,attrs={},text)=>{const node=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))node.setAttribute(k,v);if(text!=null)node.textContent=text;return node;};
    const measure=n('text',{'font-size':13,'font-family':'Arial, sans-serif','font-weight':700,style:'white-space:pre',visibility:'hidden'});svg.append(measure);
    const lines=wrapParts(parts(spec),width-60,text=>{measure.textContent=text;return measure.getComputedTextLength()||text.length*8;});measure.remove();
    const extra=lines.length*19+24,group=n('g',{'data-source-caption':'true','font-family':'Arial, sans-serif','font-size':13,fill:'#263e4e'});
    group.append(n('rect',{x,y:y+height,width,height:extra,fill:'white'}));
    lines.forEach((line,i)=>{const text=n('text',{x:x+24,y:y+height+22+i*19,style:'white-space:pre'});
      for(const part of line){const span=n('tspan',part.bold?{'font-weight':700}:{},part.text);if(part.url){const a=n('a',{href:part.url,target:'_blank',rel:'noopener',fill:'#146b88'});a.append(span);text.append(a);}else text.append(span);}group.append(text);
    });
    svg.append(group);svg.setAttribute('viewBox',`${x} ${y} ${width} ${height+extra}`);
    if(originalHeight!=null&&Number.isFinite(+originalHeight))svg.setAttribute('height',height+extra);
    figures.set(svg,{signature,viewBox,height:originalHeight});
  }
  function annotateTable(table,spec){
    let note=tables.get(table);if(!note){note=document.createElement('p');note.className='source-caption';tables.set(table,note);}
    const signature=JSON.stringify(spec);if(note.dataset.sourceSignature===signature&&note.isConnected)return;
    note.replaceChildren();for(const part of parts(spec)){const n=document.createElement(part.url?'a':part.bold?'strong':'span');n.textContent=part.text;if(part.url){n.href=part.url;n.target='_blank';n.rel='noopener';}note.append(n);}
    note.dataset.sourceSignature=signature;
    const wrapper=table.closest('.scroll,.table-scroll');(wrapper||table).after(note);
  }
  function refresh(){
    if(!main)return;observer?.disconnect();
    try{
      for(const[table,note]of tables)if(!table.isConnected){note.remove();tables.delete(table);}
      for(const svg of main.querySelectorAll('svg.chart, .plot-wrap > svg, #chart > svg'))annotateFigure(svg,describe(context(svg)));
      for(const table of main.querySelectorAll('table'))annotateTable(table,describe(context(table)));
    }finally{observer?.observe(main,{childList:true,subtree:true});}
  }
  function initialize(){
    main=document.querySelector('main');if(!main)return;
    const style=document.createElement('style');style.textContent='.source-caption{font:12px/1.6 Arial,sans-serif;color:#263e4e;text-align:left;margin:10px 0 14px;overflow-wrap:anywhere}.source-caption a{color:#146b88}';document.head.append(style);
    observer=new MutationObserver(records=>{
      // Ignore inspectors and tooltips; only chart/table redraws need a new note.
      if(records.some(r=>r.target.closest?.('svg,table,#chart,#charts,#research-chart,.plot-wrap,#breakdown-panels')||[...r.addedNodes].some(n=>n.nodeType===1&&(n.matches('svg,table')||n.querySelector('svg,table')))))refresh();
    });refresh();
  }
  const api={describe,sourceTokens,industrySources,wrapParts,refresh};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else{root.SourceCaptions=api;document.addEventListener('DOMContentLoaded',initialize);}
})(typeof window!=='undefined'?window:globalThis);
