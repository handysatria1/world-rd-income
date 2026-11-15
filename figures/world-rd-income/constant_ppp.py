"""Archive and attach WDI NY.GDP.PCAP.PP.KD without modifying existing series."""
import csv
import hashlib
import json
import math
from pathlib import Path

from wdi_bulk import load_wdi_observations

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/income_raw'
INDICATOR = 'NY.GDP.PCAP.PP.KD'
METRIC = 'pppConstant'
UNIT = 'constant 2021 international $'


def archive_inputs(raw=RAW, refresh=False):
    # Share the official dated WDI archive with the innovation pipeline, rather
    # than relying on a frequently unavailable API or estimating a deflator.
    from download_data import download
    from income_sources import WDI_CATALOG_URL, wdi_archive_url

    raw = Path(raw)
    raw.mkdir(parents=True, exist_ok=True)
    path = raw / 'manifest.json'
    manifest = json.loads(path.read_text('utf-8')) if path.exists() else {}
    for name in ['wdi_catalog.html', 'wdi_csv.zip']:
        if not refresh and name in manifest and (raw / name).exists():
            assert hashlib.sha256((raw / name).read_bytes()).hexdigest() == manifest[name]['sha256'], name
            continue
        url = WDI_CATALOG_URL if name.endswith('.html') else wdi_archive_url((raw / 'wdi_catalog.html').read_bytes())
        body, info = download(url, timeout=300)
        (raw / name).write_bytes(body)
        manifest[name] = info
        path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    assert manifest['wdi_csv.zip']['url'] == wdi_archive_url((raw / 'wdi_catalog.html').read_bytes())
    return manifest


def attach_constant_ppp(data, raw=RAW):
    """Exact ISO3/year joins; region values and missing annual cells stay blank."""
    raw = Path(raw)
    manifest = json.loads((raw / 'manifest.json').read_text('utf-8'))
    info = manifest['wdi_csv.zip']
    assert hashlib.sha256((raw / 'wdi_csv.zip').read_bytes()).hexdigest() == info['sha256']
    observations = load_wdi_observations(raw / 'wdi_csv.zip', {INDICATOR}, data['firstYear'], data['lastYear'])[INDICATOR]
    return attach_observations(data, observations, info)


def attach_observations(data, observations, info):
    countries = {country['iso']: country for country in data['countries']}
    for country in countries.values():
        country['gdp'][METRIC] = {}
    seen, audit = set(), []
    for row in observations:
        assert row['indicator']['id'] == INDICATOR
        assert 'constant 2021 international $' in row['indicator']['value'], row['indicator']
        iso, year = row['countryiso3code'], int(row['date'])
        assert data['firstYear'] <= year <= data['lastYear']
        assert (iso, year) not in seen, (iso, year)
        seen.add((iso, year))
        if iso not in countries or countries[iso].get('geographyType') == 'region':
            continue
        value = row['value']
        if value is not None:
            assert math.isfinite(value) and value > 0, (iso, year, value)
            countries[iso]['gdp'][METRIC][str(year)] = {
                'v': value, 'flags': row.get('obs_status', ''), 'note': row.get('footnote', ''),
                'source': INDICATOR, 'sourceRecord': row['_source_record'],
            }
        audit.append({'iso3': iso, 'economy': countries[iso]['name'], 'year': year,
                      'indicator': INDICATOR, 'unit': UNIT, 'value': value,
                      'source_record': row['_source_record'], 'source_url': info['url'],
                      'retrieved_utc': info['retrieved_utc'], 'source_sha256': info['sha256']})
    data['constantPPP'] = {'indicator': INDICATOR, 'unit': UNIT, 'source': info,
                           'observations': sum(len(c['gdp'][METRIC]) for c in countries.values()),
                           'method': 'Exact ISO3 and calendar-year joins. No interpolation, substitution or regional proxy.'}
    data.setdefault('sources', {})['income_raw/wdi_csv.zip'] = info
    return audit


def write_audit(path, rows):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: '' if value is None else value for key, value in row.items()} for row in rows)


if __name__ == '__main__':
    archive_inputs()
