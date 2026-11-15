"""Package the editorial site after the documented browser/Node tests pass."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from test_wording_release import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-archive', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.base_archive, args.site)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / 'pages-site.zip'
    size = sum(p.stat().st_size for p in args.site.rglob('*') if p.is_file())
    assert size < 300_000_000
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(args.site.rglob('*')):
            if path.is_file():
                z.write(path, path.relative_to(args.site).as_posix())
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    report.update(commit=commit, sha256=sha, site_bytes=size,
                  base_release='snapshot-2026-11-15-dashboard-ui',
                  validation_suites=['10 Node suites', '31-route UI and baseline table comparison',
                                     '31-route source captions and SVG/PNG downloads',
                                     'Three GDP bases, exact observations and CSV',
                                     'Longer SVG wording bounds and 27 byte-identical generated CSV exports', 'Byte-preservation audit'])
    (args.output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    notes = f'''# R&D and Economic Development

Approved dashboard-wide professional wording in British English. **Editorial release only; no data refresh.**

- Main title: R&D and Economic Development.
- Clearer navigation, chart and table headings, controls, observation instructions, statistical explanations, source captions and methods documentation across all 31 views.
- Source guide documents all three existing GDP per capita measures, including constant-2021 PPP.
- All existing datasets, embedded JSON observations, downloads and static figures are byte-identical to the validated UI release. Calculations, exact economy/year joins, missing-data treatment, source qualifications and income-group styling are unchanged.
- Published absorptive-capacity means remain fixed at 2000–2025, with equal country weights. No unpublished selectable-period or enriched-snapshot functionality is introduced.
- Regression checks passed: all ten Node suites; all 31 route table values, flags and order (only approved heading and documentation changes allowed); UI/share/presentation/mobile; sources and SVG/PNG exports; all three GDP options and exact WDI values; 27 byte-identical generated CSV exports; SVG wording bounds; byte-preservation audit.
- Editorial source and reproducible staging: commit {commit}, `figures/world-rd-income/WORDING_RELEASE.md`.
- Base release: snapshot-2026-11-15-dashboard-ui. Existing data vintages, provenance and archived research packages are retained.
- Website size: {size:,} bytes.
- pages-site.zip SHA-256: `{sha}`
'''
    (args.output / 'release-notes.md').write_text(notes, encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
