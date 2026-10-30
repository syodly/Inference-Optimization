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
    out.mkdir(parents=True, exist_ok=True)
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
            page.goto(url+('&'if '?'in url else '?')+'source=legacy', wait_until='networkidle')
            page.wait_for_function("document.querySelectorAll('#cases button').length===5 && document.querySelector('#case-id').textContent.endsWith('coding')")
            assert page.locator('#summary tr').count() == 5
            for case, models, tools, peak in [('simple', 1, 0, 0), ('research', 13, 68, 10), ('coding', 6, 11, 5), ('analysis', 16, 18, 4), ('incident', 5, 11, 5)]:
                page.locator(f'[data-case="{case}"]').click()
                page.wait_for_function('(id)=>document.querySelector("#case-id").textContent.endsWith(id)', arg=case)
                assert page.locator('#graph [data-node]').count() == models+tools
                assert '没有创建子Agent' in page.locator('#agent-map').inner_text()
                assert f'工具在途峰值 {peak}' in page.locator('#parallel-explanation').inner_text()
                assert page.locator('#graph .wire-svg > path').count() > 0
                if tools:
                    assert page.locator('#gantt .gantt-bar:not(.wait-bar)').count() >= peak
                report['cases'].append({'case': case, 'model_nodes': models, 'tool_nodes': tools, 'observed_tool_peak': peak})
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
            page.locator('#graph .parallel-block summary').first.click()
            page.wait_for_timeout(100)
            assert page.locator('#graph .branch-svg path').count() == 10
            assert page.locator('#graph .wire-svg > path[stroke-dasharray]').count() == 2
            page.locator('#graph .parallel-block .tool').first.click()
            assert page.locator('#drawer-content .file-line').count() == 13
            assert 'Public contracts' in page.locator('#drawer-content .file-preview').inner_text()
            page.screenshot(path=str(out/'natural-readable-file.png'))
            page.keyboard.press('Escape')
            page.locator('#graph [data-node]').first.click()
            assert not page.locator('#drawer').get_attribute('hidden')
            assert '本轮完整提出的动作' in page.locator('#drawer-content').inner_text()
            page.locator('[data-tab="context"]').click()
            assert 'Fix the checkout service' in page.locator('#drawer-content details[open] .readable').inner_text()
            page.screenshot(path=str(out/'natural-raw-card.png'))
            page.keyboard.press('Escape')
            # At the first request, a future response must not be exposed.
            page.locator('#cursor').evaluate("el=>{el.value=2;el.dispatchEvent(new Event('input'))}")
            page.locator('#graph [data-node]').first.click()
            assert '响应尚未完整提交' in page.locator('#drawer-content').inner_text()
            assert '模型实际返回' not in page.locator('#drawer-content').inner_text()
            page.locator('[data-tab="config"]').click()
            assert '响应完成后显示' in page.locator('#drawer-content').inner_text()
            page.keyboard.press('Escape')
            page.locator('#cursor').evaluate("el=>{el.value=el.max;el.dispatchEvent(new Event('input'))}")
            page.locator('#step-select').select_option(index=1)
            assert '重叠峰值 5' in page.locator('#gantt-caption').inner_text()
            page.locator('#step-select').select_option(index=3)
            assert '3 个已提出工具' in page.locator('#gantt-caption').inner_text()
            assert '重叠峰值 1' in page.locator('#gantt-caption').inner_text()
            page.locator('#step-select').select_option(index=1)
            page.locator('#timeline-panel').screenshot(path=str(out/'natural-timeline-desktop.png'))
            page.locator('.timeline-box').screenshot(path=str(out/'natural-tool-overlap.png'))
            page.locator('#findings').screenshot(path=str(out/'natural-findings-desktop.png'))
            # Coding step two completes at 12.588 s. Its five actions are
            # known before the first native tool/call at 12.5916 s.
            page.locator('#cursor').evaluate("el=>{el.value=12.590;el.dispatchEvent(new Event('input'))}")
            assert page.locator('#graph .tool').count() == 6
            assert '完整提出' in page.locator('#graph').inner_text()
            page.locator('#cursor').evaluate("el=>{el.value=el.max;el.dispatchEvent(new Event('input'))}")
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#timeline-panel').screenshot(path=str(out/'natural-timeline-mobile.png'))
            page.locator('#findings').screenshot(path=str(out/'natural-findings-mobile.png'))
            assert page.locator('#failed-links a').count() == 4
            # Native ODR / GPT Researcher are separate data models; keep the
            # existing DSH graph parser and its five regression cases intact.
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.wait_for_function("document.querySelectorAll('#fw-tabs button').length===4")
            catalogue=page.request.get(urljoin(url,'../experiments/dsh-engine/results/natural-dag-20261029/frameworks/experiment-catalogue.json')).json()
            assert page.locator('#fw-coverage [data-coverage]').count()==4
            assert '0题' in page.locator('[data-coverage="odr"]').inner_text()
            assert '未完成' in page.locator('[data-coverage="coding"]').inner_text()
            assert '未完成' in page.locator('[data-coverage="crag"]').inner_text()
            assert '不是三个数据集' in page.locator('.fw-view-note').inner_text()
            page.locator('#fw-coverage').screenshot(path=str(out/'experiment-coverage-desktop.png'))
            report['native_frameworks'] = []
            for framework, workers in [('odr',3),('odr-focused',0),('odr-wide',3),('gptr',6)]:
                page.locator(f'[data-fw="{framework}"]').click()
                page.wait_for_function('(id)=>document.querySelector("#fw-body").dataset.loaded===id',arg=framework)
                assert page.locator('#fw-graph .worker').count() == workers
                assert page.locator('#fw-graph svg > path').count() >= workers*2
                assert page.locator('#fw-gantt .fw-bar').count() == workers
                dataset=page.request.get(urljoin(url,'../experiments/dsh-engine/results/natural-dag-20261029/frameworks/'+framework+'.json')).json()
                assert 'Codex' in page.locator('#fw-body .fw-provenance').inner_text()
                assert '无；这是自编诊断任务' in page.locator('#fw-body .fw-provenance').inner_text()
                row=next(r for r in catalogue['upstream_runs'] if r['display_id']==framework)
                assert row['run_id'] in page.locator('#fw-body .fw-provenance').inner_text()
                assert dataset['query']==row['initial_task']
                for label,target in dataset['links']:
                    if target.startswith('../'):
                        assert page.request.head(urljoin(url,target)).status==200,(label,target)
                page.locator('#fw-cursor').evaluate("el=>{el.value=0;el.dispatchEvent(new Event('input'))}")
                assert page.locator('#fw-graph [data-fw-node]').count()==1
                page.locator('#fw-cursor').evaluate("el=>{el.value=2;el.dispatchEvent(new Event('input'))}")
                page.locator('#fw-graph [data-fw-node]:not([data-fw-node="task"])').first.click()
                page.locator('.fw-drawer .fw-request>summary').first.click()
                assert '响应尚未完整返回' in page.locator('.fw-drawer').inner_text(), {'framework':framework,'cursor':page.locator('#fw-cursor').input_value(),'drawer':page.locator('.fw-drawer').inner_text()[-1600:]}
                assert '本次返回' not in page.locator('.fw-drawer').inner_text()
                page.keyboard.press('Escape')
                page.locator('#fw-cursor').evaluate("el=>{el.value=el.max;el.dispatchEvent(new Event('input'))}")
                rects=page.locator('#fw-graph .fw-node').evaluate_all('nodes=>nodes.map(n=>{const b=n.getBoundingClientRect();return {x:b.x,y:b.y,r:b.right,b:b.bottom}})')
                assert not any(a['x']<b['r'] and a['r']>b['x'] and a['y']<b['b'] and a['b']>b['y'] for i,a in enumerate(rects) for b in rects[i+1:])
                page.locator('#fw-graph .worker' if workers else '#fw-graph [data-fw-node="supervisor"]').first.click()
                assert page.locator('.fw-drawer .fw-request').count()>0
                page.locator('.fw-drawer .fw-request>summary').first.click()
                assert page.locator('.fw-drawer .fw-message').count()>0
                page.screenshot(path=str(out/f'{framework}-native-drawer.png'))
                page.keyboard.press('Escape')
                page.locator('#fw-body').screenshot(path=str(out/f'{framework}-native-desktop.png'))
                page.set_viewport_size({'width':390,'height':844})
                page.wait_for_timeout(120)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('#fw-graph').evaluate('el=>el.scrollWidth<=el.clientWidth+2')
                page.locator('#fw-body').screenshot(path=str(out/f'{framework}-native-mobile.png'))
                page.set_viewport_size({'width':1440,'height':1000})
                report['native_frameworks'].append({'id':framework,'workers':workers,'progressive_reveal':True,'drawer':True,'mobile':True})
            page.locator('#fw-audit').evaluate('n=>n.parentElement.open=true')
            assert page.locator('#fw-audit [data-dsh-group]').count()==6
            assert page.locator('#fw-audit [data-dsh-run]').count()==18
            for row in catalogue['dsh_runs']:
                item=page.locator(f'[data-dsh-run="{row["run_id"]}"]')
                assert item.locator('.fw-task').text_content()==row['initial_task']
            group=page.locator('[data-dsh-group="multi-object-review"]')
            group.locator(':scope>summary').click()
            assert '不是DSH四个真实组件' in group.inner_text()
            group.locator('.fw-run>summary').first.click()
            page.locator('#fw-audit').screenshot(path=str(out/'dsh-grouped-provenance-desktop.png'))
            page.locator('#fw-attempts').evaluate('n=>n.parentElement.open=true')
            assert page.locator('#fw-attempts [data-upstream-run]').count()==12
            for row in catalogue['upstream_runs']:
                item=page.locator(f'[data-upstream-run="{row["run_id"]}"]')
                assert item.locator('.fw-task').text_content()==row['initial_task']
            page.locator('#fw-archives').evaluate('n=>n.parentElement.open=true')
            assert page.locator('#fw-archives .fw-archive').count()==4
            for anchor in page.locator('#fw-archives a').all():
                assert page.request.head(urljoin(url,anchor.get_attribute('href'))).status==200
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_timeout(120)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert group.evaluate('n=>n.scrollWidth<=n.clientWidth+2')
            page.locator('#fw-coverage').screenshot(path=str(out/'experiment-coverage-mobile.png'))
            group.screenshot(path=str(out/'dsh-provenance-mobile.png'))
            report['provenance']={'coverage_rows':4,'dsh_groups':6,'dsh_runs':18,'upstream_attempts':12,'exact_tasks_verified':30,'mobile':True}
            page.set_viewport_size({'width':1440,'height':1000})
            # New public originals reuse the measured DSH graph view. The old
            # five cases remain a separate source set, with their own inputs.
            page.locator('[data-source="public"]').click()
            page.wait_for_function("document.querySelectorAll('#cases button').length===6")
            assert page.locator('#summary tr').count()==6
            assert page.locator('#observation').evaluate('(n)=>!!(n.compareDocumentPosition(document.getElementById("frameworks"))&Node.DOCUMENT_POSITION_FOLLOWING)')
            public=page.request.get(urljoin(url,'../experiments/dsh-engine/results/public-tasks-20261030-v001/index.json')).json()
            report['public_tasks']=[]
            for case in public['cases']:
                page.locator(f'[data-case="{case["case_id"]}"]').click()
                page.wait_for_function('(id)=>document.querySelector("#case-id").textContent.endsWith(id)',arg=case['case_id'])
                assert page.locator('#initial-task').text_content()==case['initial_task']
                assert '数据集' in page.locator('#provenance').inner_text()
                assert 'DSH' in page.locator('#provenance').inner_text()
                assert page.locator('#graph [data-node]').count()==case['model_calls']+case['tool_calls']
                if case['case_id']=='drb-19':
                    assert '检索研究资料' in page.locator('#graph .model').first.inner_text()
                    assert '读取 2 个网页' in page.locator('#graph .model').nth(1).inner_text()
                    assert '执行失败' in page.locator('#graph .tool').first.inner_text()
                if case['case_id']=='lcb-abc387_f':
                    assert '输出截断' in page.locator('#graph .model').first.inner_text()
                    assert '推理达到输出上限' in page.locator('#graph .model').first.inner_text()
                page.locator('#graph .model').first.click()
                page.locator('[data-tab="context"]').click()
                assert case['initial_task'].replace('\r\n','\n') in page.locator('#drawer-content').text_content().replace('\r\n','\n'),case['case_id']
                page.keyboard.press('Escape')
                for anchor in page.locator('#evidence-links a').all():
                    target=urljoin(url,anchor.get_attribute('href'))
                    assert page.request.head(target).status==200,target
                report['public_tasks'].append({'id':case['case_id'],'models':case['model_calls'],'tools':case['tool_calls'],'exact_original_prompt':True})
            page.locator('[data-case="drb-19"]').click()
            page.wait_for_function("document.querySelector('#case-id').textContent.endsWith('drb-19')")
            page.locator('#case-detail').screenshot(path=str(out/'public-task-source-desktop.png'))
            page.locator('#timeline-panel').screenshot(path=str(out/'public-task-timeline-desktop.png'))
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#case-detail').screenshot(path=str(out/'public-task-source-mobile.png'))
            page.set_viewport_size({'width':1440,'height':1000})
            # Check the original structure page's links and expandable roles.
            page.goto(urljoin(url,'topic1-four-workflows.html'),wait_until='networkidle')
            for name in ['research','coding','gptr','crag','dsh']:
                page.locator(f'[data-workflow="{name}"]').click()
                assert page.locator(f'[data-panel="{name}"]').is_visible()
                assert page.locator('#workflow-overview').inner_text()
                if name in ['research','gptr']:
                    assert page.locator('#workflow-overview a[href*="?framework="]').count()==1
            page.locator('[data-workflow="gptr"]').click()
            page.locator('[data-panel="gptr"] [data-node]').first.click()
            assert '原生运行' in page.locator('[data-drawer-pane="calls"]').inner_text()
            assert not report['page_errors'] and not report['missing_resources'], report
            browser.close()
    finally:
        if server:server.shutdown();server.server_close()
    (out/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
