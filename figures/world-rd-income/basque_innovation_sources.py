"""Archive Eustat innovation inputs, definitions and exact PxWeb queries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from download_data import download as fetch_source

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'data/basque_innovation_raw'
API = 'https://www.eustat.eus/bankupx/api/v1/en/DB/'
TABLES = {'researchers': 'PX_043201_cid_res08.px', 'population': 'PX_010154_cepv1_ep17.px'}
SELECTIONS = {
    'researchers': {'sector de ejecución': ['00'], 'ocupación': ['200'], 'sexo': ['10']},
    'population': {'territorio histórico': ['00'], 'sexo': ['10'], 'año de nacimiento': ['1000']},
}
SOURCES, REQUESTS = {}, {}
for key, table in TABLES.items():
    SOURCES[key+'_metadata.json'] = API+table
    SOURCES[key+'.json'] = API+table
    REQUESTS[key+'.json'] = {'query': [{'code': code, 'selection': {'filter': 'item', 'values': values}} for code, values in SELECTIONS[key].items()], 'response': {'format': 'json-stat'}}
SOURCES.update({
    'researchers_table.html': 'https://en.eustat.eus/elementos/tbl0010998_i.html',
    'researchers_methodology.html': 'https://en.eustat.eus/document/datos/fm_043201_i.html',
    'patents.xlsx': 'https://en.eustat.eus/elem/xls0014425_i.xlsx',
    'publications.xlsx': 'https://en.eustat.eus/elem/xls0006196_i.xlsx',
    'patents_table.html': 'https://en.eustat.eus/elementos/tbl0014425_i.html',
    'publications_table.html': 'https://en.eustat.eus/elementos/tbl0006196_i.html',
    'eis_methodology.html': 'https://en.eustat.eus/document/datos/fm_223203_i.html',
    'patents_definition.html': 'https://en.eustat.eus/documentos/elem_26374/definicion.html',
    'publications_definition.html': 'https://en.eustat.eus/documentos/elem_26739/definicion.html',
})

def download(refresh=False):
    RAW.mkdir(exist_ok=True)
    path = RAW / 'manifest.json'
    manifest = json.loads(path.read_text('utf-8')) if path.exists() else {}
    def one(item):
        name, url = item
        if not refresh and name in manifest and (RAW/name).exists():
            assert hashlib.sha256((RAW/name).read_bytes()).hexdigest() == manifest[name]['sha256']
            assert manifest[name]['url'] == url
            if name in REQUESTS:
                assert json.loads(manifest[name]['request_body']) == REQUESTS[name]
            return name, manifest[name]
        body, info = fetch_source(url, REQUESTS.get(name))
        if name.endswith('.json'):
            json.loads(body)
        if name.endswith('.xlsx'):
            assert body.startswith(b'PK')
        (RAW/name).write_bytes(body)
        print(name, len(body), flush=True)
        return name, info
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, info in pool.map(one, SOURCES.items()):
            manifest[name] = info
            path.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    download(parser.parse_args().refresh)
