"""Independently audit released cells, signed class vectors, exact joins and exports."""
import json
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from basque_rd import px_rows
from industry_data import read_csv, digest

DATA = Path(__file__).parent / 'data'
RAW = DATA / 'rd_industry_raw'
FLAGS = ['OBS_STATUS', 'OBS_STATUS_2', 'OBS_STATUS_3', 'AUX_OBS_STATUS', 'AUX_OBS_STATUS_2', 'AUX_OBS_STATUS_3', 'CONF_STATUS']
GROUPS = ['MHT', 'LMT', 'KIS', 'LIS', 'UTL', 'OTH']


def close(a, b):
    if a in ['', None] or b in ['', None]:
        assert a in ['', None] and b in ['', None], (a, b)
    else:
        assert math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-4), (a, b)


def verify():
    report = json.loads((DATA / 'rd_industry_validation.json').read_text('utf-8'))
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    assert digest(RAW / 'manifest.json') == report['source_manifest_sha256']
    for file, meta in manifest.items():
        assert digest(RAW / file) == meta['sha256']
    for file, sha in {**report['input_sha256'], **report['output_sha256']}.items():
        assert digest(DATA / file) == sha, file
    xml = ET.parse(RAW / 'oecd_berd_structure.xml')
    catalog = next(c for c in xml.findall('.//{*}Codelist') if c.get('id') == 'CL_ACTIVITY_ISIC4')
    leaves = {c.get('id') for c in catalog.findall('{*}Code') if re.fullmatch('[A-U][0-9]{4}', c.get('id'))}
    def prefixes(*parts):
        return {c for c in leaves if any(c.startswith(p) for p in parts)}
    # Reviewed aggregate semantics, independent of the production expression parser.
    explicit = {'_T': leaves, 'GTN': prefixes(*'GHIJKLMN'), 'GTU': prefixes(*'GHIJKLMNOPQRSTU'),
                'OTU': prefixes(*'OPQRSTU'), 'STU': prefixes(*'STU'), 'M_N': prefixes('M', 'N'),
                'O_P': prefixes('O', 'P'), 'D_E': prefixes('D', 'E'), 'D35_E36': prefixes('D35', 'E36'),
                'E37T39': prefixes('E37', 'E38', 'E39'), 'J58T60': prefixes('J58', 'J59', 'J60'),
                'J59_60': prefixes('J59', 'J60'), 'Q87_88': prefixes('Q87', 'Q88'), 'G4651_4652': prefixes('G4651', 'G4652'),
                'C10T12': prefixes('C10', 'C11', 'C12'), 'C13T15': prefixes('C13', 'C14', 'C15'),
                'C16T18': prefixes('C16', 'C17', 'C18'), 'C25T30': prefixes('C25', 'C26', 'C27', 'C28', 'C29', 'C30'),
                'C10_11': prefixes('C10', 'C11'), 'C241_2431': prefixes('C241', 'C2431'), 'C242_2432': prefixes('C242', 'C2432')}
    class_sets = {}
    # Native assignments are label-level containments, never full class vectors.
    native_groups = {'EUSTAT_NATIVE': {'060': 'LMT', '080': 'LMT', '100': 'LMT', '120': 'LMT',
                                      '140': 'MHT', '160': 'MHT', '180': 'MHT', '200': 'MHT', '220': 'MHT', '260': 'MHT',
                                      '320': 'OTH', '340': 'KIS', '360': 'KIS'},
                     'SGP_RIE': {'RIE_09': 'MHT', 'RIE_12': 'LMT', 'RIE_14': 'KIS', 'RIE_16': 'KIS', 'RIE_17': 'LIS'}}
    for r in read_csv(DATA / 'rd_industry_mapping.csv'):
        if r['source'] != 'OECD_RDS':
            expected = native_groups[r['source']].get(r['activity_code'], '')
            assert not r['isic4_classes'] and r['group_memberships'] == expected
            assert (r['wholly_within_one_group'] == 'True') == bool(expected)
            continue
        code = r['activity_code']
        expected = explicit.get(code)
        if expected is None:
            assert re.fullmatch('[A-U][0-9]{0,4}', code), code
            expected = prefixes(code)
        assert expected and set(r['isic4_classes'].split(';')) == expected, code
        class_sets[code] = expected
        assert (r['contains_U'] == 'True') == bool(expected & prefixes('U'))
    targets = {'MHT': prefixes(*['C' + str(d) for d in [20, 21, 26, 27, 28, 29, 30]]),
               'LMT': prefixes(*['C' + str(d) for d in [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 23, 24, 25, 31, 32, 33]]),
               'KIS': prefixes(*'JKMP'), 'LIS': prefixes(*'GHILNOQRST'), 'UTL': prefixes(*'DE'), 'OTH': prefixes(*'ABF')}
    raw = read_csv(RAW / 'oecd_berd_industry.csv')
    basque = list(px_rows(RAW / 'eustat_rd_industry.json'))
    rie = load_workbook(RAW / 'singapore_rie_2023.xlsx', read_only=True, data_only=True)
    components = read_csv(DATA / 'rd_industry_components.csv')
    cells = {}
    for r in components:
        record = int(r['raw_record']) - 1
        if r['source'] == 'OECD_RDS':
            s = raw[record]
            assert (s['REF_AREA'], s['TIME_PERIOD'], s['ACTIVITY']) == (r['iso3'], r['year'], r['activity_code'])
            assert s['CURRENCY'] == r['currency'] and s['UNIT_MULT'] == r['unit_multiplier'] and s['DECIMALS'] == r['source_decimals']
            for f in FLAGS:
                assert r[f] == s[f]
            statuses = {s[f] for f in FLAGS[:3]}
            aux = {s[f] for f in FLAGS[3:6]}
            available = s['OBS_VALUE'] != '' and s['CONF_STATUS'] in ['', 'F'] and not statuses & {'K', 'O', 'M', 'L', 'H', 'Q'} and 'N2' not in aux
            amount = float(Decimal(s['OBS_VALUE']) * 10 ** int(s['UNIT_MULT'])) if available else None
            close(r['value_reported'], s['OBS_VALUE'])
            assert (r['aggregation_eligible'] == 'True') == (available and 'W' not in statuses and 'O2' not in aux)
        elif r['source'] == 'EUSTAT_NATIVE':
            coords, _, value, flag, _ = basque[record]
            assert (coords['periodo'], coords['rama de actividad']) == (r['year'], r['activity_code'])
            assert r['OBS_STATUS'] == flag and r['currency'] == 'EUR'
            close(r['value_reported'], value)
            amount = None if value is None else value * 1000
            assert (r['aggregation_eligible'] == 'True') == (r['activity_code'] in native_groups['EUSTAT_NATIVE'] and value is not None and not flag and int(r['year']) >= 2003)
        else:
            assert r['source'] == 'SGP_RIE' and r['iso3'] == 'SGP' and r['currency'] == 'SGD'
            assert r['source_file'] == 'singapore_rie_2023.xlsx'
            s = rie[r['source_sheet']]
            value = s[r['source_cell']].value
            close(r['value_reported'], value)
            amount = float(Decimal(str(value)) * 1_000_000)
            if r['activity_code'] == 'RIE_TOTAL':
                assert r['source_sheet'] == 'Table 5.1' and r['source_cell'] == f'I{record + 1}'
                assert int(r['year']) == s[f'A{record + 1}'].value
            else:
                assert r['year'] == '2023' and r['source_sheet'] == 'Table 3.1' and 5 <= record + 1 <= 19
                assert r['activity_code'] == f'RIE_{record + 1:02}' and r['source_cell'] == f'J{record + 1}'
                assert r['activity_label'] == s[f'A{record + 1}'].value.strip()
            assert (r['aggregation_eligible'] == 'True') == (r['activity_code'] in native_groups['SGP_RIE'])
            assert all(not r[f] for f in FLAGS)
        close(r['amount_local'], amount)
        key = r['iso3'], r['year'], r['activity_code']
        assert key not in cells
        cells[key] = r
    rie.close()
    fx = {(r['iso3'], r['year']): r for r in read_csv(DATA / 'rd_industry_fx.csv')}
    fx_raw = json.loads((RAW / 'wb_exchange_history.json').read_bytes())[1]
    for r in fx.values():
        if r['currency'] == 'USD':
            close(r['local_per_usd'], 1)
        elif r['local_per_usd']:
            s = fx_raw[int(r['raw_record']) - 1]
            assert s['date'] == r['year']
            assert s['countryiso3code'] == r['fx_reference_area'] == ('ESP' if r['currency'] == 'EUR' else r['iso3'])
            close(r['local_per_usd'], s['value'])
        else:
            assert r['availability'] == 'missing_conversion'
    annual = read_csv(DATA / 'rd_industry_annual.csv')
    aindex, sums, used = {}, defaultdict(float), defaultdict(set)
    for r in annual:
        key = r['iso3'], r['year']
        terms = json.loads(r['source_terms_json'])
        aindex[*key, r['group']] = r
        vector = Counter()
        value = 0
        native = r['rd_source'] != 'OECD_RDS'
        for code, coefficient in terms.items():
            s = cells[*key, code]
            assert s['aggregation_eligible'] == 'True' and s['source'] == r['rd_source']
            value += coefficient * float(s['amount_local'])
            if native:
                assert coefficient == 1 and native_groups[r['rd_source']][code] == r['group']
                assert code not in used[key]
                used[key].add(code)
            else:
                for c in class_sets[code]:
                    vector[c] += coefficient
        assert all(w in [0, 1] for w in vector.values())
        assigned = {c for c, w in vector.items() if w}
        assert assigned <= targets[r['group']] and not assigned & prefixes('U')
        assert not assigned & used[key]
        used[key].update(assigned)
        assert set(filter(None, r['covered_isic4_classes'].split(';'))) == assigned
        assert set(filter(None, r['missing_isic4_classes'].split(';'))) == (set() if native else targets[r['group']] - assigned)
        if native:
            assert not assigned and r['group_complete'] == 'False'
            assert r['class_coverage_basis'] == 'native branch-label containment; exact classes unresolved'
        assert (r['group_complete'] == 'True') == (assigned == targets[r['group']])
        close(r['assigned_rd_local'], value if terms else None)
        if terms:
            assert value >= 0
            sums[key] += value
        conversion = float(fx[key]['local_per_usd']) if key in fx and fx[key]['local_per_usd'] else None
        close(r['assigned_rd_usd'], value / conversion if terms and conversion else None)
        close(r['group_rd_total_usd'], value / conversion if r['group_complete'] == 'True' and conversion else None)
    audits = read_csv(DATA / 'rd_industry_coverage.csv')
    for r in audits:
        key = r['iso3'], r['year']
        if r['native_leaf_sum_local']:
            source_rows = [s for s in components if (s['iso3'], s['year'], s['source']) == (*key, r['rd_source'])]
            leaf_codes = [f'{n:03}' for n in [20,40,60,80,100,120,140,160,180,200,220,240,260,280,320,340,360,380,400]] if r['iso3'] == 'ES-PV' else [f'RIE_{n:02}' for n in [5,7,8,9,10,11,12,14,15,16,17,18]]
            leaf_values = [float(s['amount_local']) for s in source_rows if s['activity_code'] in leaf_codes]
            assert len(leaf_values) == len(leaf_codes)
            close(r['native_leaf_sum_local'], sum(leaf_values))
            close(r['native_total_minus_leaves_local'], float(r['reported_total_local']) - sum(leaf_values))
        if r['assigned_local']:
            close(r['assigned_local'], sums[key])
        if r['reported_total_local']:
            total = float(r['reported_total_local'])
            original = cells[*key, r['total_activity_code']]
            close(total, original['amount_local'])
            assert original['source_file'] == r['total_source_file'] and original['raw_record'] == r['total_raw_record']
            assert original['source_sheet'] == r['total_source_sheet'] and original['source_cell'] == r['total_source_cell']
            close(r['unallocated_local'], total - sums[key])
            if float(r['unallocated_local']) < 0:
                assert r['coverage_status'] == 'negative_reconciliation_remainder'
                assert not r['assigned_share_percent']
        for g in GROUPS:
            a = aindex[*key, g]
            close(a['assigned_share_reported_rd_percent'], float(a['assigned_rd_local']) / float(r['reported_total_local']) * 100
                  if a['assigned_rd_local'] and r['assigned_share_percent'] else None)
    def index(file):
        return {(r['iso3'], r['year'], r['group']): r for r in read_csv(DATA / file)}
    gva, emp, prod, exports = [index(f) for f in ['broad_sector_annual.csv', 'sector_employment.csv', 'sector_productivity.csv', 'sector_exports.csv']]
    joined = read_csv(DATA / 'rd_economy_joined.csv')
    jindex = {}
    for r in joined:
        key = r['iso3'], r['year'], r['group']
        jindex[key] = r
        for field, value in aindex[key].items():
            assert r[field] == value
        for column, table, field in [('gva_usd', gva, 'value_usd'), ('employed_persons', emp, 'persons'),
                                     ('gva_per_person_usd_thousand', prod, 'gva_per_person_usd_thousand'),
                                     ('goods_exports_usd', exports, 'value_usd')]:
            s = table.get(key, {})
            close(r[column], s.get(field) if s.get('coverage_status') == 'available' else None)
        rd = r['group_rd_total_usd'] if r['coverage_status'] not in ['negative_reconciliation_remainder', 'nonpositive_reported_total'] else ''
        for col, denom, scale in [('rd_percent_sector_gva', 'gva_usd', 100), ('rd_usd_per_sector_worker', 'employed_persons', 1)]:
            expected = float(rd) / float(r[denom]) * scale if rd and r[denom] and float(r[denom]) > 0 else None
            close(r[col], expected)
    contexts = read_csv(DATA / 'rd_economy_context.csv')
    prior = {(r['iso3'], r['year']): r for r in read_csv(DATA / 'rd_income_exports_annual.csv')}
    nominal = read_csv(DATA / 'rd_nominal_annual.csv')
    for r in contexts:
        key = r['iso3'], r['year']
        for k, v in prior.get(key, {}).items():
            assert r[k] == v, (key, k)
        for src in ['oecd', 'wdi', 'uis', 'eustat']:
            if r[f'gerd_{src}_nominal_record']:
                s = nominal[int(r[f'gerd_{src}_nominal_record']) - 1]
                assert (s['iso3'], s['year']) == key and s['unit'] == 'current US dollars'
                close(r[f'gerd_{src}_usd'], s['amount'])
    view = json.loads((DATA / 'rd_industry_explorer.json').read_text('utf-8'))
    for r in view['rows']:
        native_cells = {s['activity_code']: s for s in components if s['source'] != 'OECD_RDS' and s['iso3'] == r['iso'] and s['year'] == str(r['year'])} if r['iso'] in ['SGP', 'ES-PV'] else {}
        assert {s['code'] for s in r['nativeRows']} == set(native_cells)
        for n in r['nativeRows']:
            s = native_cells[n['code']]
            close(n['amountLocal'], s['amount_local'])
            assert n['label'] == s['activity_label'] and n['currency'] == s['currency'] and n['sourceFile'] == s['source_file']
            assert n['group'] == s['mapping_group'] and n['eligible'] == (s['aggregation_eligible'] == 'True')
        for i, group in enumerate(GROUPS):
            j = jindex[r['iso'], str(r['year']), group]
            for col, field in [('assigned', 'assigned_rd_usd'), ('assignedLocal', 'assigned_rd_local'), ('shares', 'assigned_share_reported_rd_percent'),
                               ('intensity', 'rd_percent_sector_gva'), ('perWorker', 'rd_usd_per_sector_worker'), ('gvaUSD', 'gva_usd'),
                               ('gvaShares', 'gva_share_percent'), ('persons', 'employed_persons'), ('employmentShares', 'employment_share_percent'),
                               ('productivity', 'gva_per_person_usd_thousand'), ('exportUSD', 'goods_exports_usd'), ('exportShares', 'goods_exports_share_percent')]:
                close(r[col][i], j[field])
            assert r['complete'][i] == (j['group_complete'] == 'True')
        if r['stackAvailable']:
            close(sum(v or 0 for v in r['shares']) + r['remainingShare'], 100)
        if r['status'] == 'negative_reconciliation_remainder':
            assert not r['stackAvailable'] and all(v is None for v in r['intensity'] + r['perWorker'])
    # Selected real-world boundary cases, not interpolated or silently harmonized.
    singapore_last = max(int(r['year']) for r in components if r['iso3'] == 'SGP' and r['amount_local'])
    assert not any(r['assigned_rd_local'] for r in annual if r['iso3'] == 'SGP' and int(r['year']) > singapore_last)
    assert not any(r['group_complete'] == 'True' for r in annual if r['iso3'] == 'ES-PV')
    assert all(not r['assigned_rd_local'] for r in annual if r['iso3'] == 'SGP' and 2014 <= int(r['year']) <= 2022)
    assert all(r['group_complete'] == 'False' for r in annual if r['rd_source'] == 'SGP_RIE')
    close(aindex['SGP', '2023', 'KIS']['assigned_rd_local'], 2316260000)
    close(aindex['SGP', '2023', 'LIS']['assigned_rd_local'], 1438530000)
    close(aindex['SGP', '2022', 'MHT']['reported_rd_total_local'], 8130090000)
    close(aindex['SGP', '2023', 'MHT']['reported_rd_total_local'], 8955990000)
    close(aindex['ES-PV', '2022', 'MHT']['assigned_rd_local'], 321839000)
    close(aindex['ES-PV', '2024', 'KIS']['assigned_rd_local'], 726150000)
    close(aindex['USA', '2022', 'MHT']['assigned_rd_local'], 335921000000)
    close(aindex['CHN', '2022', 'MHT']['assigned_rd_local'], 1340280286000)
    workbook = load_workbook(DATA / 'rd_industry_economy.xlsx', read_only=True, data_only=True)
    count = 0
    for sheet in workbook:
        rows = read_csv(DATA / (sheet.title + '.csv'))
        values = sheet.iter_rows(values_only=True)
        assert list(next(values)) == list(rows[0])
        n = 0
        for n, cells_ in enumerate(values, 1):
            for a, b in zip(cells_, rows[n - 1].values()):
                if isinstance(a, (int, float)) and not isinstance(a, bool):
                    close(a, b)
                else:
                    assert ('' if a is None else str(a)) == b
        assert n == len(rows)
        count += n
    workbook.close()
    result = {'verification': 'passed', 'built_utc': report['built_utc'], 'source_cells_checked': len(components),
              'signed_group_expressions_checked': len(annual), 'exact_join_rows_checked': len(joined),
              'embedded_economy_years_checked': len(view['rows']), 'workbook_rows_checked': count,
              'validation_sha256': digest(DATA / 'rd_industry_validation.json')}
    (DATA / 'rd_industry_verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    verify()
