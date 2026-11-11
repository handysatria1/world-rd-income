"""Archive main-activity business R&D and exchange-rate inputs independently."""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree as ET

from download_data import download

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/rd_industry_raw'
OECD = 'https://sdmx.oecd.org/public/rest/v1'
EUSTAT = 'https://www.eustat.eus/bankupx/api/v1/en/DB/'
TABLE = 'PX_043201_cid_e05_19t.px'
KEY = '.'.join(['', 'A', '', '', '', '', '', '', 'MA', 'XDC+USD', 'V'])
SOURCES = {
    'oecd_berd_structure.xml': f'{OECD}/dataflow/OECD.STI.STP/DSD_RDS_BERD@DF_BERD_INDU/1.0?references=all',
    'oecd_berd_industry.csv': f'{OECD}/data/OECD.STI.STP,DSD_RDS_BERD@DF_BERD_INDU,1.0/{KEY}?startPeriod=2000&endPeriod=2025&format=csvfilewithlabels',
    'eustat_rd_industry_metadata.json': EUSTAT + TABLE,
    'eustat_rd_industry.json': EUSTAT + TABLE,
    'eustat_rd_industry.px': 'https://www.eustat.eus/bankupx/Resources/PX/Databases/DB/' + TABLE,
    'wb_exchange_history.json': 'https://api.worldbank.org/v2/country/all/indicator/PA.NUS.FCRF?source=2&date=2000:2025&format=json&per_page=20000&footnote=y',
    'wb_exchange_metadata.json': 'https://api.worldbank.org/v2/indicator/PA.NUS.FCRF?source=2&format=json',
}
REQUESTS = {'eustat_rd_industry.json': {'query': [{'code': 'naturaleza', 'selection': {'filter': 'item', 'values': ['10']}}], 'response': {'format': 'json-stat'}}}


def validate(name, body):
    if name.endswith('.xml'):
        assert ET.fromstring(body).find('.//{*}DataStructure') is not None
    elif name.endswith('.csv'):
        assert body.lstrip(b'\xef\xbb\xbf').startswith(b'STRUCTURE,') and b'OBS_VALUE' in body.splitlines()[0]
    elif name.endswith('.px'):
        assert b'DATA=' in body and b'DECIMALS=' in body
    elif name.startswith('wb_'):
        meta, rows = json.loads(body)
        assert int(meta['pages']) == int(meta['page']) == 1 and len(rows) == int(meta['total'])
    elif name.endswith('_metadata.json'):
        assert json.loads(body)['variables']
    else:
        assert 'value' in json.loads(body)['dataset']


def refresh_inputs(refresh=False, import_cache=None):
    RAW.mkdir(exist_ok=True)
    path = RAW / 'manifest.json'
    old = json.loads(path.read_text('utf-8')) if path.exists() else {}
    manifest, pending = {}, {}

    def obtain(item):
        name, url = item
        query = REQUESTS.get(name)
        if not refresh and name in old:
            body, info = (RAW / name).read_bytes(), old[name]
        elif import_cache and (import_cache / name).exists():
            body = (import_cache / name).read_bytes()
            info = json.loads((import_cache / (name + '.provenance.json')).read_text('utf-8'))
        else:
            body, info = download(url, query)
        assert info['url'] == url and json.loads(info.get('request_body', 'null')) == query
        assert hashlib.sha256(body).hexdigest() == info['sha256'] and len(body) == info['bytes']
        validate(name, body)
        pending[name], manifest[name] = body, info
        print('Verified', name, len(body), flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(obtain, SOURCES.items()))
    for name, body in pending.items():
        (RAW / name).write_bytes(body)
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--import-cache', type=Path)
    args = parser.parse_args()
    refresh_inputs(args.refresh, args.import_cache)
