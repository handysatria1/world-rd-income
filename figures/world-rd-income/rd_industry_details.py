"""Explain selected public R&D expressions without estimating suppressed amounts."""
import json
from collections import defaultdict

from industry_data import read_csv, digest
from rd_industry_mapping import Classification


def build_details(data):
    classification = Classification(data / 'rd_industry_raw/oecd_berd_structure.xml')
    blocks = defaultdict(dict)
    for row in read_csv(data / 'rd_industry_components.csv'):
        blocks[row['iso3'], row['year'], row['source']][row['activity_code']] = row
    catalog = dict(classification.labels)
    details = {}
    # Compact exact class sets into sections/divisions where possible. Counts are
    # classification counts, never percentages of expenditure or establishments.
    def compact(classes):
        remaining, codes = set(classes), []
        candidates = sorted((c for c in catalog if len(c) in (1, 3, 4, 5) and c[0].isalpha()
                             and (len(c) == 1 or c[1:].isdigit())), key=lambda c: (len(c), c))
        for code in candidates:
            covered = classification.coverage(code)
            if covered and covered <= remaining:
                codes.append(code)
                remaining -= covered
        assert not remaining
        return codes
    for row in read_csv(data / 'rd_industry_annual.csv'):
        block = blocks[row['iso3'], row['year'], row['rd_source']]
        if not block:
            continue
        terms = json.loads(row['source_terms_json'])
        included = []
        for code, weight in terms.items():
            cell = block[code]
            catalog[code] = cell['activity_label']
            included.append({'code': code, 'weight': weight, 'amountLocal': float(cell['amount_local']),
                             'file': cell['source_file'],
                             'locator': f"{cell['source_sheet']}!{cell['source_cell']}" if cell['source_sheet'] else 'record ' + cell['raw_record']})
        native = row['rd_source'] != 'OECD_RDS'
        missing = []
        if native:
            reason = ('Native branch labels identify only part of this group. An exact ISIC class concordance is unresolved; '
                      'neither the full sector total nor its expenditure coverage percentage is known.')
            for code, cell in block.items():
                if not cell['mapping_group'] and code not in {'000', 'RIE_TOTAL', 'RIE_06', 'RIE_13', 'RIE_19'}:
                    catalog[code] = cell['activity_label']
                    missing.append({'code': code, 'reason': cell['eligibility_note'], 'flags': '', 'file': cell['source_file'],
                                    'locator': f"{cell['source_sheet']}!{cell['source_cell']}" if cell['source_sheet'] else 'record ' + cell['raw_record']})
        else:
            reason = ('The selected disjoint public observations do not cover every activity in the requested group. '
                      'Uncovered activities are not treated as zero; their R&D amount is unknown.')
            for code in compact(filter(None, row['missing_isic4_classes'].split(';'))):
                cell = block.get(code)
                related = [(c, r) for c, r in block.items() if c != '_T' and classification.coverage(code) <= classification.coverage(c)]
                related.sort(key=lambda item: len(classification.coverage(item[0])))
                evidence = cell or (related[0][1] if related else None)
                if cell:
                    why = cell['availability'].replace('_', ' ')
                    if cell['aggregation_eligible'] == 'True':
                        why = 'Reported aggregate is not usable in the selected disjoint expression.'
                else:
                    why = 'No separately usable observation for this activity in the archived response.'
                    if related:
                        why += ' Broader ' + related[0][0] + ': ' + related[0][1]['availability'].replace('_', ' ') + '.'
                crossings = [c for c, r in related if r['aggregation_eligible'] == 'True'
                             and not classification.coverage(c) <= classification.groups[row['group']]]
                if crossings:
                    why += ' Broader ' + ', '.join(crossings[:3]) + ' crosses group boundaries and cannot be allocated intact.'
                missing.append({'code': code, 'reason': why,
                                'flags': '; '.join(k + '=' + evidence[k] for k in ['OBS_STATUS', 'OBS_STATUS_2', 'OBS_STATUS_3', 'AUX_OBS_STATUS', 'AUX_OBS_STATUS_2', 'AUX_OBS_STATUS_3', 'CONF_STATUS'] if evidence and evidence[k]),
                                'file': evidence['source_file'] if evidence else '',
                                'locator': 'record ' + evidence['raw_record'] if evidence else ''})
        details['/'.join([row['iso3'], row['year'], row['group']])] = {
            'coverage': row['group_coverage'], 'basis': row['class_coverage_basis'], 'native': native,
            'reason': reason if row['group_complete'] != 'True' else 'All requested ISIC classes are covered by disjoint public observations.',
            'included': included, 'missing': missing, 'flags': row['source_flags'], 'source': row['rd_source'], 'scope': row['rd_scope']}
    return {'build': json.loads((data / 'rd_industry_validation.json').read_text('utf-8'))['built_utc'],
            'inputs': {n: digest(data / n) for n in ['rd_industry_annual.csv', 'rd_industry_components.csv']},
            'labels': catalog, 'rows': details}
