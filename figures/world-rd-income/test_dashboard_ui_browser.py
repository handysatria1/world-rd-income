"""Presentation UI and share-link regression checks against a served dashboard."""
import argparse
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

HEADING_REPLACEMENTS = {
    'metric':'Indicator', 'group label':'Income group', 'economy':'Economy',
    'year':'Year', 'value':'Value', 'unit':'Unit', 'method':'Calculation method',
    'n':'Economies with observations', 'eligible':'Eligible economies',
    'classification':'Income classification', 'included':'Included economies',
    'missing':'Missing or excluded economies', 'missing reason':'Reason for missing observation',
    'source country code':'Source economy code', 'country match':'Economy-code matching',
    'population used':'Population used in calculation', 'population method':'Population calculation method',
    'population flags':'Population source flags', 'flags':'Source flags', 'notes':'Notes',
    'Average of country means':'Unweighted mean of country means',
    'Million local currency':'Local currency (millions)', 'Million US$':'US$ (millions)',
    'Official source':'Source', 'Assigned R&D · US$ bn':'Assigned business R&D (US$ billion)',
    'GVA/person · US$ thousand':'GVA per employed person (US$ thousand)',
    'R&D/worker · US$':'Business R&D per employed person (US$)',
    'GDP/person · current US$':'GDP per capita (current US$)',
    '% manufactured exports':'Share of manufactured exports (%)',
    'Provider USD (unit amounts)':'Source-reported US$ (units)',
}


def active(page):
    return next((f for f in page.frames[1:] if f.frame_element().is_visible()), None)


def ready(page):
    page.wait_for_function("window.DashboardUI && document.querySelector('#ui-present') && !document.querySelector('#loading').hidden === false && document.querySelector('#view-host iframe:not([hidden])')?.contentWindow.RDExplorer?.result != null")
    assert page.locator('#dashboard-error').is_hidden(), page.locator('#dashboard-error').text_content()


def expand(frame):
    details=frame.locator('.ui-advanced').first
    if not details.evaluate('(el)=>el.open'):details.locator(':scope > summary').click()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8767/')
    parser.add_argument('--screenshots',type=Path)
    parser.add_argument('--baseline-url',help='Optional previous deployment to compare every displayed data table')
    args=parser.parse_args()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge' if sys.platform=='win32' else None)
        page=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
        page.set_default_navigation_timeout(90000)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='networkidle');ready(page)
        assert page.locator('h1').text_content()=='R&D and Economic Development'
        assert page.locator('nav.tabs button').all_text_contents()==['Overview','Economy comparisons','Industry analysis','Data and methods']
        frame=active(page)
        assert not frame.locator('.ui-advanced').first.evaluate('(el)=>el.open')
        assert not frame.locator('#ui-plotted-data').evaluate('(el)=>el.open')
        assert 'GDP per capita · Current US$' in frame.locator('#selection-description').text_content()
        # Observe complete animation cycles to detect self-triggering observer loops.
        mutations=frame.evaluate("""async()=>{let n=0;const o=new MutationObserver(()=>n++);o.observe(document.querySelector('main'),{childList:true,subtree:true});for(let i=0;i<12;i++)await new Promise(requestAnimationFrame);o.disconnect();return n;}""")
        assert mutations<4,mutations
        expand(frame)
        frame.locator('#metric').select_option('pppConstant')
        page.evaluate("async()=>{document.querySelector('#shared-year').value='2022';document.querySelector('#sample-scope').value='selected';await Dashboard.update();}")
        frame.locator('#rdMode').select_option('3')
        assert 'constant 2021' in frame.locator('#selection-description').text_content()
        baseline=frame.evaluate('RDExplorer.exported')
        before=page.evaluate('DashboardUI.state()')
        # Clipboard fallback stays accessible even in presentation mode.
        page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('Unavailable')}}})")
        page.locator('#ui-present').click()
        assert page.locator('#shared-controls').is_hidden()
        assert frame.locator('.ui-advanced').first.is_hidden()
        assert frame.locator('svg.chart [data-source-caption]').is_visible()
        page.locator('#ui-share').click()
        assert page.locator('#ui-share-link').is_visible()
        shared=page.url
        page.keyboard.press('Escape')
        assert page.locator('#shared-controls').is_visible()
        page.locator('#ui-present').click()
        frame.locator('svg.chart').click(position={'x':100,'y':100})
        frame.locator('body').press('Escape')
        assert page.locator('#shared-controls').is_visible()
        page.goto(shared,wait_until='networkidle');ready(page)
        frame=active(page)
        assert page.evaluate('DashboardUI.state()')==before
        assert frame.evaluate('RDExplorer.exported')==baseline
        assert frame.locator('#metric').input_value()=='pppConstant'
        expand(frame)
        frame.locator('#strict').check()
        frame.locator('#ui-plotted-data > summary').click()
        assert frame.locator('#data-table').is_visible()
        frame.locator('#stats .ui-info').first.click()
        assert frame.locator('#ui-stat-note').is_visible()
        # Compare controls restore exactly too (including ordered years).
        page.evaluate("async()=>{Dashboard.navigate('compare');await Dashboard.update();}")
        frame.locator('#fromYear').select_option('2010')
        frame.locator('#toYear').select_option('2022')
        page.locator('#ui-share').click()
        compare_state=page.evaluate('DashboardUI.state()');compare_url=page.url
        page.goto(compare_url,wait_until='networkidle');ready(page)
        assert page.evaluate('DashboardUI.state()')==compare_state
        # All original routes and table/figure methods remain available.
        routes=page.locator('#view option').evaluate_all('(els)=>els.map(el=>el.value)')
        for route in routes:
            page.evaluate("async route=>{document.querySelector('#view').value=route;await Dashboard.update();}",route)
            assert page.locator('#dashboard-error').is_hidden(),(route,page.locator('#dashboard-error').text_content())
            target=active(page) or page
            assert target.locator('svg.chart,.plot-wrap > svg,#chart > svg,table').count()>0,route
            target.evaluate('SourceCaptions.refresh()')
            assert target.locator('.source-methods').count()>0,route
        # Navigation uses the real category entry points.
        page.locator('nav.tabs button').nth(2).click()
        page.wait_for_function("document.querySelector('#view').value==='research'&&!document.querySelector('#loading').hidden===false")
        frame=active(page)
        expand(frame)
        frame.locator('#research-layout').select_option('industries')
        page.locator('#ui-share').click()
        industry_state=page.evaluate('DashboardUI.state()');industry_url=page.url
        old_page=page
        page=browser.new_page(viewport={'width':1440,'height':1100},accept_downloads=True)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(industry_url,wait_until='load')
        page.wait_for_function("window.DashboardUI && document.querySelector('#view-host iframe:not([hidden])')?.contentDocument.body.classList.contains('ui-frame') && document.querySelector('#loading').hidden")
        old_page.close()
        assert page.evaluate('DashboardUI.state()')==industry_state
        # Reset is a clean recovery from a saved view.
        page.locator('#ui-reset').click();page.wait_for_url('**/#snapshot');ready(page)
        assert '?' not in page.url
        assert active(page).locator('#metric').input_value()=='nominal'
        if args.screenshots:
            args.screenshots.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(args.screenshots/'overview.png'),full_page=True)
            page.locator('#ui-present').click()
            page.screenshot(path=str(args.screenshots/'presentation.png'),full_page=True)
            page.locator('#ui-present').click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        frame=active(page)
        assert frame.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        expand(frame)
        assert frame.locator('#metric').is_visible()
        if args.screenshots:page.screenshot(path=str(args.screenshots/'mobile.png'),full_page=True)
        assert not errors,errors
        if args.baseline_url:
            reference=browser.new_page(viewport={'width':1440,'height':1100})
            reference.goto(args.baseline_url,wait_until='networkidle')
            page.goto(args.url,wait_until='networkidle');ready(page)
            for route in routes:
                outputs=[]
                for current in [reference,page]:
                    current.evaluate("async route=>{document.querySelector('#view').value=route;await Dashboard.update();}",route)
                    target=active(current) or current
                    outputs.append(target.locator('table').evaluate_all('(tables)=>tables.map(t=>({id:t.id,headings:[...t.querySelectorAll("thead th")].map(c=>c.textContent),rows:[...t.tBodies].flatMap(b=>[...b.rows].map(r=>[...r.cells].map(c=>c.textContent)))}))'))
                for table in outputs[0]:
                    if route!='sources':
                        table['headings']=[HEADING_REPLACEMENTS.get(value,value) for value in table['headings']]
                if route=='sources':
                    # Only the approved source-map documentation cell may change.
                    for table in outputs[0]:
                        table['rows']=[[cell.replace('GDP per person in current US$ and current international dollars (PPP); total current-US$ GDP for derived nominal R&D.', 'GDP per capita in current US$, current international dollars (PPP) and constant 2021 international dollars (PPP). Total GDP in current US$ is used to derive nominal R&D expenditure.') for cell in row] for row in table['rows']]
                assert outputs[0]==outputs[1],('Changed displayed data',route)
            print('All 31 routes retain identical table values, coverage flags and row ordering versus the prior deployment; approved display headings may differ.')
        browser.close()
    print('UI checks passed: all routes, collapsed controls/data, observer settling, exact share restoration, presentation/Escape, clipboard fallback, reset and mobile.')


if __name__=='__main__':
    main()
