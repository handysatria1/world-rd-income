"""Build country and World Bank income-group averages for absorptive-capacity indicators."""
from math import fsum, isfinite


METRICS = [
    {'key': 'researchers', 'slug': 'researcher_density', 'column': 'researcher_density_mean_per_million',
     'label': 'FTE researchers per million people', 'unit': 'researchers per million people'},
    {'key': 'rd', 'slug': 'rd_expenditure', 'column': 'rd_expenditure_mean_percent_gdp',
     'label': 'R&D expenditure intensity', 'unit': '% of GDP'},
    {'key': 'bachelorAttainment', 'slug': 'bachelor_attainment', 'column': 'bachelor_attainment_mean_percent_age_25_plus',
     'label': "Bachelor's attainment, population 25+", 'unit': '% of population ages 25+ (cumulative)'},
    {'key': 'humanCapitalIndex', 'slug': 'human_capital_index', 'column': 'human_capital_index_mean_0_1',
     'label': 'Human Capital Index', 'unit': 'index (0–1)'},
    {'key': 'internetUsers', 'slug': 'internet_users', 'column': 'internet_users_mean_percent',
     'label': 'Internet users', 'unit': '% of population'},
    {'key': 'governmentEffectiveness', 'slug': 'government_effectiveness_score', 'column': 'government_effectiveness_score_mean_0_100',
     'label': 'Government effectiveness score', 'unit': 'score (0–100)'},
    {'key': 'governmentEffectivenessEstimate', 'slug': 'government_effectiveness_estimate', 'column': 'government_effectiveness_estimate_mean',
     'label': 'Government effectiveness estimate (separate WGI series)',
     'unit': 'estimate (approximately −2.5 to +2.5)'},
    {'key': 'publications', 'slug': 'journal_articles', 'column': 'journal_articles_mean_per_year',
     'label': 'Scientific and technical journal articles', 'unit': 'articles per year'},
]
GROUPS = [
    ('HIC', 'High income'), ('UMC', 'Upper-middle income'), ('LMC', 'Lower-middle income'),
    ('MIC', 'Middle income'), ('LIC', 'Low income'),
]
FIRST_YEAR, LAST_YEAR = 2000, 2025


def _country_average(country, metric):
    observations = []
    for raw_year, cell in country.get('series', {}).get(metric['key'], {}).items():
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            continue
        value = cell.get('v') if isinstance(cell, dict) else None
        if FIRST_YEAR <= year <= LAST_YEAR and value is not None:
            value = float(value)
            assert isfinite(value), (country.get('iso'), metric['key'], year, value)
            observations.append((year, value))
    observations.sort()
    n = len(observations)
    return {
        'mean': fsum(value for _, value in observations) / n if n else None,
        'n': n,
        'first_year': observations[0][0] if n else None,
        'last_year': observations[-1][0] if n else None,
    }


def build_absorptive_capacity(payload):
    """Return an integrated country-mean table and group means for every WB vintage.

    Each country's mean uses its available, non-missing annual values in 2000–2025.
    Income-group means are unweighted means of those country means, so each economy
    contributes equally regardless of its observation count. No missing years are filled.
    """
    current_vintage = payload['currentVintage']
    vintages = list(dict.fromkeys([current_vintage, *payload.get('historicalVintages', [])]))
    countries = sorted((c for c in payload['countries'] if not c.get('region')),
                       key=lambda c: (c['name'].casefold(), c['iso']))
    country_rows, country_json = [], []

    for country in countries:
        current_code = country.get('current', 'UNK')
        current_label = dict(GROUPS).get(current_code, 'Unclassified')
        averages = {metric['key']: _country_average(country, metric) for metric in METRICS}
        row = {
            'iso3': country['iso'], 'economy': country['name'], 'geography_type': 'economy',
            'current_classification_vintage': current_vintage,
            'current_income_code': current_code, 'current_income_group': current_label,
        }
        for metric in METRICS:
            average = averages[metric['key']]
            row[metric['column']] = average['mean']
            row[metric['slug'] + '_n_years'] = average['n']
            row[metric['slug'] + '_first_year'] = average['first_year']
            row[metric['slug'] + '_last_year'] = average['last_year']
        country_rows.append(row)
        country_json.append({
            'iso3': country['iso'], 'economy': country['name'],
            'current_income_code': current_code, 'current_income_group': current_label,
            'history': country.get('history', {}), 'averages': averages,
        })

    group_rows = []
    for vintage in vintages:
        membership = {}
        for country in countries:
            if vintage == current_vintage:
                code = country.get('current', 'UNK')
            else:
                code = country.get('history', {}).get(vintage, 'UNK')
            membership.setdefault(code, []).append(country['iso'])
        averages_by_iso = {row['iso3']: row['averages'] for row in country_json}
        for code, label in GROUPS:
            members = (membership.get('UMC', []) + membership.get('LMC', [])
                       if code == 'MIC' else membership.get(code, []))
            for metric in METRICS:
                means = [
                    averages_by_iso[iso][metric['key']]['mean'] for iso in members
                    if averages_by_iso[iso][metric['key']]['mean'] is not None
                ]
                group_rows.append({
                    'classification_vintage': vintage, 'income_group_code': code,
                    'income_group': label, 'metric': metric['key'], 'indicator': payload['indicators'][metric['key']]['code'],
                    'unit': metric['unit'],
                    'mean_of_country_means': fsum(means) / len(means) if means else None,
                    'economies_with_data': len(means), 'economies_in_group': len(members),
                    'coverage_percent': 100 * len(means) / len(members) if members else None,
                    'included_iso3': ';'.join(sorted(
                        iso for iso in members if averages_by_iso[iso][metric['key']]['mean'] is not None)),
                    'missing_iso3': ';'.join(sorted(
                        iso for iso in members if averages_by_iso[iso][metric['key']]['mean'] is None)),
                })

    return {
        'country_rows': country_rows,
        'group_rows': group_rows,
        'json': {
            'schema_version': 1, 'builtUTC': payload['builtUTC'],
            'first_year': FIRST_YEAR, 'last_year': LAST_YEAR,
            'current_vintage': current_vintage, 'classification_vintages': vintages,
            'method': 'Arithmetic mean of each economy’s observed annual values, 2000–2025; group value is the unweighted mean of country means. Missing years are not filled. Regional observations are excluded.',
            'metrics': [
                {'key': metric['key'], 'label': metric['label'],
                 'code': payload['indicators'][metric['key']]['code'], 'unit': metric['unit'],
                 'average_column': metric['column']}
                for metric in METRICS
            ],
            'countries': country_json, 'group_averages': group_rows,
        },
    }
