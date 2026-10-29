"""Check the DSH result selector, every task graph, raw drawers and navigation."""
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
    parser.add_argument('--url', help='Use a published result page instead of a temporary local server.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = Path(__file__).parent/'state/results-web-check'
    out.mkdir(parents=True, exist_ok=True)
    server = None
    if args.url:
        url = args.url
    else:
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/LLM_Optimization_Milestone/topic1-experiments.html'
    report = {'url': url, 'task_graphs': 0, 'page_errors': [], 'missing_resources': []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.on('pageerror', lambda error: report['page_errors'].append(str(error)))
            page.on('response', lambda r: report['missing_resources'].append([r.status, r.url]) if r.status >= 400 else None)
            page.goto(url, wait_until='networkidle')
            page.wait_for_function("document.querySelector('#run-label').textContent==='dsh-e1-small-native' && document.querySelectorAll('#flow .flow-node').length===13")
            assert page.locator('#dataset').input_value() == 'dsh'
            assert page.locator('#rounds tr').count() == 3
            runs = page.locator('#run option').evaluate_all('(nodes)=>nodes.map(n=>n.value)')
            for run in runs:
                page.select_option('#run', run)
                page.wait_for_function('(id)=>document.querySelector("#run-label").textContent===id && document.querySelector("#status").textContent.includes("第 ")', arg=run)
                tasks = page.locator('#task option').evaluate_all('(nodes)=>nodes.map(n=>n.value)')
                assert len(tasks) == 8
                for task in tasks:
                    page.select_option('#task', task)
                    page.wait_for_function('(id)=>document.querySelector("#task-data").href.includes(id)', arg=task)
                    assert page.locator('#flow .flow-node').count() == 13
                    assert page.locator('#flow svg > path').count() == 14
                    assert page.locator('#flow .flow-node .type').all_text_contents().count('QWEN · 模型调用') == 8
                    report['task_graphs'] += 1
                if run.endswith('pressure12'):
                    assert '压力收缩触发 0 次' in page.locator('#cache-note').inner_text()
                for a in page.locator('#links a').all():
                    assert page.request.get(urljoin(page.url, a.get_attribute('href'))).status == 200
            page.locator('#flow .flow-node').nth(1).click()
            page.wait_for_function("document.querySelector('#drawer').classList.contains('open')")
            drawer = page.locator('#drawer-content')
            assert '前端派发等待' in drawer.inner_text()
            drawer.get_by_text('完整 Prompt · 实际 messages', exact=True).click()
            assert 'Research question:' in drawer.locator('details[open] pre').inner_text()
            drawer.get_by_text('派发时的真实后端状态与控制动作', exact=True).click()
            assert 'observed_wall_time' in drawer.inner_text()
            page.screenshot(path=str(out/'dsh-raw-drawer.png'))
            page.keyboard.press('Escape')
            page.wait_for_timeout(250)
            page.locator('#detail').screenshot(path=str(out/'dsh-flow-desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.locator('#task').bounding_box()['width'] <= 365
            page.locator('#detail').screenshot(path=str(out/'dsh-flow-mobile.png'))
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.select_option('#dataset', 'shared')
            page.wait_for_function("document.querySelectorAll('#flow .flow-node').length===17")
            assert page.locator('#rounds tr').count() == 8
            page.select_option('#dataset', 'dsh')
            page.wait_for_function("document.querySelectorAll('#flow .flow-node').length===13")
            page.goto(urljoin(url, 'topic1-harness-engine.html'), wait_until='networkidle')
            assert '官方 DSH 八题三轮完成' in page.locator('.status').inner_text()
            page.goto(urljoin(url, 'LLM_Optimization_Milestone.html'), wait_until='networkidle')
            assert '官方 DSH 八题三轮' in page.locator('.current-research').last.inner_text()
            assert not report['page_errors'] and not report['missing_resources'], report
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
