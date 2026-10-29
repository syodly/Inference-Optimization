"""Small completed HotpotQA group, executed by official DSH CLI hosts.

Python supplies real BM25, a baseline dispatch gate and metrics recording.
All Agent creation, model/tool loops, workflow fan-out/join and cleanup use DSH.
"""
import argparse
import asyncio
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import uuid

ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
OLD = Path('/home/Liangyijia_Hu/harness-engine')
# Reuse the unchanged, actual BM25 helper; never instantiate the old Harness.
sys.path.insert(0, str(OLD))
from run import retrieve


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


class Journal:
    def __init__(self, directory):
        self.directory = directory
        self.lock = threading.Lock()

    def write(self, stream, **values):
        with self.lock, (self.directory/f'{stream}.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps({'wall_time': time.time(), **values}, ensure_ascii=False)+'\n')


class Broker:
    def __init__(self, tasks, policy, cap, journal):
        self.tasks = {task['task_id']: task for task in tasks}
        self.policy, self.cap, self.journal = policy, cap, journal
        self.condition = threading.Condition()
        self.queue, self.running, self.cancelled = [], {}, set()
        self.latest = {}
        self.stop = threading.Event()
        self.metric_thread = None
        self.server = None
        self.branch_owners = {}

    def target(self):
        if self.policy == 'native':
            return 128
        if self.policy == 'pressure':
            if self.latest.get('kv_usage', 0) > .9:
                return max(2, self.cap//2)
            if self.latest.get('waiting', 0) > 2:
                return max(2, self.cap-int(self.latest['waiting']))
        return self.cap

    def pump(self):
        while self.queue and len(self.running) < self.target():
            item = self.queue.pop(0)
            if item['call_id'] in self.cancelled:
                continue
            item['admitted'] = time.time()
            self.running[item['call_id']] = item
            self.journal.write('dispatch', event='admit', **item,
                               frontend_wait=item['admitted']-item['ready'], target=self.target(),
                               inflight=len(self.running), pending=len(self.queue),
                               engine=self.latest, policy=self.policy)
        self.condition.notify_all()

    def dispatch(self, path, data):
        if path == '/search':
            task = self.tasks[data['task_id']]
            branch = data['branch']
            if branch not in [0, 1, 2]:
                raise ValueError('branch must be 0, 1 or 2')
            documents = task['documents'][branch::3]
            selected, duration = retrieve(documents, data['query'], 3)
            key = (task['task_id'], data['agent_id'])
            previous = self.branch_owners.setdefault(key, branch)
            if previous != branch:
                raise ValueError('one research Agent cannot change its shard')
            result = {'branch': branch, 'query': data['query'], 'documents': selected,
                      'scope': 'Top three full original documents in this shard, no hidden labels.'}
            self.journal.write('tools', event='bm25', **data, duration_seconds=duration,
                               result=result)
            return result
        with self.condition:
            identifier = data['call_id']
            if path == '/admit':
                item = {**data, 'ready': time.time()}
                self.queue.append(item)
                self.journal.write('dispatch', event='ready', **item)
                while 'admitted' not in item and identifier not in self.cancelled:
                    self.pump()
                    if 'admitted' not in item:
                        self.condition.wait(.1)
                if identifier in self.cancelled:
                    raise RuntimeError('DSH request cancelled')
                return {'frontend_wait': item['admitted']-item['ready'], 'target': self.target()}
            if path in ['/release', '/cancel']:
                item = self.running.pop(identifier, None)
                if path == '/cancel':
                    self.cancelled.add(identifier)
                    self.queue = [item for item in self.queue if item['call_id'] != identifier]
                self.journal.write('dispatch', event=path[1:], **data, held_permit=item is not None)
                self.pump()
                return {'ok': True}
        raise ValueError('unknown broker path: '+path)

    def sample(self):
        with urllib.request.urlopen('http://127.0.0.1:18082/metrics', timeout=10) as response:
            raw = response.read().decode()
        names = {'vllm:num_requests_running': 'running', 'vllm:num_requests_waiting': 'waiting',
                 'vllm:kv_cache_usage_perc': 'kv_usage', 'vllm:num_preemptions_total': 'preemptions',
                 'vllm:prefix_cache_queries_total': 'prefix_queries',
                 'vllm:prefix_cache_hits_total': 'prefix_hits'}
        metrics = {}
        for line in raw.splitlines():
            match = re.match(r'([^\s{]+)(?:\{[^}]*\})?\s+([-+\d.eE]+)$', line)
            if match and match[1] in names:
                key = names[match[1]]
                metrics[key] = metrics.get(key, 0)+float(match[2])
        if not all(key in metrics for key in ['running', 'waiting', 'kv_usage']):
            raise RuntimeError('Required real engine metrics missing')
        metrics['observed_wall_time'] = time.time()
        with self.condition:
            self.latest = metrics
            self.pump()
        self.journal.write('metrics', **metrics)
        return raw

    def start(self):
        raw = self.sample()
        (self.journal.directory/'metrics-start.prom').write_text(raw)
        broker = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                try:
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    value = broker.dispatch(self.path, body)
                    output, status = json.dumps(value, ensure_ascii=False).encode(), 200
                except Exception as error:
                    output, status = json.dumps({'error': repr(error)}).encode(), 500
                    broker.journal.write('errors', where='broker', error=repr(error))
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(output)))
                self.end_headers()
                try:
                    self.wfile.write(output)
                except BrokenPipeError:
                    pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

        def poll():
            while not self.stop.wait(.25):
                try:
                    self.sample()
                except Exception as error:
                    self.journal.write('errors', where='metrics', error=repr(error))

        self.metric_thread = threading.Thread(target=poll, daemon=True)
        self.metric_thread.start()
        return f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.stop.set()
        self.metric_thread.join(timeout=15)
        raw = self.sample()
        (self.journal.directory/'metrics-end.prom').write_text(raw)
        self.server.shutdown()
        self.server.server_close()


async def execute(args):
    reference = json.loads((OLD/'runs/v004-cal-native-a/config.json').read_text())
    source = OLD/'datasets/hotpot/tasks.jsonl'
    all_tasks = {task['task_id']: task for task in map(json.loads, source.read_text().splitlines())}
    tasks = [all_tasks[identifier] for identifier in reference['task_ids'][:args.count]]
    assert len(tasks) == args.count
    directory = ROOT/'runs'/args.run_id
    directory.mkdir(parents=True, exist_ok=False)
    journal = Journal(directory)
    for name in ['e1_run.py', 'e1-plugin.mjs', 'e1.patch.yml', 'qwen.patch.yml', 'start_engine.py']:
        (directory/'sources').mkdir(exist_ok=True)
        shutil.copy2(ROOT/name, directory/'sources'/name)
    config = {'run_id': args.run_id, 'policy': args.policy, 'cap': args.cap,
              'count': len(tasks), 'task_ids': [task['task_id'] for task in tasks],
              'reference_group': 'v004-calibration; smallest completed 8-task dispatch group',
              'selected_reference_conditions': ['v004-cal-native-a', 'v004-cal-fixed12', 'v004-cal-pressure12'],
              'source_tasks_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'legacy_bm25_module_sha256': hashlib.sha256((OLD/'run.py').read_bytes()).hexdigest(),
              'application': 'DSH native Agent loop and Workflow engine, fixed three-shard BM25 application',
              'expected_agents': 4*len(tasks), 'expected_agent_model_calls': 8*len(tasks),
              'expected_bm25_calls': 3*len(tasks), 'reasoning_effort': 'low', 'max_tokens': 2048,
              'temperature': 0, 'arrival': 'all eight roots submitted together, including process startup',
              'old_framework_used_for_agents': False, 'official_framework_source_modified': False,
              'auxiliary_title_generation_disabled': True,
              'engine': json.loads((ROOT/'state/engine.json').read_text()),
              'dsh_source': json.loads((ROOT/'state/source.json').read_text()),
              'comparison_limit': 'DSH has one mandatory parent workflow tool call in addition to the old seven-call graph; no cross-framework latency attribution.'}
    dump(directory/'config.json', config)
    with urllib.request.urlopen('http://127.0.0.1:18082/health', timeout=10) as response:
        assert response.status == 200
    broker = Broker(tasks, args.policy, args.cap, journal)
    broker.sample()
    assert broker.latest['running'] == broker.latest['waiting'] == 0
    request = urllib.request.Request('http://127.0.0.1:18082/reset_prefix_cache', data=b'', method='POST')
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read())
        assert result['success'] is True
        journal.write('events', event='prefix_cache_reset', result=result)
    endpoint = broker.start()
    started = time.time()
    journal.write('events', event='round_started', policy=args.policy, task_count=len(tasks))
    node = ROOT/'toolchain/node-v24.22.2-linux-x64/bin/node'
    cli = ROOT/'runtime/node_modules/@deepseek-ai/dsh/lib/bin.js'

    async def task_run(task):
        work = directory/'tasks'/task['task_id']
        work.mkdir(parents=True)
        dump(work/'task.json', task)
        prompt = ('Research question: '+task['question']+'\n'
                  'Call research_workflow exactly once. It runs all three mandatory research agents. '
                  'After receiving all three reports, answer using only their evidence. Do not search yourself. '
                  'Your final response must be one JSON object: '
                  '{"answer":"short direct answer","supporting_doc_ids":["d0","d1"],"reason":"brief evidence-based explanation"}. '
                  'Do not add markdown fences. If evidence is missing, say so honestly.')
        (work/'prompt.txt').write_text(prompt+'\n')
        import os
        env = {**os.environ, 'DSH_HOME': str(work/'home'), 'DSH_QWEN_API_KEY': 'local-qwen-no-auth',
               'DSH_BENCH_TASK_FILE': str(work/'task.json'), 'DSH_BENCH_BROKER': endpoint,
               'DSH_BENCH_EVENT_FILE': str(work/'native-plugin.jsonl')}
        command = [str(node), str(cli), '--profile', 'headless', '--patch', str(ROOT/'qwen.patch.yml'),
                   '--patch', str(ROOT/'e1.patch.yml'), '--json', prompt]
        submitted = time.time()
        journal.write('roots', event='task_submitted', task_id=task['task_id'])
        with (work/'cli.jsonl').open('wb') as output, (work/'stderr.log').open('wb') as error:
            process = await asyncio.create_subprocess_exec(*command, cwd=work, env=env, stdout=output, stderr=error)
            journal.write('events', event='host_process_started', task_id=task['task_id'], pid=process.pid)
            code = await process.wait()
        journal.write('roots', event='task_finished', task_id=task['task_id'], exit_code=code,
                      duration_seconds=time.time()-submitted)
        print(json.dumps({'task': task['task_id'], 'exit_code': code,
                          'seconds': round(time.time()-submitted, 2)}), flush=True)

    try:
        await asyncio.gather(*(task_run(task) for task in tasks))
    finally:
        broker.close()
    journal.write('events', event='round_finished', duration_seconds=time.time()-started,
                  outstanding_permits=list(broker.running), pending_permits=len(broker.queue))
    dump(directory/'completion.json', {'finished_wall_time': time.time(), 'started_wall_time': started,
                                      'duration_seconds': time.time()-started,
                                      'remaining_permits': len(broker.running), 'queued_permits': len(broker.queue)})
    print('ROUND_COMPLETE', args.run_id, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--policy', choices=['native', 'fixed', 'pressure'], default='native')
    parser.add_argument('--cap', type=int, default=12)
    parser.add_argument('--count', type=int, default=8)
    asyncio.run(execute(parser.parse_args()))
