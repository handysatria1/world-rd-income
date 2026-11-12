"""Publish the hash-pinned, frozen study without refreshing or refitting it."""
import csv
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'analysis/2026-11-11'


def build_analysis_site(destination):
    destination = Path(destination)
    pin = json.loads((SNAPSHOT / 'snapshot.json').read_text('utf-8'))
    package = SNAPSHOT / 'Global_RD_Income_Study.zip'
    assert hashlib.sha256(package.read_bytes()).hexdigest() == pin['sha256'], 'Study package hash mismatch'
    target = destination / 'analysis/2026-11-11'
    target.mkdir(parents=True, exist_ok=True)
    files = []

    def put(name, body):
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        files.append(path.relative_to(destination).as_posix())

    with ZipFile(package) as archive:
        manifest = json.loads(archive.read('Delivery_Manifest.json'))
        for item in manifest['files']:
            assert hashlib.sha256(archive.read(item['path'])).hexdigest() == item['sha256'], item['path']
        def rows(name):
            return list(csv.DictReader(io.StringIO(archive.read('Data/' + name + '.csv').decode('utf-8-sig'))))
        payload = {
            'snapshot': pin,
            'summary': json.loads(archive.read('Data/summary.json')),
            'countries': rows('global_countries_2022'),
            'correlations': rows('income_correlations'),
            'pairs': rows('all_near_intensity_pairs'),
            'manufacturing': rows('manufacturing_standardisation'),
        }
        assert len(payload['countries']) == payload['summary']['n'] == 83
        assert len(payload['pairs']) == payload['summary']['near_pairs'] == 120
        assert len(payload['manufacturing']) == 19
        downloads = []
        for item in manifest['files']:
            name = item['path']
            # Publish authored documents and analytical tables, not research PDF copies.
            if (name.startswith('Data/') and '/' not in name[5:] and name.endswith(('.csv', '.json'))) or name.startswith(('Figures/', 'Policy_Brief/Figures/')) or name in {
                'Paper.pdf', 'Paper.docx', 'Paper.md', 'Global_Analysis.xlsx', 'Key_Findings.md',
                'README.md', 'Research_Audit.md', 'Data_Dictionary.md', 'Literature_Review.md', 'Journal_Argument_Guide.md',
                'Policy_Brief/Policy_Brief.pdf', 'Policy_Brief/Policy_Brief.docx',
                'Policy_Brief/Policy_Brief_Evidence.xlsx', 'Policy_Brief/Comparability.md',
                'Policy_Brief/Patterns_and_Hypotheses.md', 'Methods/Methods_Guide.pdf',
                'Methods/Methods_Guide.docx', 'Methods/Worked_Example.xlsx',
            }:
                put(name, archive.read(name))
                downloads.append(name)
        payload['downloads'] = downloads
        put('Delivery_Manifest.json', archive.read('Delivery_Manifest.json'))
    put(package.name, package.read_bytes())
    put('snapshot.json', (SNAPSHOT / 'snapshot.json').read_bytes())
    put('study.json', (json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8'))
    for name in ['analysis.html', 'analysis.js']:
        (destination / name).write_bytes((ROOT / name).read_bytes())
        files.append(name)
    put('integration_validation.json', (json.dumps({
        'validation': 'passed', 'package_sha256': pin['sha256'],
        'verified_payload_files': len(manifest['files']), 'countries': 83,
        'near_intensity_pairs': 120, 'manufacturing_economies': 19,
        'scope': 'Package integrity and exact publication of frozen analytical results; no live-data substitution or causal inference.',
    }, indent=2) + '\n').encode('utf-8'))
    return files


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    print(json.dumps(build_analysis_site(parser.parse_args().destination), indent=2))
