"""Verify an editorial snapshot preserves every data/download byte and embedded JSON."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

CHANGED = {
    'index.html', 'dashboard.js', 'dashboard_ui.js', 'source_captions.js',
    'absorptive_capacity_chart.js', 'income_chart.js', 'innovation_chart.js',
    'research_group_chart.js', 'research_compare_chart.js', 'official_industry_chart.js',
    'view-national.html', 'view-research.html', 'view-research-six.html',
    'view-rd.html', 'view-gva.html', 'view-economy.html', 'view-detail.html', 'view-sources.html',
}


def validate(archive, site):
    changed = []
    embedded = 0
    with zipfile.ZipFile(archive) as old:
        names = {n for n in old.namelist() if not n.endswith('/')}
        assert names == {p.relative_to(site).as_posix() for p in site.rglob('*') if p.is_file()}
        for name in sorted(names):
            before, after = old.read(name), (site / name).read_bytes()
            if before == after:
                continue
            changed.append(name)
            assert name in CHANGED, name
            if name.endswith('.html'):
                pattern = r'<script\b[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>'
                left, right = [re.findall(pattern, value.decode('utf-8'), re.S) for value in [before, after]]
                assert left == right, ('Changed embedded observations', name)
                embedded += len(left)
    assert set(changed) == CHANGED, set(changed) ^ CHANGED
    index = (site / 'index.html').read_text('utf-8')
    assert '<h1>R&amp;D and Economic Development</h1>' in index
    assert 'capacity-period' not in index
    assert 'Country means, 2000–2025' in index
    assert "Income-group means give equal weight to each country's period mean." in index
    assert 'snapshotIndicators' not in (site / 'view-national.html').read_text('utf-8')
    report = {'changed_files': changed, 'all_other_files_byte_identical': True,
              'embedded_JSON_blocks_byte_identical': embedded, 'fixed_capacity_period_preserved': True}
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--site', type=Path, required=True)
    args = parser.parse_args()
    validate(args.archive, args.site)
