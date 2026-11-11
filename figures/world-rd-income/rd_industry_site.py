"""Package the verified six-group R&D/economy join and self-contained explorer."""
import csv
import json
import re
from html import escape
from pathlib import Path

from industry_site import sha
from rd_industry import OUTPUTS

ROOT = Path(__file__).parent
DOWNLOADS = [*OUTPUTS, 'rd_industry_economy.xlsx', 'rd_industry_explorer.json', 'rd_industry_validation.json', 'rd_industry_verification.json']


def build_rd_industry_site(destination):
    data, raw = ROOT / 'data', ROOT / 'data/rd_industry_raw'
    report = json.loads((data / 'rd_industry_validation.json').read_text('utf-8'))
    check = json.loads((data / 'rd_industry_verification.json').read_text('utf-8'))
    assert report['validation'] == check['verification'] == 'passed'
    assert report['built_utc'] == check['built_utc']
    assert check['validation_sha256'] == sha(data / 'rd_industry_validation.json')
    assert report['source_manifest_sha256'] == sha(raw / 'manifest.json')
    for file, digest in {**report['input_sha256'], **report['output_sha256']}.items():
        assert sha(data / file) == digest
    manifest = json.loads((raw / 'manifest.json').read_text('utf-8'))
    fields = sorted({k for info in manifest.values() for k in info})
    with (destination / 'rd_industry_source_inventory.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['source_file', *fields])
        writer.writeheader()
        for file, info in sorted(manifest.items()):
            assert sha(raw / file) == info['sha256'] and (raw / file).stat().st_size == info['bytes']
            writer.writerow({'source_file': file, **info})
    (destination / 'rd_industry_source_manifest.json').write_bytes((raw / 'manifest.json').read_bytes())
    for file in DOWNLOADS:
        (destination / file).write_bytes((data / file).read_bytes())
    (destination / 'RD_INDUSTRY.md').write_bytes((ROOT / 'RD_INDUSTRY.md').read_bytes())
    serialized = (data / 'rd_industry_explorer.json').read_text('utf-8').replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    document = (ROOT / 'rd-industry.html').read_text('utf-8')
    style = re.search(r'<style>(.*?)</style>', (ROOT / 'sector-economy.html').read_text('utf-8'), re.S)[1]
    for marker, value in {'__STYLE__': style, '__BUILD_UTC__': escape(report['built_utc']), '__DATA__': serialized,
                          '__CORE__': (ROOT / 'rd_industry_core.js').read_text('utf-8'), '__CHART__': (ROOT / 'rd_industry_chart.js').read_text('utf-8')}.items():
        assert document.count(marker) == 1
        document = document.replace(marker, value)
    (destination / 'rd-industry.html').write_text(document, encoding='utf-8')
