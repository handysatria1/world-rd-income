"""Archive official World Bank classifications and WDI innovation indicators."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import time
from zipfile import ZipFile

from openpyxl import load_workbook

from download_data import download as fetch_source

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/income_raw'
INDICATORS = {
    'rd': ('GB.XPD.RSDV.GD.ZS', 'R&D expenditure', '% of GDP'),
    'researchers': ('SP.POP.SCIE.RD.P6', 'Researchers in R&D', 'per million people'),
    'patents': ('IP.PAT.RESD', 'Patent applications, residents', 'applications'),
    'patentsNonresident': ('IP.PAT.NRES', 'Patent applications, nonresidents', 'applications'),
    'publications': ('IP.JRN.ARTC.SC', 'Scientific and technical journal articles', 'articles'),
    'population': ('SP.POP.TOTL', 'Population', 'people'),
    'internetUsers': ('IT.NET.USER.ZS', 'Internet users', '% of population'),
    'governmentEffectiveness': ('GOV_WGI_GE_SC', 'Government Effectiveness', 'score (0-100)'),
    'governmentEffectivenessEstimate': ('GOV_WGI_GE.EST', 'Government effectiveness estimate', 'estimate (approximately -2.5 to +2.5)'),
    'humanCapitalIndex': ('HD.HCI.OVRL', 'Human Capital Index', 'index (0-1)'),
    'bachelorAttainment': ('SE.TER.CUAT.BA.ZS', "Bachelor's attainment, population 25+", '% of population ages 25+ (cumulative)'),
}
SOURCES = {
    'countries.json': 'https://api.worldbank.org/v2/country?format=json&per_page=1000',
    'classification_current.xlsx': 'https://ddh-openapi.worldbank.org/resources/DR0095333/download',
    'classification_history.xlsx': 'https://ddh-openapi.worldbank.org/resources/DR0095334/download',
    'classification_definitions.html': 'https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups',
}
INDICATOR_SOURCE_PARAMS = {'governmentEffectivenessEstimate': '&source=3', 'humanCapitalIndex': ''}
WGI_DATASET_URL = ('https://www.worldbank.org/content/dam/sites/govindicators/doc/'
                   'wgidataset_with_sourcedata-2026.xlsx')
for key, (code, _, _) in INDICATORS.items():
    if key == 'governmentEffectiveness':
        SOURCES[key + '.zip'] = f'https://api.worldbank.org/v2/en/indicator/{code}?downloadformat=csv'
        continue
    source_param = INDICATOR_SOURCE_PARAMS.get(key, '&source=2')
    if key == 'governmentEffectivenessEstimate':
        # The 2026 WGI estimates workbook is the official dataset behind this
        # indicator; its World Bank API endpoint repeatedly returned HTTP 502.
        SOURCES[key + '.xlsx'] = WGI_DATASET_URL
    else:
        SOURCES[key + '.json'] = f'https://api.worldbank.org/v2/country/all/indicator/{code}?date=2000:2025{source_param}&format=json&per_page=20000&footnote=y'
    SOURCES[key + '_metadata.json'] = f'https://api.worldbank.org/v2/indicator/{code}?{source_param.lstrip("&") + "&" if source_param else ""}format=json'


def download(refresh=False):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / 'manifest.json'
    manifest = json.loads(path.read_text('utf-8')) if path.exists() else {}
    manifest.pop('governmentEffectivenessEstimate.json', None)

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
                if name.endswith('.zip'):
                    with ZipFile(io.BytesIO(body)) as archive:
                        assert archive.testzip() is None
                        assert any(n.startswith('API_GOV_WGI_GE_SC_') and n.endswith('.csv') for n in archive.namelist())
                if name.endswith('.xlsx'):
                    with ZipFile(io.BytesIO(body)) as archive:
                        assert archive.testzip() is None and 'xl/workbook.xml' in archive.namelist()
                    if name == 'governmentEffectivenessEstimate.xlsx':
                        book = load_workbook(io.BytesIO(body), read_only=True, data_only=True)
                        assert 'ge' in book.sheetnames
                        book.close()
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
