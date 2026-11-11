"""Package the validated, independently timestamped exports/value-added supplement."""
import csv
import hashlib
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ['mht_exports_annual.csv', 'rd_income_exports_annual.csv', 'rd_income_exports_snapshot.csv',
             'gva_isic2.csv', 'gva_other_activities.csv', 'gva_country_year_coverage.csv',
             'industry_country_coverage.csv', 'gva_metadata.csv', 'gva_definitions.csv',
             'industry_exports_gva.xlsx', 'industry_validation.json', 'industry_verification.json']


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def build_industry_site(destination: Path, rd_build: str):
    data, raw = ROOT / 'data', ROOT / 'data/industry_raw'
    report = json.loads((data / 'industry_validation.json').read_text('utf-8'))
    verify = json.loads((data / 'industry_verification.json').read_text('utf-8'))
    assert report['rd_income_build_utc'] == rd_build
    assert verify['built_utc'] == report['built_utc'] and verify['verification'] == 'passed'
    assert verify['industry_validation_sha256'] == sha(data / 'industry_validation.json')
    assert all(v == 'passed' for v in report['validation'].values())
    for name, digest in {**report['output_sha256'], **report['baseline_file_sha256']}.items():
        assert sha(data / name) == digest, name
    manifest_bytes = (raw / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    fields = sorted({k for info in manifest.values() for k in info})
    entries = []
    with (destination / 'industry_source_inventory.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['source_file', *fields])
        writer.writeheader()
        for name, info in sorted(manifest.items()):
            assert sha(raw / name) == info['sha256']
            writer.writerow({'source_file': name, **info})
            entries.append('<details><summary>' + escape(name) + '</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">' +
                           escape(json.dumps(info, indent=2)) + '</pre></details>')
    (destination / 'industry_source_manifest.json').write_bytes(manifest_bytes)
    for name in DOWNLOADS:
        (destination / name).write_bytes((data / name).read_bytes())
    (destination / 'INDUSTRY_DATA.md').write_bytes((ROOT / 'INDUSTRY_DATA.md').read_bytes())
    coverage = [f'<div><strong>{report["exports"]["economies"]}</strong>economies with export shares<br><span class="muted">Latest year: {report["exports"]["latest_year"]}</span></div>',
                f'<div><strong>{report["gva_union_economies"]}</strong>economies with some single-division value added</div>',
                f'<div><strong>{report["gva"]["OECD_NA"]["economies_with_divisions"]}</strong>economies with some OECD national-accounts divisions<br><span class="muted">{verify["native_single_division_economies_excluding_section_equivalents"]["OECD_NA"]} have explicit division codes; remaining coverage uses one-division sections</span></div>']
    serialized = (data / 'industry_explorer.json').read_text('utf-8').replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    document = (ROOT / 'industry.html').read_text('utf-8')
    for marker, value in {'__BUILD_UTC__': escape(report['built_utc']), '__RD_BUILD_UTC__': escape(rd_build),
                          '__COVERAGE__': ''.join(coverage), '__SOURCE_ENTRIES__': '\n'.join(entries),
                          '__INDUSTRY_DATA__': serialized}.items():
        assert document.count(marker) == 1
        document = document.replace(marker, value)
    (destination / 'industry.html').write_text(document, encoding='utf-8')
