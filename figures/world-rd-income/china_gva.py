"""China-specific TiVA sources and native NBS input-output value added."""
import json
import math
import re

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

NBS = 'https://data.stats.gov.cn/dg/website'
CHINA_SOURCES = {
    'oecd_tiva_structure_resolved.xml': 'https://sdmx.oecd.org/sti-public/rest/v1/dataflow/OECD.STI.PIE/DSD_TIVA_MAINLV@DF_MAINLV/1.1?references=all',
    'oecd_tiva_china_valu.csv': 'https://sdmx.oecd.org/sti-public/rest/v1/data/OECD.STI.PIE,DSD_TIVA_MAINLV@DF_MAINLV,1.1/VALU.CHN..W.USD.A?startPeriod=2000&endPeriod=2025&format=csvfile',
    'oecd_icio_2025_annex.pdf': 'https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2025/ICIO2025annex.pdf',
    'oecd_icio_2025_readme.xlsx': 'https://webfs-sti.oecd.org/files/STI-PIE/ICIO/2025/ReadMe_ICIO_small.xlsx',
    'nbs_classification_2017.pdf': 'https://www.stats.gov.cn/sj/tjbz/gmjjhyfl/202501/P020250116506795831658.pdf',
    'nbs_io_catalog.json': NBS + '/publicrelease/web/external/queryPbLibCatalogTree?code=15',
}


def obtain_nbs(obtain):
    """Resolve the selected 2023 competitive table from NBS's public catalogue."""
    catalog = json.loads(obtain('nbs_io_catalog.json', CHINA_SOURCES['nbs_io_catalog.json']))
    assert catalog['success']
    years = catalog['data'][0]['children']
    year, = [r for r in years if r['name'] == '2023年投入产出表']
    table, = [r for r in year['children'] if r['name'] == '竞争型投入产出表']
    content = json.loads(obtain('nbs_io_2023_content.json', NBS + '/publicrelease/web/external/new/getHtmlContentTime?id=' + table['_id']))
    assert content['success'] and content['data']['pblib_name'] == '竞争型投入产出表'
    file, = json.loads(content['data']['file'])
    assert file['originalFileName'] == '2023年全国投入产出表.xlsx' and file['suffix'] == 'xlsx'
    # Use the public relative path, not the provider's internal absolutePath field.
    assert file['relativePath'].startswith('/publicrelease.pblib/pblibedit/upload/file/xlsx/')
    obtain('nbs_io_2023.xlsx', NBS + file['relativePath'])


def nbs_value_added(raw):
    """Extract native product-sector columns; no inferred ISIC correspondence."""
    book = load_workbook(raw / 'nbs_io_2023.xlsx', read_only=True, data_only=True)
    sheet, = book.worksheets
    matrix = list(sheet.values)
    assert matrix[0][0] == '2023年全国投入产出表'
    assert 'producers\' prices in 2023' in matrix[1][0] and matrix[2][0] == '单位：万元'
    row_index = {r[2]: i for i, r in enumerate(matrix) if len(r) > 2 and isinstance(r[2], str)}
    indices = {code: row_index[code] for code in ['VA001', 'VA002', 'VA003', 'VA004', 'TVA', 'TII', 'TI']}
    assert matrix[indices['TVA']][1] == '增加值合计'
    columns = [j for j, code in enumerate(matrix[5]) if isinstance(code, str) and re.fullmatch(r'\d{5}', code)]
    assert len(columns) == 211 and len({matrix[5][j] for j in columns}) == len(columns)
    rows = []
    for j in columns:
        code, label = matrix[5][j], matrix[4][j]
        assert code in row_index and matrix[row_index[code]][1] == label
        amounts = {c: matrix[i][j] for c, i in indices.items()}
        assert all(isinstance(v, (int, float)) and math.isfinite(v) for v in amounts.values())
        assert math.isclose(amounts['TVA'], sum(amounts[c] for c in ['VA001', 'VA002', 'VA003', 'VA004']), rel_tol=1e-10, abs_tol=1e-5)
        assert math.isclose(amounts['TI'], amounts['TII'] + amounts['TVA'], rel_tol=1e-10, abs_tol=1e-5)
        col = get_column_letter(j + 1)
        rows.append({'source': 'CHINA_NBS_IO', 'iso3': 'CHN', 'country': 'China', 'year': 2023,
                     'activity_code_native': code, 'activity_label_native': label,
                     'classification': 'NBS 2023 input-output product sectors', 'isic_division': '',
                     'mapping_status': 'native_classification_not_harmonised_to_ISIC',
                     'value_reported': amounts['TVA'], 'unit_reported': 'ten thousand yuan', 'unit_multiplier': 4,
                     'currency_code': 'CNY', 'value_national_currency': amounts['TVA'] * 10000,
                     'price_basis': 'current prices', 'valuation': "producers' prices",
                     'compensation_employees_reported': amounts['VA001'], 'net_production_taxes_reported': amounts['VA002'],
                     'depreciation_reported': amounts['VA003'], 'operating_surplus_reported': amounts['VA004'],
                     'intermediate_inputs_reported': amounts['TII'], 'total_inputs_reported': amounts['TI'],
                     'value_status': 'reported', 'source_file': 'nbs_io_2023.xlsx', 'source_sheet': sheet.title,
                     'value_cell': f'{col}{indices["TVA"] + 1}', 'label_cell': f'{col}5', 'code_cell': f'{col}6',
                     'component_cells': ';'.join(f'{col}{indices[c] + 1}' for c in ['VA001', 'VA002', 'VA003', 'VA004'])})
    book.close()
    return rows
