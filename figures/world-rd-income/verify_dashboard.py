"""Verify new source reclassification, exact joins, coverage explanations and packaging."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import gzip
from itertools import zip_longest
from pathlib import Path
from zipfile import ZipFile
from openpyxl import load_workbook

from income_sources import ROOT
from industry_data import read_csv, digest
from rd_industry_mapping import Classification
from research_groups import SPECS
from sector_field_rd import FLAGS


def same(a,b):
    return a is None and b is None or a is not None and b is not None and math.isclose(a,b,rel_tol=1e-11,abs_tol=.01)


def verify(stage):
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
    for r in read_csv(data/'research_group_components.csv'):
        components[r['iso3'],r['year'],r['group_id'],r['metric']].append(r)
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
    for path in stage.glob('*.json.gz'):json.loads(gzip.decompress(path.read_bytes()))
    with ZipFile(stage/'world-rd-income.zip') as archive:
        assert archive.testzip() is None
        for name in ['dashboard.js','income_core.js','view-national.html','view-research.html','research-GBR.json.gz','income_source_manifest.json']:
            assert 'world-rd-income/'+name in archive.namelist(),name
        for name,info in json.loads((data/'income_raw/manifest.json').read_text('utf-8')).items():
            body=archive.read('world-rd-income/figures/world-rd-income/data/income_raw/'+name)
            assert hashlib.sha256(body).hexdigest()==info['sha256']
    site_bytes=sum(p.stat().st_size for p in stage.rglob('*') if p.is_file())
    assert site_bytes<1_000_000_000,site_bytes
    result={'verification':'passed','metric_group_values_recomputed':count,'complete_group_ratios_checked':ratio_checks,
            'original_source_terms_checked':source_checks,'research_workbook_rows_checked':workbook_rows,'site_bytes':site_bytes,
            'group_16_U_exclusion':'passed','UK_KIS_coverage_explanation':'passed','income_classifications':'passed'}
    (stage/'dashboard_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',type=Path,required=True);verify(parser.parse_args().site)
