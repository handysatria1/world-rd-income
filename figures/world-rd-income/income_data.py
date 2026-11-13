"""Extract classifications and innovation indicators with source-cell provenance."""
import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import math
import re
from zipfile import ZipFile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from absorptive_capacity import build_absorptive_capacity
from income_sources import ROOT, RAW, INDICATORS, HCI_ARCHIVE_NAME
from basque_innovation import load_basque_innovation
from wdi_bulk import load_wdi_observations

DATA = ROOT / 'data'
GROUPS = {'High income': 'HIC', 'Upper middle income': 'UMC', 'Lower middle income': 'LMC', 'Low income': 'LIC'}


def governance_score_observations(path):
    """Read the exact WDI 0–100 governance-score CSV from its official ZIP archive."""
    with ZipFile(path) as archive:
        member = next(name for name in archive.namelist()
                      if name.startswith('API_GOV_WGI_GE_SC_') and name.endswith('.csv'))
        rows = list(csv.reader(StringIO(archive.read(member).decode('utf-8-sig'))))
        metadata_member = next(name for name in archive.namelist()
                               if name.startswith('Metadata_Indicator_API_GOV_WGI_GE_SC_') and name.endswith('.csv'))
        definition_rows = list(csv.reader(StringIO(archive.read(metadata_member).decode('utf-8-sig'))))
    header_position = next(i for i, row in enumerate(rows) if row and row[0] == 'Country Name')
    header = rows[header_position]
    years = [(i, int(value)) for i, value in enumerate(header) if value.isdigit() and 2000 <= int(value) <= 2025]
    assert {year for _, year in years} == set(range(2000, 2026))
    updated = next((row[1] for row in rows[:header_position] if row and row[0] == 'Last Updated Date'), '')
    assert definition_rows[1][0] == 'GOV_WGI_GE_SC'
    definition = {'id': definition_rows[1][0], 'name': definition_rows[1][1],
                  'sourceNote': definition_rows[1][2], 'sourceOrganization': definition_rows[1][3]}
    observations = []
    for row_number, row in enumerate(rows[header_position + 1:], header_position + 2):
        if not row or not row[0] or row[3] != 'GOV_WGI_GE_SC':
            continue
        for column, year in years:
            raw = row[column]
            observations.append({'indicator': {'id': 'GOV_WGI_GE_SC'}, 'date': str(year),
                                 'countryiso3code': row[1], 'country': {'id': row[1], 'value': row[0]},
                                 'value': float(raw) if raw else None, '_source_record': f'{member}:row {row_number}, column {column + 1}',
                                 '_source_file': 'governmentEffectiveness.zip', '_source_country_code': row[1],
                                 '_country_match': 'iso3'})
    return {'lastupdated': updated, 'sourceid': '2'}, observations, definition


def governance_estimate_observations(path):
    """Read WGI's official 2026 workbook estimates for the ge dimension."""
    book = load_workbook(path, read_only=True, data_only=True)
    assert 'ge' in book.sheetnames
    sheet = book['ge']
    rows = sheet.iter_rows(values_only=True)
    header = next(rows)
    assert header[2] == 'Economy (code)' and header[5] == 'Year'
    assert header[6] == 'Governance dimension' and header[8].startswith('Governance estimate')
    observations, seen = [], set()
    for row_number, row in enumerate(rows, 2):
        if len(row) < 9 or row[6] != 'ge' or not row[2] or row[5] is None:
            continue
        iso, year = str(row[2]).strip(), int(row[5])
        if not 2000 <= year <= 2025:
            continue
        assert len(iso) == 3 and iso.isalpha(), (row_number, iso)
        assert (iso, year) not in seen, (iso, year)
        seen.add((iso, year))
        raw = row[8]
        value = None if raw is None or (isinstance(raw, str) and raw.strip() in {'', '..'}) else float(raw)
        observations.append({'indicator': {'id': INDICATORS['governmentEffectivenessEstimate'][0]}, 'date': str(year),
                             'countryiso3code': iso, 'country': {'id': iso, 'value': row[1]},
                             'value': value, '_source_record': f'ge!I{row_number}',
                             '_source_file': 'governmentEffectivenessEstimate.xlsx',
                             '_source_country_code': iso, '_country_match': 'iso3'})
    book.close()
    assert observations and {2000, 2025} <= {int(row['date']) for row in observations}
    return {'lastupdated': '2026 WGI edition'}, observations


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
    wdi_metrics = {key: code for key, (code, _, _) in INDICATORS.items()
                   if key not in {'governmentEffectiveness', 'governmentEffectivenessEstimate', 'humanCapitalIndex'}}
    wdi_observations = load_wdi_observations(RAW / 'wdi_csv.zip', wdi_metrics.values())
    hci_code = INDICATORS['humanCapitalIndex'][0]
    hci_observations = load_wdi_observations(RAW / HCI_ARCHIVE_NAME, {hci_code}, 2010, 2020,
                                             member_name='HCIData.csv', observed_only_years=True)
    metadata, annual = {}, []
    for metric, (code, label, unit) in INDICATORS.items():
        if metric == 'governmentEffectiveness':
            source_file = metric + '.zip'
            meta, observations, definition = governance_score_observations(RAW / source_file)
        elif metric == 'governmentEffectivenessEstimate':
            source_file = metric + '.xlsx'
            meta, observations = governance_estimate_observations(RAW / source_file)
            definition = json.loads((RAW / (metric + '_metadata.json')).read_text('utf-8'))[1][0]
        elif metric == 'humanCapitalIndex':
            source_file = HCI_ARCHIVE_NAME
            observations = hci_observations[code]
            meta = {'lastupdated': '2020 HCI database'}
            definition = json.loads((RAW / (metric + '_metadata.json')).read_text('utf-8'))[1][0]
        else:
            source_file = 'wdi_csv.zip'
            observations = wdi_observations[code]
            meta = {'lastupdated': manifest[source_file]['release_date']}
            definition = json.loads((RAW / (metric + '_metadata.json')).read_text('utf-8'))[1][0]
        assert definition['id'] == code
        metadata[metric] = {'code': code, 'label': label, 'unit': unit, 'definition': definition['sourceNote'],
                            'organization': definition['sourceOrganization'], 'updated': meta.get('lastupdated', ''),
                            'retrieved': manifest[source_file]['retrieved_utc'], 'url': manifest[source_file]['url'],
                            'source_file': source_file}
        seen = set()
        for record, r in enumerate(observations, 1):
            year = int(r['date'])
            assert r['indicator']['id'] == code
            if not 2000 <= year <= 2025:
                continue
            source_iso3 = r.get('countryiso3code') or ''
            source_country_code = r.get('_source_country_code') or (r.get('country') or {}).get('id') or ''
            assert len(source_iso3) == 3 and source_iso3.isalpha(), (metric, source_iso3, year)
            assert source_country_code == source_iso3 and r.get('_country_match') == 'iso3', (metric, r, year)
            iso = source_iso3
            if iso not in countries or countries[iso].get('region'):
                continue
            assert (iso, year) not in seen
            seen.add((iso, year))
            value = r['value']
            assert value is None or math.isfinite(value)
            if value is not None:
                if metric == 'humanCapitalIndex':
                    assert 0 <= value <= 1, (metric, iso, year, value)
                elif metric in {'internetUsers', 'bachelorAttainment', 'governmentEffectiveness'}:
                    assert 0 <= value <= 100, (metric, iso, year, value)
                elif metric != 'governmentEffectivenessEstimate':
                    assert value >= 0, (metric, iso, year, value)
            match_method = 'iso3'
            source_record = r.get('_source_record', record)
            source_file = r.get('_source_file', source_file)
            countries[iso]['series'].setdefault(metric, {})[str(year)] = {
                'v': value, 'flags': r.get('obs_status', ''), 'note': r.get('footnote', ''), 'record': source_record,
                'countryCode': source_country_code, 'sourceISO3': source_iso3, 'countryMatch': match_method}
            annual.append({'iso3': iso, 'economy': countries[iso]['name'], 'year': year, 'metric': metric, 'indicator': code,
                           'value': value, 'unit': unit, 'availability': 'reported' if value is not None else 'missing',
                           'obs_status': r.get('obs_status', ''), 'footnote': r.get('footnote', ''), 'source_file': source_file,
                           'source_record': source_record, 'source_country_code': source_country_code, 'source_iso3': source_iso3,
                           'country_match': match_method, 'source_lastupdated': meta.get('lastupdated', ''),
                           'retrieved_utc': metadata[metric]['retrieved']})
    series, regional_meta, context, regional_annual, regional_manifest = load_basque_innovation()
    assert countries['ES-PV']['region']
    countries['ES-PV']['series'].update(series)
    countries['ES-PV']['indicatorMetadata'] = regional_meta
    countries['ES-PV']['contextIndicators'] = context
    payload = {'builtUTC': datetime.now(timezone.utc).isoformat(), 'currentVintage': vintage, 'classificationNotes': notes,
               'historicalVintages': sorted(set(fiscal.values()), reverse=True), 'indicators': metadata,
               'countries': sorted(countries.values(), key=lambda c: c['name']), 'sources': manifest, 'regionalSources': regional_manifest}
    capacity = build_absorptive_capacity(payload)
    write_csv('income_classifications.csv', classifications)
    write_csv('innovation_annual.csv', annual)
    write_csv('basque_innovation_annual.csv', regional_annual)
    (DATA / 'income_explorer.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    write_csv('absorptive_capacity_country.csv', capacity['country_rows'])
    write_csv('absorptive_capacity_groups.csv', capacity['group_rows'])
    (DATA / 'absorptive_capacity.json').write_text(
        json.dumps(capacity['json'], ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    report = {'validation': 'passed', 'built_utc': payload['builtUTC'], 'current_vintage': vintage,
              'classification_rows': len(classifications), 'indicator_rows_including_missing': len(annual),
              'absorptive_capacity_countries': len(capacity['country_rows']),
              'absorptive_capacity_group_rows': len(capacity['group_rows']),
              'checks': ['archived_hashes', 'official_current_historical_agreement', 'unique_country_year_indicator',
                         'finite_values_and_indicator_specific_ranges', 'WDI_aggregates_and_regions_excluded',
                         'WDI_bulk_and_HCI_observed_years', 'exact_iso3_joins_and_source_cell_locators',
                         'Eustat_hashes_requests_coordinates', 'population_midyear_proxy_flagged', 'EIS_indicators_separate',
                          'country_means_observed_years_only', 'income_group_means_equal_country_weight'],
               'regional_rows_including_missing': len(regional_annual),
              'note': 'Historical workbook Parameters sheet still says FY21; classification columns and current notes explicitly extend to ' + vintage + '. Parameters is not used.'}
    (DATA / 'income_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build()
