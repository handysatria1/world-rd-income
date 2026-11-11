"""Package the validated six-sector chart and independently versioned downloads."""
import csv
import json
from html import escape
from pathlib import Path

from industry_site import sha

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ['broad_sector_annual.csv', 'broad_sector_components.csv', 'broad_sector_coverage.csv',
             'broad_sector_classification.csv', 'broad_sector_gva.xlsx', 'broad_sector_explorer.json',
             'broad_sector_validation.json', 'broad_sector_verification.json']
FIGURES = ['broad_sector_gva_latest.' + ext for ext in ['png', 'svg', 'pdf']]


def build_broad_sector_site(destination):
    data, raw = ROOT / 'data', ROOT / 'data/broad_sector_raw'
    report = json.loads((data / 'broad_sector_validation.json').read_text('utf-8'))
    verify = json.loads((data / 'broad_sector_verification.json').read_text('utf-8'))
    assert report['validation'] == verify['verification'] == 'passed'
    assert report['built_utc'] == verify['built_utc']
    assert verify['validation_sha256'] == sha(data / 'broad_sector_validation.json')
    assert report['industry_validation_sha256'] == sha(data / 'industry_validation.json')
    for name, checksum in report['output_sha256'].items():
        assert sha(data / name) == checksum, name
    manifest = json.loads((raw / 'manifest.json').read_text('utf-8'))
    fields = sorted({k for info in manifest.values() for k in info})
    with (destination / 'broad_sector_source_inventory.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['source_file', *fields])
        writer.writeheader()
        for name, info in sorted(manifest.items()):
            assert sha(raw / name) == info['sha256'] and (raw / name).stat().st_size == info['bytes']
            writer.writerow({'source_file': name, **info})
    (destination / 'broad_sector_source_manifest.json').write_bytes((raw / 'manifest.json').read_bytes())
    for name in DOWNLOADS:
        (destination / name).write_bytes((data / name).read_bytes())
    for name in FIGURES:
        (destination / name).write_bytes((ROOT / 'output' / name).read_bytes())
    (destination / 'BROAD_SECTORS.md').write_bytes((ROOT / 'BROAD_SECTORS.md').read_bytes())
    with (data / 'broad_sector_classification.csv').open(encoding='utf-8-sig') as handle:
        classification = ''.join('<tr>' + ''.join('<td>' + escape(r[k].replace(';', ', ')) + '</td>' for k in ['label', 'sections', 'divisions']) + '</tr>' for r in csv.DictReader(handle))
    serialized = (data / 'broad_sector_explorer.json').read_text('utf-8').replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    document = (ROOT / 'broad-sectors.html').read_text('utf-8')
    for marker, value in {'__CLASSIFICATION__': classification, '__BUILD_UTC__': escape(report['built_utc']),
                          '__DATA__': serialized, '__CORE__': (ROOT / 'broad_sector_core.js').read_text('utf-8'),
                          '__CHART__': (ROOT / 'broad_sector_chart.js').read_text('utf-8')}.items():
        assert document.count(marker) == 1
        document = document.replace(marker, value)
    (destination / 'broad-sectors.html').write_text(document, encoding='utf-8')
