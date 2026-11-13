"""Join annual country indicators for the national R&D snapshot."""
from math import isfinite


FIRST_YEAR, LAST_YEAR = 2000, 2025
BERD_GROUPS = [
    ('MHT', 'Medium/high-tech manufacturing'),
    ('LMT', 'Low/medium-tech manufacturing'),
    ('KIS', 'Knowledge-intensive services'),
    ('LIS', 'Labour-intensive services'),
    ('UTL', 'Utilities'),
    ('OTH', 'Other production'),
]


def _number(value):
    if value is None or value == '':
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _observation(country, metric, year):
    return country.get('series', {}).get(metric, {}).get(str(year), {})


def build_snapshot_indicators(income, broad, industry, six_group, country_ids=()):
    """Return exact ISO3/year rows; absent or nonannual observations stay missing."""
    group_index = {group['id']: index for index, group in enumerate(broad['groups'])}
    assert {'MHT', 'KIS'} <= group_index.keys()
    berd_ids = {group_id for group_id, _ in BERD_GROUPS}
    assert berd_ids <= {group['id'] for group in six_group['groups']}

    countries = {country['iso'] for country in income['countries']}
    countries.update(country_ids)
    for source in (broad, industry, six_group):
        countries.update(row.get('iso') or row.get('iso3') for row in source.get('rows', source.get('exports', [])))
    countries.discard(None)

    rows = {
        (iso, year): {
            'iso3': iso, 'year': year,
            'gva_mht_percent': None, 'gva_kis_percent': None, 'gva_coverage': '',
            'human_capital_index': None,
            'researchers_fte_total': None, 'researchers_fte_per_million': None,
            'researchers_method': '', 'researchers_rate_method': '',
            'mht_exports_percent_manufactured': None, 'mht_exports_status': '',
            'bachelor_attainment_percent': None,
            **{f'berd_{group_id.lower()}_percent': None for group_id, _ in BERD_GROUPS},
            **{f'berd_{group_id.lower()}_coverage': '' for group_id, _ in BERD_GROUPS},
        }
        for iso in countries for year in range(FIRST_YEAR, LAST_YEAR + 1)
    }

    for country in income['countries']:
        iso = country['iso']
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            target = rows[iso, year]
            target['human_capital_index'] = _number(_observation(country, 'humanCapitalIndex', year).get('v'))
            target['bachelor_attainment_percent'] = _number(_observation(country, 'bachelorAttainment', year).get('v'))

            density = _number(_observation(country, 'researchers', year).get('v'))
            population = _number(_observation(country, 'population', year).get('v'))
            reported_total = _observation(country, 'researchersTotal', year)
            reported_value = _number(reported_total.get('v'))
            if reported_value is not None:
                target['researchers_fte_total'] = reported_value
                target['researchers_method'] = (reported_total.get('provenance') or {}).get('method') or 'Reported FTE total'
            elif density is not None and population is not None and population > 0:
                target['researchers_fte_total'] = density * population / 1_000_000
                target['researchers_method'] = 'Derived from FTE researchers per million × same-year population / 1,000,000'
            target['researchers_fte_per_million'] = density
            if density is not None:
                target['researchers_rate_method'] = 'Reported FTE researchers per million people'
            elif target['researchers_fte_total'] is not None and population is not None and population > 0:
                target['researchers_fte_per_million'] = target['researchers_fte_total'] / population * 1_000_000
                target['researchers_rate_method'] = 'Derived from same-year FTE total / population × 1,000,000'

    for row in broad.get('rows', []):
        key = (row['iso'], int(row['year']))
        if key not in rows:
            continue
        target = rows[key]
        shares = row.get('shares') or []
        target['gva_mht_percent'] = _number(shares[group_index['MHT']]) if len(shares) > group_index['MHT'] else None
        target['gva_kis_percent'] = _number(shares[group_index['KIS']]) if len(shares) > group_index['KIS'] else None
        target['gva_coverage'] = row.get('status', '')

    export_seen = set()
    for row in industry.get('exports', []):
        key = (row['iso3'], int(row['year']))
        assert key not in export_seen, key
        export_seen.add(key)
        if key in rows:
            rows[key]['mht_exports_percent_manufactured'] = _number(row.get('mht_exports_percent_manufactured'))
            rows[key]['mht_exports_status'] = row.get('status', '')

    berd_seen = set()
    for row in six_group.get('rows', []):
        if row.get('group_id') not in berd_ids:
            continue
        key = (row['iso3'], int(row['year']), row['group_id'])
        assert key not in berd_seen, key
        berd_seen.add(key)
        if key[:2] in rows:
            target = rows[key[:2]]
            group = row['group_id'].lower()
            target[f'berd_{group}_percent'] = _number(row.get('berd_share_percent'))
            target[f'berd_{group}_coverage'] = row.get('berd_coverage', '')

    return {
        'schema_version': 1,
        'builtUTC': income.get('builtUTC'),
        'first_year': FIRST_YEAR,
        'last_year': LAST_YEAR,
        'berd_groups': [{'id': group_id, 'label': label} for group_id, label in BERD_GROUPS],
        'join_rule': 'Exact ISO3 and year; no last-observation-carried-forward or other year substitution.',
        'rows': [rows[key] for key in sorted(rows)],
    }
