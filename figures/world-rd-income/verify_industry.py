"""Independently reconcile every exported observation against its archived source row."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA, RAW = ROOT / 'data', ROOT / 'data/industry_raw'


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def numeric(text):
    return None if text in ('', None) else float(text)


def main():
    report = json.loads((DATA / 'industry_validation.json').read_text('utf-8'))
    for name, digest in report['output_sha256'].items():
        assert sha(DATA / name) == digest
    for name, digest in report['baseline_file_sha256'].items():
        assert sha(DATA / name) == digest
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for name, info in manifest.items():
        assert sha(RAW / name) == info['sha256']
    raw = {name: rows(RAW / name) for name in ['oecd_gva_history.csv', 'oecd_stan_history.csv']}
    for name in manifest:
        if name.startswith('unido_data_'):
            raw[name] = json.loads((RAW / name).read_text('utf-8'))['data']
    division_rows, other_rows = rows(DATA / 'gva_isic2.csv'), rows(DATA / 'gva_other_activities.csv')
    expected_records = {(name, i) for name, observations in raw.items() for i, r in enumerate(observations, 1)
                        if r.get('REF_AREA') not in {'EA20', 'EU27_2020'}}
    output_records = [(r['source_file'], int(r['raw_record'])) for r in division_rows + other_rows]
    assert len(set(output_records)) == len(output_records) and set(output_records) == expected_records
    for r in division_rows + other_rows:
        original = raw[r['source_file']][int(r['raw_record']) - 1]
        if r['source'] == 'UNIDO_INDSTAT':
            assert r['year'] == original['p'] and r['activity_code'] == original['a']
            value = original.get('v')
            assert numeric(r['value_reported']) == value == numeric(r['value_national_currency'])
            assert numeric(r['value_usd_provider']) == original.get('u')
            assert r['combination_code'] == original.get('c', '') and r['combination_note'] == original.get('cn', '')
            assert bool(r['isic_division']) == (not bool(original.get('c') or original.get('cn')))
            assert (r['value_status'] == 'provider_zero_displayed_as_dash') == (value == 0)
        else:
            assert r['iso3'] == original['REF_AREA'] and r['year'] == original['TIME_PERIOD']
            assert r['activity_code'] == original['ACTIVITY']
            assert numeric(r['value_reported']) == numeric(original['OBS_VALUE'])
            original_value = numeric(original['OBS_VALUE'])
            assert numeric(r['value_national_currency']) == (original_value * 10 ** int(original['UNIT_MULT']) if original_value is not None else None)
            assert r['currency_code'] == original.get('CURRENCY', '')
            assert r['obs_status'] == original.get('OBS_STATUS', '')
            assert r['conf_status'] == original.get('CONF_STATUS', '')
        if r['isic_division']:
            assert len(r['isic_division']) == 2 and r['isic_division'].isdigit()
            if r['division_mapping'] == 'single_division_section_equivalent':
                assert (r['activity_code'], r['isic_division']) in {('D','35'), ('L','68'), ('O','84'), ('P','85'), ('U','99')}
            else:
                assert r['activity_code'][-2:] == r['isic_division']
    numeric_groups = defaultdict(set)
    native_economies = defaultdict(set)
    for r in division_rows:
        if r['value_reported'] != '':
            numeric_groups[r['iso3'], r['source'], r['year']].add(r['isic_division'])
            if r['division_mapping'] == 'single_division_code':
                native_economies[r['source']].add(r['iso3'])
    coverage = rows(DATA / 'gva_country_year_coverage.csv')
    assert len(coverage) == report['economies_audited'] * 26 * 3
    for r in coverage:
        codes = numeric_groups[r['iso3'], r['source'], r['year']]
        assert int(r['numeric_divisions']) == len(codes)
        assert set(filter(None, r['division_codes'].split(';'))) == codes

    wb = json.loads((RAW / 'wb_mht_history.json').read_text('utf-8'))[1]
    exports = rows(DATA / 'mht_exports_annual.csv')
    assert len(exports) == report['economies_audited'] * 26
    export_by_key = {(r['iso3'], r['year']): r for r in exports}
    assert len(export_by_key) == len(exports)
    for r in exports:
        if r['raw_record']:
            original = wb[int(r['raw_record']) - 1]
            assert r['year'] == original['date']
            assert numeric(r['mht_exports_percent_manufactured']) == original['value']
            assert r['obs_status'] == original.get('obs_status', '') and r['footnote'] == original.get('footnote', '')
        else:
            assert not r['mht_exports_percent_manufactured']
    before = rows(DATA / 'world_2025_nominal.csv')
    history = json.loads((DATA / 'explorer_history.json').read_text('utf-8'))
    history_countries = {c['iso']: c for c in history['countries']}
    annual = rows(DATA / 'rd_income_exports_annual.csv')
    assert len(annual) == len(exports)
    for r in annual:
        assert all(r[k] == v for k, v in export_by_key[r['iso3'], r['year']].items())
        c = history_countries.get(r['iso3'], {})
        for provider in ['oecd', 'wdi', 'eustat', 'ons']:
            if provider == 'ons':
                observation = history['breakdowns']['officialIntensity'].get(r['iso3'], {}).get(r['year'], {})
            else:
                observation = c.get('rd', {}).get(provider, {}).get(r['year'], {})
            assert numeric(r[f'rd_percent_gdp_{provider}']) == observation.get('v')
            assert r[f'rd_{provider}_status'] == observation.get('flags', '')
            assert r[f'rd_{provider}_note'] == observation.get('note', '')
        for metric, unit in [('nominal', 'usd'), ('ppp', 'ppp')]:
            observation = c.get('gdp', {}).get(metric, {}).get(r['year'], {})
            assert numeric(r[f'gdp_per_capita_current_{unit}']) == observation.get('v')
            assert r[f'gdp_{metric}_status'] == observation.get('flags', '')
            assert r[f'gdp_{metric}_note'] == observation.get('note', '')
    after = rows(DATA / 'rd_income_exports_snapshot.csv')
    assert len(before) == len(after)
    for a, b in zip(before, after):
        assert all(b[k] == v for k, v in a.items())
        vals = [numeric(export_by_key[a['iso3'], str(y)]['mht_exports_percent_manufactured']) for y in range(2020, 2025)]
        vals = [v for v in vals if v is not None]
        assert int(b['mht_exports_n_years_2020_2024']) == len(vals)
        assert numeric(b['mht_exports_mean_2020_2024_available']) == (sum(vals) / len(vals) if vals else None)
    result = {'built_utc': report['built_utc'], 'verification': 'passed',
              'raw_gva_records_reconciled': len(output_records), 'export_grid_records_verified': len(exports),
              'native_single_division_economies_excluding_section_equivalents': {s: len(v) for s,v in native_economies.items()},
              'normalized_gva_rows_by_source': dict(Counter(r['source'] for r in division_rows)),
              'baseline_file_hashes_preserved': True, 'original_snapshot_columns_preserved': True,
              'complete_country_year_coverage_verified': True,
              'same_year_rd_income_joins_and_flags_verified': True,
              'industry_validation_sha256': sha(DATA / 'industry_validation.json')}
    (DATA / 'industry_verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
