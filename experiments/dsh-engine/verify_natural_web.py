"""Verify timestamps, progressive graph reveal, raw cards and mobile layout."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urljoin


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser()
    parser.add_argument('--url')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = Path(__file__).parent/'state/natural-web-check'
    out.mkdir(exist_ok=True)
    server = None
    if args.url:
        url = args.url
    else:
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/LLM_Optimization_Milestone/topic1-dag-observation.html'
    report = {'url': url, 'page_errors': [], 'missing_resources': [], 'cases': []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda e: report['page_errors'].append(str(e)))
            page.on('response', lambda r: report['missing_resources'].append([r.status, r.url]) if r.status >= 400 else None)
            page.goto(url, wait_until='networkidle')
            page.wait_for_function("document.querySelectorAll('#cases button').length===5 && document.querySelector('#case-id').textContent.endsWith('coding')")
            assert page.locator('#summary tr').count() == 5
            for case, models, tools in [('simple', 1, 0), ('research', 13, 68), ('coding', 6, 11), ('analysis', 16, 18), ('incident', 5, 11)]:
                page.locator(f'[data-case="{case}"]').click()
                page.wait_for_function('(id)=>document.querySelector("#case-id").textContent.endsWith(id)', arg=case)
                assert page.locator('#graph [data-node]').count() == models+tools
                assert '没有创建子Agent' in page.locator('#agent-map').inner_text()
                report['cases'].append({'case': case, 'model_nodes': models, 'tool_nodes': tools})
                for a in page.locator('#evidence-links a').all():
                    evidence = urljoin(page.url, a.get_attribute('href'))
                    # Archives are independently hash-checked offline. Check
                    # their published availability without downloading 9 MB
                    # repeatedly for scenarios sharing the same archive.
                    response = page.request.head(evidence) if evidence.endswith('.tar.gz') else page.request.get(evidence)
                    assert response.status == 200, evidence
                page.locator('#cursor').evaluate("el=>{el.value=0;el.dispatchEvent(new Event('input'))}")
                assert page.locator('#graph [data-node]').count() == 0
                page.locator('#cursor').evaluate("el=>{el.value=el.max;el.dispatchEvent(new Event('input'))}")
            page.locator('[data-case="coding"]').click()
            page.wait_for_function("document.querySelector('#case-id').textContent.endsWith('coding')")
            page.locator('#graph [data-node]').first.click()
            assert not page.locator('#drawer').get_attribute('hidden')
            page.locator('#drawer-content summary').get_by_text('完整 Prompt · 实际 messages', exact=True).click()
            assert 'Fix the checkout service' in page.locator('#drawer-content details[open] pre').inner_text()
            page.screenshot(path=str(out/'natural-raw-card.png'))
            page.keyboard.press('Escape')
            # At the first request, a future response must not be exposed.
            page.locator('#cursor').evaluate("el=>{el.value=2;el.dispatchEvent(new Event('input'))}")
            page.locator('#graph [data-node]').first.click()
            assert '响应尚未完整提交' in page.locator('#drawer-content').inner_text()
            assert '模型实际返回' not in page.locator('#drawer-content').inner_text()
            page.keyboard.press('Escape')
            page.locator('#cursor').evaluate("el=>{el.value=el.max;el.dispatchEvent(new Event('input'))}")
            page.locator('#timeline-panel').screenshot(path=str(out/'natural-timeline-desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#timeline-panel').screenshot(path=str(out/'natural-timeline-mobile.png'))
            assert page.locator('#failed-links a').count() == 4
            assert not report['page_errors'] and not report['missing_resources'], report
            browser.close()
    finally:
        if server:server.shutdown();server.server_close()
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
