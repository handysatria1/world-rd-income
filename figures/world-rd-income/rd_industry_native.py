"""Conservative, explicitly partial allocations of published native R&D branches.

These are reviewed branch-label containments, not invented exact ISIC class sets.
See RD_INDUSTRY.md for the source definitions and unresolved mixed branches.
"""
from decimal import Decimal

from openpyxl import load_workbook
from basque_rd import px_rows
from sector_field_rd import FLAGS

BASQUE = {'060': 'LMT', '080': 'LMT', '100': 'LMT', '120': 'LMT',
          '140': 'MHT', '160': 'MHT', '180': 'MHT', '200': 'MHT', '220': 'MHT', '260': 'MHT',
          '320': 'OTH', '340': 'KIS', '360': 'KIS'}
SINGAPORE = {'RIE_09': 'MHT', 'RIE_12': 'LMT', 'RIE_14': 'KIS', 'RIE_16': 'KIS', 'RIE_17': 'LIS'}
SCOPE = {'EUSTAT_NATIVE': 'companies + PNPI', 'SGP_RIE': 'BERD; science and technology only'}
CRITERIA = 'main activity; reviewed native branch labels; partial class coverage'


def mapping_note(source, code):
    if source == 'EUSTAT_NATIVE':
        if code in BASQUE:
            return 'Branch-label containment only; exact class coverage not established; allocated from 2003.'
        return {'000': 'Reported total; not an additive branch.',
                '020': 'Agriculture/mining/energy mixes OTH and UTL.',
                '040': 'Chemistry/refining mixes MHT and LMT.',
                '240': 'Precision material may mix C26 and C32; no verified split.',
                '280': 'Residual manufacturing branch has no published code-level bridge.',
                '380': 'Other business activities may mix M and N.',
                '400': 'Other services span KIS and LIS.'}[code]
    if code in SINGAPORE:
        return 'Reviewed SSIC2020 industry-cluster label; partial group, not an exact class crosswalk.'
    return {'RIE_TOTAL': 'Historical private-sector total; no annual industry decomposition.',
            'RIE_05': 'Primary industries/construction: utilities boundary not documented in appendix.',
            'RIE_06': 'Manufacturing parent overlaps its six clusters; not added to them.',
            'RIE_07': 'Biomedical manufacturing may mix C21/C26 and C325 medical supplies.',
            'RIE_08': 'Chemicals cluster may include petroleum refining; no verified split.',
            'RIE_10': 'Precision engineering mixes machinery, metal/plastic components and repair.',
            'RIE_11': 'Transport engineering mixes manufacturing and C33 repair.',
            'RIE_13': 'Services parent overlaps its five branches; not added to them.',
            'RIE_15': 'Financial/other business activities may mix K/M and L/N.',
            'RIE_18': 'Other services may mix KIS and LIS.',
            'RIE_19': 'Reported total; not an additive branch.'}[code]


def base(iso, year, source, code, label, value, multiplier, decimals, file, record, sheet='', cell='', flag=''):
    group = (BASQUE if source == 'EUSTAT_NATIVE' else SINGAPORE).get(code, '')
    eligible = bool(group) and value is not None and not flag and (source != 'EUSTAT_NATIVE' or year >= 2003)
    return {'iso3': iso, 'economy': 'Basque Country' if iso == 'ES-PV' else 'Singapore', 'year': year,
            'source': source, 'scope': SCOPE[source], 'criteria': CRITERIA, 'activity_code': code, 'activity_label': label,
            'value_reported': value, 'unit_multiplier': multiplier, 'currency': 'EUR' if iso == 'ES-PV' else 'SGD',
            'price_base': 'V', 'source_decimals': decimals,
            'amount_local': float(Decimal(str(value)) * 10 ** multiplier) if value is not None else None,
            'availability': 'available' if value is not None else 'missing_source_value',
            'aggregation_eligible': eligible, 'eligibility_note': mapping_note(source, code), 'mapping_group': group,
            'rounding_local': .5 * 10 ** (multiplier - decimals), **{k: flag if k == 'OBS_STATUS' else '' for k in FLAGS},
            'source_file': file, 'raw_record': record, 'source_sheet': sheet, 'source_cell': cell}


def native_components(raw):
    rows = []
    for i, (coords, labels, value, flag, _) in enumerate(px_rows(raw / 'eustat_rd_industry.json'), 1):
        year, code = int(coords['periodo']), coords['rama de actividad']
        if year >= 2000:
            assert coords['naturaleza'] == '10'
            rows.append(base('ES-PV', year, 'EUSTAT_NATIVE', code, labels['rama de actividad'], value, 3, 0,
                             'eustat_rd_industry.json', i, flag=flag))
    book = load_workbook(raw / 'singapore_rie_2023.xlsx', read_only=True, data_only=True)
    assert 'List of Tables (2023)' in book.sheetnames and book['Table 5.1']['A37'].value == 2023
    sheet = book['Table 3.1']
    assert sheet['J3'].value == 'Total' and 'R&D Expenditure' in sheet['J4'].value and '$ million' in sheet['J4'].value
    for i in range(5, 20):
        label, value = sheet[f'A{i}'].value.strip(), sheet[f'J{i}'].value
        assert isinstance(value, (int, float)) and value >= 0
        rows.append(base('SGP', 2023, 'SGP_RIE', f'RIE_{i:02}', label, value, 6, 2,
                         'singapore_rie_2023.xlsx', i, 'Table 3.1', f'J{i}'))
    assert sheet['J19'].value == book['Table 5.1']['I37'].value
    history = book['Table 5.1']
    assert history['I3'].value == 'Private Sector R&D Expenditure ($m)'
    for i in range(14, 38):
        year, value = history[f'A{i}'].value, history[f'I{i}'].value
        assert year == 2000 + i - 14 and isinstance(value, (int, float)) and value >= 0
        # The historical sheet retains more precision than the 2023 industry table.
        decimals = max(0, -Decimal(str(value)).as_tuple().exponent)
        rows.append(base('SGP', year, 'SGP_RIE', 'RIE_TOTAL', 'Private-sector R&D total (time series)', value, 6, decimals,
                         'singapore_rie_2023.xlsx', i, 'Table 5.1', f'I{i}'))
    book.close()
    return rows


def aggregate_native(cells, groups):
    result = {}
    for group in groups:
        selected = {c: r for c, r in cells.items() if r['aggregation_eligible'] and r['mapping_group'] == group}
        result[group] = {'value': sum(r['amount_local'] for r in selected.values()),
                         'rounding': sum(r['rounding_local'] for r in selected.values()),
                         'terms': dict.fromkeys(selected, 1), 'classes': frozenset()} if selected else None
    return result
