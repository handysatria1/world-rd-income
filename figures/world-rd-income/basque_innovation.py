"""Normalize archived Eustat researchers, population and distinct EIS indicators."""
from datetime import datetime
import hashlib
import json
import math
import re

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from basque_rd import px_rows
from basque_innovation_sources import RAW, SOURCES, REQUESTS, TABLES, SELECTIONS

POPULATION_METHOD = ('Use reported 1 July population where available; otherwise the mean of '
                     '1 January in the observation year and 1 January of the following year (midyear proxy).')
EIS_NOTE = ('EIS 2025 edition; years are workbook column years, not the edition year. '
            'EIS methodology §§3.8, 5.1 and 18.5 describes changing definitions/reference years and imputation; '
            'these tables do not identify imputed cells. Blank cells are retained; no local imputation.')


def load_basque_innovation():
    manifest = json.loads((RAW / 'manifest.json').read_text('utf-8'))
    for name, url in SOURCES.items():
        assert manifest[name]['url'] == url
        assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == manifest[name]['sha256']
        if name in REQUESTS:
            body = manifest[name]['request_body']
            assert json.loads(body) == REQUESTS[name]
            assert hashlib.sha256(body.encode()).hexdigest() == manifest[name]['request_sha256']

    def updated(key):
        html = (RAW / (key + '_table.html')).read_text('utf-8')
        date = re.search(r"itemprop='dateModified'>([^<]+)", html)[1]
        return datetime.strptime(date, '%m/%d/%Y').date().isoformat()

    def metadata(code, label, unit, definition, filename, date='', display=''):
        return {'code': code, 'label': label, 'unit': unit, 'definition': definition,
                'organization': 'Eustat', 'source_file': 'basque_innovation_raw/' + filename,
                'url': manifest[filename]['url'], 'updated': date,
                'retrieved': manifest[filename]['retrieved_utc'], 'display_url': SOURCES.get(display, '')}

    meta = {
        'researchersTotal': metadata(TABLES['researchers'], 'Researchers in R&D', 'researchers (FTE)',
            'All execution sectors; researchers only; both sexes. Full-time equivalents, not headcounts. '
            'PxWeb updated=9999 is a placeholder; source update date is from the archived display table.',
            'researchers.json', updated('researchers'), 'researchers_table.html'),
        'population': metadata(TABLES['population'], 'Population denominator', 'people',
            POPULATION_METHOD + ' PxWeb updated=9999 is a placeholder; no verified update date is available.', 'population.json'),
    }
    series = {'researchersTotal': {}, 'population': {}}

    def cell(v, flags, record, note, method, **provenance):
        assert v is None or (math.isfinite(v) and v >= 0)
        return {'v': v, 'flags': flags, 'note': note, 'record': record,
                'provenance': {'method': method, **provenance}}

    dates = {}
    for key in ['researchers', 'population']:
        for index, (coords, labels, value, status, dataset) in enumerate(px_rows(RAW / (key + '.json'))):
            assert all(coords[k] in values for k, values in SELECTIONS[key].items())
            record = f'dataset.value[{index}] ' + json.dumps(coords, ensure_ascii=False, separators=(',', ':'))
            v = None if value is None else float(value)
            if key == 'researchers':
                year = int(coords['periodo'])
                if 2000 <= year <= 2025:
                    series['researchersTotal'][str(year)] = cell(v, status, record, meta['researchersTotal']['definition'], 'reported Eustat FTE total')
            else:
                dates[coords['periodo']] = (v, status, record)
    for year in range(2000, 2026):
        july = dates.get(f'{year}0701')
        inputs = [july] if july and july[0] is not None else [dates.get(f'{year}0101'), dates.get(f'{year+1}0101')]
        if any(r is None or r[0] is None for r in inputs):
            continue
        proxy = len(inputs) == 2
        value = sum(r[0] for r in inputs) / len(inputs)
        assert value > 0
        series['population'][str(year)] = cell(value,
            ';'.join(filter(None, [*(r[1] for r in inputs), 'MIDYEAR_PROXY' if proxy else ''])),
            ';'.join(r[2] for r in inputs), POPULATION_METHOD,
            'mean of consecutive 1 January counts (midyear proxy)' if proxy else 'reported 1 July population',
            source_values=';'.join(str(r[0]) for r in inputs))

    context = {}
    for key, filename, row, label, unit, definition in [
        ('pctPatents', 'patents.xlsx', 6, 'PCT patent applications', 'applications per billion GDP (PPP euros)',
         'PCT applications normalized by GDP in PPP euros. Different filing coverage and denominator from WDI office-based resident/nonresident applications; total and per-population conversions are not supported by these inputs.'),
        ('internationalPublications', 'publications.xlsx', 6, 'International scientific co-publications', 'co-publications per million people',
         'International scientific co-publications, not the WDI scientific and technical journal article series. Retained in its published unit; no matching EIS denominator/count is archived for inversion.'),
        ('topCitedShare', 'publications.xlsx', 7, 'Publications among the worldwide top 10% most cited', '% of scientific publications',
         'Share of scientific publications among the worldwide top 10% most cited, not an article count or population rate.'),
    ]:
        book = load_workbook(RAW / filename, read_only=True, data_only=True)
        sheet = book['Hoja1']
        indicator = str(sheet.cell(row, 1).value)
        assert ('PCT' in indicator if key == 'pctPatents' else 'co-publications' in indicator if key == 'internationalPublications' else '10%' in indicator)
        m = metadata(indicator.split(' ')[0], label, unit, definition + ' ' + EIS_NOTE,
                     filename, updated(filename.split('.')[0]), filename.split('.')[0] + '_table.html')
        values = {}
        for column in range(2, sheet.max_column + 1):
            year = sheet.cell(5, column).value
            if year is None:
                continue
            assert isinstance(year, int) and 2000 <= year <= 2025 and str(year) not in values
            c = sheet.cell(row, column)
            values[str(year)] = cell(c.value, '', f'Hoja1!{get_column_letter(column)}{row}', EIS_NOTE, 'reported Eustat EIS 2025 ratio')
        context[key] = {'metadata': m, 'series': values}
        book.close()

    annual = []
    for metric, observations, m in [(k, v, meta[k]) for k, v in series.items()] + [(k, v['series'], v['metadata']) for k, v in context.items()]:
        for year, c in observations.items():
            annual.append({'iso3': 'ES-PV', 'economy': 'Basque Country', 'year': int(year), 'metric': metric,
                'value': c['v'], 'unit': m['unit'], 'availability': 'available' if c['v'] is not None else 'missing',
                'method': c['provenance']['method'], 'flags': c['flags'], 'notes': c['note'],
                'indicator': m['code'], 'source_file': m['source_file'], 'source_record': c['record'],
                'source_values': c['provenance'].get('source_values', c['v']), 'source_url': m['url'],
                'source_updated': m['updated'], 'retrieved_utc': m['retrieved']})
    return series, meta, context, annual, manifest
