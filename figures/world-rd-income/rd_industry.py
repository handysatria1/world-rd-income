"""Classify industry R&D and join exact economy/year/group economic observations."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from openpyxl import Workbook
from basque_rd import px_rows
from broad_sectors import DATA, GROUPS, DISPLAY, write
from industry_data import read_csv, digest
from rd_industry_sources import RAW, SOURCES
from rd_industry_mapping import Classification, aggregate
from sector_field_rd import FLAGS, normalized_value

OUTPUTS = ['rd_industry_annual.csv', 'rd_economy_joined.csv', 'rd_economy_context.csv',
           'rd_industry_components.csv', 'rd_industry_coverage.csv', 'rd_industry_mapping.csv', 'rd_industry_fx.csv']
CURRENCY_COUNTRIES = {'ARS': 'ARG', 'AUD': 'AUS', 'BGN': 'BGR', 'CAD': 'CAN', 'CHF': 'CHE', 'CLP': 'CHL',
                      'CNY': 'CHN', 'CZK': 'CZE', 'DKK': 'DNK', 'GBP': 'GBR', 'HUF': 'HUN', 'ILS': 'ISR',
                      'ISK': 'ISL', 'JPY': 'JPN', 'KRW': 'KOR', 'MXN': 'MEX', 'NOK': 'NOR', 'NZD': 'NZL',
                      'PLN': 'POL', 'RON': 'ROU', 'SEK': 'SWE', 'SGD': 'SGP', 'TRY': 'TUR'}
SOURCE_NAMES = {'OECD_RDS': 'OECD RDS BERD · main activity', 'EUSTAT_NATIVE': 'Eustat companies + PNPI · native branches'}
GROUP_IDS = [g['id'] for g in GROUPS]


def number(value):
    return None if value in ['', None] else float(value)


def build():
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for file, info in manifest.items():
        assert info['url'] == SOURCES[file] and digest(RAW / file) == info['sha256']
    classification = Classification(RAW / 'oecd_berd_structure.xml')
    sector = json.loads((DATA / 'sector_economy_explorer.json').read_text('utf-8'))
    economic = {(r['iso'], r['year']): r for r in sector['rows']}
    broad = json.loads((DATA / 'broad_sector_explorer.json').read_text('utf-8'))
    gva = {(r['iso'], r['year']): r for r in broad['rows']}
    country_names = {r['iso3']: r['country'] for r in read_csv(DATA / 'industry_country_coverage.csv')}
    fx_raw = json.loads((RAW / 'wb_exchange_history.json').read_bytes())[1]
    exchange = {(r['countryiso3code'], int(r['date'])): (r, i) for i, r in enumerate(fx_raw, 1)}
    fx_records = {}

    def conversion(iso, year, currency):
        key = iso, year, currency
        if key in fx_records:
            return fx_records[key]
        source_iso = 'ESP' if currency == 'EUR' else CURRENCY_COUNTRIES.get(currency, '')
        assert currency in ['EUR', 'USD', 'TWD'] or source_iso == iso, (iso, currency)
        raw, record = exchange.get((source_iso, year), ({}, None))
        factor = 1 if currency == 'USD' else raw.get('value')
        # OECD historical EUR amounts are already euro-denominated; pre-adoption local rates are not used.
        # RON/TRY are modern currencies: unsupported pre-redenomination years stay unconverted.
        if currency in ['RON', 'TRY'] and year < 2005:
            factor = None
        assert factor is None or factor > 0
        result = {'iso3': iso, 'year': year, 'currency': currency, 'local_per_usd': factor,
                  'fx_reference_area': source_iso, 'source_file': 'wb_exchange_history.json' if source_iso else '',
                  'raw_record': record, 'obs_status': raw.get('obs_status', ''), 'footnote': raw.get('footnote', ''),
                  'method': 'USD identity' if currency == 'USD' else 'same-year EUR rate from Spain; currency-code matched' if currency == 'EUR' else 'same-year official currency per USD; currency-code matched' if source_iso else 'no verified exchange-rate series',
                  'availability': 'available' if factor is not None else 'missing_conversion'}
        fx_records[key] = result
        return result

    components, blocks, excluded = [], defaultdict(dict), set()
    for i, row in enumerate(read_csv(RAW / 'oecd_berd_industry.csv'), 1):
        for field, value in {'MEASURE': 'B', 'SECT_PERF': 'BES', 'SECT_FUND': '_T', 'TYPE_COST': '_T', 'SIZE_CLASS': '_Z',
                             'FREQ': 'A', 'CRITERIA': 'MA', 'UNIT_MEASURE': 'XDC', 'PRICE_BASE': 'V', 'BASE_PER': ''}.items():
            assert row[field] == value, (field, row[field])
        iso, year, code = row['REF_AREA'], int(row['TIME_PERIOD']), row['ACTIVITY']
        if iso not in country_names:
            excluded.add(iso)
            continue
        assert row['Economic activity'] == classification.labels[code]
        amount, availability = normalized_value(row)
        includes = any(row[k] in ['W', 'O2'] for k in FLAGS)
        eligible = amount is not None and not includes
        classes = classification.coverage(code)
        matching = [g for g, target in classification.groups.items() if classes <= target]
        component = {'iso3': iso, 'economy': country_names[iso], 'year': year, 'source': 'OECD_RDS',
                     'scope': 'BERD', 'criteria': 'MA', 'activity_code': code, 'activity_label': row['Economic activity'],
                     'value_reported': row['OBS_VALUE'], 'unit_multiplier': int(row['UNIT_MULT']), 'currency': row['CURRENCY'],
                     'price_base': row['PRICE_BASE'], 'source_decimals': int(row['DECIMALS']), 'amount_local': amount, 'availability': availability,
                     'aggregation_eligible': eligible, 'eligibility_note': 'includes unspecified other categories' if includes else availability,
                     'mapping_group': matching[0] if matching else '', 'rounding_local': .5 * 10 ** (int(row['UNIT_MULT']) - int(row['DECIMALS'])),
                     **{flag: row[flag] for flag in FLAGS}, 'source_file': 'oecd_berd_industry.csv', 'raw_record': i}
        assert code not in blocks[iso, year]
        blocks[iso, year][code] = component
        components.append(component)
    for i, (coords, labels, value, flag, _) in enumerate(px_rows(RAW / 'eustat_rd_industry.json'), 1):
        year, code = int(coords['periodo']), coords['rama de actividad']
        if year < 2000:
            continue
        assert coords['naturaleza'] == '10'
        component = {'iso3': 'ES-PV', 'economy': 'Basque Country', 'year': year, 'source': 'EUSTAT_NATIVE',
                     'scope': 'companies + private non-profit institutions', 'criteria': 'native branches; exact ISIC4 bridge unresolved',
                     'activity_code': code, 'activity_label': labels['rama de actividad'], 'value_reported': value, 'unit_multiplier': 3,
                     'currency': 'EUR', 'price_base': 'V', 'source_decimals': 0, 'amount_local': value * 1000 if value is not None else None,
                     'availability': 'available' if value is not None else 'missing_source_value', 'aggregation_eligible': False,
                     'eligibility_note': 'native branch classification crosses requested groups; no verified exact bridge',
                     'mapping_group': '', 'rounding_local': 500, **{k: '' for k in FLAGS},
                     'source_file': 'eustat_rd_industry.json', 'raw_record': i}
        component['OBS_STATUS'] = flag
        blocks['ES-PV', year][code] = component
        components.append(component)
    annual, coverage, view = [], [], []
    economies = sorted(set(c['iso'] for c in sector['countries']) | {k[0] for k in blocks})
    for iso in economies:
        for year in range(2000, 2026):
            cells = blocks.get((iso, year), {})
            basque = iso == 'ES-PV'
            source = 'EUSTAT_NATIVE' if basque else 'OECD_RDS'
            scope = 'companies + PNPI' if basque else 'BERD'
            currencies = {r['currency'] for r in cells.values()}
            assert len(currencies) <= 1
            currency = next(iter(currencies), '')
            fx = conversion(iso, year, currency) if currency else {}
            rate = fx.get('local_per_usd')
            total_row = cells.get('000' if basque else '_T', {})
            total = total_row.get('amount_local')
            grouped = {g: None for g in GROUP_IDS} if basque else aggregate(cells, classification)
            valid_groups = [r for r in grouped.values() if r is not None]
            assigned = sum(r['value'] for r in valid_groups) if valid_groups else None
            remainder = total - (assigned or 0) if total is not None else None
            complete_groups = [g for g, r in grouped.items() if r is not None and r['classes'] == classification.groups[g]]
            status = ('no_industry_observations' if not cells else 'native_classification_unresolved' if basque else
                      'missing_reported_total' if total is None else 'nonpositive_reported_total' if total <= 0 else
                      'negative_reconciliation_remainder' if remainder < 0 else 'fully_classified' if len(complete_groups) == 6 and remainder == 0 else
                      'partially_classified' if assigned is not None else 'no_classifiable_components')
            usable = total is not None and total > 0 and remainder is not None and remainder >= 0
            rd_rows = []
            for group in GROUPS:
                gid = group['id']
                result = grouped[gid]
                local = result['value'] if result else None
                complete = gid in complete_groups
                terms = result['terms'] if result else {}
                covered = result['classes'] if result else frozenset()
                flags = ';'.join(sorted({f'{f}={cells[code][f]}' for code in terms for f in FLAGS if cells[code][f]}))
                row = {'iso3': iso, 'economy': country_names[iso], 'year': year, 'group': gid, 'group_label': group['label'],
                       'rd_source': source, 'rd_scope': scope, 'classification_criteria': 'main activity' if not basque else 'native branches; bridge unresolved',
                       'assigned_rd_local': local, 'currency': currency, 'assigned_rd_usd': local / rate if local is not None and rate else None,
                       'group_complete': complete, 'group_coverage': 'complete' if complete else 'partial' if result else 'unavailable',
                       'group_rd_total_usd': local / rate if complete and rate else None,
                       'assigned_share_reported_rd_percent': local / total * 100 if local is not None and usable else None,
                       'reported_rd_total_local': total, 'reported_rd_total_usd': total / rate if total is not None and rate else None,
                       'unallocated_rd_local': remainder, 'unallocated_rd_usd': remainder / rate if remainder is not None and rate else None,
                       'coverage_status': status, 'source_terms_json': json.dumps(terms, sort_keys=True, separators=(',', ':')),
                       'source_records': ';'.join(str(cells[c]['raw_record']) for c in sorted(terms)),
                       'source_file': 'eustat_rd_industry.json' if basque else 'oecd_berd_industry.csv',
                       'covered_isic4_classes': ';'.join(sorted(covered)), 'missing_isic4_classes': ';'.join(sorted(classification.groups[gid] - covered)),
                       'source_flags': flags, 'local_per_usd': rate, 'fx_source_file': fx.get('source_file', ''),
                       'fx_raw_record': fx.get('raw_record'), 'fx_reference_area': fx.get('fx_reference_area', ''),
                       'value_status': 'derived_disjoint_public_components' if result else 'not_derived',
                       'note': 'Partial assigned amounts are not full sector totals. U is excluded; unsplittable S-U aggregates remain unallocated.' if not basque else 'Native branches mix chemistry/refining, production/utilities and services; companies also include PNPI. Exact six-sector allocation unavailable.'}
                annual.append(row)
                rd_rows.append(row)
            coverage.append({'iso3': iso, 'economy': country_names[iso], 'year': year, 'rd_source': source, 'rd_scope': scope,
                             'coverage_status': status, 'currency': currency, 'reported_total_local': total, 'assigned_local': assigned,
                             'unallocated_local': remainder, 'assigned_share_percent': (assigned or 0) / total * 100 if usable else None,
                             'complete_groups': ';'.join(complete_groups), 'source_cells': len(cells),
                             'eligible_cells': sum(r['aggregation_eligible'] for r in cells.values()),
                             'total_source_file': total_row.get('source_file', ''), 'total_raw_record': total_row.get('raw_record'),
                             'total_flags': ';'.join(f'{f}={total_row[f]}' for f in FLAGS if total_row.get(f)),
                             'local_per_usd': rate, 'rounding_tolerance_local': sum(r['rounding'] for r in valid_groups) + total_row.get('rounding_local', 0),
                             'interpretation': 'Remainder includes unresolved classification, missing/confidential components, U and source discrepancies; not a seventh economic industry.'})
            view.append({'iso': iso, 'year': year, 'source': source, 'scope': scope, 'status': status, 'currency': currency,
                         'totalLocal': total, 'totalUSD': total / rate if total is not None and rate else None,
                         'assigned': [r['assigned_rd_usd'] for r in rd_rows], 'assignedLocal': [r['assigned_rd_local'] for r in rd_rows],
                         'shares': [r['assigned_share_reported_rd_percent'] for r in rd_rows],
                         'complete': [r['group_complete'] for r in rd_rows], 'groupCoverage': [r['group_coverage'] for r in rd_rows],
                         'remainingUSD': remainder / rate if remainder is not None and rate else None,
                         'remainingShare': remainder / total * 100 if usable else None,
                         'classifiedShare': (assigned or 0) / total * 100 if usable else None,
                         'stackAvailable': usable, 'totalFlags': ';'.join(f'{f}={total_row[f]}' for f in FLAGS if total_row.get(f)),
                         'flags': '; '.join(sorted({r['source_flags'] for r in rd_rows if r['source_flags']}))})

    context_input = read_csv(DATA / 'rd_income_exports_annual.csv')
    context_keys = {(r['iso3'], int(r['year'])): r for r in context_input}
    nominal = defaultdict(dict)
    source_keys = {'OECD MSTI': 'oecd', 'UNESCO UIS via World Bank WDI': 'wdi', 'UNESCO UIS direct': 'uis', 'Eustat (Basque Country)': 'eustat'}
    for i, r in enumerate(read_csv(DATA / 'rd_nominal_annual.csv'), 1):
        if r['unit'] == 'current US dollars':
            prefix = 'gerd_' + source_keys[r['rd_source']]
            target = nominal[r['iso3'], int(r['year'])]
            assert prefix + '_usd' not in target
            target.update({prefix + '_usd': number(r['amount']), prefix + '_status': r['status'], prefix + '_nominal_record': i})
    view_index = {(r['iso'], r['year']): r for r in view}
    context = []
    for iso, year in sorted(set(context_keys) | set(view_index)):
        row = dict(context_keys.get((iso, year), {k: '' for k in context_input[0]}))
        row.update(iso3=iso, country=country_names.get(iso, row.get('country', iso)), year=year)
        for name in source_keys.values():
            for suffix in ['usd', 'status', 'nominal_record']:
                row['gerd_' + name + '_' + suffix] = nominal[iso, year].get('gerd_' + name + '_' + suffix)
        rd = view_index.get((iso, year), {})
        ec, gv = economic.get((iso, year), {}), gva.get((iso, year), {})
        row.update(berd_or_companies_pnpi_usd=rd.get('totalUSD'), industry_rd_scope=rd.get('scope', ''),
                   industry_rd_coverage=rd.get('status', 'no_industry_observations'), assigned_industry_rd_percent=rd.get('classifiedShare'),
                   gva_usd=gv.get('totalUSD') if gv.get('status') == 'available' else None,
                   employed_persons=ec.get('employment', {}).get('total') if ec.get('employment', {}).get('status') == 'available' else None,
                   gva_per_person_usd_thousand=ec.get('productivity', {}).get('total') if ec.get('productivity', {}).get('status') == 'available' else None,
                   goods_exports_usd=ec.get('exports', {}).get('total') if ec.get('exports', {}).get('status') == 'available' else None,
                   goods_exports_coverage=ec.get('exports', {}).get('status', 'not_returned'),
                   industry_rd_source_table='rd_industry_coverage.csv', gva_source_table='broad_sector_annual.csv',
                   employment_source_table='sector_employment.csv', exports_source_table='sector_exports.csv',
                   nominal_rd_source_table='rd_nominal_annual.csv', join_rule='exact economy and year; no interpolation')
        context.append(row)
    context_index = {(r['iso3'], r['year']): r for r in context}
    joined = []
    for r in annual:
        iso, year, gid = r['iso3'], r['year'], r['group']
        i = GROUP_IDS.index(gid)
        ec, gv = economic.get((iso, year), {}), gva.get((iso, year), {})
        emp, prod, ex = (ec.get(s, {}) for s in ['employment', 'productivity', 'exports'])
        value = gv.get('amounts', [None] * 6)[i] if gv.get('status') == 'available' else None
        persons = emp.get('amounts', [None] * 6)[i] if emp.get('status') == 'available' else None
        rate = prod.get('amounts', [None] * 6)[i] if prod.get('status') == 'available' else None
        full_rd = r['group_rd_total_usd'] if r['coverage_status'] not in ['negative_reconciliation_remainder', 'nonpositive_reported_total'] else None
        context_row = context_index[iso, year]
        joined_row = {**r, 'gva_usd': value, 'gva_share_percent': gv.get('shares', [None] * 6)[i] if value is not None else None,
                      'employed_persons': persons, 'employment_share_percent': emp.get('shares', [None] * 6)[i] if persons is not None else None,
                      'gva_per_person_usd_thousand': rate, 'rd_percent_sector_gva': full_rd / value * 100 if full_rd is not None and value is not None and value > 0 else None,
                      'rd_usd_per_sector_worker': full_rd / persons if full_rd is not None and persons is not None and persons > 0 else None,
                      'goods_exports_usd': ex.get('amounts', [None] * 3)[i] if i < 2 and ex.get('status') == 'available' else None,
                      'goods_exports_share_percent': ex.get('shares', [None] * 3)[i] if i < 2 and ex.get('status') == 'available' else None,
                      'export_scope_note': 'LMT exports exclude C33 repair/installation services; R&D and GVA include C33.' if gid == 'LMT' else 'Exports classify goods by associated industry, not exporter main activity.' if gid == 'MHT' else 'No six-sector service/other-production export assignment; goods residual is not this sector.',
                      'gva_source': gv.get('source', ''), 'gva_flags': gv.get('flags', ''), 'employment_source': emp.get('source', ''),
                      'employment_flags': emp.get('flags', ''), 'exports_source': ex.get('source', ''), 'exports_flags': ex.get('flags', ''),
                      'gva_coverage_status': gv.get('status', 'not_returned'), 'employment_coverage_status': emp.get('status', 'not_returned'),
                      'exports_coverage_status': ex.get('status', 'not_returned'), 'join_rule': 'exact economy, year and broad group',
                      **{k: context_row.get(k) for k in ['rd_percent_gdp_oecd', 'rd_percent_gdp_wdi', 'rd_percent_gdp_eustat', 'rd_percent_gdp_ons',
                                                       'gdp_per_capita_current_usd', 'gdp_per_capita_current_ppp', 'gerd_oecd_usd', 'gerd_wdi_usd', 'gerd_uis_usd', 'gerd_eustat_usd']},
                      'context_source_table': 'rd_economy_context.csv', 'gva_source_table': 'broad_sector_annual.csv',
                      'employment_source_table': 'sector_employment.csv', 'exports_source_table': 'sector_exports.csv'}
        joined.append(joined_row)
    for row in view:
        records = [joined[(economies.index(row['iso']) * 26 + row['year'] - 2000) * 6 + i] for i in range(6)]
        for name, field in [('intensity', 'rd_percent_sector_gva'), ('perWorker', 'rd_usd_per_sector_worker'), ('gvaUSD', 'gva_usd'),
                            ('gvaShares', 'gva_share_percent'), ('persons', 'employed_persons'), ('employmentShares', 'employment_share_percent'),
                            ('productivity', 'gva_per_person_usd_thousand'), ('exportUSD', 'goods_exports_usd'), ('exportShares', 'goods_exports_share_percent')]:
            row[name] = [r[field] for r in records]
        ctx = context_index[row['iso'], row['year']]
        row['context'] = {k: number(ctx.get(k)) for k in ['gerd_oecd_usd', 'gerd_wdi_usd', 'gerd_eustat_usd', 'rd_percent_gdp_oecd',
                                                        'rd_percent_gdp_wdi', 'rd_percent_gdp_eustat', 'rd_percent_gdp_ons', 'gdp_per_capita_current_usd']}
        row['economicSources'] = {k: records[0][k] for k in ['gva_source', 'gva_flags', 'employment_source', 'employment_flags', 'exports_source', 'exports_flags']}
    mapping = []
    for code in sorted({r['activity_code'] for r in components if r['source'] == 'OECD_RDS'}):
        classes = classification.coverage(code)
        groups = [g for g, target in classification.groups.items() if classes & target]
        mapping.append({'source': 'OECD_RDS', 'activity_code': code, 'activity_label': classification.labels[code],
                        'isic4_classes': ';'.join(sorted(classes)), 'group_memberships': ';'.join(groups),
                        'wholly_within_one_group': len(groups) == 1 and not classes & classification.coverage('U'),
                        'contains_U': bool(classes & classification.coverage('U')), 'note': 'Source totals overlap components; only selected disjoint expressions are aggregated.'})
    for code, cell in sorted(next(c for (iso, _), c in blocks.items() if iso == 'ES-PV').items()):
        mapping.append({'source': 'EUSTAT_NATIVE', 'activity_code': code, 'activity_label': cell['activity_label'], 'isic4_classes': '',
                        'group_memberships': '', 'wholly_within_one_group': False, 'contains_U': '',
                        'note': 'Native branch values retained; exact ISIC4 bridge not established. No six-group allocation.'})
    tables = [annual, joined, context, components, coverage, mapping, list(fx_records.values())]
    workbook = Workbook(write_only=True)
    for name, rows in zip(OUTPUTS, tables):
        write(name, rows)
        sheet = workbook.create_sheet(name.removesuffix('.csv'))
        sheet.append(list(rows[0]))
        for r in rows:
            sheet.append(list(r.values()))
    workbook.save(DATA / 'rd_industry_economy.xlsx')
    built = datetime.now(timezone.utc).isoformat()
    payload = {'builtUTC': built, 'groups': [{k: g[k] for k in ['id', 'label', 'color']} for g in GROUPS],
               'countries': [{'iso': iso, 'name': country_names[iso], 'display': DISPLAY.get(iso, country_names[iso]), 'region': iso == 'ES-PV'} for iso in economies],
               'defaults': sector['defaults'], 'sources': SOURCE_NAMES, 'rows': view}
    (DATA / 'rd_industry_explorer.json').write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')
    inputs = ['broad_sector_validation.json', 'sector_economy_validation.json', 'industry_validation.json', 'validation_report.json',
              'rd_income_exports_annual.csv', 'rd_nominal_annual.csv', 'broad_sector_explorer.json', 'sector_economy_explorer.json',
              'industry_country_coverage.csv']
    report = {'validation': 'passed', 'built_utc': built, 'source_components': len(components), 'archived_responses': len(manifest),
              'economies_in_picker': len(economies), 'economies_with_industry_source': len({k[0] for k in blocks}),
              'complete_group_observations': sum(r['group_complete'] for r in annual), 'matched_rd_gva_observations': sum(r['rd_percent_sector_gva'] is not None for r in joined),
              'coverage_counts': dict(Counter(r['coverage_status'] for r in coverage)), 'excluded_provider_codes': sorted(excluded),
              'source_manifest_sha256': digest(RAW / 'manifest.json'), 'input_sha256': {n: digest(DATA / n) for n in inputs},
              'output_sha256': {n: digest(DATA / n) for n in [*OUTPUTS, 'rd_industry_economy.xlsx', 'rd_industry_explorer.json']}}
    (DATA / 'rd_industry_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build()
