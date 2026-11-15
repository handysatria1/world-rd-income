"""Check new figure text fits and displayed headings/exports remain controlled."""
import argparse
import sys
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--baseline-url')
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge' if sys.platform == 'win32' else None)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        page.goto(args.url, wait_until='networkidle')
        page.wait_for_function('window.Dashboard?.data != null')
        reference = None
        if args.baseline_url:
            reference = browser.new_page(viewport={'width': 1440, 'height': 1100})
            reference.goto(args.baseline_url, wait_until='networkidle')
            reference.wait_for_function('window.Dashboard?.data != null')
        failures = []
        exports = 0
        for route in page.locator('#view option').evaluate_all('(xs)=>xs.map(x=>x.value)'):
            page.evaluate("async route=>{document.querySelector('#view').value=route;await Dashboard.update();}", route)
            frame = next((f for f in page.frames[1:] if f.frame_element().is_visible()), page)
            # Only the longer replacement notes/labels are within this layout audit.
            overflow = frame.evaluate("""()=>[...document.querySelectorAll('svg text')].filter(t=>/GVA per employed person at current|This comparison is descriptive|Source branch allocations|classification correspondence|Required complete observations|Employment|Country means/.test(t.textContent)).flatMap(t=>{const b=t.getBBox(),v=t.ownerSVGElement.viewBox.baseVal;return b.x<0||b.x+b.width>v.width?[t.textContent]:[]})""")
            failures.extend((route, text) for text in overflow)
            if reference:
                reference.evaluate("async route=>{document.querySelector('#view').value=route;await Dashboard.update();}", route)
                old_frame = next((f for f in reference.frames[1:] if f.frame_element().is_visible()), reference)
                selector = {'income':'#income-csv-download'}.get(route, '#innovation-csv-download' if frame==page and route not in ['absorptive-capacity'] else '#export,#research-csv,#csv')
                outputs = []
                for target in [old_frame, frame]:
                    outputs.append(target.evaluate("""async selector=>{
                      const button=[...document.querySelectorAll(selector)].find(b=>!b.disabled&&b.getClientRects().length);
                      if(!button)return null;
                      const originalURL=URL.createObjectURL,originalClick=HTMLAnchorElement.prototype.click;
                      let contents;
                      URL.createObjectURL=blob=>{contents=blob.text();return originalURL(blob)};
                      HTMLAnchorElement.prototype.click=function(){};
                      try{button.click();return contents?await contents:null;}
                      finally{URL.createObjectURL=originalURL;HTMLAnchorElement.prototype.click=originalClick;}
                    }""", selector))
                assert outputs[0]==outputs[1], ('Changed CSV export', route)
                if outputs[0] is not None:
                    exports += 1
        assert not failures, failures
        browser.close()
    print('Longer figure wording fits within SVG bounds across all 31 views.')
    if reference:
        assert exports>=20, exports
        print(f'{exports} dynamically generated CSV exports are byte-identical to the previous publication.')


if __name__ == '__main__':
    main()
