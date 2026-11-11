"""Aggregate disjoint source activities into the user's six broad GVA sectors."""
import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import Workbook
from basque_rd import px_rows
from broad_sector_sources import RAW, ROOT
from industry_data import digest, read_csv

DATA = ROOT / 'data'
GROUPS = [
    {'id': 'MHT', 'label': 'Medium/high-tech manufacturing', 'color': '#176181', 'sections': 'C',
     'divisions': [20, 21, 26, 27, 28, 29, 30], 'tiva': ['C20', 'C21', 'C26', 'C27', 'C28', 'C29', 'C30'], 'eustat': ['07', '08', '11', '12', '13', '14']},
    {'id': 'LMT', 'label': 'Low/medium-tech manufacturing', 'color': '#05aee0', 'sections': 'C',
     'divisions': [*range(10, 20), 22, 23, 24, 25, 31, 32, 33], 'tiva': ['C10T12', 'C13T15', 'C16T18', 'C19', 'C22', 'C23', 'C24_25', 'C31T33'], 'eustat': ['03', '04', '05', '06', '09', '10', '15']},
    {'id': 'KIS', 'label': 'Knowledge-intensive services', 'color': '#206e2b', 'sections': 'J;K;M;P',
     'divisions': [*range(58, 67), *range(69, 76), 85], 'tiva': ['J', 'K', 'M', 'P'], 'eustat': ['22', '23', '24', '25', '27', '28', '29', '32']},
    {'id': 'LIS', 'label': 'Labour-intensive services', 'color': '#ee742c', 'sections': 'G;H;I;L;N;O;Q;R;S;T',
     'divisions': [45, 46, 47, *range(49, 54), 55, 56, 68, *range(77, 83), 84, 86, 87, 88, *range(90, 99)],
     'tiva': ['G', 'H', 'I', 'L', 'N', 'O', 'Q', 'R', 'S', 'T'], 'eustat': ['19', '20', '21', '26', '30', '31', '33', '34', '35', '36', '37']},
    {'id': 'UTL', 'label': 'Utilities', 'color': '#a2239e', 'sections': 'D;E',
     'divisions': [35, 36, 37, 38, 39], 'tiva': ['D_E'], 'eustat': ['16', '17']},
    {'id': 'OTH', 'label': 'Other production', 'color': '#858585', 'sections': 'A;B;F',
     'divisions': [1, 2, 3, 5, 6, 7, 8, 9, 41, 42, 43], 'tiva': ['A', 'B', 'F'], 'eustat': ['01', '02', '18']},
]
DEFAULTS = ['KOR', 'SGP', 'CHN', 'ES-PV', 'USA', 'GBR']
DISPLAY = {'KOR': 'Korea', 'USA': 'US', 'GBR': 'UK'}


def write(name, rows):
    with (DATA / name).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build():
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for name, info in manifest.items():
        assert digest(RAW / name) == info['sha256']
    divisions = [d for g in GROUPS for d in g['divisions']]
    assert len(divisions) == len(set(divisions)) == 87 and 99 not in divisions
    for provider in ['tiva', 'eustat']:
        codes = [c for g in GROUPS for c in g[provider]]
        assert len(codes) == len(set(codes))
    countries = {r['iso3']: r['country'] for r in read_csv(DATA / 'industry_country_coverage.csv')}
    xml = ET.parse(RAW / 'oecd_tiva_structure_resolved.xml').getroot()
    activity = next(c for c in xml.findall('.//{*}Codelist') if c.get('id') == 'CL_ACTIVITY_ISIC4')
    labels = {c.get('id'): next(n.text for n in c.findall('{*}Name') if n.get('{http://www.w3.org/XML/1998/namespace}lang') == 'en') for c in activity.findall('{*}Code')}
    tiva, excluded = {}, set()
    for i, row in enumerate(read_csv(RAW / 'oecd_tiva_valu_all.csv'), 1):
        assert all(row[k] == v for k, v in {'MEASURE': 'VALU', 'COUNTERPART_AREA': 'W', 'UNIT_MEASURE': 'USD', 'FREQ': 'A', 'UNIT_MULT': '6'}.items())
        if row['REF_AREA'] not in countries:
            excluded.add(row['REF_AREA'])
            continue
        key = row['REF_AREA'], int(row['TIME_PERIOD']), row['ACTIVITY']
        assert key not in tiva
        tiva[key] = {'value': float(row['OBS_VALUE']) if row['OBS_VALUE'] else None, 'record': i, 'status': row.get('OBS_STATUS', '')}
    nations = sorted({key[0] for key in tiva})
    px = list(px_rows(RAW / 'eustat_gva_a38.json'))
    eustat = {}
    for i, (coord, label, value, flag, dataset) in enumerate(px, 1):
        assert coord['territorio histórico'] == '_T' and coord['tipo de dato'] == coord['tipo de medida'] == '10'
        assert label['tipo de medida'] == 'Current prices (thousand euros)'
        eustat[int(coord['periodo']), coord['sector']] = {'value': None if value is None else float(value), 'record': i,
                                                       'status': flag, 'label': label['sector']}
    notes = (RAW / 'eustat_gva_a38.px').read_bytes().decode('cp1252')
    note = ''.join(re.findall(r'"([^"]*)"', re.search(r'NOTEX\[en\]=([^;]*);', notes)[1])).replace('#', '; ')
    assert '1995 and 2020' in note and '2025 Provisional data' in note
    fx_rows = json.loads((RAW / 'wb_spain_exchange.json').read_bytes())[1]
    assert all(r['countryiso3code'] == 'ESP' and r['indicator']['id'] == 'PA.NUS.FCRF' for r in fx_rows)
    exchange = {int(r['date']): (r, i) for i, r in enumerate(fx_rows, 1)}
    annual, components, audit, browser_rows = [], [], [], []
    for iso in [*nations, 'ES-PV']:
        basque = iso == 'ES-PV'
        source = 'EUSTAT_A38' if basque else 'OECD_TIVA'
        source_file = 'eustat_gva_a38.json' if basque else 'oecd_tiva_valu_all.csv'
        for year in range(2000, 2026):
            fx_row, fx_record = exchange.get(year, ({}, None)) if basque else ({}, None)
            fx = fx_row.get('value') if basque else 1
            assert fx is None or fx > 0
            amounts, missing, statuses, group_rows = [], [], [], []
            for group in GROUPS:
                codes = group['eustat' if basque else 'tiva'][:]
                combined_note = ''
                if basque and year <= 2020 and group['id'] == 'MHT':
                    codes.remove('07')
                    combined_note = 'Eustat note: code 08 includes chemicals (07) and pharmaceuticals (08) through 2020; counted once.'
                values, records, flags = [], [], []
                for code in codes:
                    obs = eustat.get((year, code), {}) if basque else tiva.get((iso, year, code), {})
                    value = obs.get('value')
                    if value is None:
                        missing.append(code)
                    values.append(value)
                    records.append(str(obs.get('record', '')))
                    flags.append(obs.get('status', ''))
                    components.append({'iso3': iso, 'economy': countries[iso], 'source': source, 'year': year,
                                       'group': group['id'], 'activity_code': code,
                                       'activity_label': obs.get('label', '') if basque else labels[code],
                                       'value_reported': value, 'unit_multiplier': 3 if basque else 6,
                                       'currency_code': 'EUR' if basque else 'USD', 'obs_status': obs.get('status', ''),
                                       'source_file': source_file, 'raw_record': obs.get('record', ''),
                                       'mapping_note': combined_note if code == '08' else ''})
                amount = sum(values) * (1000 if basque else 1e6) if all(v is not None for v in values) else None
                usd = amount / fx if amount is not None and fx is not None else None
                amounts.append(amount)
                statuses.extend(filter(None, flags))
                group_rows.append({'iso3': iso, 'economy': countries[iso], 'source': source, 'year': year,
                                   'group': group['id'], 'group_label': group['label'],
                                   'value_source_currency': amount, 'currency_code': 'EUR' if basque else 'USD',
                                   'value_usd': usd, 'share_percent': None,
                                   'value_status': 'derived_sum_and_currency_conversion' if basque else 'derived_sum_of_provider_USD',
                                   'source_activity_codes': ';'.join(codes), 'source_records': ';'.join(records),
                                   'source_file': source_file, 'obs_status': ';'.join(sorted(set(filter(None, flags)))),
                                   'mapping_note': combined_note,
                                   'eur_per_usd': fx if basque else None, 'exchange_source_file': 'wb_spain_exchange.json' if basque else '',
                                   'exchange_raw_record': fx_record, 'exchange_status': fx_row.get('obs_status', ''),
                                   'exchange_note': fx_row.get('footnote', ''),
                                   'provider_note': note if basque else 'OECD ICIO harmonised and balanced estimates; current basic prices.'})
            complete = all(v is not None for v in amounts)
            total = sum(amounts) if complete else None
            provider = eustat.get((year, '50'), {}) if basque else tiva.get((iso, year, '_T'), {})
            provider_value = provider.get('value')
            provider_total = provider_value * (1000 if basque else 1e6) if provider_value is not None else None
            u = eustat.get((year, '38'), {}).get('value') if basque else None
            residual = provider_total - total if total is not None and provider_total is not None else None
            adjusted_residual = residual - u * 1000 if residual is not None and u is not None else residual
            tolerance = max(50000, abs(provider_total or 0) * 1e-7)
            reconciled = adjusted_residual is not None and abs(adjusted_residual) <= tolerance
            status = 'missing_components' if not complete else 'nonpositive_total_or_negative_group' if total <= 0 or min(amounts) < 0 else 'unreconciled_total' if not reconciled else 'available'
            total_usd = total / fx if total is not None and fx is not None else None
            for r, amount in zip(group_rows, amounts):
                r['share_percent'] = amount / total * 100 if status == 'available' else None
                r['coverage_status'] = status
            annual.extend(group_rows)
            audit.append({'iso3': iso, 'economy': countries[iso], 'source': source, 'year': year,
                          'coverage_status': status, 'missing_activity_codes': ';'.join(missing),
                          'grouped_gva_source_currency': total, 'provider_total_gva_source_currency': provider_total,
                          'excluded_U_source_currency': u * 1000 if u is not None else None,
                          'provider_total_minus_grouped': residual, 'reconciliation_tolerance': tolerance,
                          'currency_code': 'EUR' if basque else 'USD', 'grouped_gva_usd': total_usd,
                          'exchange_available': fx is not None, 'provider_total_source_file': source_file,
                          'provider_total_raw_record': provider.get('record', ''),
                          'denominator': 'sum of six groups; sections A–T; excludes U and net taxes on products',
                          'year_note': 'provisional' if basque and year == 2025 else ''})
            browser_rows.append({'iso': iso, 'year': year, 'source': source, 'status': status,
                                 'amounts': [r['value_usd'] for r in group_rows], 'shares': [r['share_percent'] for r in group_rows],
                                 'totalUSD': total_usd, 'totalLocal': total, 'currency': 'EUR' if basque else 'USD',
                                 'missing': missing, 'note': '2025 provisional' if basque and year == 2025 else '',
                                 'flags': '; '.join(sorted(set(statuses)))})
    mapping = [{'group': g['id'], 'label': g['label'], 'sections': g['sections'],
                'divisions': ';'.join(f'{d:02}' for d in g['divisions']), 'tiva_activity_codes': ';'.join(g['tiva']),
                'eustat_a38_codes_from_2021': ';'.join(g['eustat']), 'color': g['color']} for g in GROUPS]
    outputs = {'broad_sector_annual.csv': annual, 'broad_sector_components.csv': components,
               'broad_sector_coverage.csv': audit, 'broad_sector_classification.csv': mapping}
    for name, rows in outputs.items():
        write(name, rows)
    workbook = Workbook(write_only=True)
    for name, rows in outputs.items():
        sheet = workbook.create_sheet(name.removesuffix('.csv')[:31])
        sheet.append(list(rows[0]))
        for row in rows:
            sheet.append(list(row.values()))
    workbook.save(DATA / 'broad_sector_gva.xlsx')
    built = datetime.now(timezone.utc).isoformat()
    view = {'builtUTC': built, 'groups': [{k: g[k] for k in ['id', 'label', 'color']} for g in GROUPS], 'defaults': DEFAULTS,
            'countries': [{'iso': iso, 'name': countries[iso], 'display': DISPLAY.get(iso, countries[iso]),
                           'region': iso == 'ES-PV'} for iso in [*nations, 'ES-PV']], 'rows': browser_rows,
            'sources': {'OECD_TIVA': 'OECD TiVA 2025', 'EUSTAT_A38': 'Eustat A38 (Basque Country)'}}
    (DATA / 'broad_sector_explorer.json').write_text(json.dumps(view, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')
    report = {'built_utc': built, 'validation': 'passed', 'country_economies': len(nations), 'regions': 1,
              'archived_responses': len(manifest), 'excluded_provider_aggregate_codes': sorted(excluded),
              'coverage_status_counts': {s: sum(r['coverage_status'] == s for r in audit) for s in sorted({r['coverage_status'] for r in audit})},
              'latest_complete_years_examples': {iso: max((r['year'] for r in audit if r['iso3'] == iso and r['coverage_status'] == 'available'), default=None) for iso in DEFAULTS},
              'output_sha256': {name: digest(DATA / name) for name in [*outputs, 'broad_sector_gva.xlsx', 'broad_sector_explorer.json']},
              'industry_validation_sha256': digest(DATA / 'industry_validation.json')}
    assert all(report['latest_complete_years_examples'].values())
    (DATA / 'broad_sector_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build()
