"""Verify new source reclassification, exact joins, coverage explanations and packaging."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import gzip
import re
from itertools import zip_longest
from pathlib import Path
from zipfile import ZipFile
from openpyxl import load_workbook

from income_sources import ROOT
from industry_data import read_csv, digest
from absorptive_capacity import METRICS
from rd_industry_mapping import Classification
from research_groups import SPECS
from sector_field_rd import FLAGS
from snapshot_indicators import build_snapshot_indicators


def same(a,b):
    return a is None and b is None or a is not None and b is not None and math.isclose(a,b,rel_tol=1e-11,abs_tol=.01)


def verify(stage,before_distribution=False):
    data=ROOT/'data'
    report=json.loads((data/'research_group_validation.json').read_text('utf-8'))
    for name,sha in report['input_sha256'].items():assert digest(data/name)==sha,name
    for name,sha in report['output_sha256'].items():assert digest(data/name)==sha,name
    cl=Classification(data/'rd_industry_raw/oecd_berd_structure.xml')
    targets={gid:frozenset.union(*(cl.coverage(c) for c in codes)) for gid,_,_,codes,_ in SPECS}
    components=defaultdict(list)
    originals={
        'GVA':{(r['iso3'],r['year'],r['activity_code']):r for r in read_csv(data/'broad_sector_components.csv')},
        'Employment':{(r['iso3'],r['year'],r['activity_code']):r for r in read_csv(data/'sector_economy_components.csv') if r['metric']=='employment'},
        'BERD':{(r['iso3'],r['year'],r['source'],r['activity_code']):r for r in read_csv(data/'rd_industry_components.csv')}}
    source_checks=0
    official={(r['iso3'],str(r['year']),r['metric'],r['source'],r['activity_code']):r for r in json.loads((data/'government_industry_explorer.json').read_text('utf-8'))['rows']}
    for r in read_csv(data/'research_group_components.csv'):
        components[r['iso3'],r['year'],r['group_id'],r['metric']].append(r)
        gov=official.get((r['iso3'],r['year'],r['metric'],r['source'],r['code']))
        if gov and r['source'] in ['ONS BERD 2024','ONS current-price GVA','OECD STAN 2025']:
            assert same(gov['amount_local'],float(r['source_amount_units']) if r['source_amount_units'] else None)
            assert r['source_file']==gov['source_file'] and r['source_locator']==gov['source_locator'] and r['flags']==gov['flags']
            source_checks+=1
            continue
        key=(r['iso3'],r['year'],r['source'],r['code']) if r['metric']=='BERD' else (r['iso3'],r['year'],r['code'])
        original=originals[r['metric']].get(key)
        if original is None:
            assert r['source_amount_units']=='' and r['source_locator']=='not returned'
        else:
            if r['metric']=='BERD':
                value=float(original['amount_local']) if original['amount_local'] else None
                locator=original['source_sheet']+'!'+original['source_cell'] if original['source_sheet'] else 'record '+original['raw_record']
                flags=';'.join(f+'='+original[f] for f in FLAGS if original[f])
            else:
                value=float(original['value_reported'])*10**int(original['unit_multiplier']) if original['value_reported'] else None
                locator='record '+original['raw_record'] if original['raw_record'] else 'not returned'
                flags=original['obs_status']
            assert same(value,float(r['source_amount_units']) if r['source_amount_units'] else None),key
            assert r['source_file']==original['source_file'] and r['source_locator']==locator and r['flags']==flags,key
        source_checks+=1
    del originals
    count=0
    for r in read_csv(data/'research_group_annual.csv'):
        terms=components[r['iso3'],r['year'],r['group_id'],r['metric']]
        observed=[t for t in terms if t['source_amount_units']!='']
        expected=sum(float(t['coefficient'])*float(t['source_amount_units']) for t in observed) if observed else None
        assert same(expected,float(r['assigned_amount']) if r['assigned_amount'] else None),(r['iso3'],r['year'],r['group_id'],r['metric'])
        if r['metric']=='BERD' and r['source']=='OECD_RDS':
            weights=defaultdict(int)
            for t in terms:
                for c in cl.coverage(t['code']):weights[c]+=int(t['coefficient'])
            assert all(w in [0,1] for w in weights.values())
            covered={c for c,w in weights.items() if w};assert covered<=targets[r['group_id']]
            assert ('complete'==r['coverage'])==(covered==targets[r['group_id']])
            if r['group_id']=='16':assert not any(c.startswith(('O','P','Q','U')) for c in covered)
        count+=1
    ratio_checks=0
    for r in read_csv(data/'research_group_joined.csv'):
        for out,num,den,coverage_num,coverage_den,scale in [('berd_percent_gva','berd_assigned_usd','gva_assigned_usd','berd_coverage','gva_coverage',100),('berd_usd_per_worker','berd_assigned_usd','employment_assigned_persons','berd_coverage','employment_coverage',1),('gva_usd_per_worker','gva_assigned_usd','employment_assigned_persons','gva_coverage','employment_coverage',1)]:
            if r[out]:
                assert r[coverage_num]==r[coverage_den]=='complete' and r[num] and r[den] and float(r[den])>0
                assert same(float(r[out]),float(r[num])/float(r[den])*scale)
                ratio_checks+=1
    details=json.loads((stage/'rd_industry_details.json').read_text('utf-8'))
    uk=details['rows']['GBR/2023/KIS'];missing={r['code'] for r in uk['missing']}
    assert {'J60','M69','M70','M73','M74','M75','P'}<=missing,missing
    assert uk['coverage']=='partial' and any('CONF_STATUS=C' in r['flags'] for r in uk['missing'])
    assert details['rows']['SGP/2023/KIS']['native'] and details['rows']['ES-PV/2024/KIS']['native']
    income=json.loads((stage/'income_explorer.json').read_text('utf-8'));assert income['currentVintage']=='FY2027'
    lookup={c['iso']:c for c in income['countries']}
    assert lookup['GBR']['current']=='HIC' and lookup['CHN']['current']=='UMC' and lookup['IND']['current']=='LMC'
    assert lookup['ES-PV']['current']=='UNK' and lookup['ES-PV']['region']
    indicators={'internetUsers':'IT.NET.USER.ZS','governmentEffectiveness':'GOV_WGI_GE_SC',
                'governmentEffectivenessEstimate':'GOV_WGI_GE.EST','humanCapitalIndex':'HD.HCI.OVRL',
                'bachelorAttainment':'SE.TER.CUAT.BA.ZS'}
    assert all(income['indicators'][key]['code']==code for key,code in indicators.items())
    assert any(cell['v']<0 for c in income['countries'] for cell in c['series'].get('governmentEffectivenessEstimate',{}).values() if cell['v'] is not None)
    assert any(cell['v'] is not None for c in income['countries'] for cell in c['series'].get('governmentEffectiveness',{}).values())
    catalog=json.loads((data/'income_raw/countries.json').read_text('utf-8'))[1]
    iso2_to_iso3={r['iso2Code']:r['id'] for r in catalog if r.get('iso2Code') and r.get('id') and (r.get('region') or {}).get('id')!='NA'}
    matched=0
    for key in ['internetUsers','governmentEffectivenessEstimate','humanCapitalIndex','bachelorAttainment']:
        _,records=json.loads((data/'income_raw'/f'{key}.json').read_text('utf-8'))
        for position,record in enumerate(records,1):
            year=int(record['date'])
            if not 2000<=year<=2025:continue
            source_iso3=record.get('countryiso3code') or ''
            source_code=(record.get('country') or {}).get('id') or ''
            iso=source_iso3 or iso2_to_iso3.get(source_code,'')
            country=lookup.get(iso)
            if country is None or country.get('region'):continue
            cell=country['series'].get(key,{}).get(str(year))
            assert cell is not None,(key,iso,year)
            assert cell['record']==position and cell['v']==record['value'],(key,iso,year,cell,record)
            assert cell['countryCode']==source_code
            assert cell['countryMatch']==('iso3' if source_iso3 else 'iso2_country_catalog')
            matched+=1
    assert matched>0
    capacity=json.loads((data/'absorptive_capacity.json').read_text('utf-8'))
    assert capacity['builtUTC']==income['builtUTC'] and capacity['current_vintage']==income['currentVintage']
    assert capacity['first_year']==2000 and capacity['last_year']==2025
    country_means=read_csv(data/'absorptive_capacity_country.csv')
    expected_countries={c['iso']:c for c in income['countries'] if not c.get('region')}
    assert {r['iso3'] for r in country_means}==set(expected_countries)
    country_mean_lookup={}
    for row in country_means:
        country=expected_countries[row['iso3']]
        assert row['current_income_code']==country['current']
        country_mean_lookup[row['iso3']]={}
        for metric in METRICS:
            observations=sorted((int(year),cell['v']) for year,cell in country['series'].get(metric['key'],{}).items()
                                if 2000<=int(year)<=2025 and cell['v'] is not None)
            mean=math.fsum(value for _,value in observations)/len(observations) if observations else None
            assert int(row[metric['slug']+'_n_years'])==len(observations)
            assert row[metric['slug']+'_first_year']==(str(observations[0][0]) if observations else '')
            assert row[metric['slug']+'_last_year']==(str(observations[-1][0]) if observations else '')
            actual=float(row[metric['column']]) if row[metric['column']] else None
            assert actual is None and mean is None or actual is not None and mean is not None and math.isclose(actual,mean,rel_tol=1e-12,abs_tol=1e-12)
            country_mean_lookup[row['iso3']][metric['key']]=mean
    group_csv=read_csv(data/'absorptive_capacity_groups.csv')
    assert len(group_csv)==len(capacity['group_averages'])
    group_csv_lookup={(r['classification_vintage'],r['income_group_code'],r['metric']):r for r in group_csv}
    assert len(group_csv_lookup)==len(group_csv)
    for group in capacity['group_averages']:
        key=(group['classification_vintage'],group['income_group_code'],group['metric'])
        exported=group_csv_lookup[key]
        memberships=[]
        for country in expected_countries.values():
            code=country['current'] if group['classification_vintage']==income['currentVintage'] else country.get('history',{}).get(group['classification_vintage'],'UNK')
            if code==group['income_group_code'] or group['income_group_code']=='MIC' and code in {'UMC','LMC'}:
                memberships.append(country['iso'])
        values=[country_mean_lookup[iso][group['metric']] for iso in memberships if country_mean_lookup[iso][group['metric']] is not None]
        mean=math.fsum(values)/len(values) if values else None
        assert group['economies_in_group']==len(memberships) and group['economies_with_data']==len(values)
        assert mean is None and group['mean_of_country_means'] is None or mean is not None and math.isclose(mean,group['mean_of_country_means'],rel_tol=1e-12,abs_tol=1e-12)
        assert exported['indicator']==group['indicator'] and exported['economies_in_group']==str(len(memberships))
        exported_mean=float(exported['mean_of_country_means']) if exported['mean_of_country_means'] else None
        assert exported_mean is None and mean is None or exported_mean is not None and math.isclose(exported_mean,mean,rel_tol=1e-12,abs_tol=1e-12)
    for name in ['absorptive_capacity.json','absorptive_capacity_country.csv','absorptive_capacity_groups.csv']:
        assert digest(stage/name)==digest(data/name),name
    workbook_rows=0
    book=load_workbook(data/'research_groups.xlsx',read_only=True,data_only=True)
    for name in ['research_group_classification','research_group_bridge','research_group_annual','research_group_joined','research_group_components','research_group_coverage']:
        values=iter(book[name].values)
        with (data/(name+'.csv')).open(encoding='utf-8-sig',newline='') as handle:
            rows=csv.reader(handle);assert list(next(values))==next(rows),name
            for actual,expected in zip_longest(values,rows):
                assert actual is not None and expected is not None,name
                for a,b in zip(actual,expected):
                    assert (b=='' if a is None else same(a,float(b)) if isinstance(a,(float,int)) else str(a)==b),(name,a,b)
                workbook_rows+=1
    book.close()
    for name in ['research_group_annual.csv','research_group_joined.csv','research_group_components.csv']:
        assert gzip.decompress((stage/(name+'.gz')).read_bytes())==(data/name).read_bytes()
    for name in ['rd_breakdown_annual.csv','rd_sector_field_annual.csv','research_six_group_annual.csv','research_six_group_joined.csv','research_six_group_components.csv']:
        assert gzip.decompress((stage/(name+'.gz')).read_bytes())==(data/name).read_bytes()
    for path in stage.glob('*.json.gz'):json.loads(gzip.decompress(path.read_bytes()))
    with ZipFile(stage/'world-rd-income.zip') as archive:
        assert archive.testzip() is None
        for name in ['dashboard.js','income_core.js','view-national.html','view-research.html','research-GBR.json.gz','income_source_manifest.json']:
            assert 'world-rd-income/'+name in archive.namelist(),name
        for name,info in json.loads((data/'income_raw/manifest.json').read_text('utf-8')).items():
            body=archive.read('world-rd-income/figures/world-rd-income/data/income_raw/'+name)
            assert hashlib.sha256(body).hexdigest()==info['sha256']
    dashboard_js=(stage/'dashboard.js').read_text('utf-8')
    for view in ["'internet-users'", "'government-effectiveness-score'", "'government-effectiveness'", "'human-capital'", "'bachelor-attainment'"]:
        assert view in dashboard_js,view
    assert "'absorptive-capacity'" in dashboard_js
    assert 'AbsorptiveCapacityChart' in dashboard_js
    assert (stage/'absorptive_capacity.json').is_file()
    assert (stage/'absorptive_capacity_chart.js').is_file()
    national_html=(stage/'view-national.html').read_text('utf-8')
    embedded=re.search(r'<script type="application/json" id="history-data">(.*?)</script>',national_html,re.S)
    assert embedded,'National snapshot data block missing'
    national_payload=json.loads(embedded.group(1))
    snapshot=national_payload['snapshotIndicators']
    expected=build_snapshot_indicators(
        json.loads((data/'income_explorer.json').read_text('utf-8')),
        json.loads((data/'broad_sector_explorer.json').read_text('utf-8')),
        json.loads((data/'industry_explorer.json').read_text('utf-8')),
        json.loads((data/'research_six_group_explorer.json').read_text('utf-8')),
        country_ids=[country['iso'] for country in json.loads((data/'explorer_history.json').read_text('utf-8'))['countries']],
    )
    assert snapshot==expected
    assert len(snapshot['rows'])==len({(row['iso3'],row['year']) for row in snapshot['rows']})
    explorer_js=(ROOT/'explorer.js').read_text('utf-8')
    assert 'snapshotIndicatorLines' in explorer_js and 'snapshotIndicatorFields' in explorer_js
    site_bytes=sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
    if not before_distribution:
        assert site_bytes<300_000_000,site_bytes
    result={'verification':'passed','metric_group_values_recomputed':count,'complete_group_ratios_checked':ratio_checks,
            'original_source_terms_checked':source_checks,'research_workbook_rows_checked':workbook_rows,'site_bytes':site_bytes,
            'group_16_U_exclusion':'passed','UK_KIS_coverage_explanation':'passed','income_classifications':'passed',
            'income_indicator_source_matches':matched,'negative_WGI_estimate':'passed',
            'absorptive_capacity_country_means':len(country_means),
             'absorptive_capacity_group_rows':len(group_csv),
             'absorptive_capacity_source_recalculation':'passed',
             'snapshot_indicator_rows':len(snapshot['rows']),
             'snapshot_indicator_exact_iso3_year_join':'passed',
            'distribution_stage':'before_release_offload' if before_distribution else 'full_site',
            'final_pages_size_check':'release_downloads.py' if before_distribution else 'passed'}
    (stage/'dashboard_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--before-distribution',action='store_true',help='Validate the combined staging area; release_downloads.py checks final Pages size')
    args=parser.parse_args();verify(args.site,args.before_distribution)
