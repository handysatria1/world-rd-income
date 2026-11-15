"""Optional Playwright regression test for a served constant-2021 PPP dashboard."""
import argparse
import csv
import io
from pathlib import Path
import sys
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8766/')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    with urlopen(args.url + 'gdp_per_capita_ppp_constant_2021.csv', timeout=60) as response:
        audit = {(row['iso3'], int(row['year'])): None if not row['value'] else float(row['value'])
                 for row in csv.DictReader(io.StringIO(response.read().decode('utf-8-sig')))}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if sys.platform == 'win32' else None)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, accept_downloads=True)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='networkidle')
        page.wait_for_function('window.Dashboard?.data != null')
        page.evaluate("async()=>{document.querySelector('#view').value='snapshot';document.querySelector('#shared-year').value='2022';await Dashboard.update();}")
        frame = next(frame for frame in page.frames[1:] if frame.frame_element().is_visible())
        assert frame.locator('#metric option').all_text_contents() == [
            'Current US$', 'PPP (current international $)', 'PPP (constant 2021 international $)']
        baseline = frame.evaluate('RDExplorer.result.rows.map(r=>r.country.iso)')
        frame.locator('#metric').select_option('ppp')
        assert frame.evaluate('RDExplorer.result.rows.map(r=>r.country.iso)') == baseline
        frame.locator('#metric').select_option('pppConstant')
        assert frame.locator('#error').is_hidden()
        assert 'constant 2021' in frame.locator('#charts').text_content()
        assert frame.locator('#charts [data-source-caption] a[href$="/NY.GDP.PCAP.PP.KD"]').count() > 0
        rows = frame.evaluate('RDExplorer.result.rows.map(r=>({iso:r.country.iso,year:r.end.gdpYear,value:r.end.pppConstant}))')
        assert len(rows) > 50
        for row in rows:
            assert row['year'] == 2022
            assert row['value'] == audit[row['iso'], row['year']], row
        assert not any(row['iso'] == 'ES-PV' for row in rows)
        with page.expect_download() as download:
            frame.locator('#export').click()
        exported = list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text('utf-8-sig'))))
        assert len(exported) == len(rows)
        assert all('constant 2021' in row['gdp_unit'] for row in exported)
        for row in exported:
            assert float(row['gdp']) == audit[row['code'], int(row['gdp_year'])]
        if args.screenshot:
            page.screenshot(path=str(args.screenshot), full_page=True)
        # Both endpoints must have actual constant-price income, and keep one sample.
        page.evaluate("async()=>{document.querySelector('#view').value='compare';await Dashboard.update();}")
        assert frame.locator('#metric').input_value() == 'pppConstant'
        pairs = frame.evaluate('RDExplorer.result.rows.map(r=>({iso:r.country.iso,start:r.start,end:r.end}))')
        assert pairs
        for row in pairs:
            for endpoint in ['start', 'end']:
                cell = row[endpoint]
                assert cell['pppConstant'] == audit[row['iso'], cell['gdpYear']]
        # History keeps gaps, exposes the new series, and leaves nominal R&D alone.
        page.evaluate("async()=>{document.querySelector('#view').value='history';await Dashboard.update();}")
        frame.locator('#country').select_option('USA')
        history = frame.evaluate('RDExplorer.result.rows')
        for row in history:
            assert row['pppConstant'] == audit.get(('USA', row['year']))
        before = [row['rdNominalUSD'] for row in history]
        frame.locator('#metric').select_option('nominal')
        assert before == frame.evaluate('RDExplorer.result.rows.map(r=>r.rdNominalUSD)')
        frame.locator('#metric').select_option('pppConstant')
        with page.expect_download() as download:
            frame.locator('#export').click()
        assert 'gdp_constant_2021_international_dollars_ppp' in Path(download.value.path()).read_text('utf-8-sig')
        # Explicit latest/common modes apply to the selected measure, not current PPP.
        page.evaluate("async()=>{document.querySelector('#view').value='snapshot';document.querySelector('#shared-year').value='latest';await Dashboard.update();}")
        for row in frame.evaluate('RDExplorer.result.rows.map(r=>({iso:r.country.iso,year:r.end.gdpYear,value:r.end.pppConstant}))'):
            assert row['value'] == audit[row['iso'], row['year']]
        page.evaluate("async()=>{document.querySelector('#shared-year').value='common';await Dashboard.update();}")
        assert frame.locator('#error').is_hidden()
        assert frame.evaluate('RDExplorer.result.rows.length') == 0  # includes unavailable Basque Country
        # Mobile control still exposes all three options and redraws without errors.
        page.set_viewport_size({'width': 390, 'height': 844})
        page.evaluate("async()=>{document.querySelector('#shared-year').value='2022';await Dashboard.update();}")
        assert frame.locator('#metric').is_visible()
        assert not errors, errors
        browser.close()
    print('Three income options, exact WDI values, preserved old cohorts, paired endpoints, history/CSV, latest/common years and mobile checks passed.')


if __name__ == '__main__':
    main()
