"""Read selected country/year observations from the official World Bank WDI CSV."""
import csv
from io import TextIOWrapper
from pathlib import Path
from zipfile import ZipFile


def load_wdi_observations(path, indicator_codes, first_year=2000, last_year=2025,
                          member_name='WDICSV.CSV', observed_only_years=False):
    """Read one WDI CSV pass and retain exact annual cells for requested series."""
    wanted = set(indicator_codes)
    assert wanted
    observations = {code: [] for code in wanted}
    observed_years = {code: set() for code in wanted}
    with ZipFile(path) as archive:
        member = next(name for name in archive.namelist()
                      if name.rsplit('/', 1)[-1].upper() == member_name.upper())
        with TextIOWrapper(archive.open(member), encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames or []
            assert {'Country Name', 'Country Code', 'Indicator Name', 'Indicator Code'} <= set(fields)
            years = {year: str(year) for year in range(first_year, last_year + 1)}
            assert set(years.values()) <= set(fields), (first_year, last_year, fields[-30:])
            columns = {year: fields.index(column) + 1 for year, column in years.items()}
            found = set()
            for row_number, row in enumerate(reader, 2):
                code = row['Indicator Code']
                if code not in wanted:
                    continue
                iso = (row['Country Code'] or '').strip()
                name = row['Country Name'] or ''
                assert len(iso) == 3 and iso.isalpha(), (row_number, iso, code)
                found.add(code)
                for year, column in columns.items():
                    raw = (row.get(years[year]) or '').strip()
                    value = None if raw in {'', '..'} else float(raw)
                    if value is not None:
                        observed_years[code].add(year)
                    observations[code].append({
                        'indicator': {'id': code, 'value': row['Indicator Name']},
                        'date': str(year), 'countryiso3code': iso,
                        'country': {'id': iso, 'value': name}, 'value': value,
                        '_source_record': f'{member}:row {row_number}, column {column} ({year})',
                        '_source_file': Path(path).name, '_source_country_code': iso,
                        '_country_match': 'iso3',
                    })
    assert found == wanted, {'missing WDI indicators': sorted(wanted - found)}
    if observed_only_years:
        for code in wanted:
            assert observed_years[code], code
            observations[code] = [row for row in observations[code]
                                  if int(row['date']) in observed_years[code]]
    return observations
