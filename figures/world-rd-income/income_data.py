"""Extract classifications and innovation indicators with source-cell provenance."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import re

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from income_sources import ROOT, RAW, INDICATORS
from basque_innovation import load_basque_innovation

DATA = ROOT / 'data'
GROUPS = {'High income': 'HIC', 'Upper middle income': 'UMC', 'Lower middle income': 'LMC', 'Low income': 'LIC'}


def write_csv(name, rows):
    with (DATA / name).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build():
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for name, info in manifest.items():
        assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == info['sha256']
    book = load_workbook(RAW / 'classification_current.xlsx', read_only=True, data_only=True)
    notes = '\n'.join(str(r[0]) for r in book['notes'].values if r[0])
    match = re.search(r'For FY(\d{2}) \(', notes)
    assert match, notes
    vintage = 'FY20' + match[1]
    countries, classifications = {}, []
    for row_number, (name, iso, region, group, _) in enumerate(book['List of economies'].values, 1):
        if row_number == 1 or not region:
            continue
        assert iso and len(iso) == 3 and group in {*GROUPS, None}, (iso, group)
        countries[iso] = {'iso': iso, 'name': name, 'current': GROUPS.get(group, 'UNK'), 'history': {}, 'series': {}}
        classifications.append({'iso3': iso, 'economy': name, 'fiscal_year': vintage, 'income_code': GROUPS.get(group, 'UNK'),
                                'source_value': group, 'source_file': 'classification_current.xlsx', 'source_cell': f"List of economies!D{row_number}"})
    book.close()
    assert 200 < len(countries) < 230
    historical = load_workbook(RAW / 'classification_history.xlsx', read_only=True, data_only=True)
    rows = list(historical['Country Analytical History'].values)
    fiscal = {}
    for i, v in enumerate(rows[4]):
        if isinstance(v, str) and re.fullmatch(r'FY\d{2}', v):
            year = int(v[2:]) + (1900 if int(v[2:]) >= 80 else 2000)
            if year >= 2000:
                fiscal[i] = 'FY' + str(year)
    assert vintage in fiscal.values()
    codes = {'H': 'HIC', 'UM': 'UMC', 'LM': 'LMC', 'L': 'LIC', '..': 'UNK', None: 'UNK'}
    for row_number, row in enumerate(rows[6:], 7):
        iso = row[0]
        if iso not in countries:
            continue
        for i, fy in fiscal.items():
            raw = row[i].strip() if isinstance(row[i], str) else row[i]
            assert raw in codes, (iso, fy, raw)
            countries[iso]['history'][fy] = codes[raw]
            classifications.append({'iso3': iso, 'economy': countries[iso]['name'], 'fiscal_year': fy, 'income_code': codes[raw],
                                    'source_value': raw, 'source_file': 'classification_history.xlsx',
                                    'source_cell': f'Country Analytical History!{get_column_letter(i+1)}{row_number}'})
        assert countries[iso]['history'][vintage] == countries[iso]['current'], iso
    historical.close()
    # National dashboard names and the Basque regional comparator, without inheriting Spain's class.
    national = json.loads((DATA / 'explorer_history.json').read_text('utf-8'))
    for c in national['countries']:
        countries.setdefault(c['iso'], {'iso': c['iso'], 'name': c['name'], 'current': 'UNK', 'history': {}, 'series': {}})
        countries[c['iso']]['region'] = c.get('geographyType') == 'region'
    metadata, annual = {}, []
    for metric, (code, label, unit) in INDICATORS.items():
        meta, observations = json.loads((RAW / (metric + '.json')).read_text('utf-8'))
        assert meta['pages'] == 1 and len(observations) == meta['total']
        definition = json.loads((RAW / (metric + '_metadata.json')).read_text('utf-8'))[1][0]
        assert definition['id'] == code
        metadata[metric] = {'code': code, 'label': label, 'unit': unit, 'definition': definition['sourceNote'],
                            'organization': definition['sourceOrganization'], 'updated': meta.get('lastupdated', ''),
                            'retrieved': manifest[metric + '.json']['retrieved_utc'], 'url': manifest[metric + '.json']['url']}
        seen = set()
        for record, r in enumerate(observations, 1):
            iso, year = r['countryiso3code'], int(r['date'])
            assert r['indicator']['id'] == code and 2000 <= year <= 2025
            if iso not in countries or countries[iso].get('region'):
                continue
            assert (iso, year) not in seen
            seen.add((iso, year))
            value = r['value']
            assert value is None or (math.isfinite(value) and value >= 0)
            countries[iso]['series'].setdefault(metric, {})[str(year)] = {'v': value, 'flags': r.get('obs_status', ''), 'note': r.get('footnote', ''), 'record': record}
            annual.append({'iso3': iso, 'economy': countries[iso]['name'], 'year': year, 'metric': metric, 'indicator': code,
                           'value': value, 'unit': unit, 'availability': 'reported' if value is not None else 'missing',
                           'obs_status': r.get('obs_status', ''), 'footnote': r.get('footnote', ''), 'source_file': metric + '.json',
                           'source_record': record, 'api_lastupdated': meta.get('lastupdated', ''),
                           'retrieved_utc': manifest[metric + '.json']['retrieved_utc']})
    series, regional_meta, context, regional_annual, regional_manifest = load_basque_innovation()
    assert countries['ES-PV']['region']
    countries['ES-PV']['series'].update(series)
    countries['ES-PV']['indicatorMetadata'] = regional_meta
    countries['ES-PV']['contextIndicators'] = context
    payload = {'builtUTC': datetime.now(timezone.utc).isoformat(), 'currentVintage': vintage, 'classificationNotes': notes,
               'historicalVintages': sorted(set(fiscal.values()), reverse=True), 'indicators': metadata,
               'countries': sorted(countries.values(), key=lambda c: c['name']), 'sources': manifest, 'regionalSources': regional_manifest}
    write_csv('income_classifications.csv', classifications)
    write_csv('innovation_annual.csv', annual)
    write_csv('basque_innovation_annual.csv', regional_annual)
    (DATA / 'income_explorer.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    report = {'validation': 'passed', 'built_utc': payload['builtUTC'], 'current_vintage': vintage,
              'classification_rows': len(classifications), 'indicator_rows_including_missing': len(annual),
              'checks': ['archived_hashes', 'official_current_historical_agreement', 'unique_country_year_indicator',
                          'finite_nonnegative_values', 'WDI_aggregates_and_regions_excluded', 'source_cell_locators',
                          'Eustat_hashes_requests_coordinates', 'population_midyear_proxy_flagged', 'EIS_indicators_separate'],
               'regional_rows_including_missing': len(regional_annual),
              'note': 'Historical workbook Parameters sheet still says FY21; classification columns and current notes explicitly extend to ' + vintage + '. Parameters is not used.'}
    (DATA / 'income_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build()
