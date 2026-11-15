"""Apply only editorial source changes to the validated UI publication.

Never rebuild data or copy whole modules: HEAD contains unpublished features.
Run from the repository root with --archive and --destination.
"""
import argparse
import difflib
import hashlib
import re
from pathlib import Path
import subprocess
import zipfile

BASE = '09a40142195e2f907659e4cb2552f352e34ec521'
ROOT = Path('figures/world-rd-income')
TARGETS = {
    'dashboard.html': ['index.html'],
    'explorer.html': ['view-national.html'],
    'explorer.js': ['view-national.html'],
    'research-groups.html': ['view-research.html', 'view-research-six.html'],
    'rd-industry.html': ['view-rd.html'],
    'broad-sectors.html': ['view-gva.html'],
    'sector-economy.html': ['view-economy.html'],
    'industry.html': ['view-detail.html'],
    'data_sources.html': ['view-sources.html'],
    'rd_industry_chart.js': ['view-rd.html'],
    'rd_coverage.js': ['view-rd.html'],
    'sector_economy_chart.js': ['view-economy.html'],
    'broad_sector_chart.js': ['view-gva.html'],
}


def replace_html(text, before, after):
    """Change text nodes only, preserving generated attributes and embedded data."""
    a, b = re.split('(<[^>]+>)', before), re.split('(<[^>]+>)', after)
    assert len(a) == len(b), (before[:80], after[:80])
    seen = set()
    for left, right in zip(a, b):
        if left == right:
            continue
        if (left, right) in seen:
            continue
        seen.add((left, right))
        assert left and not left.startswith('<'), (left, right)
        if '__BUILD_UTC__' in left:
            pattern = re.escape(left).replace('__BUILD_UTC__', '(.*?)').replace('__RD_BUILD_UTC__', '(.*?)')
            match = re.search(pattern, text)
            assert match
            replacement = right.replace('__BUILD_UTC__', match[1]).replace('__RD_BUILD_UTC__', match[2])
            text = text[:match.start()] + replacement + text[match.end():]
        else:
            left = {'Integrated country means (2000–2025)': 'Integrated country averages', 'Income-group means by classification vintage (2000–2025)': 'Income-group averages by classification vintage'}.get(left, left)
            assert '>' + left + '<' in text, left[:200]
            text = text.replace('>' + left + '<', '>' + right + '<')
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    assert hashlib.sha256(args.archive.read_bytes()).hexdigest() == '12c0878afdd3aef6ce98dd5f760e8091df085a4830d03cfb7afbecd9a86d1aad'
    args.destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        archive.extractall(args.destination)
    failures = []
    names = subprocess.check_output(['git', 'diff', BASE, '--name-only', '--', str(ROOT)], text=True).splitlines()
    for filename in names:
        source = Path(filename)
        if source.suffix not in ['.js', '.html'] or source.name.startswith('test_'):
            continue
        old = subprocess.check_output(['git', 'show', BASE + ':' + source.as_posix()]).decode('utf-8')
        new = source.read_text('utf-8')
        for target in TARGETS.get(source.name, [source.name]):
            path = args.destination / target
            if not path.exists():
                continue
            text = path.read_text('utf-8')
            for op, i, j, k, l in difflib.SequenceMatcher(None, old.splitlines(True), new.splitlines(True), autojunk=False).get_opcodes():
                if op == 'equal':
                    continue
                before = ''.join(old.splitlines(True)[i:j]).rstrip('\r\n')
                after = ''.join(new.splitlines(True)[k:l]).rstrip('\r\n')
                if op == 'insert':
                    anchor = old.splitlines(True)[i-1].rstrip('\r\n')
                    assert text.count(anchor) == 1
                    text = text.replace(anchor, anchor + '\n' + after)
                elif before and before in text:
                    text = text.replace(before, after)
                elif source.suffix == '.html':
                    text = replace_html(text, before, after)
                elif source.name == 'explorer.js' and 'Additional country-indicator' in before:
                    text = text.replace('"Plotted data"', '"Chart data"')
                    left = 'Income in ${unit()}. Search filters this table and highlights points; it does not change the sample or regression. CSV includes windows, missing years and flags.'
                    right = 'GDP per capita is expressed in ${unit()}. Search filters the table and highlights chart observations without changing the analytical sample or regression. The CSV records R&D periods, missing years and source flags.'
                    assert left in text
                    text = text.replace(left, right)
                elif source.name == 'dashboard.js' and "$('year-help')" in before:
                    # The deployed capacity branch is deliberately fixed-period.
                    left = before.split("id==='absorptive-capacity'?")[0].lstrip()
                    right = after.split("id==='absorptive-capacity'?")[0].lstrip()
                    assert left in text
                    text = text.replace(left, right)
                    for left, right in [('Select two years below to compare income groups.', 'Select two comparison years for the income-group analysis.'), ('Data providers, methods and downloads.', 'Data sources, calculation methods and downloads.'), ('Latest available uses the most recent year with the data required for this chart. Reporting years are shown; a selected year uses only that year.', '‘Latest available’ selects the most recent year with the observations required for the chart. Reporting years are displayed. Selecting a specific year restricts the comparison to that year.'), ('Select the time period below. Economy selections apply across views.', 'Select the analysis period below. Economy selections apply across views.')]:
                        assert left in text
                        text = text.replace(left, right)
                else:
                    failures.append((source.name, target, before, after))
            path.write_text(text, encoding='utf-8', newline='\n')
    for source, target, before, after in failures:
        print('\nUNMATCHED', source, '->', target, '\nOLD:', before[:1800], '\nNEW:', after[:1800])
    assert not failures, f'{len(failures)} source differences need explicit deployed-context handling'
    fixed = {
        'index.html': [
            ('Country-level period averages', 'Country means, 2000–2025'),
            ('Country values are arithmetic means of available annual observations from 2000–2025. Each income-group value is the unweighted mean of its countries’ period means; the count and coverage are shown. Missing years are not filled. These descriptive averages do not identify causal absorptive-capacity thresholds.', "Country means are calculated from available annual observations over 2000–2025. Income-group means give equal weight to each country's period mean. Country counts and coverage are reported. Missing years are not imputed. These descriptive statistics do not establish causal thresholds for absorptive capacity."),
        ],
        'absorptive_capacity_chart.js': [
            ('Classification: ${shownVintage}${combine?', 'Income classification: ${shownVintage}${combine?'),
            ('Group averages weight each country equally; n is the number of country means available. ${populatedGroups} of ${groups.length} displayed income groups have observations.', 'Each country receives equal weight; n denotes the number of available country means. Observations are available for ${populatedGroups} of ${groups.length} displayed income groups.'),
            ('Researchers are FTE per million people; R&D is expenditure as % of GDP; WGI estimate is separate from the 0–100 score; journal articles are annual counts.', 'Researchers are measured in full-time equivalents per million people; R&D expenditure is expressed as a percentage of GDP; the WGI estimate is distinct from the 0–100 absolute score; journal articles are annual counts.'),
            ('${data.countries.length} country-level period means for ${metric.label}. Each mean and its observed-year count/range are shown; the integrated CSV includes all indicators at once. The selected income vintage changes group labels, not country values.', 'Country means for ${metric.label} are reported for ${data.countries.length} economies. The table includes each mean, the number of observed years and the first and last observation years. The integrated CSV contains all indicators. Changing the income-classification vintage changes group membership, not country means.'),
        ],
    }
    for target, replacements in fixed.items():
        path = args.destination / target
        text = path.read_text('utf-8')
        for before, after in replacements:
            assert text.count(before) == 1, before
            text = text.replace(before, after)
        path.write_text(text, encoding='utf-8', newline='\n')
    # Preserve embedded observation payloads byte-for-byte, including line endings.
    with zipfile.ZipFile(args.archive) as archive:
        for path in args.destination.glob('*.html'):
            original = archive.read(path.name).decode('utf-8')
            current = path.read_bytes().decode('utf-8')
            pattern = r'(<script\b[^>]*type=["\']application/json["\'][^>]*>)(.*?)(</script>)'
            old_payloads = [match[1] for match in re.findall(pattern, original, re.S)]
            new_payloads = [match[1] for match in re.findall(pattern, current, re.S)]
            assert len(old_payloads) == len(new_payloads)
            for old_payload, new_payload in zip(old_payloads, new_payloads):
                assert old_payload.replace('\r\n', '\n') == new_payload.replace('\r\n', '\n')
                current = current.replace(new_payload, old_payload, 1)
            if old_payloads:
                path.write_bytes(current.encode('utf-8'))


if __name__ == '__main__':
    main()
