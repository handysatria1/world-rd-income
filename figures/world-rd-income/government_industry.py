"""Source-native official observations and strictly code-aligned UK/Korean additions.

National classifications are retained, not renamed to ISIC or split by assumed shares.
"""
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO
import json
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from broad_sectors import DATA, write
from government_industry_sources import RAW
from industry_data import digest, read_csv
from rd_industry_mapping import Classification, cover


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(); self.tables=[]; self.table=None; self.row=None; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table': self.table=[]
        elif tag=='tr' and self.table is not None: self.row=[]
        elif tag in ('td','th') and self.row is not None: self.cell=[]
    def handle_data(self,text):
        if self.cell is not None: self.cell.append(text)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(''.join(self.cell).strip()); self.cell=None
        elif tag=='tr' and self.row is not None:
            self.table.append(self.row); self.row=None
        elif tag=='table' and self.table is not None:
            self.tables.append(self.table); self.table=None


def numeric(value):
    if isinstance(value,(int,float)): return float(value)
    text=str(value).strip().replace(',','')
    return float(text) if re.fullmatch(r'-?\d+(\.\d+)?',text) else None


def extract():
    manifests={folder:json.loads((DATA/folder/'manifest.json').read_text('utf-8')) for folder in
               ['government_industry_raw','industry_raw','raw','rd_industry_raw','broad_sector_raw']}
    used=set(); rows=[]; classification=Classification(DATA/'rd_industry_raw/oecd_berd_structure.xml')
    fx={(r['countryiso3code'],int(r['date'])):(r['value'],i) for i,r in enumerate(json.loads((DATA/'rd_industry_raw/wb_exchange_history.json').read_bytes())[1],1)}
    def add(iso,year,metric,source,code,label,value,mult,currency,file,locator,scope,flags='',isic='',note=''):
        folder,name=file.split('/',1); info=manifests[folder][name]; used.add(file)
        v=numeric(value); rate,fx_record=(1,None) if currency=='USD' else fx.get(('ESP' if currency=='EUR' else iso,year),(None,None))
        rows.append(dict(iso3=iso,year=year,metric=metric,source=source,activity_code=str(code),activity_label=str(label).strip(),
                         value_reported=value,unit_multiplier=mult,currency=currency,amount_local=v*10**mult if v is not None else None,
                         amount_usd=v*10**mult/rate if v is not None and rate else None,local_per_usd=rate,
                         fx_source_file='rd_industry_raw/wb_exchange_history.json' if currency!='USD' else '',fx_record=fx_record,
                         source_file=file,source_locator=locator,source_url=info['url'],retrieved_utc=info['retrieved_utc'],sha256=info['sha256'],
                         scope=scope,flags=flags,isic_code=isic,note=note))
    # SingStat national accounts and manufacturing establishments have DIFFERENT scopes.
    for table,scope in [('M354861','EDB manufacturing establishments; SSIC 2025; not national-accounts GVA'),
                        ('M355181','EDB manufacturing clusters; SSIC 2025; not national-accounts GVA'),
                        ('M015731','National accounts; SSIC 2020; current prices; GDP total includes product taxes')]:
        d=json.loads((RAW/f'singstat_{table}.json').read_bytes())['Data']
        for row in d['row']:
            for cell in row['columns']:
                year=int(cell['key'])
                if year<2023: continue
                add('SGP',year,'GVA','SingStat '+table,row['seriesNo'],row['rowText'],cell['value'],6,'SGD',
                    f'government_industry_raw/singstat_{table}.json',f"series {row['seriesNo']}; year {year}",scope,
                    'preliminary' if year==2025 and table in ['M354861','M355181'] else '',note=d['footnote'])
    # ONS performer industry (sheet 3), never the product-group table (sheet 2).
    file='raw/ons_berd_2024.xlsx'; book=load_workbook(DATA/file,data_only=True,read_only=True); s=book['3']
    assert list(next(s.iter_rows(min_row=9,max_row=9,values_only=True)))[:5]==['SIC','Industry description ','2022','2023','2024']
    for i,r in enumerate(s.values,1):
        if not 10<=i<=70: continue
        code=str(r[0]); digits=re.fullmatch(r'(\d{1,2})(?:-(\d{1,2}))?',code)
        isic='_T' if code=='All' else ''
        if digits:
            lo,hi=int(digits[1]),int(digits[2] or digits[1])
            # UK SIC 2007 and ISIC4 division boundaries align for these published ranges.
            divisions=[d for d in range(lo,hi+1) if any(int(c[1:3])==d for c in classification.classes)]
            isic=','.join(f'{d:02}' for d in divisions)
        for j,year in [(2,2022),(3,2023),(4,2024)]:
            flag=str(r[j]) if numeric(r[j]) is None else ''
            add('GBR',year,'BERD','ONS BERD 2024',code,r[1],r[j],6,'GBP',file,f'3!{get_column_letter(j+1)}{i}',
                'Business R&D by performer main industry; UK SIC 2007',flag,isic,
                '[c] confidential; [x] nil, unavailable or too small to display: neither converted to zero. Annual sample rotation limits growth interpretation.')
    book.close()
    file='government_industry_raw/ons_gva_2026q2.xlsx'; book=load_workbook(DATA/file,data_only=True,read_only=True); s=book['1']
    heads=list(s.iter_rows(min_row=5,max_row=5,values_only=True))[0]
    # Keep disjoint section totals and detailed manufacturing only.
    aliases={'Total GVA':'_T','CA':'10,11,12','CB':'13,14,15','CC':'16,17,18','CM':'31,32,33'}
    for i,r in enumerate(s.values,1):
        if r[0] not in (2023,2024,2025): continue
        for j,head in enumerate(heads):
            code=str(head).split('\n')[0].strip()
            isic=aliases.get(code,code if re.fullmatch('[A-T]',code) or code in [str(n) for n in range(19,31)] else '')
            if not isic: continue
            add('GBR',r[0],'GVA','ONS current-price GVA',code,head,r[j],6,'GBP',file,f'1!{get_column_letter(j+1)}{i}',
                'National accounts GVA; current basic prices; UK SIC 2007', 'short-term output proxy' if r[0]==2025 else '',isic,
                '2025 uses short-term output proxies; 1997–2024 benchmarked to supply-use tables. Published million-pound cells are rounded.')
    book.close()
    # STAN provides harmonised detail, not a direct BOK download. Keep its estimation flags.
    for i,r in enumerate(read_csv(DATA/'industry_raw/oecd_stan_history.csv'),1):
        if r['REF_AREA']!='KOR' or r['TIME_PERIOD'] not in ('2023','2024','2025'): continue
        assert r['MEASURE']=='B1G' and r['PRICE_BASE']=='V' and r['UNIT_MEASURE']=='XDC' and r['UNIT_MULT']=='6'
        try:
            classification.coverage(r['ACTIVITY']); isic=r['ACTIVITY']
        except ValueError:
            isic=''  # Special analytical aggregates remain native observations only.
        add('KOR',int(r['TIME_PERIOD']),'GVA','OECD STAN 2025',r['ACTIVITY'],classification.labels.get(r['ACTIVITY'],r['ACTIVITY']),r['OBS_VALUE'],6,'KRW',
            'industry_raw/oecd_stan_history.csv',f'record {i}','OECD STAN harmonised GVA; ISIC4; current national currency',
            '; '.join(k+'='+r[k] for k in ['OBS_STATUS','EST_METHOD'] if r[k]),isic,
            'BOK national accounts release checked separately; these detailed values are OECD STAN observations. E / POST entries are estimates, not direct official observations.')
    file='government_industry_raw/bea_value_added.xlsx'; book=load_workbook(DATA/file,data_only=True,read_only=True); s=book['TVA105-A']
    headers=list(s.iter_rows(min_row=8,max_row=8,values_only=True))[0]
    assert s['A2'].value=='[Millions of dollars]'
    for i,r in enumerate(s.values,1):
        if not 9<=i<=105: continue
        for j,year in enumerate(headers):
            if str(year) in ('2023','2024','2025'):
                add('USA',int(year),'GVA','BEA value added',r[0],r[1],r[j],6,'USD',file,f'TVA105-A!{get_column_letter(j+1)}{i}',
                    'BEA GDP by industry; NAICS; private-industry rows exclude government',note='National NAICS industries retained; no exact ISIC equivalence assumed. GDP total is not a basic-price A–T denominator.')
    book.close()
    file='government_industry_raw/ncses_berd_2024_tables.zip'
    book=load_workbook(BytesIO(ZipFile(DATA/file).read('nsf27300-tab065.xlsx')),data_only=True,read_only=True); s=book.worksheets[0]
    assert 'Adjusted domestic' in s['I4'].value and s['I6'].value==778069
    for i,r in enumerate(s.values,1):
        if not 6<=i<=78: continue
        add('USA',2024,'BERD','NCSES BERD 2024, Table 65',str(r[1]).removesuffix('.0'),r[0],r[8],6,'USD',file,
            f'nsf27300-tab065.xlsx; I{i}; flag J{i}',
            'Adjusted domestic R&D; nonfarm for-profit companies with >=10 employees; NAICS 2017',str(r[9] or '').strip(),
            note='International adjustment removes depreciation and adds R&D capital. Industry assigned by largest domestic R&D business segment, with payroll fallback. National classification and survey coverage differ from whole-economy ISIC BERD.')
    book.close()
    file='government_industry_raw/msit_rd_2024.hwpx'; z=ZipFile(DATA/file)
    root=ET.fromstring(z.read('Contents/section5.xml'))
    tables=[t for t in root.findall('.//{*}tbl') if len(t.findall('{*}tr'))==34 and '1,066,988' in ''.join(t.itertext())]
    assert len(tables)==1
    for i,tr in enumerate(tables[0].findall('{*}tr'),1):
        cells=[''.join(tc.itertext()).strip() for tc in tr.findall('{*}tc')]
        if i==1: assert cells==['산업','2023년','2024년','전년대비']; continue
        assert len(cells)==4
        for j,year in [(1,2023),(2,2024)]:
            add('KOR',year,'BERD','MSIT R&D Survey 2024',f'T18_{i}',cells[0],cells[j],8,'KRW',file,
                f'printed p.38; Table 18; row {i}; {year}; Contents/section5.xml',
                'Business-enterprise R&D; Korean national industries',note='Original Korean industry labels retained. Medical/precision/optical industry crosses ISIC group boundaries; no unsupported split.')
    file='government_industry_raw/nbs_rd_2025.html'; parser=Tables(); parser.feed((DATA/file).read_text('utf-8'))
    tables=[t for t in parser.tables if any('23228.5' in c for r in t for c in r)]
    assert len(tables)==2 and tables[0]==tables[1], 'Expected identical desktop/mobile copies of Appendix Table 1'
    for i,r in enumerate(tables[0],1):
        if len(r)<2 or numeric(r[1]) is None: continue
        add('CHN',2025,'BERD','NBS 2025 R&D communiqué',f'APP1_{i}',r[0],r[1],8,'CNY',file,f'Appendix Table 1; row {i}; expenditure column',
            'Industrial enterprises above designated size; annual main-business revenue >=20 million CNY',
            note='Not all-business BERD. Excludes smaller industrial enterprises and nonindustrial businesses. Industry R&D / revenue intensity is not R&D / GVA.')
    # Existing Eustat/RIE archives are already independently extracted with source locators.
    for r in read_csv(DATA/'rd_industry_components.csv'):
        if (r['iso3'],r['year']) not in [('SGP','2023'),('ES-PV','2024')] or r['source'] not in ['SGP_RIE','EUSTAT_NATIVE']: continue
        add(r['iso3'],int(r['year']),'BERD',r['source'],r['activity_code'],r['activity_label'],r['value_reported'],int(r['unit_multiplier']),r['currency'],
            'rd_industry_raw/'+r['source_file'],r['source_sheet']+'!'+r['source_cell'] if r['source_sheet'] else 'record '+r['raw_record'],r['scope'],
            '; '.join(r[k] for k in ['OBS_STATUS','CONF_STATUS'] if r.get(k)),note=r['eligibility_note'])
    for r in read_csv(DATA/'broad_sector_components.csv'):
        if r['iso3']!='ES-PV' or r['year'] not in ['2023','2024','2025']: continue
        add('ES-PV',int(r['year']),'GVA','Eustat A38',r['activity_code'],r['activity_label'],r['value_reported'],3,'EUR',
            'broad_sector_raw/'+r['source_file'],'record '+r['raw_record'],'Regional national accounts; A38; current basic prices',
            'provisional' if r['year']=='2025' else r['obs_status'],note=r['mapping_note'])
    # Latest verified Chinese detailed nominal VA remains the 2023 input-output table.
    for r in read_csv(DATA/'china_nbs_io_value_added.csv'):
        add('CHN',int(r['year']),'GVA','NBS input-output 2023',r['activity_code_native'],r['activity_label_native'],r['value_reported'],int(r['unit_multiplier']),'CNY',
            'industry_raw/'+r['source_file'],r['source_sheet']+'!'+r['value_cell'],
            'Native input-output product sectors; producers prices',note='Not harmonised ISIC industries; no newer verified detailed nominal replacement.')
    for file in used:
        folder,name=file.split('/',1); assert digest(DATA/file)==manifests[folder][name]['sha256'],file
    assert digest(DATA/'rd_industry_raw/wb_exchange_history.json')==manifests['rd_industry_raw']['wb_exchange_history.json']['sha256']
    write('government_industry_observations.csv',rows)
    return rows


def aligned(rows,targets):
    """Aggregate observed disjoint ISIC sets; no confidential-value residuals."""
    cl=Classification(DATA/'rd_industry_raw/oecd_berd_structure.xml'); blocks=defaultdict(list)
    for r in rows:
        if r['isic_code']: blocks[r['iso3'],r['year'],r['metric']].append(r)
    result={}
    for key,items in blocks.items():
        def classes(code):
            if re.fullmatch(r'\d{2}(,\d{2})*',code):
                divisions={int(d) for d in code.split(',')}; return frozenset(c for c in cl.classes if int(c[1:3]) in divisions)
            return cl.coverage(code)
        available=[dict(value=r['amount_local'],rounding=.5*10**r['unit_multiplier'],classes=classes(r['isic_code']),terms={r['activity_code']:1}) for r in items if r['amount_local'] is not None]
        cells={r['activity_code']:r for r in items}; total=next((r['amount_local'] for r in items if r['isic_code']=='_T'),None)
        for gid,target in targets.items():
            found=cover(target,available)
            if not found:
                result[(*key,gid)]={'amount':None,'usd':None,'currency':items[0]['currency'],'coverage':'unavailable','share':None,
                    'denominator':total if key[2]=='BERD' else None,'scope':items[0]['scope'],'source':items[0]['source'],
                    'terms':{},'missing':';'.join(sorted(target)),'flags':'','note':'No disjoint assignable observation in this source block.','cells':[]}
                continue
            selected=[cells[c] for c in found['terms']]; amount=found['value']; rate=selected[0]['local_per_usd']
            full=found['classes']==target
            # GVA denominator requires explicit A–T coverage. R&D reported total can include U.
            denominator=total if key[2]=='BERD' else None
            result[(*key,gid)]={'amount':amount,'usd':amount/rate if rate else None,'currency':selected[0]['currency'],
                'coverage':'complete' if full else 'partial','share':amount/denominator*100 if denominator else None,
                'denominator':denominator,'scope':selected[0]['scope'],'source':selected[0]['source'],
                'terms':found['terms'],'missing':';'.join(sorted(target-found['classes'])),
                'flags':'; '.join(sorted({r['flags'] for r in selected if r['flags']})),
                'note':' '.join(sorted({r['note'] for r in selected})), 'cells':selected}
        if key[2]=='GVA':
            group_rows=[result[(*key,g)] for g in targets if (*key,g) in result]
            if len(group_rows)==len(targets) and all(r['coverage']=='complete' for r in group_rows):
                subtotal=sum(r['amount'] for r in group_rows)
                # Total may include U. Use the complete A–T subtotal, and record discrepancy.
                if total and abs(total-subtotal)<=max(2e7,abs(total)*1e-5):
                    for r in group_rows:r.update(denominator=subtotal,share=r['amount']/subtotal*100)
    return result


if __name__=='__main__':
    observations=extract()
    (DATA/'government_industry_explorer.json').write_text(json.dumps({'builtUTC':datetime.now(timezone.utc).isoformat(),'rows':observations},ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
    print('Extracted',len(observations),'official/source-native observations')
