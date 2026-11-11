"""Archive official World Bank classifications and WDI innovation indicators."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

from download_data import download as fetch_source

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/income_raw'
INDICATORS = {
    'rd': ('GB.XPD.RSDV.GD.ZS', 'R&D expenditure', '% of GDP'),
    'researchers': ('SP.POP.SCIE.RD.P6', 'Researchers in R&D', 'per million people'),
    'patents': ('IP.PAT.RESD', 'Patent applications, residents', 'applications'),
    'patentsNonresident': ('IP.PAT.NRES', 'Patent applications, nonresidents', 'applications'),
    'publications': ('IP.JRN.ARTC.SC', 'Scientific and technical journal articles', 'articles'),
}
SOURCES = {
    'classification_current.xlsx': 'https://ddh-openapi.worldbank.org/resources/DR0095333/download',
    'classification_history.xlsx': 'https://ddh-openapi.worldbank.org/resources/DR0095334/download',
    'classification_definitions.html': 'https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups',
}
for key, (code, _, _) in INDICATORS.items():
    SOURCES[key + '.json'] = f'https://api.worldbank.org/v2/country/all/indicator/{code}?source=2&date=2000:2025&format=json&per_page=20000&footnote=y'
    SOURCES[key + '_metadata.json'] = f'https://api.worldbank.org/v2/indicator/{code}?source=2&format=json'


def download(refresh=False):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / 'manifest.json'
    manifest = json.loads(path.read_text('utf-8')) if path.exists() else {}

    def one(item):
        name, url = item
        if not refresh and name in manifest and (RAW / name).exists():
            assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == manifest[name]['sha256']
            return name, manifest[name]
        for attempt in range(4):
            try:
                body, info = fetch_source(url)
                if name.endswith('.json'):
                    obj = json.loads(body)
                    assert isinstance(obj, list) and len(obj) == 2, obj
                    assert int(obj[0]['pages']) == 1 and len(obj[1]) == int(obj[0]['total'])
                if name.endswith('.xlsx'):
                    assert body.startswith(b'PK'), 'Not an XLSX response'
                (RAW / name).write_bytes(body)
                if name.endswith('.json'):
                    info['api_lastupdated'] = obj[0].get('lastupdated', '')
                print(name, len(body), flush=True)
                return name, info
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, info in pool.map(one, SOURCES.items()):
            manifest[name] = info
            path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    download(parser.parse_args().refresh)
