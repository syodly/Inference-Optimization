"""Run ordinary initial tasks in official DSH and observe the online graph.

Run on songprojgpu1. No replay, scripted graph, research tool or admission gate.
"""
import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
import urllib.request


ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
OLD = Path('/home/Liangyijia_Hu/harness-engine')
WORKSPACES = Path('/home/Liangyijia_Hu/dsh-natural-workspaces')
NODE = ROOT/'toolchain/node-v24.22.2-linux-x64/bin/node'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def snapshot(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def prepare(batch, max_tokens=4096):
    work = WORKSPACES/batch
    work.mkdir(parents=True, exist_ok=False)
    record = ROOT/'runs'/batch
    record.mkdir(parents=True, exist_ok=False)
    cases = []

    def case(name, title, prompt, provenance):
        directory = work/name
        directory.mkdir()
        cases.append({'case_id': name, 'title': title, 'initial_task': prompt,
                      'workspace': str(directory), 'provenance': provenance})
        return directory

    case('simple', 'Single calculation',
         'An invoice is 240 dollars before a 17.5% discount. What is the final price? Give a brief calculation.',
         'Curated one-step control; expected price 198 dollars.')
    research = case('research', 'Source-grounded multi-document research',
                    'Prepare a source-grounded fact-check report answering the questions in questions.md. '
                    'Use the supplied source collection, cite the supporting filenames and explain any missing or conflicting evidence. '
                    'Write the report to report.md and summarize your findings.',
                    'Six original HotpotQA calibration questions and their distractor document collections; no answer labels supplied.')
    source = OLD/'datasets/hotpot/tasks.jsonl'
    rows = {task['task_id']: task for task in map(json.loads, source.read_text().splitlines())}
    ids = ['5a78f59755429970f5fffdf7', '5ae75a5a5542991bbc9761f3', '5a87868c5542996e4f308828',
           '5ab29624554299545a2cf9b5', '5ab97c0255429970cfb8eb1f', '5ae1316555429901ffe4adda']
    questions = []
    for index, identifier in enumerate(ids, 1):
        task = rows[identifier]
        questions.append(f'{index}. {task["question"]} (source collection: sources/q{index}/)')
        for doc in task['documents']:
            p = research/'sources'/f'q{index}'/(doc['doc_id']+'.md')
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f'# {doc["title"]}\n\n{doc["text"]}\n', encoding='utf-8')
    (research/'questions.md').write_text('\n\n'.join(questions)+'\n')
    dump(record/'research-data.json', {'dataset': 'HotpotQA', 'task_ids': ids,
                                      'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                                      'labels_visible_at_runtime': False})

    coding = case('coding', 'Repair a small service from regression failures',
                  'Fix the checkout service so that its documented contracts and regression tests pass. '
                  'Preserve the public APIs and existing tests. Run the tests, make the necessary implementation changes, '
                  'and summarize the cause of each bug and your verification.',
                  'Curated Python checkout repository, seven public unittest cases; not an upstream benchmark.')
    shutil.copytree(ROOT/'fixtures/order-service', coding, dirs_exist_ok=True)

    analysis = case('analysis', 'Reconcile CSV data and explain a business change',
                    'Investigate why February net revenue differs from January. Reconcile the supplied orders, refunds '
                    'and product data using the definitions in data_dictionary.md. Produce a reproducible analysis '
                    'and report.md with the monthly totals, the main drivers, and any data quality issues. '
                    'Do not silently count duplicate events or include orders that are not paid.',
                    'Deterministic curated commerce CSV workload with duplicate events, refunds and a product mix change; not production data.')
    products = [('p1', 'Starter', 20), ('p2', 'Pro', 60), ('p3', 'Team', 100), ('p4', 'Enterprise', 200)]
    with (analysis/'products.csv').open('w', newline='') as f:
        w = csv.writer(f);w.writerow(['product_id', 'category', 'unit_price']);w.writerows(products)
    orders = []
    for month in [1, 2]:
        for i in range(48):
            sku = i % 4 if month == 1 else (0 if i % 3 else 2)
            orders.append([f'o{month}{i:03}', f'2026-{month:02}-{i%26+1:02}', products[sku][0],
                           1+i%3, 'cancelled' if i%13 == 0 else 'paid'])
    with (analysis/'orders.csv').open('w', newline='') as f:
        w = csv.writer(f);w.writerow(['order_id', 'paid_date', 'product_id', 'quantity', 'status'])
        w.writerows(orders+[orders[5], orders[49], orders[60]])
    refunds = [[f'r{i}', orders[index][0], amount] for i, (index, amount) in
               enumerate([(5, 20), (11, 100), (24, 20), (50, 20), (55, 60), (62, 20), (71, 100)], 1)]
    with (analysis/'refunds.csv').open('w', newline='') as f:
        w = csv.writer(f);w.writerow(['refund_id', 'order_id', 'amount']);w.writerows(refunds+[refunds[-1]])
    (analysis/'data_dictionary.md').write_text(
        '# Revenue definitions\n\nAmounts are USD. These are curated test data.\n'
        'Orders may contain exact repeated order_id delivery events; count each order_id once. '
        'Only status=paid contributes quantity times products.unit_price. '
        'Refunds are dollar amounts; deduplicate by refund_id and attribute each refund to its original paid order month. '
        'Net revenue equals paid gross revenue minus unique refunds. Product mix uses paid orders only.\n')

    incident = case('incident', 'Diagnose a service incident from correlated evidence',
                    'Diagnose the checkout outage described in ticket.md. Correlate the available logs, metrics and '
                    'configuration history. Write incident-report.md with a timestamped causal timeline, the most '
                    'likely root cause, plausible alternatives, and a concrete mitigation and verification plan. '
                    'Cite the supplied evidence and distinguish facts from hypotheses.',
                    'Curated service incident with controlled timestamps and a connection-pool configuration regression; not a production trace.')
    (incident/'ticket.md').write_text(
        '# Incident\n\nCheckout latency and failures rose shortly after 09:04 UTC on 2026-10-28. '
        'An edge release and a checkout deployment occurred that morning. Determine what happened. '
        'All supplied logs are UTC and generated for this diagnostic exercise.\n')
    config = incident/'config';config.mkdir()
    (config/'checkout-before.json').write_text(json.dumps({'replicas': 6, 'database_pool_max_per_replica': 12,
                                                         'database_max_connections': 100, 'other_clients': 18}, indent=2))
    (config/'checkout-after.json').write_text(json.dumps({'replicas': 6, 'database_pool_max_per_replica': 24,
                                                        'database_max_connections': 100, 'other_clients': 18}, indent=2))
    (incident/'deployments.log').write_text(
        '2026-10-28T08:58:00Z edge v4.11 deployed; routing rules unchanged; adds request-id response header\n'
        '2026-10-28T09:03:00Z checkout v2.18 rollout begins; database_pool_max_per_replica 12 -> 24\n'
        '2026-10-28T09:04:00Z checkout v2.18 rollout complete, replicas=6\n'
        '2026-10-28T09:10:00Z edge v4.11 rolled back; checkout timeouts persist\n')
    logs = incident/'logs';logs.mkdir()
    start = datetime(2026, 10, 28, 8, 58, tzinfo=timezone.utc)
    streams = {name: [] for name in ['edge', 'checkout', 'database', 'payments']}
    metric_rows = []
    for minute in range(18):
        at = (start+timedelta(minutes=minute)).isoformat().replace('+00:00', 'Z')
        bad = minute >= 6
        metric_rows.append([at, 100, 8 if bad else 0.3, 4200 if bad else 180,
                            100 if bad else 75, 24 if bad else 0, 31 if bad else 30, 28])
        streams['edge'].append(f'{at} checkout upstream_status={504 if bad else 200} latency_ms={4200 if bad else 180} request_id=req{minute}')
        streams['checkout'].append(f'{at} request_id=req{minute} '+('database connection acquisition timeout; queue_wait_ms=4000; payment not called' if bad else 'completed db_wait_ms=3 payment_ms=28'))
        streams['database'].append(f'{at} '+('FATAL remaining connection slots are reserved; active=100; query_p95_ms=9; lock_waiters=0' if bad else 'active=75; query_p95_ms=9; lock_waiters=0'))
        streams['payments'].append(f'{at} status=healthy p95_ms=28 errors=0')
    for name, lines in streams.items():
        (logs/(name+'.log')).write_text('\n'.join(lines)+'\n')
    with (incident/'metrics.csv').open('w', newline='') as f:
        w = csv.writer(f);w.writerow(['time', 'requests_per_second', 'error_percent', 'checkout_p95_ms',
                                     'db_active_connections', 'db_connection_waiters', 'db_cpu_percent', 'payment_p95_ms'])
        w.writerows(metric_rows)

    for spec in cases:
        directory = Path(spec['workspace'])
        for ancestor in [directory, *directory.parents]:
            assert not (ancestor/'AGENTS.md').exists(), f'Unexpected policy in task workspace: {ancestor}'
        before = record/spec['case_id']/'input'
        before.parent.mkdir(parents=True)
        shutil.copytree(directory, before)
        spec['input_sha256'] = snapshot(directory)
    dump(record/'plan.json', {'batch_id': batch, 'cases': cases,
                              'model': 'Qwen/Qwen3.8-27B', 'reasoning': 'low', 'temperature': 0,
                              'max_output_tokens': max_tokens, 'graph_or_agent_count_specified': False,
                              'native_subagent_defaults': {'maxDepth': 1, 'maxActiveSubagents': 8},
                              'wall_watchdog_seconds_per_case': 1200,
                              'observer_changes': f'Only sampling envelope temp=0/maxTokens={max_tokens}; passive lifecycle/tool/session observation. No tool restrictions or gate.'})
    return record, cases


def sample_metrics(directory, stop):
    with (directory/'metrics.jsonl').open('a') as f:
        while not stop.is_set():
            try:
                with urllib.request.urlopen('http://127.0.0.1:18082/metrics', timeout=10) as response:
                    raw = response.read().decode()
                f.write(json.dumps({'wall_time': time.time(), 'prometheus': raw})+'\n');f.flush()
            except Exception as error:
                f.write(json.dumps({'wall_time': time.time(), 'error': repr(error)})+'\n');f.flush()
            stop.wait(.5)


def run_case(record, spec):
    directory = record/spec['case_id']
    directory.mkdir(exist_ok=True)
    (directory/'initial-task.txt').write_text(spec['initial_task']+'\n')
    env = {**os.environ, 'DSH_HOME': str(directory/'home'), 'DSH_QWEN_API_KEY': 'local-qwen-no-auth',
           'DSH_DAG_EVENT_FILE': str(directory/'observer.jsonl'),
           'DSH_DAG_MAX_TOKENS': str(json.loads((record/'plan.json').read_text())['max_output_tokens']),
           'PATH': str(NODE.parent)+':/home/Liangyijia_Hu/harness-engine/.venv-engine/bin:'+os.environ['PATH']}
    command = [str(NODE), str(ROOT/'runtime/node_modules/@deepseek-ai/dsh/lib/bin.js'),
               '--profile', 'headless', '--patch', str(ROOT/'qwen.patch.yml'),
               '--patch', str(ROOT/'natural.patch.yml'), '--json', spec['initial_task']]
    started = time.time()
    stop = threading.Event()
    metrics = threading.Thread(target=sample_metrics, args=(directory, stop), daemon=True)
    metrics.start()
    with (directory/'cli.jsonl').open('wb') as stdout, (directory/'stderr.log').open('wb') as stderr:
        process = subprocess.Popen(command, cwd=spec['workspace'], env=env, stdout=stdout,
                                   stderr=stderr, stdin=subprocess.DEVNULL, start_new_session=True)
        dump(directory/'launch.json', {'pid': process.pid, 'started_wall_time': started, 'command': command})
        watchdog = False
        try:
            code = process.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            watchdog = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL);code = process.wait()
    stop.set();metrics.join(timeout=15)
    completion = {'case_id': spec['case_id'], 'exit_code': code, 'watchdog_triggered': watchdog,
                  'started_wall_time': started, 'finished_wall_time': time.time(),
                  'duration_seconds': time.time()-started}
    dump(directory/'completion.json', completion)
    shutil.copytree(spec['workspace'], directory/'output', ignore=shutil.ignore_patterns('__pycache__'))
    dump(directory/'output-sha256.json', snapshot(Path(spec['workspace'])))
    print(json.dumps(completion), flush=True)
    return completion


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-id', required=True)
    parser.add_argument('--case', help='Run one case; omitted runs all prepared cases.')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--max-output-tokens', type=int, default=4096)
    args = parser.parse_args()
    record = ROOT/'runs'/args.batch_id
    if (record/'plan.json').exists():
        cases = json.loads((record/'plan.json').read_text())['cases']
    else:
        record, cases = prepare(args.batch_id, args.max_output_tokens)
    if args.prepare_only:
        print('PREPARED', record);return
    state_path = ROOT/'state'/f'{args.batch_id}.json'
    state = {'batch_id': args.batch_id, 'status': 'running',
             'completed': [spec['case_id'] for spec in cases if (record/spec['case_id']/'completion.json').exists()]}
    for name in ['natural_run.py', 'natural-observer.mjs', 'natural.patch.yml', 'qwen.patch.yml']:
        (record/'sources').mkdir(exist_ok=True);shutil.copy2(ROOT/name, record/'sources'/name)
    dump(record/'engine.json', json.loads((ROOT/'state/engine.json').read_text()))
    dump(record/'source.json', json.loads((ROOT/'state/source.json').read_text()))
    for spec in cases:
        if args.case and spec['case_id'] != args.case:
            continue
        if (record/spec['case_id']/'completion.json').exists():
            continue
        state['current'] = spec['case_id'];dump(state_path, state)
        state['last_result'] = run_case(record, spec)
        state['completed'].append(spec['case_id']);dump(state_path, state)
    state.update(status='completed', current=None);dump(state_path, state)
    print('NATURAL_OBSERVATION_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
