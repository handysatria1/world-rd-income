"""Archive independently versioned inputs for the user-specified six-sector chart."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from download_data import download
from china_gva import CHINA_SOURCES

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/broad_sector_raw'
TABLE = 'PX_170112_cpib_pib_a_01.px'
EUSTAT = 'https://www.eustat.eus/bankupx/api/v1/en/DB/' + TABLE
SOURCES = {
    'oecd_tiva_valu_all.csv': 'https://sdmx.oecd.org/sti-public/rest/v1/data/OECD.STI.PIE,DSD_TIVA_MAINLV@DF_MAINLV,1.1/VALU...W.USD.A?startPeriod=2000&endPeriod=2025&format=csvfile',
    'oecd_tiva_structure_resolved.xml': CHINA_SOURCES['oecd_tiva_structure_resolved.xml'],
    'oecd_icio_2025_readme.xlsx': CHINA_SOURCES['oecd_icio_2025_readme.xlsx'],
    'eustat_gva_a38_metadata.json': EUSTAT,
    'eustat_gva_a38.json': EUSTAT,
    'eustat_gva_a38.px': 'https://www.eustat.eus/bankupx/Resources/PX/Databases/DB/' + TABLE,
    'wb_spain_exchange.json': 'https://api.worldbank.org/v2/country/ESP/indicator/PA.NUS.FCRF?source=2&date=2000:2025&format=json&per_page=100&footnote=y',
}
REQUESTS = {'eustat_gva_a38.json': {'query': [
    {'code': code, 'selection': {'filter': 'item', 'values': values}}
    for code, values in [('territorio histórico', ['_T']), ('tipo de dato', ['10']), ('tipo de medida', ['10'])]],
    'response': {'format': 'json-stat'}}}


def main(refresh=False, import_cache=None):
    from industry_sources import validate
    RAW.mkdir(parents=True, exist_ok=True)
    old = json.loads((RAW / 'manifest.json').read_text('utf-8')) if (RAW / 'manifest.json').exists() else {}
    caches = [p for p in [import_cache, ROOT / 'data/industry_raw', ROOT / 'data/raw'] if p]

    def obtain(item):
        name, url = item
        query = REQUESTS.get(name)
        body, info = None, None
        if not refresh and name in old:
            body, info = (RAW / name).read_bytes(), old[name]
        elif not refresh:
            for cache in caches:
                provenance = cache / (name + '.provenance.json')
                manifest = cache / 'manifest.json'
                entry = json.loads(provenance.read_text('utf-8')) if provenance.exists() else json.loads(manifest.read_text('utf-8')).get(name) if manifest.exists() else None
                if entry and entry['url'] == url and json.loads(entry.get('request_body', 'null')) == query:
                    body, info = (cache / name).read_bytes(), entry
                    break
        if body is None:
            body, info = download(url, query)
        assert info['url'] == url and json.loads(info.get('request_body', 'null')) == query
        assert hashlib.sha256(body).hexdigest() == info['sha256'] and len(body) == info['bytes']
        if name.endswith('.px'):
            assert b'MATRIX=' in body and b'DATA=' in body
        elif name.endswith('_metadata.json'):
            assert json.loads(body)['variables']
        elif name == 'eustat_gva_a38.json':
            assert json.loads(body)['dataset']['value']
        else:
            validate(name, body)
        print('Verified', name, len(body), flush=True)
        return name, body, info

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(obtain, SOURCES.items()))
    for name, body, _ in responses:
        path = RAW / (name + '.download')
        path.write_bytes(body)
        path.replace(RAW / name)
    (RAW / 'manifest.json').write_text(json.dumps({n: info for n, _, info in responses}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--import-cache', type=Path)
    args = parser.parse_args()
    main(args.refresh, args.import_cache)
