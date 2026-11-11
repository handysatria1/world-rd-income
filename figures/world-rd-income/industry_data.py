"""Normalize the separately archived export/GVA supplement and audit actual coverage."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import Workbook
from china_gva import nbs_value_added
from industry_sources import ROOT, RAW, START, END, INDICATOR

DATA = ROOT / 'data'
SOURCE_NAMES = {'OECD_NA': 'OECD annual national accounts, Table 6',
                'OECD_STAN': 'OECD STAN 2025', 'UNIDO_INDSTAT': 'UNIDO INDSTAT Rev.4',
                'OECD_TIVA_CHN': 'OECD TiVA 2025 (China selection)'}
ALIASES = {'D': '35', 'L': '68', 'O': '84', 'P': '85', 'U': '99'}


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def dump_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def write_csv(name, rows):
    assert rows, name
    with (DATA / name).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def number(value):
    if value is None or value == '':
        return None
    value = float(value)
    assert math.isfinite(value)
    return value


def label(element):
    return next(n.text for n in element.findall('{*}Name') if n.get('{http://www.w3.org/XML/1998/namespace}lang') == 'en')


def codelists(name):
    root = ET.parse(RAW / name).getroot()
    return {c.get('id'): {r.get('id'): label(r) for r in c.findall('{*}Code')}
            for c in root.findall('.//{*}Codelist')}


def activity_mapping(code, combination=False):
    if combination:
        return '', 'provider_combination'
    if re.fullmatch(r'[A-U]\d{2}', code):
        return code[1:], 'single_division_code'
    if re.fullmatch(r'\d{2}', code):
        return code, 'single_division_code'
    if code in ALIASES:
        return ALIASES[code], 'single_division_section_equivalent'
    return '', 'aggregate_or_finer_activity'


def build():
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for name, info in manifest.items():
        assert digest(RAW / name) == info['sha256'] and (RAW / name).stat().st_size == info['bytes'], name
    history = json.loads((DATA / 'explorer_history.json').read_text('utf-8'))
    baseline = {name: digest(DATA / name) for name in ['explorer_history.json', 'validation_report.json',
                'world_2025_nominal.csv', 'world_2025_ppp.csv', 'world_rd_income_data.xlsx']}
    wb = json.loads((RAW / 'wb_countries.json').read_text('utf-8'))[1]
    countries = {r['id']: r['name'] for r in wb if r['region']['id'] != 'NA'}
    iso2 = {r['iso2Code']: r['id'] for r in wb}
    countries.update({r['iso']: r['name'] for r in history['countries']})
    unido = json.loads((RAW / 'unido_indstat_metadata.json').read_text('utf-8'))
    countries.update({r['iso3']: countries.get(r['iso3'], r['lang']['en']) for r in unido['countries']})

    exports, seen = {}, set()
    for i, r in enumerate(json.loads((RAW / 'wb_mht_history.json').read_text('utf-8'))[1], 1):
        assert r['indicator']['id'] == INDICATOR
        iso = r['countryiso3code'] or iso2[r['country']['id']]
        year, value = int(r['date']), number(r['value'])
        assert START <= year <= END and (iso, year) not in seen
        seen.add((iso, year))
        if iso not in countries:
            continue
        assert value is None or 0 <= value <= 100
        exports[iso, year] = {'value': value, 'flag': r.get('obs_status', ''), 'note': r.get('footnote', ''), 'raw_record': i}
    export_rows = []
    history_map = {r['iso']: r for r in history['countries']}
    annual_join = []
    for iso, country in sorted(countries.items()):
        for year in range(START, END + 1):
            r = exports.get((iso, year), {})
            row = {'iso3': iso, 'country': country, 'year': year, 'mht_exports_percent_manufactured': r.get('value'),
                   'status': 'reported' if r.get('value') is not None else 'reported_null' if r else 'not_returned',
                   'obs_status': r.get('flag', ''), 'footnote': r.get('note', ''), 'indicator': INDICATOR,
                   'source_file': 'wb_mht_history.json', 'raw_record': r.get('raw_record', '')}
            export_rows.append(row)
            h = history_map.get(iso, {})
            rd = h.get('rd', {})
            joined = dict(row)
            for provider in ['oecd', 'wdi', 'eustat', 'ons']:
                series = history.get('breakdowns', {}).get('officialIntensity', {}).get(iso, {}) if provider == 'ons' else rd.get(provider, {})
                observation = series.get(str(year), {})
                joined.update({f'rd_percent_gdp_{provider}': observation.get('v'),
                               f'rd_{provider}_status': observation.get('flags', ''),
                               f'rd_{provider}_note': observation.get('note', '')})
            for kind, unit in [('nominal', 'usd'), ('ppp', 'ppp')]:
                observation = h.get('gdp', {}).get(kind, {}).get(str(year), {})
                joined.update({f'gdp_per_capita_current_{unit}': observation.get('v'),
                               f'gdp_{kind}_status': observation.get('flags', ''),
                               f'gdp_{kind}_note': observation.get('note', '')})
            joined['rd_income_build_utc'] = history['builtUTC']
            annual_join.append(joined)

    gva, metadata, definitions = [], [], []
    def add_metadata(source, iso, level, key, notes, file):
        for n in notes:
            metadata.append({'source': source, 'iso3': iso, 'level': level, 'key': str(key),
                             'note_class': n['noteClass'], 'note': n['note'], 'source_file': file})

    for source, stem in [('OECD_NA', 'oecd_gva'), ('OECD_STAN', 'oecd_stan'), ('OECD_TIVA_CHN', 'oecd_tiva')]:
        tiva = source == 'OECD_TIVA_CHN'
        structure = 'oecd_tiva_structure_resolved.xml' if tiva else stem + '_structure.xml'
        file = 'oecd_tiva_china_valu.csv' if tiva else stem + '_history.csv'
        codes = codelists(structure)
        for category in ['CL_ACTIVITY_ISIC4', 'CL_OBS_STATUS', 'CL_CONF_STATUS', 'CL_UNIT_MULT', 'CL_PRICES', 'CL_TIVA_MEASURE']:
            for code, text in codes.get(category, {}).items():
                definitions.append({'source': source, 'dimension': category, 'code': code, 'label': text,
                                    'source_file': structure})
        for section, division in ALIASES.items():
            assert codes['CL_ACTIVITY_ISIC4'][section] == codes['CL_ACTIVITY_ISIC4'][section + division]
        seen = set()
        for i, r in enumerate(read_csv(RAW / file), 1):
            assert r['FREQ'] == 'A'
            if tiva:
                assert all(r[k] == v for k, v in {'UNIT_MEASURE': 'USD', 'MEASURE': 'VALU', 'REF_AREA': 'CHN', 'COUNTERPART_AREA': 'W'}.items())
            else:
                assert r['UNIT_MEASURE'] == 'XDC' and r['PRICE_BASE'] == 'V'
                assert r.get('TRANSACTION', r.get('MEASURE')) == 'B1G'
            if source == 'OECD_NA':
                assert all(r[k] == v for k, v in {'SECTOR': 'S1', 'COUNTERPART_SECTOR': 'S1', 'INSTR_ASSET': '_Z',
                           'EXPENDITURE': '_Z', 'TRANSFORMATION': 'N', 'TABLE_IDENTIFIER': 'T0301'}.items())
            iso, year, code = r['REF_AREA'], int(r['TIME_PERIOD']), r['ACTIVITY']
            assert START <= year <= END and (iso, year, code) not in seen
            seen.add((iso, year, code))
            if iso in {'EA20', 'EU27_2020'}:
                continue
            assert iso in countries, f'Classify OECD geography {iso}'
            division, mapping = activity_mapping(code)
            value, exponent = number(r['OBS_VALUE']), int(r['UNIT_MULT'])
            assert exponent == 6
            gva.append({'source': source, 'iso3': iso, 'country': countries[iso], 'year': year,
                        'activity_code': code, 'activity_label': codes['CL_ACTIVITY_ISIC4'][code],
                        'isic_revision': '4', 'isic_division': division, 'division_mapping': mapping,
                        'value_reported': value, 'unit_multiplier': exponent,
                        'value_national_currency': None if tiva or value is None else value * 10 ** exponent,
                        'value_usd_provider': value * 10 ** exponent if tiva and value is not None else None,
                        'currency_code': 'USD' if tiva else r.get('CURRENCY', ''), 'currency_label_provider': '',
                        'price_basis': 'current prices', 'measure_code': 'VALU' if tiva else 'B1G',
                        'valuation': 'basic prices; OECD ICIO ReadMe Structure sheet' if tiva else 'B1G; see source national-accounts metadata',
                        'obs_status': r.get('OBS_STATUS', ''), 'conf_status': r.get('CONF_STATUS', ''),
                        'est_method': 'OECD ICIO harmonised and balanced estimates' if tiva else r.get('EST_METHOD', ''),
                        'combination_code': '', 'combination_note': '',
                        'value_status': 'reported' if value is not None else 'missing',
                        'source_file': file, 'raw_record': i})

    for country in unido['countries']:
        iso = country['iso3']
        file = f'unido_data_{iso}.json'
        payload = json.loads((RAW / file).read_text('utf-8'))
        assert json.loads(manifest[file]['request_body'])['datasetId'] == unido['id']
        country_notes = json.loads((RAW / f'unido_country_{iso}.json').read_text('utf-8'))
        variable_notes = json.loads((RAW / f'unido_variable_{iso}.json').read_text('utf-8'))['metadataList']
        add_metadata('UNIDO_INDSTAT', iso, 'country', '', country_notes, f'unido_country_{iso}.json')
        add_metadata('UNIDO_INDSTAT', iso, 'variable', '20', variable_notes, f'unido_variable_{iso}.json')
        year_notes = {r['year']: r['metadataList'] for r in payload.get('ym', [])}
        for year, notes in year_notes.items():
            add_metadata('UNIDO_INDSTAT', iso, 'year', year, notes, file)
        for r in payload.get('am', []):
            add_metadata('UNIDO_INDSTAT', iso, 'activity', r['code'], r['metadataList'], file)
        labels = {a['c']: a['lang']['en'] for a in unido['activities']}
        seen = set()
        for i, r in enumerate(payload['data'], 1):
            year, code = int(r['p']), r['a']
            assert START <= year <= END and re.fullmatch(r'\d{2}', code) and (year, code) not in seen
            seen.add((year, code))
            division, mapping = activity_mapping(code, bool(r.get('c') or r.get('cn')))
            value, usd = number(r.get('v')), number(r.get('u'))
            add_metadata('UNIDO_INDSTAT', iso, 'observation', i, r.get('m', []), file)
            notes = year_notes.get(r['p'], []) + variable_notes + country_notes + r.get('m', [])
            valuation = '; '.join(dict.fromkeys(n['note'] for n in notes if 'value added at' in n['note'].lower()))
            gva.append({'source': 'UNIDO_INDSTAT', 'iso3': iso, 'country': countries[iso], 'year': year,
                        'activity_code': code, 'activity_label': labels[code],
                        'isic_revision': '4', 'isic_division': division, 'division_mapping': mapping,
                        'value_reported': value, 'unit_multiplier': 0, 'value_national_currency': value,
                        'value_usd_provider': usd, 'currency_code': '', 'currency_label_provider': country.get('currency', ''),
                        'price_basis': 'current prices', 'measure_code': '20',
                        'valuation': valuation or 'not resolved; consult country/year/variable notes',
                        'obs_status': '', 'conf_status': '', 'est_method': '',
                        'combination_code': r.get('c', ''), 'combination_note': r.get('cn', ''),
                        'value_status': 'missing' if value is None else 'provider_zero_displayed_as_dash' if value == 0 else 'reported',
                        'source_file': file, 'raw_record': i})
    gva.sort(key=lambda r: (r['source'], r['iso3'], r['year'], r['activity_code']))
    divisions = [r for r in gva if r['isic_division']]
    others = [r for r in gva if not r['isic_division']]
    assert len({(r['source'], r['iso3'], r['year'], r['isic_division']) for r in divisions}) == len(divisions), 'Duplicate section/division equivalence'
    groups = defaultdict(list)
    for r in divisions:
        groups[r['iso3'], r['source'], r['year']].append(r)
    coverage, overview = [], []
    for iso, country in sorted(countries.items()):
        available = [(y, exports[iso, y]['value']) for y in range(START, END + 1) if exports.get((iso, y), {}).get('value') is not None]
        overview_row = {'iso3': iso, 'country': country, 'export_latest_year': available[-1][0] if available else None,
                        'export_latest_percent': available[-1][1] if available else None, 'export_years_available': len(available)}
        for source in SOURCE_NAMES:
            years_available = []
            for year in range(START, END + 1):
                rows = groups[iso, source, year]
                numeric = [r for r in rows if r['value_reported'] is not None]
                nonzero = [r for r in numeric if r['value_reported'] != 0]
                if numeric:
                    years_available.append((year, len(numeric)))
                coverage.append({'iso3': iso, 'country': country, 'source': source, 'year': year,
                                 'single_division_records': len(rows), 'numeric_divisions': len(numeric),
                                 'nonzero_divisions': len(nonzero), 'missing_value_records': len(rows) - len(numeric),
                                 'section_equivalents': sum(r['division_mapping'] == 'single_division_section_equivalent' for r in numeric),
                                 'division_codes': ';'.join(sorted(r['isic_division'] for r in numeric)),
                                  'coverage_status': 'not_requested_for_this_source' if source == 'OECD_TIVA_CHN' and iso != 'CHN' else 'some_divisions_available' if numeric else 'no_numeric_divisions',
                                  'scope': 'industrial establishments; B-E only' if source == 'UNIDO_INDSTAT' else 'ICIO-based estimates; China-only selection; mixed activity detail' if source == 'OECD_TIVA_CHN' else 'national accounts; activity availability varies'})
            overview_row[source + '_latest_year'] = years_available[-1][0] if years_available else None
            overview_row[source + '_divisions_latest'] = years_available[-1][1] if years_available else 0
            overview_row[source + '_first_year'] = years_available[0][0] if years_available else None
        overview.append(overview_row)

    snapshot = []
    for r in read_csv(DATA / 'world_2025_nominal.csv'):
        iso = r['iso3']
        values = [(y, exports.get((iso, y), {}).get('value')) for y in range(2020, 2025)]
        observed = [(y, v) for y, v in values if v is not None]
        latest = next(row for row in overview if row['iso3'] == iso)
        snapshot.append({**r, **{f'mht_exports_pct_{y}': v for y, v in values},
                         'mht_exports_mean_2020_2024_available': sum(v for _, v in observed) / len(observed) if observed else None,
                         'mht_exports_n_years_2020_2024': len(observed),
                         'mht_exports_latest_year': latest['export_latest_year'], 'mht_exports_latest_percent': latest['export_latest_percent'],
                         'rd_income_build_utc': history['builtUTC']})

    nbs = nbs_value_added(RAW)
    outputs = {'mht_exports_annual.csv': export_rows, 'rd_income_exports_annual.csv': annual_join,
               'rd_income_exports_snapshot.csv': snapshot, 'gva_isic2.csv': divisions,
               'gva_other_activities.csv': others, 'gva_country_year_coverage.csv': coverage,
               'industry_country_coverage.csv': overview, 'gva_metadata.csv': metadata, 'gva_definitions.csv': definitions,
               'china_nbs_io_value_added.csv': nbs}
    for name, rows in outputs.items():
        write_csv(name, rows)
    workbook = Workbook(write_only=True)
    for name, rows in outputs.items():
        sheet = workbook.create_sheet(name.removesuffix('.csv')[:31])
        sheet.append(list(rows[0]))
        for r in rows:
            sheet.append(list(r.values()))
    workbook.save(DATA / 'industry_exports_gva.xlsx')

    # A small, offline browser contains latest GVA by source and economy. Full history is downloadable.
    latest_years = {(r['iso3'], s): r[s + '_latest_year'] for r in overview for s in SOURCE_NAMES}
    latest_gva = [r for r in divisions if r['year'] == latest_years[r['iso3'], r['source']]]
    view = {'countries': overview, 'exports': export_rows, 'gva': latest_gva, 'sourceNames': SOURCE_NAMES,
            'rdIncomeBuildUTC': history['builtUTC'], 'chinaNbs': nbs}
    dump_json(DATA / 'industry_explorer.json', view)
    report = {'built_utc': datetime.now(timezone.utc).isoformat(), 'rd_income_build_utc': history['builtUTC'],
              'request_years': [START, END], 'archived_responses': len(manifest), 'economies_audited': len(countries),
              'exports': {'numeric_observations': sum(r['mht_exports_percent_manufactured'] is not None for r in export_rows),
                          'economies': sum(r['export_years_available'] > 0 for r in overview),
                          'latest_year': max(r['export_latest_year'] or 0 for r in overview)},
              'gva': {s: {'numeric_division_rows': sum(r['source'] == s and r['value_reported'] is not None for r in divisions),
                          'economies_with_divisions': sum(r[s + '_latest_year'] is not None for r in overview),
                          'latest_year': max(r[s + '_latest_year'] or 0 for r in overview)} for s in SOURCE_NAMES},
              'gva_union_economies': sum(any(r[s + '_latest_year'] is not None for s in SOURCE_NAMES) for r in overview),
               'unido_combination_records_excluded_from_divisions': sum(r['source'] == 'UNIDO_INDSTAT' for r in others),
              'china_nbs': {'year': 2023, 'native_product_sectors': len(nbs), 'isic_mapping': 'not harmonised',
                            'value_added_total_cny': sum(r['value_national_currency'] for r in nbs)},
              'baseline_file_sha256': baseline,
              'output_sha256': {name: digest(DATA / name) for name in [*outputs, 'industry_exports_gva.xlsx', 'industry_explorer.json']},
              'validation': {k: 'passed' for k in ['source_hashes', 'export_range_and_unique_years', 'gva_dimensions_and_unique_cells',
                             'isic_combinations_separated', 'unit_multipliers_and_current_prices', 'aggregate_geographies_excluded',
                              'missingness_preserved', 'country_year_coverage_grid', 'baseline_inputs_preserved',
                              'tiva_valu_usd_and_china_selection', 'nbs_native_cells_units_and_accounting']}}
    assert all(digest(DATA / name) == sha for name, sha in baseline.items())
    dump_json(DATA / 'industry_validation.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ['output_sha256', 'baseline_file_sha256']}, indent=2))


if __name__ == '__main__':
    build()
