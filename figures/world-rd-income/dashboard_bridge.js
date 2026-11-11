/* Same-origin view adapter: shared controls, automatic sizing and in-dashboard links. */
'use strict';
const dashboardBridge={register(api){window.dashboardAPI=api;}};
const dashboardLoads=new Map();
function loadDashboardJSON(url){if(!dashboardLoads.has(url))dashboardLoads.set(url,(async()=>{try{const response=await fetch(url);if(!response.ok)throw new Error('Dataset unavailable: '+url+' ('+response.status+')');return await (url.endsWith('.gz')?new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json():response.json());}catch(error){dashboardLoads.delete(url);throw error;}})());return dashboardLoads.get(url);}
function positionDashboardTooltip(tip,x,y){
  const frame=window.frameElement?.getBoundingClientRect(),top=frame?Math.max(0,-frame.top):0,bottom=frame?Math.min(innerHeight,parent.innerHeight-frame.top):innerHeight;
  tip.style.maxHeight=Math.max(80,bottom-top-24)+'px';tip.style.overflowY='auto';
  tip.style.left=Math.max(8,Math.min(x,innerWidth-tip.offsetWidth-12))+'px';
  tip.style.top=Math.max(top+8,Math.min(y+14,bottom-tip.offsetHeight-12))+'px';
}
document.addEventListener('DOMContentLoaded',()=>{
  const resize=()=>{if(window.frameElement)window.frameElement.style.height=Math.ceil(document.querySelector('main').getBoundingClientRect().height+32)+'px';};
  new ResizeObserver(resize).observe(document.querySelector('main'));resize();
  if(window.frameElement)parent.addEventListener('scroll',()=>{for(const id of ['tooltip','coverage-tooltip']){const tip=document.getElementById(id);if(tip)tip.hidden=true;}},{passive:true});
  const routes={'index.html':'snapshot','rd-industry.html':'rd-composition','sector-economy.html':'economy-employment','broad-sectors.html':'gva','industry.html':'detail','sources.html':'sources'};
  document.addEventListener('click',event=>{const a=event.target.closest('a');if(!a)return;const u=new URL(a.href,location.href),key=u.pathname.split('/').pop();
    if(u.origin===location.origin&&routes[key]&&parent.Dashboard){event.preventDefault();parent.Dashboard.navigate(routes[key]);}
  });
});
