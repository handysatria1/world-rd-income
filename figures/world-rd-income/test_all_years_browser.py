"""Validate actual annual CSV downloads against every embedded observation."""
import argparse
import csv
import io
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

GDP = {'nominal':'current_usd','ppp':'ppp_current_international_dollars',
       'pppConstant':'ppp_constant_2021_international_dollars'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if sys.platform == 'win32' else None)
        page = browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
        errors = []
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='networkidle')
        page.wait_for_function('window.Dashboard?.data != null')
        frame = next(f for f in page.frames[1:] if f.frame_element().is_visible())
        data = frame.locator('#history-data').text_content()
        data = json.loads(data)
        countries = {c['iso']:c for c in data['countries']}
        assert len(countries) == 219

        def download():
            state = frame.evaluate('JSON.stringify({result:RDExplorer.result,controls:[...document.querySelectorAll("select,input")].map(e=>[e.id,e.value,e.checked])})')
            with page.expect_download() as event:
                frame.locator('#export-all-years').click()
            assert event.value.suggested_filename == 'rd-intensity-gdp-per-capita-all-economies-2000-2025.csv'
            content = Path(event.value.path()).read_bytes()
            assert content.startswith(b'\xef\xbb\xbf') and b'\r\n' in content
            assert state == frame.evaluate('JSON.stringify({result:RDExplorer.result,controls:[...document.querySelectorAll("select,input")].map(e=>[e.id,e.value,e.checked])})')
            return content

        content = download()
        rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
        assert len(rows) == 5694
        assert len({(r['economy_code'],r['year']) for r in rows}) == 5694
        providers = list(dict.fromkeys(['oecd','wdi','eustat','ons']+[s for c in countries.values() for s in c['rd']]))
        missing = 0
        for row in rows:
            c, year = countries[row['economy_code']], row['year']
            assert 2000 <= int(year) <= 2025
            assert row['economy'] == c['name']
            assert row['geography_notes'] == c.get('note','')
            assert row['data_build_utc'] == data.get('builtUTC','')
            priority = c.get('rdProviders',[s for s in ['oecd','wdi','eustat','ons'] if s in c['rd']])
            source = next((s for s in priority if year in c['rd'].get(s,{})),priority[0] if priority else '')
            assert row['rd_source_code'] == source
            selected = c['rd'].get(source,{}).get(year,{})
            pairs = [('rd_intensity_percent_gdp',selected)]
            for metric,stem in GDP.items():
                pairs.append(('gdp_per_capita_'+stem,c['gdp'].get(metric,{}).get(year,{})))
            for provider in providers:
                cell = c['rd'].get(provider,{}).get(year,{})
                pairs.append(('rd_'+provider+'_percent_gdp',cell))
                assert row['rd_'+provider+'_flags'] == cell.get('flags','')
                assert row['rd_'+provider+'_notes'] == cell.get('note','')
            for key,cell in pairs:
                expected = cell.get('v')
                assert (float(row[key]) if row[key] else None) == expected,(c['iso'],year,key)
            for metric,stem in GDP.items():
                key,cell = 'gdp_per_capita_'+stem,c['gdp'].get(metric,{}).get(year,{})
                for suffix,field in [('_flags','flags'),('_notes','note'),('_source_record','sourceRecord')]:
                    assert row[key+suffix] == cell.get(field,'')
            assert row['rd_flags'] == selected.get('flags','')
            assert row['rd_notes'] == selected.get('note','')
            if all(not cell for _,cell in pairs):
                missing += 1
            if c['iso'] == 'ES-PV':
                assert row['gdp_per_capita_ppp_constant_2021_international_dollars'] == ''
                assert row['parent_economy'] == 'ESP'
        assert missing > 0
        # Shared sample/year/economy controls and local GDP/history controls cannot restrict this export.
        page.evaluate("async()=>{document.querySelector('#sample-scope').value='selected';document.querySelector('#shared-year').value='2005';document.querySelector('#view').value='history';await Dashboard.update();}")
        frame.locator('.ui-advanced').first.evaluate('(el)=>el.open=true')
        frame.locator('#metric').select_option('pppConstant')
        frame.locator('#country').select_option('USA')
        assert download() == content
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1000})
            button = frame.locator('#export-all-years')
            assert button.is_visible()
            assert button.evaluate('(e)=>{const r=e.getBoundingClientRect();return r.width>0&&r.left>=0&&r.right<=document.documentElement.clientWidth+1}')
            assert download() == content
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not errors,errors
        browser.close()
    print(f'Annual CSV passed: 5,694 rows, every value/provider/flag/note/record checked, {missing} entirely missing rows retained; filter independence, unchanged chart state and desktop/mobile downloads.')


if __name__ == '__main__':
    main()
