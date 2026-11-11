"""Independent normalized-cell checks against original JSON-stat arrays and XLSX cells."""
import json
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

ROOT = Path(__file__).resolve().parent


def verify():
    data = json.loads((ROOT / 'data/income_explorer.json').read_text('utf-8'))
    region = next(c for c in data['countries'] if c['iso'] == 'ES-PV')
    raw = ROOT / 'data/basque_innovation_raw'
    r = json.loads((raw / 'researchers.json').read_text('utf-8'))['dataset']
    p = json.loads((raw / 'population.json').read_text('utf-8'))['dataset']
    ri = r['dimension']['periodo']['category']['index']
    pi = p['dimension']['periodo']['category']['index']
    checks = 0
    for year, cell in region['series']['researchersTotal'].items():
        assert cell['v'] == r['value'][ri[year]]
        assert f'dataset.value[{ri[year]}]' in cell['record']
        assert all(k in cell['record'] for k in ['"00"', '"200"', '"10"'])
        checks += 1
    for year, cell in region['series']['population'].items():
        july = year + '0701'
        dates = [july] if july in pi else [year+'0101', str(int(year)+1)+'0101']
        original = [p['value'][pi[d]] for d in dates]
        assert cell['v'] == sum(original)/len(original)
        assert ('MIDYEAR_PROXY' in cell['flags']) == (len(dates) == 2)
        assert all(f'dataset.value[{pi[d]}]' in cell['record'] and d in cell['record'] for d in dates)
        assert [float(v) for v in cell['provenance']['source_values'].split(';')] == original
        checks += 1
    for key, indicator in region['contextIndicators'].items():
        file = ROOT / 'data' / indicator['metadata']['source_file']
        book = load_workbook(file, read_only=True, data_only=True)
        for year, cell in indicator['series'].items():
            sheet, address = cell['record'].split('!')
            source = book[sheet][address]
            assert source.value == cell['v']
            column = column_index_from_string(coordinate_from_string(address)[0])
            assert book[sheet].cell(5, column).value == int(year)
            checks += 1
        book.close()
    assert region['current'] == 'UNK' and region['region']
    assert not {'patents', 'patentsNonresident', 'publications'} & region['series'].keys()
    assert region['series']['researchersTotal']['2024']['v'] == 17296.2
    assert region['series']['researchersTotal']['2000']['v'] == 5494
    assert region['indicatorMetadata']['researchersTotal']['updated'] == '2025-11-14'
    assert region['indicatorMetadata']['population']['updated'] == ''
    assert region['contextIndicators']['pctPatents']['series']['2022']['v'] == 1.32746063252974
    assert region['contextIndicators']['internationalPublications']['series']['2024']['v'] == 2003.02395459515
    # Independently check every loaded WDI population record, including missing cells.
    observations = json.loads((ROOT / 'data/income_raw/population.json').read_text('utf-8'))[1]
    population_checks = 0
    for country in data['countries']:
        if country.get('region'):
            continue
        for year, cell in country['series'].get('population', {}).items():
            source = observations[cell['record']-1]
            assert (source['countryiso3code'], source['date'], source['value']) == (country['iso'], year, cell['v'])
            population_checks += 1
    report = {'verification': 'passed', 'Eustat_cells_checked': checks, 'WDI_population_cells_checked': population_checks,
              'basque_2024_population': region['series']['population']['2024']['v'],
              'basque_2024_researchers_per_million': 17296.2 / region['series']['population']['2024']['v'] * 1e6}
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    verify()
