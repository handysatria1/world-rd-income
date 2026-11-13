"""Optional end-to-end check: pip install playwright; use --url for a staged site."""
import argparse
from pathlib import Path
import sys
import struct

from playwright.sync_api import sync_playwright


def check_page(page):
    return page.evaluate("""() => {
      SourceCaptions.refresh();
      const charts=[...document.querySelectorAll('svg.chart,.plot-wrap > svg,#chart > svg')];
      const tables=[...document.querySelectorAll('table')];
      return {
        charts:charts.length, tables:tables.length,
        missingCharts:charts.filter(svg=>svg.querySelectorAll(':scope > [data-source-caption]').length!==1).length,
        missingTables:tables.filter(table=>{
          const container=table.closest('.scroll,.table-scroll')||table;
          return !container.nextElementSibling?.classList.contains('source-caption');
        }).length,
        brokenLinks:[...document.querySelectorAll('[data-source-caption] a,.source-caption a')].filter(a=>!a.getAttribute('href')).length,
        overflowing:charts.flatMap(svg=>[...svg.querySelectorAll('[data-source-caption] text')].filter(t=>{
          const b=t.getBBox(),v=svg.viewBox.baseVal;
          return b.x<v.x||b.x+b.width>v.x+v.width+2||b.y+b.height>v.y+v.height+2;
        })).length
      };
    }""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if sys.platform == 'win32' else None)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, accept_downloads=True)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='networkidle')
        page.wait_for_function('window.Dashboard?.data != null')
        routes = page.locator('#view option').evaluate_all('(options)=>options.map(o=>o.value)')
        for route in routes:
            page.evaluate("async route=>{document.querySelector('#view').value=route;await Dashboard.update();}", route)
            assert page.locator('#dashboard-error').is_hidden(), page.locator('#dashboard-error').text_content()
            frame = next((frame for frame in page.frames[1:] if frame.frame_element().is_visible()), None)
            target = frame or page
            report = check_page(target)
            assert not any(report[key] for key in ['missingCharts', 'missingTables', 'brokenLinks', 'overflowing']), (route, report)
            if route == 'patents':
                assert 'WIPO' in page.locator('#innovation-panel [data-source-caption]').text_content()
            print(route, report, flush=True)
        # A selected detail source must update just its own table's attribution.
        page.evaluate("async()=>{document.querySelector('#view').value='detail';await Dashboard.update();}")
        frame = next(frame for frame in page.frames[1:] if frame.frame_element().is_visible())
        frame.locator('#gva-source').select_option('UNIDO_INDSTAT')
        frame.wait_for_function("document.querySelector('#gva-rows').closest('.scroll').nextElementSibling.textContent.includes('UNIDO INDSTAT')")
        note = frame.locator('#gva-rows').locator('xpath=ancestor::table/parent::div/following-sibling::p[1]').text_content()
        assert 'OECD' not in note, note
        # Local redraws and repeated refreshes do not grow the SVG or duplicate notes.
        page.evaluate("async()=>{document.querySelector('#view').value='snapshot';await Dashboard.update();}")
        frame = next(frame for frame in page.frames[1:] if frame.frame_element().is_visible())
        before = frame.locator('svg.chart').first.get_attribute('viewBox')
        frame.evaluate('()=>{SourceCaptions.refresh();SourceCaptions.refresh();}')
        assert frame.locator('svg.chart').first.get_attribute('viewBox') == before
        page.evaluate("async()=>{document.querySelector('#shared-year').value='2022';await Dashboard.update();}")
        frame.locator('#rdMode').select_option('3')
        frame.wait_for_function("document.querySelector('svg.chart [data-source-caption]')!=null")
        assert check_page(frame)['missingCharts'] == 0
        # Exported SVG contains the visible linked source footer; PNG keeps its aspect ratio.
        page.evaluate("async()=>{document.querySelector('#view').value='income';await Dashboard.update();}")
        with page.expect_download() as download:
            page.locator('#income-svg-download').click()
        svg = Path(download.value.path()).read_text('utf-8')
        assert 'data-source-caption' in svg and 'Source:' in svg and 'IP.PAT.RESD' in svg
        with page.expect_download() as download:
            page.locator('#income-png-download').click()
        png = Path(download.value.path()).read_bytes()
        assert len(png) > 1000
        width, height = struct.unpack('>II', png[16:24])
        box = page.locator('#income-panel svg').first.get_attribute('viewBox').split()
        assert abs(width / height - float(box[2]) / float(box[3])) < 0.01
        if args.screenshots:
            args.screenshots.mkdir(parents=True, exist_ok=True)
            page.evaluate("async()=>{document.querySelector('#view').value='snapshot';await Dashboard.update();}")
            page.screenshot(path=str(args.screenshots / 'snapshot-sources.png'), full_page=True)
        # Repeat on a narrow screen and ensure table notes remain outside scrolling regions.
        page.set_viewport_size({'width': 390, 'height': 844})
        page.evaluate("async()=>{document.querySelector('#view').value='research-six';await Dashboard.update();}")
        frame = next(frame for frame in page.frames[1:] if frame.frame_element().is_visible())
        assert check_page(frame)['missingTables'] == 0
        page.evaluate("async()=>{document.querySelector('#clear-economies').click();await Dashboard.update();}")
        assert page.locator('#dashboard-error').is_hidden()
        assert check_page(frame)['missingTables'] == 0
        assert not errors, errors
        browser.close()
    print('All routes, source switching, local redraws, SVG/PNG exports and narrow-screen table notes passed.')


if __name__ == '__main__':
    main()
