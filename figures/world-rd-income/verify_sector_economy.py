"""Independently verify archived source cells, mappings, joins, workbook and browser data."""
import json
import math
from pathlib import Path

from openpyxl import load_workbook
from basque_rd import px_rows
from industry_data import digest, read_csv

ROOT = Path(__file__).resolve().parent
DATA, RAW = ROOT / 'data', ROOT / 'data/sector_economy_raw'


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-11, abs_tol=1e-5), (a, b)


def verify():
    report = json.loads((DATA / 'sector_economy_validation.json').read_text('utf-8'))
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for file, info in manifest.items():
        assert digest(RAW / file) == info['sha256']
    for file, checksum in report['output_sha256'].items():
        assert digest(DATA / file) == checksum
    sources = {}
    for file in ['oecd_tim_employment.csv', 'oecd_btige_exports.csv']:
        sources[file] = read_csv(RAW / file)
    for file in ['eustat_employment.json', 'eustat_export_groups.json', 'eustat_exports_nace.json', 'eustat_export_sectors.json']:
        sources[file] = list(px_rows(RAW / file))
    components = read_csv(DATA / 'sector_economy_components.csv')
    by_code = {}
    for row in components:
        raw = sources[row['source_file']][int(row['raw_record']) - 1]
        if row['source_file'].endswith('.csv'):
            value, flag = raw['OBS_VALUE'], raw.get('OBS_STATUS', '')
            assert raw['REF_AREA'] == row['iso3'] and raw['TIME_PERIOD'] == row['year']
            assert raw.get('ACTIVITY', raw.get('PRODUCT')) == row['activity_code']
            assert raw['UNIT_MULT'] == row['unit_multiplier'] and raw['UNIT_MEASURE'] == row['unit']
        else:
            coords, labels, value, flag, _ = raw
            assert coords['periodo'] == row['year'] and row['activity_code'] in coords.values()
            assert int(row['unit_multiplier']) == (0 if row['metric'] == 'employment' else 3)
        assert (value is None or value == '') == (row['value_reported'] == '')
        if row['value_reported']:
            close(row['value_reported'], value)
        assert flag == row['obs_status']
        by_code[row['source_file'], row['iso3'], int(row['year']), row['activity_code']] = None if not row['value_reported'] else float(row['value_reported']) * 10 ** int(row['unit_multiplier'])

    def get(file, iso, year, code):
        return by_code.get((file, iso, year, code))

    annual = read_csv(DATA / 'sector_employment.csv')
    employment = {(r['iso3'], int(r['year']), r['group']): r for r in annual}
    mapping = {r['group']: r for r in read_csv(DATA / 'broad_sector_classification.csv')}
    for row in annual:
        expected_codes = mapping[row['group']]['eustat_a38_codes_from_2021' if row['iso3'] == 'ES-PV' else 'tiva_activity_codes'].split(';')
        if row['iso3'] == 'ES-PV' and int(row['year']) <= 2020 and row['group'] == 'MHT':
            expected_codes.remove('07')
        assert row['source_codes'].split(';') == expected_codes
        values = [get(row['source_file'], row['iso3'], int(row['year']), c) for c in expected_codes]
        if all(v is not None for v in values):
            close(row['persons'], sum(values))
        else:
            assert row['persons'] == ''
        if row['coverage_status'] == 'available':
            close(row['share_percent'], float(row['persons']) / float(row['grouped_total_persons']) * 100)
    gva = {(r['iso3'], int(r['year']), r['group']): r for r in read_csv(DATA / 'broad_sector_annual.csv')}
    products = read_csv(DATA / 'sector_productivity.csv')
    for row in products:
        key = row['iso3'], int(row['year']), row['group']
        if row['gva_per_person_usd_thousand']:
            close(row['gva_usd'], gva[key]['value_usd'])
            close(row['persons'], employment[key]['persons'])
            close(row['gva_per_person_usd_thousand'], float(gva[key]['value_usd']) / float(employment[key]['persons']) / 1000)
            assert gva[key]['coverage_status'] == employment[key]['coverage_status'] == 'available'
    exports = read_csv(DATA / 'sector_exports.csv')
    export_index = {(r['iso3'], int(r['year']), r['group']): r for r in exports}
    fx = {int(r['date']): r['value'] for r in json.loads((DATA / 'broad_sector_raw/wb_spain_exchange.json').read_bytes())[1]}
    for row in exports:
        iso, year, group = row['iso3'], int(row['year']), row['group']
        if group == 'REST':
            a, b = (export_index[iso, year, g]['value_source_currency'] for g in ['MHT', 'LMT'])
            expected = float(row['reported_goods_total_source_currency']) - float(a) - float(b) if a and b and row['reported_goods_total_source_currency'] else None
        elif iso == 'ES-PV':
            codes, weights = (['A', 'B'], [-1, -1, 1]) if group == 'MHT' else (['C', 'D'], [1, 1, -1])
            values = [get('eustat_export_groups.json', iso, year, c) for c in codes]
            adjust = [get('eustat_exports_nace.json', iso, year, c) for c in ['254', '325', '301']]
            expected = sum(values) + sum(v * w for v, w in zip(adjust, weights)) if all(v is not None for v in values + adjust) else None
        else:
            # Explicitly independent division lists, not imported from builder.
            divisions = [20, 21, 26, 27, 28, 29, 30] if group == 'MHT' else [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 22, 23, 24, 25, 31, 32]
            values = [get('oecd_btige_exports.csv', iso, year, 'CPA_2_1_C' + str(d)) for d in divisions]
            expected = sum(values) if all(v is not None for v in values) else None
        if expected is None:
            assert not row['value_source_currency']
        else:
            close(row['value_source_currency'], expected)
            if row['value_usd']:
                close(row['value_usd'], expected / fx[year] if iso == 'ES-PV' else expected)
        if row['coverage_status'] == 'available':
            assert expected >= 0
            close(row['share_percent'], expected / float(row['reported_goods_total_source_currency']) * 100)
    coverage = read_csv(DATA / 'sector_economy_coverage.csv')
    for row in coverage:
        iso, year = row['iso3'], int(row['year'])
        if row['metric'] == 'employment':
            amounts = [employment[iso, year, g]['persons'] for g in ['MHT', 'LMT', 'KIS', 'LIS', 'UTL', 'OTH']]
            if all(v != '' for v in amounts):
                close(row['grouped_total'], sum(map(float, amounts)))
            if row['coverage_status'] == 'available':
                close(row['reconciliation_residual'], float(row['reported_total']) - float(row['grouped_total']) - float(row['excluded_U'] or 0))
                assert abs(float(row['reconciliation_residual'])) <= float(row['tolerance'])
                assert all(float(v) >= 0 for v in amounts)
        elif row['coverage_status'] == 'available':
            amounts = [float(export_index[iso, year, g]['value_source_currency']) for g in ['MHT', 'LMT', 'REST']]
            close(row['reported_total'], sum(amounts))
            if iso != 'ES-PV':
                gap = get('oecd_btige_exports.csv', iso, year, 'CPA_2_1_C') - sum(amounts[:2])
                close(row['division_vs_manufacturing_residual'], gap)
                assert abs(gap) <= float(row['tolerance'])
            else:
                errors, incomplete = [], []
                for c, codes in [('A', [1, 2, 3]), ('B', [4, 5, 6, 7, 8]), ('C', [9, 10, 11, 12, 13, 14]), ('D', [15, 16, 17, 18]), ('E', [99])]:
                    cells = [get('eustat_export_sectors.json', iso, year, f'{n:02}') for n in codes]
                    total = get('eustat_export_groups.json', iso, year, c)
                    if total is None or any(v is None for v in cells):
                        incomplete.append(c)
                    else:
                        errors.append(abs(total - sum(cells)))
                assert 'A' not in incomplete and 'B' not in incomplete
                assert ';'.join(incomplete) == row['native_group_audit_incomplete']
                close(max(errors), row['native_group_audit_max'])
                assert max(errors) <= float(row['tolerance'])
    view = json.loads((DATA / 'sector_economy_explorer.json').read_text('utf-8'))
    prod_index = {(r['iso3'], int(r['year']), r['group']): r for r in products}
    for row in view['rows']:
        for series, index, field in [('employment', employment, 'persons'), ('productivity', prod_index, 'gva_per_person_usd_thousand'), ('exports', export_index, 'value_usd')]:
            groups = ['MHT', 'LMT', 'REST'] if series == 'exports' else ['MHT', 'LMT', 'KIS', 'LIS', 'UTL', 'OTH']
            for i, group in enumerate(groups):
                record = index[row['iso'], row['year'], group]
                assert row[series]['status'] == record['coverage_status']
                assert row[series]['amounts'][i] == (float(record[field]) if record[field] else None)
            if series != 'productivity' and row[series]['status'] == 'available':
                close(sum(row[series]['shares']), 100)
        if row['productivity']['status'] == 'available':
            close(row['productivity']['total'], sum(row['productivity']['gvaUSD']) / sum(row['productivity']['persons']) / 1000)
    for iso in view['defaults']:
        assert next(r for r in view['rows'] if r['iso'] == iso and r['year'] == 2022)['productivity']['status'] == 'available'
        assert next(r for r in view['rows'] if r['iso'] == iso and r['year'] == 2024)['exports']['status'] == 'available'
    close(employment['CHN', 2022, 'MHT']['grouped_total_persons'], 751305700)
    close(employment['ES-PV', 2022, 'MHT']['grouped_total_persons'], 1045240)
    close(export_index['CHN', 2024, 'MHT']['reported_goods_total_usd'], 3576543293842)
    close(export_index['ES-PV', 2024, 'MHT']['value_source_currency'], 16663674000)
    workbook = load_workbook(DATA / 'sector_economy.xlsx', read_only=True, data_only=True)
    count = 0
    for sheet in workbook:
        csv = read_csv(DATA / (sheet.title + '.csv'))
        excel = sheet.iter_rows(values_only=True)
        assert list(next(excel)) == list(csv[0])
        n = 0
        for n, cells in enumerate(excel, 1):
            record = csv[n - 1]
            for value, raw in zip(cells, record.values()):
                if isinstance(value, (int, float)):
                    close(value, raw)
                else:
                    assert ('' if value is None else str(value)) == raw
        assert n == len(csv)
        count += n
    workbook.close()
    result = {'verification': 'passed', 'built_utc': report['built_utc'], 'source_cells_checked': len(components),
              'workbook_rows_checked': count, 'employment_rows_checked': len(annual), 'productivity_rows_checked': len(products),
              'export_rows_checked': len(exports), 'embedded_economy_years_checked': len(view['rows']),
              'validation_sha256': digest(DATA / 'sector_economy_validation.json')}
    (DATA / 'sector_economy_verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    verify()
