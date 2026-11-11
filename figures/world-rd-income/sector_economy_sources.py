"""Independently archive employment and goods-export inputs for sector comparisons."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from download_data import download
from industry_sources import validate

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/sector_economy_raw'
EUSTAT = 'https://www.eustat.eus/bankupx/api/v1/en/DB/'
TABLES = {'employment': 'PX_170112_cpib_pib_a_08.px',
          'export_sectors': 'PX_143101_cece_ar241.px',
          'export_groups': 'PX_143101_cece_ar242.px',
          'exports_nace': 'PX_143101_cece_ar17.px'}
PRODUCTS = ['_T', 'CPA_2_1_C', *['CPA_2_1_C' + str(d) for d in range(10, 33)]]
SOURCES = {
    'oecd_tim_structure.xml': 'https://sdmx.oecd.org/public/rest/v1/dataflow/OECD.STI.PIE/DSD_TIM_2025@DF_TIM_2025/1.0?references=all',
    'oecd_tim_employment.csv': 'https://sdmx.oecd.org/public/rest/v1/data/OECD.STI.PIE,DSD_TIM_2025@DF_TIM_2025,1.0/EMPN...W..A?startPeriod=2000&endPeriod=2025&format=csvfile',
    'oecd_tim_readme_page.html': 'https://www.oecd.org/en/data/datasets/trade-in-employment.html',
    'oecd_btige_structure.xml': 'https://sdmx.oecd.org/sti-public/rest/v1/dataflow/OECD.STI.PIE/DSD_BTIGE@DF_BTIGE/1.0?references=all',
    'oecd_btige_exports.csv': 'https://sdmx.oecd.org/sti-public/rest/v1/data/OECD.STI.PIE,DSD_BTIGE@DF_BTIGE,1.0/A..X.TOTAL.' + '+'.join(PRODUCTS) + '.W.USD?startPeriod=2000&endPeriod=2025&format=csvfile',
    'oecd_btige_readme.xlsx': 'https://webfs-sti.oecd.org/files/STI-PIE/BTIGE/OECD-Bilateral-Trade-in-Goods-End-use-ReadMe.xlsx',
    'eustat_export_sectors_metadata.json': EUSTAT + 'PX_143101_cece_ar241.px',
}
REQUESTS = {}
for name, table in TABLES.items():
    SOURCES['eustat_' + name + '_metadata.json'] = EUSTAT + table
    SOURCES['eustat_' + name + '.json'] = EUSTAT + table
    if name in {'employment', 'export_groups'}:
        SOURCES['eustat_' + name + '.px'] = 'https://www.eustat.eus/bankupx/Resources/PX/Databases/DB/' + table
    selection = [('territorio histórico', ['_T']), ('tipo de empleo', ['50']), ('tipo de dato', ['10'])] if name == 'employment' else [('flujo', ['10']), ('territorio histórico', ['00']), ('área', ['100']), ('unidad', ['10'])]
    REQUESTS['eustat_' + name + '.json'] = {'query': [{'code': code, 'selection': {'filter': 'item', 'values': values}} for code, values in selection], 'response': {'format': 'json-stat'}}


def main(refresh=False, import_cache=None):
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = RAW / 'manifest.json'
    old = json.loads(manifest.read_text('utf-8')) if manifest.exists() else {}

    def obtain(item):
        name, url = item
        query = REQUESTS.get(name)
        if not refresh and name in old:
            body, info = (RAW / name).read_bytes(), old[name]
        elif not refresh and import_cache and (import_cache / name).exists():
            body = (import_cache / name).read_bytes()
            info = json.loads((import_cache / (name + '.provenance.json')).read_text('utf-8'))
        else:
            body, info = download(url, query)
        assert info['url'] == url and json.loads(info.get('request_body', 'null')) == query
        assert hashlib.sha256(body).hexdigest() == info['sha256'] and len(body) == info['bytes']
        if name.endswith('.html'):
            assert b'Trade in Employment' in body and b'consistent with output and value added' in body
        elif name.endswith('.px'):
            assert b'DATA=' in body and b'MATRIX=' in body
        elif name.endswith('_metadata.json'):
            assert json.loads(body)['variables']
        elif name.startswith('eustat_'):
            assert json.loads(body)['dataset']['value']
        else:
            validate(name, body)
        print('Verified', name, len(body), flush=True)
        return name, body, info

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(obtain, SOURCES.items()))
    for name, body, _ in responses:
        temporary = RAW / (name + '.download')
        temporary.write_bytes(body)
        temporary.replace(RAW / name)
    temporary = manifest.with_suffix('.download')
    temporary.write_text(json.dumps({name: info for name, _, info in responses}, indent=2) + '\n', encoding='utf-8')
    temporary.replace(manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--import-cache', type=Path)
    args = parser.parse_args()
    main(args.refresh, args.import_cache)
