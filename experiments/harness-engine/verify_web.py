"""Browser regression check of real results, flow arrows, raw drawers and mobile."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading


def main():
    from playwright.sync_api import sync_playwright
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path(__file__).parent/'evidence/web-v021')
    args = parser.parse_args()
    out = args.out; out.mkdir(parents=True, exist_ok=True)

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    url = f'http://127.0.0.1:{server.server_port}/LLM_Optimization_Milestone/topic1-experiments.html'
    errors, missing = [], []
    report = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('response', lambda r: missing.append([r.status, r.url]) if r.status >= 400 else None)
            page.goto(url+'#v024-shared-native-a')
            page.wait_for_function("document.querySelectorAll('#flow .flow-node').length===17")
            report['desktop'] = {'nodes': page.locator('#flow .flow-node').count(),
                                 'arrows': page.locator('#flow svg > path').count(),
                                 'target_background_description': page.locator('#purpose').inner_text()}
            report['paused_status_visible'] = '用户已暂停研究' in page.locator('#pause-progress').inner_text()
            assert report['paused_status_visible']
            assert report['desktop']['arrows'] == 18
            assert '独立Harness控制器' in report['desktop']['target_background_description']
            page.locator('#dataset').select_option('shared')
            page.wait_for_function("document.querySelector('#status').textContent.includes('已载入')")
            report['shared_visible_rows'] = page.locator('#rounds tr').count()
            assert report['shared_visible_rows'] == 8
            page.select_option('#run', 'v024-shared-native-a')
            page.wait_for_function("document.querySelector('#run-label').textContent==='v024-shared-native-a'")
            page.wait_for_timeout(250)
            page.locator('#flow .flow-node').nth(1).click()
            page.wait_for_timeout(250)
            page.locator('#drawer-content summary').first.click()
            report['raw_prompt_present'] = 'Question:' in page.locator('#drawer-content pre').first.inner_text()
            assert report['raw_prompt_present']
            page.screenshot(path=str(out/'shared-raw-drawer-1440.png'), full_page=True)
            page.keyboard.press('Escape'); page.wait_for_timeout(250)
            page.screenshot(path=str(out/'shared-flow-1440.png'), full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            page.wait_for_timeout(250)
            report['mobile'] = page.evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})')
            assert report['mobile']['scrollWidth'] <= report['mobile']['width']
            page.screenshot(path=str(out/'shared-flow-390.png'), full_page=True)
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.select_option('#dataset', 'mixed')
            page.wait_for_function("document.querySelector('#run-title').textContent.includes('长短上下文混合')")
            report['mixed_visible_rows'] = page.locator('#rounds tr').count()
            report['page_errors'] = errors; report['missing_resources'] = missing
            assert not errors and not missing
            browser.close()
    finally:
        server.shutdown(); server.server_close()
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
