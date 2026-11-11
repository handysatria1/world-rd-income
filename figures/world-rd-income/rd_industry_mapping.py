"""Disjoint industry crosswalk using the source's genuine ISIC Rev.4 classes."""
import re
from functools import lru_cache
from xml.etree import ElementTree as ET

from broad_sectors import GROUPS


class Classification:
    def __init__(self, path):
        xml = ET.parse(path).getroot()
        book = next(c for c in xml.findall('.//{*}Codelist') if c.get('id') == 'CL_ACTIVITY_ISIC4')
        self.labels = {c.get('id'): next(n.text for n in c.findall('{*}Name') if n.get('{http://www.w3.org/XML/1998/namespace}lang') == 'en') for c in book.findall('{*}Code')}
        self.classes = sorted(c for c in self.labels if re.fullmatch(r'[A-U]\d{4}', c))
        assert len(self.classes) == 419, 'Review changed ISIC class catalog'
        self.groups = {g['id']: frozenset(c for c in self.classes if int(c[1:3]) in g['divisions']) for g in GROUPS}
        assert sum(map(len, self.groups.values())) == len(set.union(*(set(s) for s in self.groups.values())))
        assert set.union(*(set(s) for s in self.groups.values())) == set(self.classes) - set(self.coverage('U'))

    @lru_cache(maxsize=None)
    def coverage(self, code):
        if code == '_T':
            return frozenset(self.classes)
        assert code in self.labels, code
        if 'X' in code:
            base, excluded = code.split('X', 1)
            return self.coverage(base) - self.coverage(excluded if excluded[0].isalpha() else base[0] + excluded)
        if '_' in code:
            parts = code.split('_')
            return frozenset.union(*(self.coverage(p if p[0].isalpha() else parts[0][0] + p) for p in parts))
        if m := re.fullmatch(r'([A-U])(\d{2})T(\d{2})', code):
            letter, start, end = m.groups()
            return frozenset(c for c in self.classes if c[0] == letter and int(start) <= int(c[1:3]) <= int(end))
        if m := re.fullmatch(r'([A-U])T([A-U])', code):
            return frozenset(c for c in self.classes if m[1] <= c[0] <= m[2])
        if re.fullmatch(r'[A-U]\d{0,4}', code):
            found = frozenset(c for c in self.classes if c.startswith(code))
            assert found, code
            return found
        raise ValueError('Unreviewed industry code: ' + code)


def combination(parts):
    """Combine signed public observations; retain the exact source expression."""
    if not parts or any(candidate is None for _, candidate in parts):
        return None
    terms, weights, value, rounding = {}, {}, 0., 0.
    for sign, candidate in parts:
        value += sign * candidate['value']
        rounding += abs(sign) * candidate['rounding']
        for code, coefficient in candidate['terms'].items():
            terms[code] = terms.get(code, 0) + sign * coefficient
        for c in candidate['classes']:
            weights[c] = weights.get(c, 0) + sign
    terms = {c: w for c, w in terms.items() if w}
    assert all(w in [0, 1] for w in weights.values()), 'Overlapping or negative class coverage'
    return {'value': value, 'rounding': rounding, 'classes': frozenset(c for c, w in weights.items() if w), 'terms': terms}


def cover(target, candidates):
    """Prefer broader released totals; never add parent and child observations."""
    eligible = [c for c in candidates if c['classes'] and c['classes'] <= target and c['value'] >= 0]
    chosen, used = [], frozenset()
    for candidate in sorted(eligible, key=lambda c: (-len(c['classes']), len(c['terms']), tuple(sorted(c['terms'])))):
        if not candidate['classes'] & used:
            chosen.append((1, candidate))
            used |= candidate['classes']
    return combination(chosen)


def aggregate(cells, classification):
    candidates = [{'value': r['amount_local'], 'rounding': r['rounding_local'], 'classes': classification.coverage(code), 'terms': {code: 1}}
                  for code, r in cells.items() if r['aggregation_eligible']]
    direct = {next(iter(c['terms'])): c for c in candidates}
    # A published non-additivity flag invalidates subtraction identities for this block.
    if any(r.get(f) in ['S2', 'V2'] for r in cells.values()
           for f in ['AUX_OBS_STATUS', 'AUX_OBS_STATUS_2', 'AUX_OBS_STATUS_3']):
        direct = {}
    # Public aggregate differences identify broad groups without filling source cells.
    for whole, subtract in [('M_N', 'N'), ('M_N', 'M'), ('O_P', 'O84'), ('O_P', 'P85'), ('C25T30', 'C25')]:
        candidate = combination([(1, direct.get(whole)), (-1, direct.get(subtract))])
        if candidate is not None and candidate['value'] >= 0:
            candidates.append(candidate)
    initial = {g: cover(target, candidates) for g, target in classification.groups.items()}
    # Manufacturing C10-33 is exactly the disjoint union of MHT and LMT.
    for target, other in [('MHT', 'LMT'), ('LMT', 'MHT')]:
        found = initial[other]
        if (not initial[target] or initial[target]['classes'] != classification.groups[target]) and found and found['classes'] == classification.groups[other] and 'C' in direct:
            candidate = combination([(1, direct['C']), (-1, found)])
            if candidate['value'] >= 0:
                candidates.append(candidate)
    # Services G-N minus J/K/M is an exact subset of LIS. U is never assigned to LIS.
    business_kis = cover(classification.coverage('J') | classification.coverage('K') | classification.coverage('M'), candidates)
    if business_kis and business_kis['classes'] == classification.coverage('J') | classification.coverage('K') | classification.coverage('M'):
        candidate = combination([(1, direct.get('GTN')), (-1, business_kis)])
        if candidate and candidate['value'] >= 0:
            candidates.append(candidate)
    # Total A-U less C, D/E and G-U isolates A/B/F, including when one is suppressed.
    other = combination([(1, direct.get('_T')), (-1, direct.get('C')), (-1, direct.get('D_E')), (-1, direct.get('GTU'))])
    if other and other['value'] >= 0:
        assert other['classes'] == classification.groups['OTH']
        candidates.append(other)
    return {g: initial[g] if initial[g] and initial[g]['classes'] == target else cover(target, candidates)
            for g, target in classification.groups.items()}
