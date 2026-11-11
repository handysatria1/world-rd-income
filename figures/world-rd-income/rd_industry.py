"""Classify industry R&D and join exact economy/year/group economic observations."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from openpyxl import Workbook
from broad_sectors import DATA, GROUPS, DISPLAY, write
from industry_data import read_csv, digest
from rd_industry_sources import RAW, SOURCES
from rd_industry_mapping import Classification, aggregate
from rd_industry_native import native_components, aggregate_native, mapping_note, SCOPE, CRITERIA
from sector_field_rd import FLAGS, normalized_value

OUTPUTS = ['rd_industry_annual.csv', 'rd_economy_joined.csv', 'rd_economy_context.csv',
           'rd_industry_components.csv', 'rd_industry_coverage.csv', 'rd_industry_mapping.csv', 'rd_industry_fx.csv']
CURRENCY_COUNTRIES = {'ARS': 'ARG', 'AUD': 'AUS', 'BGN': 'BGR', 'CAD': 'CAN', 'CHF': 'CHE', 'CLP': 'CHL',
                      'CNY': 'CHN', 'CZK': 'CZE', 'DKK': 'DNK', 'GBP': 'GBR', 'HUF': 'HUN', 'ILS': 'ISR',
                      'ISK': 'ISL', 'JPY': 'JPN', 'KRW': 'KOR', 'MXN': 'MEX', 'NOK': 'NOR', 'NZD': 'NZL',
                      'PLN': 'POL', 'RON': 'ROU', 'SEK': 'SWE', 'SGD': 'SGP', 'TRY': 'TUR'}
SOURCE_NAMES = {'OECD_RDS': 'OECD RDS BERD · main activity', 'EUSTAT_NATIVE': 'Eustat companies + PNPI · native branches',
                'SGP_RIE': 'A*STAR National RIE Survey · private-sector R&D (S&T)'}
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
                      **{flag: row[flag] for flag in FLAGS}, 'source_file': 'oecd_berd_industry.csv', 'raw_record': i,
                      'source_sheet': '', 'source_cell': ''}
        assert code not in blocks[iso, year]
        blocks[iso, year][code] = component
        components.append(component)
    native = native_components(RAW)
    native_blocks = defaultdict(dict)
    for component in native:
        native_blocks[component['iso3'], component['year']][component['activity_code']] = component
    components.extend(native)
    for key, cells in native_blocks.items():
        # Select a coherent native block; never combine different vintages/classifications.
        # Retain all original OECD cells in the source-component download.
        if key[0] == 'ES-PV' or key == ('SGP', 2023) or not any(r['amount_local'] is not None for r in blocks[key].values()):
            blocks[key] = cells
    annual, coverage, view = [], [], []
    economies = sorted(set(c['iso'] for c in sector['countries']) | {k[0] for k in blocks})
    for iso in economies:
        for year in range(2000, 2026):
            cells = blocks.get((iso, year), {})
            basque = iso == 'ES-PV'
            source = next(iter(cells.values()))['source'] if cells else 'EUSTAT_NATIVE' if basque else 'OECD_RDS'
            native_source = source != 'OECD_RDS'
            scope = SCOPE.get(source, 'BERD')
            currencies = {r['currency'] for r in cells.values()}
            assert len(currencies) <= 1
            currency = next(iter(currencies), '')
            fx = conversion(iso, year, currency) if currency else {}
            rate = fx.get('local_per_usd')
            total_code = '000' if basque else ('RIE_19' if year == 2023 else 'RIE_TOTAL') if source == 'SGP_RIE' else '_T'
            total_row = cells.get(total_code, {})
            total = total_row.get('amount_local')
            native_leaves = [r['amount_local'] for c, r in cells.items()
                             if native_source and c not in {'000', 'RIE_TOTAL', 'RIE_06', 'RIE_13', 'RIE_19'}]
            native_leaf_sum = sum(native_leaves) if native_leaves and all(v is not None for v in native_leaves) else None
            grouped = aggregate_native(cells, GROUP_IDS) if native_source else aggregate(cells, classification)
            valid_groups = [r for r in grouped.values() if r is not None]
            assigned = sum(r['value'] for r in valid_groups) if valid_groups else None
            remainder = total - (assigned or 0) if total is not None else None
            complete_groups = [g for g, r in grouped.items() if r is not None and r['classes'] == classification.groups[g]]
            status = ('no_industry_observations' if not cells else
                      'missing_reported_total' if total is None else 'nonpositive_reported_total' if total <= 0 else
                      'negative_reconciliation_remainder' if remainder < 0 else 'fully_classified' if len(complete_groups) == 6 and remainder == 0 else
                      'partially_classified_native_branches' if native_source and assigned is not None else
                      'partially_classified' if assigned is not None else 'reported_total_only' if source == 'SGP_RIE' else 'no_classifiable_components')
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
                       'rd_source': source, 'rd_scope': scope, 'classification_criteria': CRITERIA if native_source else 'main activity',
                       'assigned_rd_local': local, 'currency': currency, 'assigned_rd_usd': local / rate if local is not None and rate else None,
                       'group_complete': complete, 'group_coverage': 'complete' if complete else 'partial' if result else 'unavailable',
                       'group_rd_total_usd': local / rate if complete and rate else None,
                       'assigned_share_reported_rd_percent': local / total * 100 if local is not None and usable else None,
                       'reported_rd_total_local': total, 'reported_rd_total_usd': total / rate if total is not None and rate else None,
                       'unallocated_rd_local': remainder, 'unallocated_rd_usd': remainder / rate if remainder is not None and rate else None,
                       'coverage_status': status, 'source_terms_json': json.dumps(terms, sort_keys=True, separators=(',', ':')),
                       'source_records': ';'.join(str(cells[c]['raw_record']) for c in sorted(terms)),
                       'source_file': total_row.get('source_file', 'eustat_rd_industry.json' if basque else 'oecd_berd_industry.csv'),
                       'source_locators': ';'.join(f"{cells[c]['source_sheet']}!{cells[c]['source_cell']}" if cells[c]['source_sheet'] else f"record {cells[c]['raw_record']}" for c in sorted(terms)),
                       'covered_isic4_classes': ';'.join(sorted(covered)),
                       'missing_isic4_classes': '' if native_source else ';'.join(sorted(classification.groups[gid] - covered)),
                       'class_coverage_basis': 'native branch-label containment; exact classes unresolved' if native_source else 'exact ISIC4 class sets',
                       'source_flags': flags, 'local_per_usd': rate, 'fx_source_file': fx.get('source_file', ''),
                       'fx_raw_record': fx.get('raw_record'), 'fx_reference_area': fx.get('fx_reference_area', ''),
                       'value_status': ('derived_partial_native_branches' if native_source else 'derived_disjoint_public_components') if result else 'not_derived',
                       'note': 'Partial assigned amounts are not full sector totals. U is excluded; unsplittable S-U aggregates remain unallocated.' if not native_source else
                               'Native branch labels support partial groups only; class lists are unresolved, not empty coverage. Mixed branches remain unallocated. '
                               + ('Companies include PNPI; allocations begin 2003.' if basque else 'S&T R&D excludes social sciences/humanities. Industry detail is 2023 only; other RIE years provide totals only.')}
                annual.append(row)
                rd_rows.append(row)
            coverage.append({'iso3': iso, 'economy': country_names[iso], 'year': year, 'rd_source': source, 'rd_scope': scope,
                             'coverage_status': status, 'currency': currency, 'reported_total_local': total, 'assigned_local': assigned,
                             'unallocated_local': remainder, 'assigned_share_percent': (assigned or 0) / total * 100 if usable else None,
                             'complete_groups': ';'.join(complete_groups), 'source_cells': len(cells),
                             'eligible_cells': sum(r['aggregation_eligible'] for r in cells.values()),
                             'total_source_file': total_row.get('source_file', ''), 'total_raw_record': total_row.get('raw_record'),
                             'total_activity_code': total_code, 'total_source_sheet': total_row.get('source_sheet', ''), 'total_source_cell': total_row.get('source_cell', ''),
                             'native_leaf_sum_local': native_leaf_sum,
                             'native_total_minus_leaves_local': total - native_leaf_sum if total is not None and native_leaf_sum is not None else None,
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
                         'flags': '; '.join(sorted({r['source_flags'] for r in rd_rows if r['source_flags']})),
                         'nativeRows': [{'code': r['activity_code'], 'label': r['activity_label'], 'amountLocal': r['amount_local'],
                                         'currency': r['currency'], 'group': r['mapping_group'], 'eligible': r['aggregation_eligible'],
                                         'note': r['eligibility_note'], 'source': r['source'], 'sourceFile': r['source_file'],
                                         'flags': ';'.join(f'{f}={r[f]}' for f in FLAGS if r[f]),
                                         'locator': f"{r['source_sheet']}!{r['source_cell']}" if r['source_sheet'] else f"record {r['raw_record']}"}
                                        for r in native_blocks.get((iso, year), {}).values()]})

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
    for (source, code), cell in sorted({(r['source'], r['activity_code']): r for r in native}.items()):
        mapping.append({'source': source, 'activity_code': code, 'activity_label': cell['activity_label'], 'isic4_classes': '',
                        'group_memberships': cell['mapping_group'], 'wholly_within_one_group': bool(cell['mapping_group']), 'contains_U': '',
                        'note': mapping_note(source, code)})
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
               'defaults': sector['defaults'], 'defaultYear': 'latest', 'sources': SOURCE_NAMES, 'rows': view}
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
