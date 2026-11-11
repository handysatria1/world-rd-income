"""Archive direct government industry inputs with byte hashes and retrieval metadata."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from download_data import download

RAW = Path(__file__).resolve().parent / 'data/government_industry_raw'
SOURCES = {
    'singstat_search_value_added.json': 'https://tablebuilder.singstat.gov.sg/api/table/resourceid?keyword=value%20added&searchOption=all',
    'singstat_M354861.json': 'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M354861',
    'singstat_M354861_metadata.json': 'https://tablebuilder.singstat.gov.sg/api/table/metadata/M354861',
    'singstat_M355181.json': 'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M355181',
    'singstat_M355181_metadata.json': 'https://tablebuilder.singstat.gov.sg/api/table/metadata/M355181',
    'singstat_M015731.json': 'https://tablebuilder.singstat.gov.sg/api/table/tabledata/M015731',
    'singstat_M015731_metadata.json': 'https://tablebuilder.singstat.gov.sg/api/table/metadata/M015731',
    'astar_rie_catalog.html': 'https://www.a-star.edu.sg/news/national-survey-of-rie',
    'ons_gva_catalog.html': 'https://www.ons.gov.uk/economy/grossdomesticproductgdp/datasets/ukgdpolowlevelaggregates/current',
    'ons_gva_2026q2.xlsx': 'https://www.ons.gov.uk/file?uri=/economy/grossdomesticproductgdp/datasets/ukgdpolowlevelaggregates/current/gdplowlevelaggregates2026q2.xlsx',
    'bea_value_added.xlsx': 'https://apps.bea.gov/industry/Release/XLS/GDPxInd/ValueAdded.xlsx',
    'bea_naics_concordance.xlsx': 'https://www.bea.gov/sites/default/files/2023-10/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx',
    'ncses_berd_2024_catalog.html': 'https://ncses.nsf.gov/surveys/business-enterprise-research-development/2024',
    'ncses_berd_2024_tables.zip': 'https://ncses.nsf.gov/pubs/nsf27300/assets/data-tables/nsf27300-data-tables-tables-excels.zip',
    'bok_national_accounts_2025_catalog.html': 'https://www.bok.or.kr/eng/bbs/E0000634/view.do?nttId=10098383&menuNo=400069',
    'bok_national_accounts_2025.xlsx': 'https://www.bok.or.kr/fileSrc/eng/12a66c1f26364a1ca7bd59d812fcef8b/3/bf89aff088c145d28cbc337ad77e7d00.xlsx',
    'bok_national_accounts_2025.pdf': 'https://www.bok.or.kr/fileSrc/eng/12a66c1f26364a1ca7bd59d812fcef8b/2/474683e1e0dc4522b5aae4b8363cf047.pdf',
    'msit_rd_2024_catalog.html': 'https://www.msit.go.kr/bbs/view.do?sCode=user&bbsSeqNo=79&nttSeqNo=3173719',
    'msit_rd_2024.hwpx': 'https://www.msit.go.kr/ssm/file/fileDown.do',
    'nbs_rd_2025.html': 'https://www.stats.gov.cn/sj/zxfb/202610/t20261016_1965512.html',
    'ine_rd_2024_release.html': 'https://www.ine.es/dyngs/Prensa/IMASD2024.htm',
}
FORMS = {'msit_rd_2024.hwpx': {'atchFileNo': '54379', 'fileOrd': '3', 'fileBtn': 'A'}}


def archive(refresh=False):
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / 'manifest.json'
    manifest = json.loads(path.read_text('utf-8')) if path.exists() else {}

    def obtain(item):
        name, url = item
        if name in manifest and not refresh:
            body, info = (RAW / name).read_bytes(), manifest[name]
            assert info['url'] == url
        else:
            if 'tablebuilder.singstat.gov.sg' in url or name in FORMS:
                form = FORMS.get(name)
                request = Request(url, data=urlencode(form).encode() if form else None,
                                  headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*',
                                           'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json'})
                with urlopen(request, timeout=180) as response:
                    body = response.read()
                    info = {'url': url, 'resolved_url': response.url,
                            'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                            'content_type': response.headers.get('Content-Type', ''),
                            'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
                    if form:
                        info.update(method='POST', form=form)
            else:
                body, info = download(url)
        assert hashlib.sha256(body).hexdigest() == info['sha256']
        if name.endswith('.json'):
            payload = json.loads(body)
            if name.startswith('singstat'):
                assert payload['StatusCode'] == 200 and payload['Data'], name
        elif name.endswith('.html'):
            assert b'<html' in body.lower(), name
        elif name.endswith('.pdf'):
            assert body.startswith(b'%PDF'), name
        pending = RAW / (name + '.download')
        pending.write_bytes(body)
        pending.replace(RAW / name)
        print('Archived', name, len(body), flush=True)
        return name, info

    with ThreadPoolExecutor(max_workers=3) as pool:
        for name, info in pool.map(obtain, SOURCES.items()):
            manifest[name] = info
            path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    archive(parser.parse_args().refresh)
