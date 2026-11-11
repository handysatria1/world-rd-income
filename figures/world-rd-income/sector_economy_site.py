"""Package independently validated employment, productivity and goods-export charts."""
import csv
import json
from html import escape
from pathlib import Path

from industry_site import sha
from sector_economy import OUTPUTS
from sector_economy_figures import EXAMPLES

ROOT = Path(__file__).resolve().parent
DOWNLOADS = [*OUTPUTS, 'sector_economy.xlsx', 'sector_economy_explorer.json', 'sector_economy_validation.json', 'sector_economy_verification.json']
FIGURES = [f'sector_{kind}_{year}.{ext}' for kind, year, _ in EXAMPLES for ext in ['png', 'svg', 'pdf']]


def build_sector_economy_site(destination):
    data, raw = ROOT / 'data', ROOT / 'data/sector_economy_raw'
    report = json.loads((data / 'sector_economy_validation.json').read_text('utf-8'))
    verification = json.loads((data / 'sector_economy_verification.json').read_text('utf-8'))
    assert report['validation'] == verification['verification'] == 'passed'
    assert report['built_utc'] == verification['built_utc']
    assert verification['validation_sha256'] == sha(data / 'sector_economy_validation.json')
    assert report['broad_sector_validation_sha256'] == sha(data / 'broad_sector_validation.json')
    assert report['source_manifest_sha256'] == sha(raw / 'manifest.json')
    for name, checksum in report['output_sha256'].items():
        assert sha(data / name) == checksum, name
    manifest = json.loads((raw / 'manifest.json').read_text('utf-8'))
    fields = sorted({k for info in manifest.values() for k in info})
    with (destination / 'sector_economy_source_inventory.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['source_file', *fields])
        writer.writeheader()
        for name, info in sorted(manifest.items()):
            assert sha(raw / name) == info['sha256'] and (raw / name).stat().st_size == info['bytes']
            writer.writerow({'source_file': name, **info})
    (destination / 'sector_economy_source_manifest.json').write_bytes((raw / 'manifest.json').read_bytes())
    for name in DOWNLOADS:
        (destination / name).write_bytes((data / name).read_bytes())
    for name in FIGURES:
        (destination / name).write_bytes((ROOT / 'output' / name).read_bytes())
    (destination / 'SECTOR_ECONOMY.md').write_bytes((ROOT / 'SECTOR_ECONOMY.md').read_bytes())
    links = ''.join('<li>' + escape(title) + f' ({year}): ' + ' / '.join(f'<a href="sector_{kind}_{year}.{ext}">{ext.upper()}</a>' for ext in ['png', 'svg', 'pdf']) + '</li>' for kind, year, title in EXAMPLES)
    serialized = (data / 'sector_economy_explorer.json').read_text('utf-8').replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    document = (ROOT / 'sector-economy.html').read_text('utf-8')
    for marker, value in {'__FIGURES__': links, '__BUILD_UTC__': escape(report['built_utc']), '__DATA__': serialized,
                          '__CORE__': (ROOT / 'sector_economy_core.js').read_text('utf-8'), '__CHART__': (ROOT / 'sector_economy_chart.js').read_text('utf-8')}.items():
        assert document.count(marker) == 1
        document = document.replace(marker, value)
    (destination / 'sector-economy.html').write_text(document, encoding='utf-8')
