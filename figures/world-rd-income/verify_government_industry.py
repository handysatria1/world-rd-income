"""Check official source cells, conversions, suppression and classification boundaries."""
import json
import math
from collections import defaultdict
from io import BytesIO
from zipfile import ZipFile
from openpyxl import load_workbook
from broad_sectors import DATA
from industry_data import read_csv,digest


def same(a,b):
    assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=.01),(a,b)


def verify():
    data=json.loads((DATA/'government_industry_explorer.json').read_text('utf-8')); rows=data['rows']
    books={}; jsons={}; csvs={}; sources=set(); fx=json.loads((DATA/'rd_industry_raw/wb_exchange_history.json').read_bytes())[1]
    for r in rows:
        file=r['source_file']; sources.add(file); v=r['amount_local']
        if v is not None:
            same(v,float(str(r['value_reported']).replace(',',''))*10**r['unit_multiplier'])
            if r['currency']=='USD':assert r['local_per_usd']==1
            elif r['local_per_usd'] is not None:
                original=fx[r['fx_record']-1];assert original['date']==str(r['year']) and original['countryiso3code']==('ESP' if r['currency']=='EUR' else r['iso3'])
                assert original['value']==r['local_per_usd']
            if r['amount_usd'] is not None:same(r['amount_usd'],v/r['local_per_usd'])
        if file.endswith('.xlsx'):
            if file not in books:books[file]=load_workbook(DATA/file,data_only=True,read_only=False)
            sheet,cell=r['source_locator'].split('!'); original=books[file][sheet][cell].value
            if v is not None:same(original,r['value_reported'])
            else:assert str(original)==str(r['value_reported']) or original is None
        elif file.endswith('.csv'):
            if file not in csvs:csvs[file]=read_csv(DATA/file)
            original=csvs[file][int(r['source_locator'].split()[-1])-1]
            assert original['REF_AREA']==r['iso3'] and original['TIME_PERIOD']==str(r['year']) and original['ACTIVITY']==r['activity_code']
            same(original['OBS_VALUE'],r['value_reported'])
        elif 'singstat_' in file:
            if file not in jsons:jsons[file]=json.loads((DATA/file).read_bytes())['Data']
            original=next(c for a in jsons[file]['row'] if a['seriesNo']==r['activity_code'] for c in a['columns'] if c['key']==str(r['year']))
            assert original['value']==r['value_reported']
    for file in sources:
        folder,name=file.split('/',1); m=json.loads((DATA/folder/'manifest.json').read_text('utf-8'))[name]
        assert digest(DATA/file)==m['sha256']
        assert all(r['sha256']==m['sha256'] and r['source_url']==m['url'] for r in rows if r['source_file']==file)
    for b in books.values():b.close()
    assert all(r['amount_local'] is None for r in rows if r['value_reported'] in ['[c]','[x]'])
    by={(r['source'],r['year'],r['activity_code']):r for r in rows}
    same(by['SingStat M354861',2025,'1']['amount_local'],132813.8e6)
    same(by['SingStat M015731',2025,'1.1.1']['amount_local'],137611.7e6)
    assert by['SingStat M354861',2025,'1']['scope']!=by['SingStat M015731',2025,'1.1.1']['scope']
    same(sum(r['amount_local'] for r in rows if r['source']=='SGP_RIE' and r['activity_code'] in [f'RIE_{n:02}' for n in range(7,13)]),4338.59e6)
    same(by['SGP_RIE',2023,'RIE_19']['amount_local'],8955.99e6)
    ncses=load_workbook(BytesIO(ZipFile(DATA/'government_industry_raw/ncses_berd_2024_tables.zip').read('nsf27300-tab065.xlsx')),read_only=True,data_only=True).worksheets[0]
    for r in rows:
        if r['source'].startswith('NCSES'):
            cell=r['source_locator'].split('; ')[1];same(ncses[cell].value,r['value_reported'])
    assert any(r['iso3']=='KOR' and r['metric']=='BERD' and r['year']==2024 and r['amount_local']==1066988e8 for r in rows)
    assert any(r['iso3']=='CHN' and r['metric']=='BERD' and r['year']==2025 and r['amount_local']==23228.5e8 for r in rows)
    assert any(r['iso3']=='CHN' and r['metric']=='GVA' and r['year']==2023 for r in rows)
    checked=0
    for prefix,groupids in [('research_group',['03','04','05','06','07']),('research_six_group',['MHT','LMT'])]:
        annual=read_csv(DATA/(prefix+'_annual.csv'));lookup={(r['iso3'],r['year'],r['group_id'],r['metric']):r for r in annual}
        for iso,total in [('GBR',228979e6),('KOR',730457300e6)]:
            selected=[lookup[iso,'2025',g,'GVA'] for g in groupids]
            if iso=='KOR' and prefix=='research_six_group':
                assert all(r['coverage']=='partial' for r in selected)
                assert sum(float(r['assigned_amount']) for r in selected)<total
                assert 'C2011' in selected[0]['missing_codes_or_classes'] and 'C2211' in selected[1]['missing_codes_or_classes']
                continue
            assert all(r['coverage']=='complete' for r in selected)
            assert math.isclose(sum(float(r['assigned_amount']) for r in selected),total,rel_tol=0,abs_tol=5e6),(prefix,iso)
        g=lookup['GBR','2024','04' if prefix=='research_group' else 'LMT','BERD']
        assert g['coverage']=='partial' and 'C19' in g['missing_codes_or_classes']
        for r in annual:
            if r['source'] not in ['ONS BERD 2024','ONS current-price GVA','OECD STAN 2025']:continue
            expression=json.loads(r['source_expression']);original=[by[r['source'],int(r['year']),c] for c in expression]
            if original:same(sum(c['amount_local']*expression[c['activity_code']] for c in original),r['assigned_amount'])
            if r['group_id']=='16':assert '94-99' not in expression
            checked+=1
    result={'verification':'passed','native_observations':len(rows),'source_files_hashed':len(sources),'aligned_group_observations':checked,
            'checks':['source_cells_and_exact_year_FX','SGP_scope_difference_preserved','RIE_2023_clusters_and_total','ONS_performer_sheet_3','suppression_not_zero','manufacturing_reconciliation_both_classifications','group_16_excludes_U'],
            'native_sha256':digest(DATA/'government_industry_explorer.json')}
    (DATA/'government_industry_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':verify()
