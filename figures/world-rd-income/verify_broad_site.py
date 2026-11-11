"""Check the broad-sector workbook, embedded page, links and reproducible ZIP."""
import argparse
import csv
import hashlib
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from openpyxl import load_workbook


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and (href := dict(attrs).get('href')):
            url = urlsplit(href)
            if not url.scheme and not url.netloc and url.path:
                self.links.append(unquote(url.path))


def verify(stage):
    workbook = load_workbook(stage / 'broad_sector_gva.xlsx', read_only=True, data_only=True)
    checked = 0
    for sheet in workbook:
        with (stage / (sheet.title + '.csv')).open(encoding='utf-8-sig', newline='') as handle:
            csv_rows = list(csv.reader(handle))
        excel_rows = sheet.iter_rows(values_only=True)
        assert list(next(excel_rows)) == csv_rows[0]
        count = 0
        for count, values in enumerate(excel_rows, 1):
            assert count < len(csv_rows)
            for excel, value in zip(values, csv_rows[count]):
                if isinstance(excel, (int, float)) and not isinstance(excel, bool):
                    assert value and math.isclose(excel, float(value), rel_tol=1e-12, abs_tol=1e-6)
                else:
                    assert ('' if excel is None else str(excel)) == value, (sheet.title, count, excel, value)
        assert count == len(csv_rows) - 1
        checked += count
    workbook.close()
    view = json.loads((stage / 'broad_sector_explorer.json').read_text('utf-8'))
    document = (stage / 'view-gva.html').read_text('utf-8')
    embedded = json.loads(re.search(r'<script id="broad-data" type="application/json">(.*?)</script>', document, re.S)[1])
    assert view == embedded
    assert not re.search(r'__(?:CLASSIFICATION|BUILD_UTC|DATA|CORE|CHART)__', document)
    with (stage / 'broad_sector_annual.csv').open(encoding='utf-8-sig', newline='') as handle:
        annual = {(r['iso3'], int(r['year']), r['group']): r for r in csv.DictReader(handle)}
    for row in view['rows']:
        for i, group in enumerate(view['groups']):
            original = annual[row['iso'], row['year'], group['id']]
            for key, field in [('shares', 'share_percent'), ('amounts', 'value_usd')]:
                assert row[key][i] == (float(original[field]) if original[field] else None)
            assert row['status'] == original['coverage_status']
    sector_view = json.loads((stage / 'sector_economy_explorer.json').read_text('utf-8'))
    sector_page = (stage / 'view-economy.html').read_text('utf-8')
    assert json.loads(re.search(r'<script id="sector-data" type="application/json">(.*?)</script>', sector_page, re.S)[1]) == sector_view
    assert not re.search(r'__(?:FIGURES|BUILD_UTC|DATA|CORE|CHART)__', sector_page)
    sector_report = json.loads((stage / 'sector_economy_verification.json').read_text('utf-8'))
    assert sector_report['verification'] == 'passed'
    sector_build = json.loads((stage / 'sector_economy_validation.json').read_text('utf-8'))
    for filename, checksum in sector_build['output_sha256'].items():
        assert hashlib.sha256((stage / filename).read_bytes()).hexdigest() == checksum
    rd_view = json.loads((stage / 'rd_industry_explorer.json').read_text('utf-8'))
    rd_page = (stage / 'view-rd.html').read_text('utf-8')
    assert json.loads(re.search(r'<script id="rd-industry-data" type="application/json">(.*?)</script>', rd_page, re.S)[1]) == rd_view
    assert not re.search(r'__(?:STYLE|BUILD_UTC|DATA|CORE|CHART)__', rd_page)
    rd_report = json.loads((stage / 'rd_industry_verification.json').read_text('utf-8'))
    assert rd_report['verification'] == 'passed'
    for filename, checksum in json.loads((stage / 'rd_industry_validation.json').read_text('utf-8'))['output_sha256'].items():
        assert hashlib.sha256((stage / filename).read_bytes()).hexdigest() == checksum
    pages = ['index.html', 'industry.html', 'sources.html', 'broad-sectors.html', 'sector-economy.html', 'rd-industry.html',
             'view-national.html','view-rd.html','view-economy.html','view-gva.html','view-research.html','view-detail.html','view-sources.html']
    links_checked = 0
    for page in pages:
        links = Links()
        links.feed((stage / page).read_text('utf-8'))
        for link in links.links:
            assert (stage / link).is_file(), (page, link)
            links_checked += 1
    with ZipFile(stage / 'world-rd-income.zip') as archive:
        assert archive.testzip() is None
        members = set(archive.namelist())
        assert len(members) == len(archive.namelist())
        for page in pages:
            links = Links()
            links.feed(archive.read('world-rd-income/' + page).decode('utf-8'))
            for link in links.links:
                assert 'world-rd-income/' + link in members, (page, link)
        raw_checked = 0
        for folder in ['raw', 'industry_raw', 'broad_sector_raw', 'sector_economy_raw', 'rd_industry_raw']:
            prefix = 'world-rd-income/figures/world-rd-income/data/' + folder + '/'
            manifest = json.loads(archive.read(prefix + 'manifest.json'))
            for name, info in manifest.items():
                with archive.open(prefix + name) as handle:
                    assert hashlib.file_digest(handle, 'sha256').hexdigest() == info['sha256'], name
                raw_checked += 1
    result = {'validation': 'passed', 'workbook_data_rows_checked': checked,
              'embedded_economy_years_checked': len(view['rows']), 'site_links_checked': links_checked,
              'research_zip_members': len(members), 'archived_response_hashes_checked': raw_checked,
              'site_files': len(list(stage.iterdir())), 'sector_economy_verification': sector_report,
              'rd_industry_verification': rd_report}
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    verify(parser.parse_args().site)
