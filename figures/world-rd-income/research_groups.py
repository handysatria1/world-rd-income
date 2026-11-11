"""Reclassify original GVA, BERD and employment observations into 16 research groups.

Group 16 is R–T, as confirmed by the user; U is never silently allocated.
"""
from collections import defaultdict
from datetime import datetime, timezone
import json
import math

from openpyxl import Workbook
from broad_sectors import DATA, DEFAULTS, DISPLAY, GROUPS as SIX_GROUPS, write
from industry_data import read_csv, digest
from rd_industry_mapping import Classification, cover, combination
from sector_field_rd import FLAGS

SPECS = [
    ('01', 'Agriculture', 'Other industries', ['A'], ['01']),
    ('02', 'Mining & quarrying', 'Other industries', ['B'], ['02']),
    ('03', 'General manufacturing', 'Manufacturing', ['C10T12','C13T15','C16T18','C31T33'], ['03','04','05','15']),
    ('04', 'Chemicals & non-metallic', 'Manufacturing', ['C19','C20','C21','C22','C23'], ['06','07','08','09']),
    ('05', 'Transport equipment', 'Manufacturing', ['C29','C30'], ['14']),
    ('06', 'Computer, electronic & optical', 'Manufacturing', ['C26'], ['11']),
    ('07', 'Electrical, machinery & metals', 'Manufacturing', ['C24_25','C27','C28'], ['10','12','13']),
    ('08', 'Utilities & waste management', 'Utilities', ['D_E'], ['16','17']),
    ('09', 'Construction', 'Other industries', ['F'], ['18']),
    ('10', 'Trade, transport & hospitality', 'Services', ['G','H','I'], ['19','20','21']),
    ('11', 'Information & communication', 'Services', ['J'], ['22','23','24']),
    ('12', 'Finance & insurance', 'Services', ['K'], ['25']),
    ('13', 'Real estate', 'Services', ['L'], ['26']),
    ('14', 'Professional & business support', 'Services', ['M','N'], ['27','28','29','30']),
    ('15', 'Public administration, education & health', 'Services', ['O','P','Q'], ['31','32','33','34']),
    ('16', 'Other services', 'Services', ['R','S','T'], ['35','36','37']),
]
COLORS=['#6d8c54','#8b7660','#408bb3','#225b85','#354d98','#098c94','#667ca6','#a2639f','#8b8b6c','#be743b','#428849','#8270a2','#9b6973','#5c9c82','#cb904a','#737e8b']
NATIVE = {
    'EUSTAT_NATIVE': {'040':'04','060':'04','080':'04','100':'07','120':'07','140':'07','160':'07','180':'07','200':'07','220':'06','260':'05','320':'09','340':'11','360':'14','380':'14'},
    'SGP_RIE': {'RIE_08':'04','RIE_09':'06','RIE_14':'14','RIE_16':'11','RIE_17':'10'},
}
INPUTS=['broad_sector_components.csv','broad_sector_annual.csv','broad_sector_coverage.csv','sector_economy_components.csv','sector_employment.csv',
        'rd_industry_components.csv','rd_industry_coverage.csv','rd_industry_fx.csv','rd_economy_context.csv']
OUTPUTS=['research_group_classification.csv','research_group_bridge.csv','research_group_annual.csv','research_group_joined.csv','research_group_components.csv','research_group_coverage.csv','research_groups.xlsx','research_group_explorer.json']


def number(v):
    return None if v in ['',None] else float(v)


def candidates(cells, cl):
    direct=[{'value':number(r['amount_local']),'rounding':float(r['rounding_local']),'classes':cl.coverage(code),'terms':{code:1}}
            for code,r in cells.items() if r['aggregation_eligible']=='True']
    result=list(direct)
    if any(r.get(f) in ['S2','V2'] for r in cells.values() for f in FLAGS):
        return result
    # Exact public residuals only. The excluded classes must be fully observed;
    # e.g. OTU - O_P - Q is insufficient for R-T unless U is also known.
    for target in cl.groups.values():
        for whole in direct:
            if target < whole['classes']:
                excluded=cover(whole['classes']-target,direct)
                if excluded and excluded['classes']==whole['classes']-target:
                    candidate=combination([(1,whole),(-1,excluded)])
                    assert candidate['classes']==target
                    if candidate['value']>=0:
                        result.append(candidate)
    return result


def build():
    cl=Classification(DATA/'rd_industry_raw/oecd_berd_structure.xml')
    old=dict(cl.groups)
    cl.groups={gid:frozenset.union(*(cl.coverage(c) for c in codes)) for gid,_,_,codes,_ in SPECS}
    union=set.union(*(set(v) for v in cl.groups.values()))
    assert len(union)==sum(map(len,cl.groups.values())) and union==set(cl.classes)-cl.coverage('U')
    groups=[{'id':gid,'label':label,'sector':sector,'codes':codes,'color':COLORS[i]} for i,(gid,label,sector,codes,_) in enumerate(SPECS)]
    mapping=[{'dataset':dataset,'group_id':gid,'research_group':label,'sector':sector,'isic_codes':';'.join(codes),
              'eustat_a38_codes':';'.join(eustat),'scope':'A-T; group 16 R/S/T; U excluded',
              'note':'Same target classes for all three datasets; source expressions may differ.'} for dataset in ['GVA','BERD','Employment'] for gid,label,sector,codes,eustat in SPECS]
    bridge=[{'research_group':gid,'six_group':sid,'isic4_classes':';'.join(sorted(target&classes)),
             'note':'Class-level intersection; never split monetary amounts proportionally.'} for gid,target in cl.groups.items() for sid,classes in old.items() if target&classes]
    country_names={r['iso3']:r['economy'] for r in read_csv(DATA/'rd_industry_coverage.csv')}
    gva_lookup={(r['iso3'],r['year'],r['activity_code']):r for r in read_csv(DATA/'broad_sector_components.csv')}
    employment_lookup={(r['iso3'],r['year'],r['activity_code']):r for r in read_csv(DATA/'sector_economy_components.csv') if r['metric']=='employment'}
    gva_total={(r['iso3'],r['year']):r for r in read_csv(DATA/'broad_sector_coverage.csv')}
    emp_total={(r['iso3'],r['year']):r for r in read_csv(DATA/'sector_employment.csv')}
    gva_annual={(r['iso3'],r['year']):r for r in read_csv(DATA/'broad_sector_annual.csv')}
    rd_total={(r['iso3'],r['year']):r for r in read_csv(DATA/'rd_industry_coverage.csv')}
    fx={(r['iso3'],r['year'],r['currency']):r for r in read_csv(DATA/'rd_industry_fx.csv')}
    rd_blocks=defaultdict(dict)
    for r in read_csv(DATA/'rd_industry_components.csv'):
        rd_blocks[r['iso3'],r['year'],r['source']][r['activity_code']]=r
    contexts={(r['iso3'],r['year']):r for r in read_csv(DATA/'rd_economy_context.csv')}
    keys=sorted(set(gva_total)|set(emp_total)|set(rd_total))
    annual,joined,components,audit,browser=[],[],[],[],[]
    for iso,year in keys:
        country=country_names[iso];rd=rd_total.get((iso,year),{});source=rd.get('rd_source','');native=source!='OECD_RDS'
        cells=rd_blocks[iso,year,source];available=candidates(cells,cl) if not native else []
        rate=number(fx.get((iso,year,rd.get('currency','')),{}).get('local_per_usd'))
        local_total=number(rd.get('reported_total_local'));gd=gva_total.get((iso,year),{});em=emp_total.get((iso,year),{})
        metric_totals={'BERD':local_total,'GVA':number(gd.get('grouped_gva_source_currency')) if gd.get('coverage_status')=='available' else None,
                       'Employment':number(em.get('grouped_total_persons')) if em.get('coverage_status')=='available' else None}
        block_rows=[];used=set()
        for gid,label,sector,codes,eustat in SPECS:
            selected=({c:1 for c,r in cells.items() if NATIVE.get(source,{}).get(c)==gid and number(r['amount_local']) is not None
                       and not any(r.get(f) for f in FLAGS) and (source!='EUSTAT_NATIVE' or int(year)>=2003)} if native else {})
            found=cover(cl.groups[gid],available) if not native else None
            terms=selected if native else found['terms'] if found else {}
            covered=found['classes'] if found else frozenset()
            assert not used&covered
            used|=covered
            value=sum(number(cells[c]['amount_local'])*w for c,w in terms.items()) if terms else None
            complete=bool(found) and covered==cl.groups[gid]
            records={}
            for metric in ['BERD','GVA','Employment']:
                missing=[];flags=[];details=[]
                if metric=='BERD':
                    amount=value;currency=rd.get('currency','');usd=amount/rate if amount is not None and rate else None
                    status='complete' if complete else 'partial' if amount is not None else 'unavailable'
                    if not native:
                        missing=sorted(cl.groups[gid]-covered)
                    source_name=source;expression=terms
                    for c,w in terms.items():
                        r=cells[c];flag=';'.join(f+'='+r[f] for f in FLAGS if r[f]);flags.append(flag)
                        details.append({'code':c,'coefficient':w,'label':r['activity_label'],'source_file':r['source_file'],
                                        'source_locator':r['source_sheet']+'!'+r['source_cell'] if r['source_sheet'] else 'record '+r['raw_record'],
                                        'source_amount_units':number(r['amount_local']),'flags':flag})
                    note='Native label containment only; exact class coverage unresolved.' if native else 'Disjoint exact ISIC4 class coverage; public aggregate subtraction only with a complete observed excluded set.'
                else:
                    basque=iso=='ES-PV';wanted=list(eustat if basque else codes)
                    if basque and int(year)<=2020 and gid=='04':wanted.remove('07')
                    lookup=gva_lookup if metric=='GVA' else employment_lookup
                    vals=[]
                    for c in wanted:
                        r=lookup.get((iso,year,c),{});v=number(r.get('value_reported'));scaled=v*10**int(r['unit_multiplier']) if v is not None else None
                        vals.append(scaled);flags.append(r.get('obs_status',''))
                        if scaled is None:missing.append(c)
                        details.append({'code':c,'coefficient':1,'label':r.get('activity_label',''),'source_file':r.get('source_file',''),
                                        'source_locator':'record '+r.get('raw_record','') if r.get('raw_record') else 'not returned',
                                        'source_amount_units':scaled,'flags':r.get('obs_status','')})
                    amount=sum(v for v in vals if v is not None) if any(v is not None for v in vals) else None
                    status='complete' if not missing else 'partial' if amount is not None else 'unavailable'
                    currency='persons' if metric=='Employment' else 'EUR' if basque else 'USD'
                    conversion=number(gva_annual.get((iso,year),{}).get('eur_per_usd')) if basque else 1
                    usd=amount/conversion if metric=='GVA' and amount is not None and conversion else None
                    source_name=('EUSTAT_A38' if basque else 'OECD_TIVA') if metric=='GVA' else ('EUSTAT_A38' if basque else 'OECD_TiM')
                    expression=dict.fromkeys(wanted,1);note='A38 08 includes 07+08 through 2020; counted once.' if basque and int(year)<=2020 and gid=='04' else 'Sum of original source components; units scaled before aggregation.'
                denominator=metric_totals[metric]
                share=amount/denominator*100 if amount is not None and denominator is not None and denominator>0 else None
                flags=';'.join(sorted(set(filter(None,flags))))
                row={'iso3':iso,'economy':country,'year':int(year),'group_id':gid,'research_group':label,'sector':sector,'metric':metric,
                     'assigned_amount':amount,'unit':currency,'assigned_usd':usd,'coverage':status,'share_percent':share,
                     'denominator':denominator,'denominator_scope':'reported industry R&D total (may include U)' if metric=='BERD' else 'A-T total; complete/reconciled six-group source audit required',
                     'source':source_name,'rd_scope':rd.get('rd_scope','') if metric=='BERD' else '',
                     'source_expression':json.dumps(expression,separators=(',',':')),'missing_codes_or_classes':';'.join(missing),
                     'flags':flags,'value_status':'derived_partial_native_branches' if metric=='BERD' and native else 'derived_disjoint_source_expression','note':note}
                annual.append(row);records[metric]=row
                for detail in details:components.append({**{k:row[k] for k in ['iso3','economy','year','group_id','metric','source','unit']},**detail})
            r,g,e=(records[m] for m in ['BERD','GVA','Employment'])
            full_r=r['assigned_usd'] if r['coverage']=='complete' else None
            full_g=g['assigned_usd'] if g['coverage']=='complete' else None
            full_e=e['assigned_amount'] if e['coverage']=='complete' else None
            join={'iso3':iso,'economy':country,'year':int(year),'group_id':gid,'research_group':label,'sector':sector,
                  'berd_assigned_local':r['assigned_amount'],'berd_currency':r['unit'],'berd_assigned_usd':r['assigned_usd'],'berd_coverage':r['coverage'],'berd_share_percent':r['share_percent'],
                  'gva_assigned_usd':g['assigned_usd'],'gva_coverage':g['coverage'],'gva_share_percent':g['share_percent'],
                  'employment_assigned_persons':e['assigned_amount'],'employment_coverage':e['coverage'],'employment_share_percent':e['share_percent'],
                  'berd_percent_gva':full_r/full_g*100 if full_r is not None and full_g is not None and full_g>0 else None,
                  'berd_usd_per_worker':full_r/full_e if full_r is not None and full_e is not None and full_e>0 else None,
                  'gva_usd_per_worker':full_g/full_e if full_g is not None and full_e is not None and full_e>0 else None,
                  'berd_source':r['source'],'gva_source':g['source'],'employment_source':e['source'],'berd_scope':r['rd_scope'],
                  'berd_flags':r['flags'],'gva_flags':g['flags'],'employment_flags':e['flags'],
                  'join_rule':'exact economy/year/research group; whole-group ratios require complete inputs',
                  'context_source':'rd_economy_context.csv; exact iso3/year',
                  **{k:contexts.get((iso,year),{}).get(k,'') for k in ['gerd_oecd_usd','gerd_wdi_usd','gerd_eustat_usd','gdp_per_capita_current_usd','goods_exports_usd']}}
            joined.append(join);block_rows.append(join)
            browser.append({**join,'details':{metric:{'expression':r0['source_expression'],'missing':r0['missing_codes_or_classes'], 'note':r0['note']} for metric,r0 in records.items()}})
        allocated=sum(r['berd_assigned_local'] or 0 for r in block_rows)
        residual=local_total-allocated if local_total is not None else None
        # A negative residual invalidates shares and ratios, but preserves amounts for audit.
        if residual is not None and residual<0:
            for row in block_rows:row['berd_share_percent']=row['berd_percent_gva']=row['berd_usd_per_worker']=None
            for row in browser[-16:]:row['berd_share_percent']=row['berd_percent_gva']=row['berd_usd_per_worker']=None
            for row in annual[-48:]:
                if row['metric']=='BERD':row['share_percent']=None
        audit.append({'iso3':iso,'year':int(year),'berd_source':source,'reported_berd_local':local_total,'assigned_berd_local':allocated,
                      'unallocated_berd_local':residual,'currency':rd.get('currency',''), 'status':'negative_remainder' if residual is not None and residual<0 else 'available' if local_total and allocated else 'missing_or_total_only',
                      'note':'Unallocated includes U, unavailable and unresolved branches and source discrepancies; not group 16.'})
        # Independent conservation against the earlier six-group partition for GVA and employment.
        for metric in ['GVA','Employment']:
            rows=[r for r in annual[-48:] if r['metric']==metric]
            if metric_totals[metric] is not None and all(r['coverage']=='complete' for r in rows):
                assert math.isclose(sum(r['assigned_amount'] for r in rows),metric_totals[metric],rel_tol=1e-12,abs_tol=.01),(iso,year,metric)
    outputs=dict(zip(OUTPUTS[:6],[mapping,bridge,annual,joined,components,audit]))
    workbook=Workbook(write_only=True)
    for name,rows in outputs.items():
        write(name,rows);sheet=workbook.create_sheet(name.removesuffix('.csv')[:31]);sheet.append(list(rows[0]));
        for r in rows:sheet.append(list(r.values()))
    workbook.save(DATA/'research_groups.xlsx')
    built=datetime.now(timezone.utc).isoformat()
    payload={'builtUTC':built,'groups':groups,'defaults':DEFAULTS,'rows':browser,'coverage':audit,
             'countries':[{'iso':iso,'name':country_names[iso],'display':DISPLAY.get(iso,country_names[iso])} for iso in sorted({k[0] for k in keys})]}
    (DATA/'research_group_explorer.json').write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
    report={'validation':'passed','built_utc':built,'groups':16,'economy_years':len(keys),'joined_rows':len(joined),'source_terms':len(components),
            'checks':['disjoint_419_class_catalog_minus_U','GVA_and_employment_conservation_against_six_groups','exact_year_ratios_complete_inputs_only','coherent_BERD_source_blocks'],
            'input_sha256':{name:digest(DATA/name) for name in INPUTS},'output_sha256':{name:digest(DATA/name) for name in OUTPUTS}}
    (DATA/'research_group_validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':
    build()
