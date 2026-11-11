"""Independently versioned exports/GVA inputs; never refresh the manuscript snapshot."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from download_data import download
from china_gva import CHINA_SOURCES, obtain_nbs

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data' / 'industry_raw'
WB = 'https://api.worldbank.org/v2'
OECD = 'https://sdmx.oecd.org/public/rest/v1'
UNIDO = 'https://stat.unido.org/portal'
START, END = 2000, 2025
INDICATOR = 'TX.MNF.TECH.ZS.UN'
SOURCES = {
    'wb_countries.json': f'{WB}/country?format=json&per_page=400',
    'wb_mht_metadata.json': f'{WB}/indicator/{INDICATOR}?source=2&format=json',
    'wb_mht_history.json': f'{WB}/country/all/indicator/{INDICATOR}?source=2&date={START}:{END}&format=json&per_page=20000&footnote=y',
    'oecd_gva_structure.xml': f'{OECD}/dataflow/OECD.SDD.NAD/DSD_NAMAIN10@DF_TABLE6/2.0?references=all',
    'oecd_stan_structure.xml': f'{OECD}/dataflow/OECD.STI.PIE/DSD_STAN@DF_STAN_2025/1.0?references=all',
    'oecd_gva_history.csv': f'{OECD}/data/OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE6,2.0/A..S1.S1.B1G._Z.._Z.XDC.V.N.T0301?startPeriod={START}&endPeriod={END}&format=csvfile',
    'oecd_stan_history.csv': f'{OECD}/data/OECD.STI.PIE,DSD_STAN@DF_STAN_2025,1.0/A...B1G.V.XDC?startPeriod={START}&endPeriod={END}&format=csvfile',
    'unido_indstat_metadata.json': f'{UNIDO}/dataset/getDataset/INDSTAT/4',
    'unido_api_schema.json': f'{UNIDO}/v3/api-docs/api',
    **CHINA_SOURCES,
}


def validate(name, body):
    if name.startswith('wb_'):
        meta, rows = json.loads(body)
        assert int(meta['pages']) == 1 and int(meta['page']) == 1
        assert len(rows) == int(meta['total'])
    elif name.endswith('.xml'):
        assert ET.fromstring(body).find('.//{*}DataStructure') is not None
    elif name.endswith('.csv'):
        assert body.lstrip(b'\xef\xbb\xbf').startswith(b'DATAFLOW,') and b'OBS_VALUE' in body.splitlines()[0]
    elif name.endswith('.pdf'):
        assert body.startswith(b'%PDF-')
    elif name.endswith('.xlsx'):
        with ZipFile(io.BytesIO(body)) as archive:
            assert 'xl/workbook.xml' in archive.namelist() and archive.testzip() is None
    elif name.startswith('nbs_'):
        assert json.loads(body)['success']
    elif name == 'unido_indstat_metadata.json':
        data = json.loads(body)
        assert data['id'] and data['countries'] and data['activities'] and data['periods']
        assert any(v['c'] == '20' and v['lang']['en'] == 'Value added' for v in data['variables'])
    elif name.startswith('unido_data_'):
        assert isinstance(json.loads(body)['data'], list)
    elif name.startswith('unido_country_'):
        assert isinstance(json.loads(body), list)
    elif name.startswith('unido_variable_'):
        assert json.loads(body)['code'] == '20'
    else:
        assert json.loads(body)['openapi']


def refresh_inputs(refresh=False, import_cache: Path | None = None):
    RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW / 'manifest.json'
    old = json.loads(manifest_path.read_text('utf-8')) if manifest_path.exists() else {}
    pending, manifest = {}, {}

    def obtain(name, url, query=None):
        if name in manifest:
            info = manifest[name]
            assert info['url'] == url
            return pending.get(name) or (RAW / name).read_bytes()
        if not refresh and name in old:
            body = (RAW / name).read_bytes()
            info = old[name]
            assert info['url'] == url
            assert json.loads(info.get('request_body', 'null')) == query
            assert hashlib.sha256(body).hexdigest() == info['sha256'], name
        elif import_cache and (import_cache / name).exists() and (import_cache / (name + '.provenance.json')).exists():
            body = (import_cache / name).read_bytes()
            info = json.loads((import_cache / (name + '.provenance.json')).read_text('utf-8'))
            assert info['url'] == url and json.loads(info.get('request_body', 'null')) == query
            assert hashlib.sha256(body).hexdigest() == info['sha256']
            pending[name] = body
        else:
            body, info = download(url, query)
            pending[name] = body
        validate(name, body)
        manifest[name] = info
        return body

    # Conservative concurrency for official services. Promotion follows complete validation.
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda item: obtain(*item), SOURCES.items()))
    obtain_nbs(obtain)
    meta = json.loads(pending.get('unido_indstat_metadata.json') or (RAW / 'unido_indstat_metadata.json').read_bytes())
    activities = sorted(a['c'] for a in meta['activities'] if re.fullmatch(r'\d{2}', a['c']))
    periods = [p for p in meta['periods'] if START <= int(p) <= END]
    assert len(activities) == 34 and periods

    def country_inputs(country):
        iso, code = country['iso3'], country['c']
        assert re.fullmatch(r'[A-Z]{3}', iso), country
        query = {'datasetId': meta['id'], 'countryCode': code, 'variableCode': '20',
                 'activityCodes': activities, 'periods': periods, 'fullPrecision': True}
        obtain(f'unido_data_{iso}.json', f'{UNIDO}/dataset/getData', query)
        obtain(f'unido_country_{iso}.json', f"{UNIDO}/dataset/getCountryMetadata/{meta['id']}/{code}")
        obtain(f'unido_variable_{iso}.json', f"{UNIDO}/dataset/getVariableMetadata/{meta['id']}/{code}/20")
        print(f'Validated INDSTAT {iso}', flush=True)

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(country_inputs, meta['countries']))
    for name, body in pending.items():
        target = RAW / name
        temporary = target.with_suffix(target.suffix + '.download')
        temporary.write_bytes(body)
        temporary.replace(target)
    temporary = manifest_path.with_suffix('.download')
    temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    temporary.replace(manifest_path)
    print(f'Archived {len(manifest)} verified industry-source responses', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--import-cache', type=Path, help='Import checksum-verified discovery responses')
    args = parser.parse_args()
    refresh_inputs(args.refresh, args.import_cache)
