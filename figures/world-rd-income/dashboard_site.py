"""Assemble the unified, lazy-loaded dashboard from the validated source blocks."""
import json
import gzip
import csv
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def safe(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c')


def build_dashboard(destination):
    files=[]
    def put(name,text):
        (destination/name).write_text(text,encoding='utf-8');files.append(name)
    def copy(name,source=None):
        (destination/name).write_bytes((source or ROOT/name).read_bytes());files.append(name)
    def compressed(name,body):
        (destination/name).write_bytes(gzip.compress(body,mtime=0));files.append(name)
    for name in ['dashboard.css','dashboard.js','income_core.js','income_chart.js','innovation_chart.js','absorptive_capacity_chart.js','dashboard_bridge.js','research_group_core.js','research_compare_chart.js','research_group_chart.js','official_industry_chart.js','INCOME_GROUPS.md','RESEARCH_GROUPS.md','GOVERNMENT_INDUSTRIES.md']:
        copy(name)
    for name in ['income_explorer.json','income_classifications.csv','innovation_annual.csv','basque_innovation_annual.csv','income_validation.json',
                 'absorptive_capacity.json','absorptive_capacity_country.csv','absorptive_capacity_groups.csv',
                 'research_group_classification.csv','research_group_bridge.csv','research_group_coverage.csv','research_groups.xlsx','research_group_validation.json']:
        copy(name,ROOT/'data'/name)
    for name in ['research_group_annual.csv','research_group_joined.csv','research_group_components.csv']:
        compressed(name+'.gz',(ROOT/'data'/name).read_bytes())
    copy('income_source_manifest.json',ROOT/'data/income_raw/manifest.json')
    copy('basque_innovation_source_manifest.json',ROOT/'data/basque_innovation_raw/manifest.json')
    copy('government_industry_source_manifest.json',ROOT/'data/government_industry_raw/manifest.json')
    for name in ['government_industry_explorer.json','government_industry_observations.csv','government_industry_verification.json']:
        copy(name,ROOT/'data'/name)
    data=json.loads((ROOT/'data/explorer_history.json').read_text('utf-8'))
    for key,name in [('sectorField','national-sector.json.gz'),('breakdowns','national-breakdowns.json.gz')]:
        compressed(name,safe(data[key]).encode('utf-8'));data[key]={**data[key],'rows':[]}
    national=(ROOT/'explorer.html').read_text('utf-8').replace('<!-- published-downloads -->','')
    for marker,value in {'__EXPLORER_CSS__':(ROOT/'explorer.css').read_text('utf-8'),'__EXPLORER_DATA__':safe(data),
                          '__EXPLORER_CORE__':(ROOT/'explorer_core.js').read_text('utf-8'),'__BREAKDOWN_CORE__':(ROOT/'breakdown_core.js').read_text('utf-8'),
                          '__EXPLORER_JS__':(ROOT/'explorer.js').read_text('utf-8')}.items():
        assert national.count(marker)==1;national=national.replace(marker,value)
    common='body{background:transparent!important}main{max-width:none!important;padding:0 2px!important}main>nav,main>h1,main>header,main>footer{display:none!important}#chart svg{max-width:100%;height:auto}#chart{overflow:auto}.card{margin-top:12px}a{overflow-wrap:anywhere}.controls label{max-width:100%;min-width:0}#title-input{min-width:0!important;width:320px}'
    sector='.settings>h2,.settings>p,.settings>details,.settings>#selection,.settings>.controls:last-child:not(:first-of-type){display:none!important}.settings label:has(#year),.settings label:has(#kind){display:none!important}'
    national_css='main>header,#citation,#data-sources,.tabs,.country-controls #reset,.country-controls #example,#breakdown-controls fieldset,#gdp-year-control,#sector-year-control{display:none!important}.controls{margin-top:10px}.methodology{margin-top:14px}'
    def frame(document,css=''):
        return document.replace('</head>','<style>'+common+css+'</style><script src="dashboard_bridge.js"></script><script src="income_core.js"></script></head>')
    put('view-national.html',frame(national,national_css))
    detail_partitions=defaultdict(list)
    with (ROOT/'data/gva_isic2.csv').open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        for row in reader:
            for key in ['year','value_reported','unit_multiplier','value_national_currency','value_usd_provider','raw_record']:
                row[key]=float(row[key]) if row[key] else None
            detail_partitions[row['iso3']].append(row)
    for iso,rows in detail_partitions.items():compressed('detail-'+iso+'.json.gz',safe(rows).encode('utf-8'))
    for old,new,css in [('rd-industry.html','view-rd.html',sector),('broad-sectors.html','view-gva.html',sector),('sector-economy.html','view-economy.html',sector),
                        ('industry.html','view-detail.html','main>p:has(a[href="broad-sectors.html"]){display:none}'),('sources.html','view-sources.html','')]:
        document=(destination/old).read_text('utf-8')
        if new=='view-detail.html':document=document.replace('</head>','<script>window.detailPartitions='+safe({iso:'detail-'+iso+'.json.gz' for iso in detail_partitions})+';</script></head>')
        put(new,frame(document,css))
    research=json.loads((ROOT/'data/research_group_explorer.json').read_text('utf-8'))
    by_iso={c['iso']:[] for c in research['countries']}
    for row in research['rows']:by_iso[row['iso3']].append(row)
    research['partitions']={iso:'research-'+iso+'.json.gz' for iso in by_iso}
    for iso,rows in by_iso.items():compressed(research['partitions'][iso],safe(rows).encode('utf-8'))
    research['columns']=[k for k in research['rows'][0] if k!='details']
    research['rows']=[]
    put('view-research.html',frame((ROOT/'research-groups.html').read_text('utf-8').replace('__RESEARCH_DATA__',safe(research))))
    six=json.loads((ROOT/'data/research_six_group_explorer.json').read_text('utf-8'))
    by_iso={c['iso']:[] for c in six['countries']}
    for row in six['rows']:by_iso[row['iso3']].append(row)
    six['partitions']={iso:'research-six-'+iso+'.json.gz' for iso in by_iso}
    for iso,rows in by_iso.items():compressed(six['partitions'][iso],safe(rows).encode('utf-8'))
    six['columns']=[k for k in six['rows'][0] if k!='details'];six['rows']=[]
    template=(ROOT/'research-groups.html').read_text('utf-8')
    for suffix in ['classification.csv','bridge.csv','coverage.csv','validation.json','annual.csv','joined.csv','components.csv']:
        name='research_six_group_'+suffix
        if suffix in ['annual.csv','joined.csv','components.csv']:compressed(name+'.gz',(ROOT/'data'/name).read_bytes())
        else:copy(name,ROOT/'data'/name)
        template=template.replace('href="research_group_'+suffix,'href="'+name)
    copy('research_six_groups.xlsx',ROOT/'data/research_six_groups.xlsx')
    template=template.replace('href="research_groups.xlsx"','href="research_six_groups.xlsx"')
    template=template.replace('Manufacturing covers groups 03–07; services covers groups 10–16.','Manufacturing covers MHT and LMT; services cover KIS and LIS.')
    template=template.replace('Group 16 covers R–T only.','The six-sector partition covers A–T only; U is excluded.')
    put('view-research-six.html',frame(template.replace('__RESEARCH_DATA__',safe(six))))
    for name,view in [('rd-industry.html','rd-composition'),('broad-sectors.html','gva'),('sector-economy.html','economy-employment'),('industry.html','detail'),('sources.html','sources')]:
        redirect=f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Open dashboard</title><meta http-equiv="refresh" content="0;url=index.html#{view}"><a href="index.html#{view}">Open this view in the unified dashboard</a></html>'
        (destination/name).write_text(redirect,encoding='utf-8')
    put('index.html',(ROOT/'dashboard.html').read_text('utf-8'))
    return files
