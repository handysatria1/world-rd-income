"""Employment, exact-year productivity joins and custom goods-export composition."""
import json
from collections import Counter
from datetime import datetime, timezone

from openpyxl import Workbook
from basque_rd import px_rows
from broad_sectors import DATA, GROUPS, DISPLAY, write
from industry_data import digest, read_csv
from sector_economy_sources import RAW

DEFAULTS = ['CHN', 'USA', 'GBR', 'KOR', 'SGP', 'ES-PV']
EXPORT_GROUPS = [dict(g) for g in GROUPS[:2]] + [{'id': 'REST', 'label': 'Other / unallocated goods', 'color': '#858585'}]
OUTPUTS = ['sector_employment.csv', 'sector_productivity.csv', 'sector_exports.csv',
           'sector_economy_components.csv', 'sector_economy_coverage.csv', 'sector_export_mapping.csv']


def build():
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for name, info in manifest.items():
        assert digest(RAW / name) == info['sha256']
    broad = json.loads((DATA / 'broad_sector_explorer.json').read_text('utf-8'))
    gva = {(r['iso'], r['year']): r for r in broad['rows']}
    countries = {r['iso3']: r['country'] for r in read_csv(DATA / 'industry_country_coverage.csv')}
    components, lookup, mapping = [], {}, []
    excluded = set()

    def add(metric, iso, year, code, value, multiplier, unit, flag, file, record, label=''):
        key = (file, iso, year, code)
        assert key not in lookup
        row = {'metric': metric, 'iso3': iso, 'economy': countries[iso], 'year': year,
               'activity_code': code, 'activity_label': label, 'value_reported': value,
               'unit_multiplier': multiplier, 'unit': unit, 'obs_status': flag,
               'source_file': file, 'raw_record': record}
        lookup[key] = row
        components.append(row)

    for metric, filename, field in [('employment', 'oecd_tim_employment.csv', 'ACTIVITY'), ('exports', 'oecd_btige_exports.csv', 'PRODUCT')]:
        for i, row in enumerate(read_csv(RAW / filename), 1):
            iso, year = row['REF_AREA'], int(row['TIME_PERIOD'])
            assert row['FREQ'] == 'A' and row['COUNTERPART_AREA'] == 'W' and row['UNIT_MULT'] == '3'
            assert row['UNIT_MEASURE'] == ('PS' if metric == 'employment' else 'USD')
            if metric == 'employment':
                assert row['MEASURE'] == 'EMPN'
            else:
                assert row['TRADE_FLOW'] == 'X' and row['END_USE'] == 'TOTAL'
            if iso not in countries:
                excluded.add(iso)
                continue
            add(metric, iso, year, row[field], float(row['OBS_VALUE']) if row['OBS_VALUE'] else None,
                3, row['UNIT_MEASURE'], row.get('OBS_STATUS', ''), filename, i)
    for filename, metric, field in [('eustat_employment.json', 'employment', 'sector'),
                                    ('eustat_exports_nace.json', 'exports', 'CNAE-09'),
                                    ('eustat_export_groups.json', 'exports', 'nivel tecnológico grupos (CNAE-09)'),
                                    ('eustat_export_sectors.json', 'exports', 'nivel tecnológico sectores (CNAE-09)')]:
        for i, (coord, labels, value, flag, dataset) in enumerate(px_rows(RAW / filename), 1):
            year = int(coord['periodo'])
            if not 2000 <= year <= 2025:
                continue
            if metric == 'employment':
                assert coord['territorio histórico'] == '_T' and coord['tipo de empleo'] == '50' and coord['tipo de dato'] == '10'
                assert labels['tipo de empleo'] == 'Employed persons. TOTAL'
            else:
                assert coord['flujo'] == '10' and coord['territorio histórico'] == '00' and coord['área'] == '100' and coord['unidad'] == '10'
            add(metric, 'ES-PV', year, coord[field], value, 0 if metric == 'employment' else 3,
                'PS' if metric == 'employment' else 'EUR', flag, filename, i, labels[field])

    def obs(file, iso, year, code):
        return lookup.get((file, iso, year, code), {})

    def amount(file, iso, year, terms):
        cells = [(obs(file, iso, year, code), weight) for code, weight in terms]
        return sum(r['value_reported'] * 10 ** r['unit_multiplier'] * w for r, w in cells) if all(r.get('value_reported') is not None for r, _ in cells) else None

    def flags(file, iso, year, terms):
        return ';'.join(sorted({obs(file, iso, year, c).get('obs_status', '') for c, _ in terms} - {''}))

    def records(file, iso, year, terms):
        return ';'.join(str(obs(file, iso, year, c).get('raw_record', '')) for c, _ in terms)

    fx = {int(r['date']): r for r in json.loads((DATA / 'broad_sector_raw/wb_spain_exchange.json').read_bytes())[1]}
    employment, productivity, exports, coverage, view = [], [], [], [], []
    economies = sorted({r['iso3'] for r in components} | {r['iso'] for r in broad['countries']})
    for iso in economies:
        basque = iso == 'ES-PV'
        for year in range(2000, 2026):
            empfile = 'eustat_employment.json' if basque else 'oecd_tim_employment.csv'
            emp, empterms, missing = [], [], []
            for group in GROUPS:
                codes = group['eustat' if basque else 'tiva'][:]
                if basque and year <= 2020 and group['id'] == 'MHT':
                    codes.remove('07')
                terms = [(c, 1) for c in codes]
                empterms.append(terms)
                emp.append(amount(empfile, iso, year, terms))
                missing.extend(c for c in codes if obs(empfile, iso, year, c).get('value_reported') is None)
            total = sum(emp) if all(v is not None for v in emp) else None
            reported = amount(empfile, iso, year, [('_T', 1)])
            u = amount(empfile, iso, year, [('38', 1)]) if basque else 0
            residual = reported - total if reported is not None and total is not None else None
            if residual is not None and u is not None:
                residual -= u
            # OECD cells are rounded to 0.1 thousand persons; bound accumulated rounding.
            tolerance = 20 if basque else (sum(map(len, empterms)) + 1) * 50
            status = 'missing_components' if total is None else 'nonpositive_total_or_negative_group' if total <= 0 or min(emp) < 0 else 'unreconciled_total' if residual is None or abs(residual) > tolerance else 'available'
            shares = [v / total * 100 for v in emp] if status == 'available' else [None] * 6
            source = 'Eustat A38 employed persons' if basque else 'OECD TiM 2025 EMPN'
            empflags = flags(empfile, iso, year, [t for terms in empterms for t in terms])
            for i, group in enumerate(GROUPS):
                employment.append({'iso3': iso, 'economy': countries[iso], 'year': year, 'group': group['id'],
                                   'persons': emp[i], 'share_percent': shares[i], 'grouped_total_persons': total,
                                   'coverage_status': status, 'source': source, 'source_file': empfile,
                                   'source_codes': ';'.join(c for c, _ in empterms[i]), 'source_records': records(empfile, iso, year, empterms[i]),
                                   'obs_status': flags(empfile, iso, year, empterms[i]), 'value_status': 'derived_sum',
                                   'mapping_note': '08 includes 07+08 through 2020' if basque and year <= 2020 and i == 0 else ''})
            coverage.append({'metric': 'employment', 'iso3': iso, 'year': year, 'coverage_status': status,
                             'grouped_total': total, 'reported_total': reported, 'unit': 'persons', 'excluded_U': u,
                             'reconciliation_residual': residual, 'tolerance': tolerance, 'missing_codes': ';'.join(missing),
                             'native_group_audit_max': None, 'native_group_audit_incomplete': '', 'division_vs_manufacturing_residual': None,
                             'reconciliation_basis': 'reported total less observed U vs A-T' if u is not None else 'reported total vs A-T; U unreported'})
            gr = gva.get((iso, year), {})
            joined = status == 'available' and gr.get('status') == 'available'
            values = gr.get('amounts', [None] * 6)
            rates = [v / n / 1000 if joined and v is not None and n is not None and n > 0 else None for v, n in zip(values, emp)]
            overall = gr.get('totalUSD') / total / 1000 if joined and gr.get('totalUSD') is not None else None
            pstatus = 'available' if all(r is not None for r in rates) else 'missing_same_year_gva_or_employment_or_nonpositive_denominator'
            for i, group in enumerate(GROUPS):
                productivity.append({'iso3': iso, 'economy': countries[iso], 'year': year, 'group': group['id'],
                                     'gva_usd': values[i], 'persons': emp[i], 'gva_share_percent': gr.get('shares', [None] * 6)[i] if joined else None,
                                     'employment_share_percent': shares[i] if joined else None, 'gva_per_person_usd_thousand': rates[i],
                                     'economy_gva_per_person_usd_thousand': overall, 'coverage_status': pstatus,
                                     'value_status': 'derived_exact_economy_year_group_ratio', 'valuation': 'current basic prices; market exchange rates',
                                     'gva_source': gr.get('source', ''), 'employment_source': source,
                                     'gva_source_table': 'broad_sector_annual.csv', 'employment_source_table': 'sector_employment.csv',
                                     'gva_obs_status': gr.get('flags', ''), 'employment_obs_status': empflags})

            expfile = 'eustat_export_groups.json' if basque else 'oecd_btige_exports.csv'
            exptotal = amount(expfile, iso, year, [('*' if basque else '_T', 1)])
            native_audit, manufacturing_gap, incomplete_audit = None, None, ''
            if basque:
                # Native A+B includes 254 and 325, and excludes 301. Move these whole groups.
                adjustments = amount('eustat_exports_nace.json', iso, year, [('254', -1), ('325', -1), ('301', 1)])
                high = amount(expfile, iso, year, [('A', 1), ('B', 1)])
                low = amount(expfile, iso, year, [('C', 1), ('D', 1)])
                exp = [high + adjustments if high is not None and adjustments is not None else None,
                       low - adjustments if low is not None and adjustments is not None else None]
                native_diffs = []
                for code, codes in [('A', range(1, 4)), ('B', range(4, 9)), ('C', range(9, 15)), ('D', range(15, 19)), ('E', [99])]:
                    native = amount(expfile, iso, year, [(code, 1)])
                    sector = amount('eustat_export_sectors.json', iso, year, [(f'{c:02}', 1) for c in codes])
                    native_diffs.append(native - sector if native is not None and sector is not None else None)
                # C contains unreported cells (09/14); do not interpret those as zeros.
                # The complete A, B, D, E sums check the technology bridge independently.
                native_audit = max(abs(v) for v in native_diffs if v is not None) if native_diffs[0] is not None and native_diffs[1] is not None else None
                incomplete_audit = ';'.join(c for c, v in zip('ABCDE', native_diffs) if v is None)
                expterms = [[('A', 1), ('B', 1)], [('C', 1), ('D', 1)]]
                formulas = ['A+B-254-325+301', 'C+D+254+325-301']
                expmissing = [c for terms in expterms for c, _ in terms if obs(expfile, iso, year, c).get('value_reported') is None]
                expmissing += [c for c in ['254', '325', '301'] if obs('eustat_exports_nace.json', iso, year, c).get('value_reported') is None]
            else:
                expterms = [[('CPA_2_1_C' + str(d), 1) for d in group['divisions'] if d != 33] for group in GROUPS[:2]]
                exp = [amount(expfile, iso, year, terms) for terms in expterms]
                formulas = ['+'.join(c for c, _ in terms) for terms in expterms]
                expmissing = [c for terms in expterms for c, _ in terms if obs(expfile, iso, year, c).get('value_reported') is None]
                manufacturing = amount(expfile, iso, year, [('CPA_2_1_C', 1)])
                manufacturing_gap = manufacturing - sum(exp) if manufacturing is not None and all(v is not None for v in exp) else None
            remaining = exptotal - sum(exp) if exptotal is not None and all(v is not None for v in exp) else None
            exp.append(remaining)
            expstatus = 'missing_components_or_total' if exptotal is None or any(v is None for v in exp) else 'nonpositive_total_or_negative_group' if exptotal <= 0 or min(exp) < 0 else 'available'
            if expstatus == 'available' and basque and (native_audit is None or native_audit > 5000):
                expstatus = 'native_group_audit_failed'
            if expstatus == 'available' and not basque and (manufacturing_gap is None or abs(manufacturing_gap) > max(10, exptotal * 1e-8)):
                expstatus = 'manufacturing_reconciliation_failed'
            rate = fx.get(year, {}).get('value') if basque else 1
            usd = [v / rate if v is not None and rate else None for v in exp]
            exp_shares = [v / exptotal * 100 for v in exp] if expstatus == 'available' else [None] * 3
            expnote = ('2025 provisional; ' if basque and year == 2025 else '') + ('Native technology groups adjusted by NACE 254, 325, 301; residual includes rounding.' if basque else 'Goods only; CPA C10–C32; C33 repair/installation services outside BTiGE product scope.')
            expflags = flags(expfile, iso, year, [(c, 1) for terms in expterms for c, _ in terms] + [('*' if basque else '_T', 1)])
            if basque:
                expflags = ';'.join(filter(None, [expflags, flags('eustat_exports_nace.json', iso, year, [('254', 1), ('325', 1), ('301', 1)])]))
            for i, group in enumerate(EXPORT_GROUPS):
                exports.append({'iso3': iso, 'economy': countries[iso], 'year': year, 'group': group['id'],
                                'value_source_currency': exp[i], 'currency': 'EUR' if basque else 'USD', 'value_usd': usd[i],
                                'share_percent': exp_shares[i], 'reported_goods_total_source_currency': exptotal,
                                'reported_goods_total_usd': exptotal / rate if exptotal is not None and rate else None,
                                'coverage_status': expstatus, 'source_file': expfile, 'formula': formulas[i] if i < 2 else 'reported_total-MHT-LMT',
                                'source_records': records(expfile, iso, year, expterms[i] if i < 2 else [('*' if basque else '_T', 1)]),
                                'adjustment_source_file': 'eustat_exports_nace.json' if basque else '',
                                'adjustment_records_254_325_301': records('eustat_exports_nace.json', iso, year, [('254', 1), ('325', 1), ('301', 1)]) if basque else '',
                                'obs_status': expflags, 'value_status': 'derived_residual' if i == 2 else 'derived_sum_and_reclassification' if basque else 'derived_sum',
                                'eur_per_usd': rate if basque else None, 'exchange_source_file': 'broad_sector_raw/wb_spain_exchange.json' if basque else '',
                                'exchange_status': fx.get(year, {}).get('obs_status', '') if basque else '', 'note': expnote})
            coverage.append({'metric': 'exports', 'iso3': iso, 'year': year, 'coverage_status': expstatus,
                             'grouped_total': sum(exp) if all(v is not None for v in exp) else None, 'reported_total': exptotal,
                             'unit': 'EUR' if basque else 'USD', 'excluded_U': None, 'reconciliation_residual': 0 if expstatus == 'available' else None,
                             'tolerance': 5000 if basque else max(10, (exptotal or 0) * 1e-8), 'missing_codes': ';'.join(expmissing),
                             'native_group_audit_max': native_audit, 'native_group_audit_incomplete': incomplete_audit,
                             'division_vs_manufacturing_residual': manufacturing_gap,
                             'reconciliation_basis': 'reported total minus manufacturing groups; native-group checks' if basque else 'division sum vs reported manufacturing; remaining goods are a residual'})
            view.append({'iso': iso, 'year': year,
                         'employment': {'status': status, 'amounts': emp, 'shares': shares, 'total': total, 'source': source, 'flags': empflags},
                         'productivity': {'status': pstatus, 'amounts': rates, 'total': overall, 'gvaShares': gr.get('shares', [None] * 6),
                                          'employmentShares': shares, 'gvaUSD': values, 'persons': emp, 'totalGVA': gr.get('totalUSD'),
                                          'totalPersons': total, 'comparisonStatus': 'available' if joined else 'missing_same_year_pair',
                                          'source': gr.get('source', '') + '; ' + source, 'flags': gr.get('flags', '') + ';' + empflags},
                         'exports': {'status': expstatus, 'amounts': usd, 'shares': exp_shares,
                                     'total': exptotal / rate if exptotal is not None and rate else None,
                                     'totalLocal': exptotal, 'currency': 'EUR' if basque else 'USD', 'source': 'Eustat foreign trade' if basque else 'OECD BTiGE',
                                     'note': expnote, 'flags': expflags}})
    for group in GROUPS[:2]:
        for d in group['divisions']:
            mapping.append({'provider': 'OECD BTiGE', 'group': group['id'], 'code': 'CPA_2_1_C' + str(d),
                            'coefficient': 1 if d != 33 else None, 'scope': 'goods' if d != 33 else 'repair/installation services outside selected goods scope; not a reported zero'})
    for group, terms in [('MHT', [('A', 1), ('B', 1), ('254', -1), ('325', -1), ('301', 1)]),
                         ('LMT', [('C', 1), ('D', 1), ('254', 1), ('325', 1), ('301', -1)])]:
        mapping.extend({'provider': 'Eustat technology groups' if len(c) == 1 else 'Eustat NACE-09', 'group': group,
                        'code': c, 'coefficient': w, 'scope': 'foreign goods trade'} for c, w in terms)
    rows = [employment, productivity, exports, components, coverage, mapping]
    workbook = Workbook(write_only=True)
    for name, records_ in zip(OUTPUTS, rows):
        write(name, records_)
        sheet = workbook.create_sheet(name.removesuffix('.csv'))
        sheet.append(list(records_[0]))
        for row in records_:
            sheet.append(list(row.values()))
    workbook.save(DATA / 'sector_economy.xlsx')
    built = datetime.now(timezone.utc).isoformat()
    payload = {'builtUTC': built, 'groups': broad['groups'], 'exportGroups': EXPORT_GROUPS, 'defaults': DEFAULTS,
               'countries': [{'iso': iso, 'name': countries[iso], 'display': DISPLAY.get(iso, countries[iso]), 'region': iso == 'ES-PV'} for iso in economies], 'rows': view}
    (DATA / 'sector_economy_explorer.json').write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')
    report = {'built_utc': built, 'validation': 'passed', 'economies': len(economies), 'source_components': len(components),
              'excluded_provider_codes_not_in_country_catalog': sorted(excluded), 'archived_responses': len(manifest),
              'coverage_counts': dict(Counter(r['metric'] + ':' + r['coverage_status'] for r in coverage)),
              'productivity_complete_economy_years': sum(r['productivity']['status'] == 'available' for r in view),
              'broad_sector_validation_sha256': digest(DATA / 'broad_sector_validation.json'),
              'source_manifest_sha256': digest(RAW / 'manifest.json'),
              'output_sha256': {name: digest(DATA / name) for name in [*OUTPUTS, 'sector_economy.xlsx', 'sector_economy_explorer.json']}}
    (DATA / 'sector_economy_validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    build()
