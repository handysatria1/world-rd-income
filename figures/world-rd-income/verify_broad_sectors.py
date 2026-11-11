"""Reconcile grouped GVA and conversion arithmetic with the archived provider cells."""
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA, RAW = ROOT / 'data', ROOT / 'data/broad_sector_raw'


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def number(value):
    return None if value in ('', None) else float(value)


def equal(a, b):
    return a is None and b is None or a is not None and b is not None and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-6)


def main():
    report = json.loads((DATA / 'broad_sector_validation.json').read_text('utf-8'))
    assert report['industry_validation_sha256'] == sha(DATA / 'industry_validation.json')
    for name, checksum in report['output_sha256'].items():
        assert sha(DATA / name) == checksum
    for name, info in json.loads((RAW / 'manifest.json').read_text('utf-8')).items():
        assert sha(RAW / name) == info['sha256']
    tiva = rows(RAW / 'oecd_tiva_valu_all.csv')
    px = json.loads((RAW / 'eustat_gva_a38.json').read_text('utf-8'))['dataset']
    dimensions = px['dimension']
    keys = dimensions['id']
    categories = []
    for key in keys:
        index = dimensions[key]['category']['index']
        categories.append(sorted(index, key=index.get) if isinstance(index, dict) else index)
    coordinates = [dict(zip(keys, values)) for values in itertools.product(*categories)]
    assert len(coordinates) == len(px['value'])
    fx = {int(r['date']): r['value'] for r in json.loads((RAW / 'wb_spain_exchange.json').read_bytes())[1]}
    components = rows(DATA / 'broad_sector_components.csv')
    sums, seen = defaultdict(list), set()
    for row in components:
        key = row['iso3'], row['year'], row['activity_code']
        assert key not in seen, 'Overlapping provider component in the six-group sum'
        seen.add(key)
        value = number(row['value_reported'])
        if row['raw_record']:
            index = int(row['raw_record']) - 1
            if row['source'] == 'OECD_TIVA':
                original = tiva[index]
                assert key == (original['REF_AREA'], original['TIME_PERIOD'], original['ACTIVITY'])
                assert original['MEASURE'] == 'VALU' and original['UNIT_MEASURE'] == 'USD' and original['UNIT_MULT'] == '6'
                assert value == number(original['OBS_VALUE']) and row['obs_status'] == original.get('OBS_STATUS', '')
            else:
                coord = coordinates[index]
                assert row['iso3'] == 'ES-PV' and row['year'] == coord['periodo'] and row['activity_code'] == coord['sector']
                assert coord['territorio histórico'] == '_T' and coord['tipo de dato'] == coord['tipo de medida'] == '10'
                assert value == px['value'][index]
                assert row['obs_status'] == px.get('status', {}).get(str(index), '')
        else:
            assert value is None
        sums[row['iso3'], row['year'], row['group']].append(value)
    annual = rows(DATA / 'broad_sector_annual.csv')
    audits = {(r['iso3'], r['year']): r for r in rows(DATA / 'broad_sector_coverage.csv')}
    actual = defaultdict(list)
    for row in annual:
        iso, year, group = row['iso3'], row['year'], row['group']
        parts = sums[iso, year, group]
        amount = sum(parts) * (1000 if iso == 'ES-PV' else 1e6) if all(v is not None for v in parts) else None
        assert equal(number(row['value_source_currency']), amount)
        factor = fx.get(int(year)) if iso == 'ES-PV' else 1
        expected_usd = amount / factor if amount is not None and factor is not None else None
        assert equal(number(row['value_usd']), expected_usd)
        assert number(row['eur_per_usd']) == (factor if iso == 'ES-PV' else None)
        actual[iso, year].append(row)
    for (iso, year), group_rows in actual.items():
        assert len(group_rows) == 6 and len({r['group'] for r in group_rows}) == 6
        audit = audits[iso, year]
        total = number(audit['grouped_gva_source_currency'])
        if audit['coverage_status'] == 'available':
            assert total > 0 and all(number(r['value_source_currency']) is not None for r in group_rows)
            assert equal(total, sum(number(r['value_source_currency']) for r in group_rows))
            assert math.isclose(sum(number(r['share_percent']) for r in group_rows), 100, abs_tol=1e-10)
            for row in group_rows:
                assert equal(number(row['share_percent']), number(row['value_source_currency']) / total * 100)
            index = int(audit['provider_total_raw_record']) - 1
            if iso == 'ES-PV':
                assert coordinates[index]['sector'] == '50'
                original_total = px['value'][index] * 1000
            else:
                assert tiva[index]['ACTIVITY'] == '_T' and tiva[index]['REF_AREA'] == iso and tiva[index]['TIME_PERIOD'] == year
                original_total = float(tiva[index]['OBS_VALUE']) * 1e6
            assert equal(original_total, number(audit['provider_total_gva_source_currency']))
            residual = original_total - total - (number(audit['excluded_U_source_currency']) or 0)
            assert abs(residual) <= float(audit['reconciliation_tolerance'])
        else:
            assert all(r['share_percent'] == '' for r in group_rows)
        if iso == 'ES-PV':
            high = next(r for r in group_rows if r['group'] == 'MHT')
            assert ('07' not in high['source_activity_codes'].split(';')) == (int(year) <= 2020)
            assert bool(high['mapping_note']) == (int(year) <= 2020)
    classification = rows(DATA / 'broad_sector_classification.csv')
    divisions = [d for r in classification for d in r['divisions'].split(';')]
    assert len(divisions) == len(set(divisions)) == 87 and '99' not in divisions
    result = {'built_utc': report['built_utc'], 'verification': 'passed',
              'original_components_checked': len(components), 'grouped_annual_rows_checked': len(annual),
              'no_overlapping_source_components': True, 'shares_and_source_totals_reconciled': True,
              'same_year_exchange_rates_verified': True, 'eustat_historical_combination_preserved': True,
              'validation_sha256': sha(DATA / 'broad_sector_validation.json')}
    (DATA / 'broad_sector_verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
