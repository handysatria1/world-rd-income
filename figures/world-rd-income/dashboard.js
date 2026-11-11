'use strict';
window.Dashboard=(()=>{
  const $=id=>document.getElementById(id),defaults=['KOR','SGP','CHN','ES-PV','USA','GBR'];
  const views=[
    ['snapshot','snapshot','R&D expenditure and income','national','snapshot'],['compare','snapshot','Compare two years','national','compare'],['history','snapshot','Trends by economy','national','history'],
    ['researchers','income','Researchers by economy',null,'researchers'],['patents','income','Patent applications by economy',null,'patents'],['publications','income','Journal articles by economy',null,'publications'],
    ['income','income','R&D and innovation by income group',null,null],
    ['breakdown','national','R&D funding and performance','national','breakdown'],['sector','national','R&D by sector and field','national','sector'],
    ['research','rd','Value added and business R&D','research','comparison'],
    ...[['comparison','Sector shares: GVA, R&D and employment'],['composition','Business R&D by sector'],['intensity','Business R&D (% of sector GVA)'],['perWorker','Business R&D per worker'],['productivity','R&D intensity and productivity'],['trade','Manufacturing R&D and exports']].map(([k,t])=>['rd-'+k,'rd',t,'rd',k]),
    ['gva','economy','Gross value added by sector','gva','gva'],
    ...[['employment','Employment by sector'],['comparison','GVA and employment shares'],['sector','Productivity by sector'],['economy','Productivity by economy'],['exports','Goods exports by sector']].map(([k,t])=>['economy-'+k,'economy',t,'economy',k]),
    ['detail','data','Industry data tables','detail','detail'],['sources','data','Definitions and sources','sources','sources']
  ];
  const files={national:'view-national.html',rd:'view-rd.html',gva:'view-gva.html',economy:'view-economy.html',research:'view-research.html',detail:'view-detail.html',sources:'view-sources.html'};
  let data=null,ids=[...defaults],frames=new Map(),request=0;
  const names=()=>Object.fromEntries(data.countries.map(c=>[c.iso,c.name]));
  const group=iso=>IncomeCore.classify(data,iso,$('income-vintage').value,$('combine-middle').checked);
  function matches(iso){const f=$('income-filter').value,c=IncomeCore.classify(data,iso,$('income-vintage').value,false).code;return f==='all'||f===c||(f==='MIC'&&['UMC','LMC'].includes(c));}
  function selection(){
    const combine=$('combine-middle').checked,filter=$('income-filter').value;
    const groups=filter==='all'?null:filter==='MIC'?(combine?['MIC']:['UMC','LMC']):combine&&['UMC','LMC'].includes(filter)?['MIC']:[filter];
    const single=views.find(v=>v[0]===$('view').value),allAllowed=['snapshot','compare','income'].includes(single[0]);
    return {ids:(allAllowed&&$('sample-scope').value==='all'?data.countries.map(c=>c.iso):ids).filter(matches),
      scope:allAllowed?$('sample-scope').value:'selected',vintage:$('income-vintage').value,combine,groups,names:names(),year:$('shared-year').value,kind:single[4],income:data};
  }
  function choices(){
    const query=$('economy-search').value.toLowerCase();$('economy-choices').replaceChildren();
    for(const c of data.countries){if(!matches(c.iso)||!(c.name+' '+c.iso).toLowerCase().includes(query))continue;
      const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.checked=ids.includes(c.iso);check.disabled=!check.checked&&ids.length>=16;
      check.onchange=()=>{ids=check.checked?[...ids,c.iso]:ids.filter(id=>id!==c.iso);chips();update();};const income=group(c.iso);
      label.append(check,`${income.symbol} ${c.name} (${c.iso})`);label.title=income.label+' · '+income.vintage;$('economy-choices').append(label);
    }
  }
  function chips(){
    const map=names();$('selected-economies').replaceChildren();
    ids.forEach((iso,i)=>{const chip=document.createElement('span');chip.className='chip';const c=group(iso);chip.append(c.symbol+' '+map[iso]);chip.title=c.label+' · '+c.vintage+(matches(iso)?'':' · excluded by income filter');if(!matches(iso))chip.style.opacity='.5';
      for(const [symbol,label,action,disabled]of[['←','Move left',()=>{[ids[i-1],ids[i]]=[ids[i],ids[i-1]];},i===0],['→','Move right',()=>{[ids[i+1],ids[i]]=[ids[i],ids[i+1]];},i===ids.length-1],['×','Remove',()=>{ids=ids.filter(id=>id!==iso);},false]]){const b=document.createElement('button');b.textContent=symbol;b.disabled=disabled;b.setAttribute('aria-label',label+' '+map[iso]);b.onclick=()=>{action();chips();update();};chip.append(b);}$('selected-economies').append(chip);
    });$('selection-count').textContent=`· ${ids.length} selected`;
    const codes=$('combine-middle').checked?['HIC','MIC','LIC','UNK']:['HIC','UMC','LMC','LIC','UNK'];$('income-legend').textContent=codes.map(c=>IncomeCore.symbols[c]+' '+IncomeCore.labels[c]).join('   ·   ');
    $('classification-note').textContent=$('income-vintage').value==='current'?`${data.currentVintage} · July 2026–June 2027; based on 2025 Atlas-method GNI/person. Low ≤$1,175; lower-middle $1,176–4,635; upper-middle $4,636–14,375; high >$14,375. These are income groups; “advanced” and “emerging” are different classifications.`:`Fixed ${$('income-vintage').value} classification from the official historical workbook, applied to all displayed years. It is not a classification calculated from the chart’s GDP/person.`;
    choices();
  }
  function frame(key){
    if(frames.has(key))return frames.get(key);
    const iframe=document.createElement('iframe');iframe.title=key==='rd'?'Industry R&D charts':key==='research'?'Comparisons by industry group':key+' data explorer';iframe.hidden=true;
    const promise=new Promise((resolve,reject)=>{iframe.onload=()=>resolve(iframe);iframe.onerror=()=>reject(new Error('Could not load '+files[key]));});
    iframe.src=files[key];$('view-host').append(iframe);const entry={iframe,promise};frames.set(key,entry);return entry;
  }
  async function update(){
    if(!data)return;const token=++request,view=views.find(v=>v[0]===$('view').value),[id,section,,key]=view;
    $('dashboard-error').hidden=true;$('loading').hidden=true;for(const {iframe}of frames.values())iframe.hidden=true;
    const innovation=['researchers','patents','publications'].includes(id);
    $('income-panel').hidden=id!=='income';$('innovation-panel').hidden=!innovation;document.querySelectorAll('[data-section]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.section===section));
    const global=['snapshot','compare','income'].includes(id),hasYear=innovation||['snapshot','sector','research','gva','detail'].includes(id)||id.startsWith('rd-')||id.startsWith('economy-');
    $('scope-label').hidden=!global;$('shared-year-label').hidden=!hasYear;$('economy-settings').hidden=id==='sources';
    $('classification-control').hidden=!['rd','economy'].includes(section);$('industry-classification').value=id==='research'?'research':'six';
    $('year-help').textContent=innovation?'Compare selected economies. Latest available uses each economy’s latest observation; latest common year requires data for every selected economy. Choose an exact year for a fixed-year comparison.':id==='income'?'Select two years below to compare income groups.':id==='sources'?'Data providers, methods and downloads.':hasYear?'Latest available uses the most recent year with the data required for this chart. Reporting years are shown; a selected year uses only that year.':'Select the time period below. Economy selections apply across views.';
    history.replaceState(null,'','#'+id);
    try{
      const state=selection();
      if(id==='income'){IncomeChart.render(data,state);return;}
      if(innovation){InnovationChart.render(data,state);return;}
      const entry=frame(key);$('loading').hidden=false;const iframe=await entry.promise;
      if(token!==request)return;
      iframe.hidden=false;
      if(iframe.contentWindow.dashboardAPI)await iframe.contentWindow.dashboardAPI.set(state);
      else if(key!=='sources')throw new Error('The selected view did not initialize. Please reload.');
      if(token!==request)return;
      const error=iframe.contentDocument.getElementById('error');if(error&&!error.hidden)throw new Error(error.textContent);
    }catch(error){if(token===request){$('dashboard-error').textContent=error.message;$('dashboard-error').hidden=false;}}finally{if(token===request)$('loading').hidden=true;}
  }
  function navigate(id){if(!views.some(v=>v[0]===id))id='snapshot';$('view').value=id;update();}
  async function initialize(){
    try{const response=await fetch('income_explorer.json');if(!response.ok)throw new Error('Income dataset unavailable ('+response.status+').');data=await response.json();
      const sections={snapshot:'Income & R&D',income:'Innovation',national:'National R&D',rd:'Industry R&D',economy:'Economy & trade',data:'Data & sources'};
      for(const [key,label]of Object.entries(sections)){const g=document.createElement('optgroup');g.label=label;for(const v of views.filter(v=>v[1]===key))g.append(new Option(v[2],v[0]));$('view').append(g);}
      for(let year=2025;year>=2000;year--)$('shared-year').add(new Option(year,year));
      $('income-vintage').add(new Option('Current · '+data.currentVintage,'current'));for(const fy of data.historicalVintages)$('income-vintage').add(new Option(fy+' · fixed membership',fy));
      IncomeChart.initialize(data);InnovationChart.initialize();chips();
      for(const id of ['view','shared-year','sample-scope'])$(id).addEventListener('change',update);
      $('industry-classification').onchange=()=>navigate($('industry-classification').value==='research'?'research':'rd-comparison');
      for(const id of ['income-vintage','income-filter','combine-middle'])$(id).addEventListener('change',()=>{chips();update();});
      for(const id of ['income-year-a','income-year-b','income-stat','income-sample','patent-mode','innovation-patent-mode'])$(id).addEventListener('change',update);
      $('economy-search').oninput=choices;$('example-economies').onclick=()=>{ids=[...defaults];chips();update();};$('clear-economies').onclick=()=>{ids=[];chips();update();};
      $('use-selection').onclick=()=>{$('sample-scope').value='selected';update();};
      document.querySelectorAll('[data-section]').forEach(b=>b.onclick=()=>navigate(views.find(v=>v[1]===b.dataset.section)[0]));
      window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));navigate(location.hash.slice(1)||'snapshot');
    }catch(error){$('dashboard-error').textContent=error.message;$('dashboard-error').hidden=false;}
  }
  initialize();return {navigate,update,get data(){return data;},get selection(){return selection();},get frames(){return frames;}};
})();
