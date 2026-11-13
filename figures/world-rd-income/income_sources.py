"""Archive official World Bank classifications and WDI innovation indicators."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
from zipfile import ZipFile

from openpyxl import load_workbook

from download_data import download as fetch_source

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/income_raw'
WDI_CATALOG_URL = 'https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators'
WDI_ARCHIVE_NAME = 'wdi_csv.zip'
HCI_ARCHIVE_NAME = 'humanCapitalIndex.zip'
HCI_ARCHIVE_URL = 'https://databank.worldbank.org/data/download/HCI_CSV.zip'
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
WDI_METRICS = {key for key in INDICATORS
               if key not in {'governmentEffectiveness', 'governmentEffectivenessEstimate', 'humanCapitalIndex'}}
SOURCES = {
    'wdi_catalog.html': WDI_CATALOG_URL,
    'classification_current.xlsx': 'https://ddh-openapi.worldbank.org/resources/DR0095333/download',
    'classification_history.xlsx': 'https://ddh-openapi.worldbank.org/resources/DR0095334/download',
    'classification_definitions.html': 'https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups',
    HCI_ARCHIVE_NAME: HCI_ARCHIVE_URL,
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
    SOURCES[key + '_metadata.json'] = f'https://api.worldbank.org/v2/indicator/{code}?{source_param.lstrip("&") + "&" if source_param else ""}format=json'


def wdi_archive_url(body):
    """Find the dated CSV archive linked by the World Bank's official WDI catalog."""
    text = body.decode('utf-8', errors='replace').replace('\\/', '/')
    urls = set(re.findall(
        r'https://datacatalogfiles\.worldbank\.org/ddh-published/0037712/DR0095335/'
        r'WDI_CSV_\d{4}_\d{2}_\d{2}\.zip', text, re.IGNORECASE))
    assert len(urls) == 1, f'Expected one current WDI CSV download on the catalog page, found {sorted(urls)}'
    return urls.pop()


def download(refresh=False):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / 'manifest.json'
    manifest = json.loads(path.read_text('utf-8')) if path.exists() else {}
    legacy_files = []
    legacy_names = [*(key + '.json' for key in sorted(WDI_METRICS | {'humanCapitalIndex'})),
                    'governmentEffectivenessEstimate.json', 'countries.json']
    for legacy_name in legacy_names:
        legacy_info = manifest.get(legacy_name)
        legacy_path = RAW / legacy_name
        if legacy_info and legacy_path.exists():
            assert hashlib.sha256(legacy_path.read_bytes()).hexdigest() == legacy_info['sha256'], legacy_name
            legacy_files.append((legacy_name, legacy_path))

    catalog_path = RAW / 'wdi_catalog.html'
    if not refresh and 'wdi_catalog.html' in manifest and catalog_path.exists():
        assert hashlib.sha256(catalog_path.read_bytes()).hexdigest() == manifest['wdi_catalog.html']['sha256']
        catalog_body = catalog_path.read_bytes()
    else:
        catalog_body, catalog_info = fetch_source(WDI_CATALOG_URL)
        assert b'World Development Indicators' in catalog_body
        catalog_path.write_bytes(catalog_body)
        manifest['wdi_catalog.html'] = catalog_info
        path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    bulk_url = wdi_archive_url(catalog_body)
    source_items = [(name, url) for name, url in SOURCES.items() if name != 'wdi_catalog.html']
    source_items.append((WDI_ARCHIVE_NAME, bulk_url))

    def one(item):
        name, url = item
        if not refresh and name in manifest and (RAW / name).exists():
            assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == manifest[name]['sha256']
            return name, manifest[name]
        attempts = 2 if name == WDI_ARCHIVE_NAME else 4
        for attempt in range(attempts):
            try:
                body, info = fetch_source(url, timeout=300 if name == WDI_ARCHIVE_NAME else 180,
                                          retries=2 if name == WDI_ARCHIVE_NAME else 3)
                if name.endswith('.json'):
                    obj = json.loads(body)
                    assert isinstance(obj, list) and len(obj) == 2, obj
                    assert int(obj[0]['pages']) == 1 and len(obj[1]) == int(obj[0]['total'])
                if name.endswith('.zip'):
                    with ZipFile(io.BytesIO(body)) as archive:
                        assert archive.testzip() is None
                        members = archive.namelist()
                        if name == 'governmentEffectiveness.zip':
                            assert any(n.startswith('API_GOV_WGI_GE_SC_') and n.endswith('.csv') for n in members)
                        elif name == WDI_ARCHIVE_NAME:
                            assert any(n.rsplit('/', 1)[-1].upper() == 'WDICSV.CSV' for n in members)
                            release = re.search(r'WDI_CSV_(\d{4}_\d{2}_\d{2})\.zip$', url, re.IGNORECASE)
                            assert release, url
                            info['release_date'] = f'{release[1][:4]}-{release[1][4:6]}-{release[1][6:]}'
                        elif name == HCI_ARCHIVE_NAME:
                            assert any(n.rsplit('/', 1)[-1].upper() == 'HCIDATA.CSV' for n in members)
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
                if attempt == attempts - 1:
                    raise
                time.sleep(2 ** attempt)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, info in pool.map(one, source_items):
            manifest[name] = info
            path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    for name, legacy_path in legacy_files:
        legacy_path.unlink()
    for name in legacy_names:
        manifest.pop(name, None)
    path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    download(parser.parse_args().refresh)
