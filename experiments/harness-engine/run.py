"""A real, source-grounded, DSH-like multi-session harness; not DSH's implementation."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import time

from engine import Engine, Journal
from scheduler import Controller


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve(documents, query, top_k):
    """Actual local BM25 document retrieval. No gold, synthetic text or dummy work."""
    started = time.monotonic()
    bags = [Counter(tokens(d['title'] + ' ' + d['text'])) for d in documents]
    lengths = [sum(b.values()) for b in bags]
    avg = sum(lengths) / max(1, len(lengths))
    query_terms = set(tokens(query))
    dfs = {q: sum(q in b for b in bags) for q in query_terms}
    scored = []
    for d, bag, length in zip(documents, bags, lengths):
        score = sum(math.log(1 + (len(bags) - dfs[q] + .5) / (dfs[q] + .5)) *
                    (bag[q] * 2.2) / (bag[q] + 1.2 * (.25 + .75 * length / max(avg, 1)))
                    for q in query_terms if bag[q])
        scored.append({**d, 'bm25': score})
    scored.sort(key=lambda d: (-d['bm25'], d['doc_id']))
    return scored[:top_k], time.monotonic() - started


class Harness:
    def __init__(self, args, engine, controller, journal):
        self.args, self.engine, self.controller, self.journal = args, engine, controller, journal
        self.activation = 0

    async def model(self, root, session, stage, messages, budget):
        await self.controller.admit(root, session, stage)
        self.activation += 1
        call_id = f'{root}-{session.rsplit("/", 1)[-1]}-{stage}'
        self.journal.write('sessions', event='activation_start', root_id=root, session_id=session,
                           activation_id=call_id, messages=messages)
        try:
            return await self.engine.generate(call_id=call_id, root_id=root, node_id=session,
                                              stage=stage, messages=messages, max_tokens=budget,
                                              seed=self.args.seed)
        finally:
            self.controller.release()
            self.journal.write('sessions', event='activation_end', root_id=root, session_id=session,
                               activation_id=call_id)

    async def branch(self, task, branch_index, task_index):
        root = task['task_id']
        session = f'{root}/child{branch_index}'
        docs = task['documents'][branch_index::self.args.branches]
        self.journal.write('events', event='session_spawn', root_id=root, node_id=session,
                           parent=root, shard=[d['doc_id'] for d in docs])
        titles = '\n'.join(f"{d['doc_id']}: {d['title']}" for d in docs)
        history = [
            {'role': 'system', 'content': 'You are a research child agent. Work only from the supplied sources. '
             'Other children investigate other document shards; the parent combines all findings.'},
            {'role': 'user', 'content': f"Question: {task['question']}\nYour shard titles:\n{titles}\n"
             'Write one short search query (at most 20 words) to retrieve evidence for this question. Query only.'}]
        query = await self.model(root, session, 'query', history, self.args.query_tokens)
        history.append({'role': 'assistant', 'content': query['text']})
        tool_id = session + '/search'
        self.controller.tools[tool_id] = {'started': time.monotonic(), 'kind': 'bm25', 'root_id': root}
        self.journal.write('events', event='tool_start', root_id=root, node_id=session,
                           tool_id=tool_id, tool_kind='bm25', query=query['text'])
        start = time.monotonic()
        result, cpu_seconds = await asyncio.to_thread(retrieve, docs, task['question'] + ' ' + query['text'],
                                                     self.args.top_k)
        delay = 0.0
        # Controlled tool-latency treatments: policy never receives these durations or return timestamps.
        if self.args.tool_profile != 'natural':
            delay = (self.args.tool_delay if task_index < self.args.cohort else .2) + branch_index * .15
            await asyncio.sleep(delay)
        self.controller.tools.pop(tool_id)
        self.journal.write('tools', root_id=root, node_id=session, tool_id=tool_id,
                           query=query['text'], results=result, actual_cpu_seconds=cpu_seconds,
                           injected_delay_seconds=delay, elapsed=time.monotonic() - start)
        self.journal.write('events', event='tool_complete', root_id=root, node_id=session,
                           tool_id=tool_id, actual_cpu_seconds=cpu_seconds, injected_delay_seconds=delay)
        history.append({'role': 'user', 'content': 'Search tool returned these documents:\n' +
                        json.dumps(result, ensure_ascii=False) + '\nExtract facts relevant to the question. '
                        'Name entities and include source IDs in square brackets. State missing information. '
                        'Do not invent facts. Keep findings under 130 words.'})
        evidence = await self.model(root, session, 'evidence', history, self.args.evidence_tokens)
        history.append({'role': 'assistant', 'content': evidence['text']})
        self.controller.remaining[root] -= 1
        self.journal.write('sessions', event='session_complete', root_id=root, session_id=session,
                           history=history, remaining_children=self.controller.remaining[root])
        return {'session_id': session, 'text': evidence['text']}

    async def root(self, task, index):
        await asyncio.sleep(index * self.args.arrival_interval if index < self.args.cohort
                            else self.args.second_wave + (index - self.args.cohort) * self.args.arrival_interval)
        root = task['task_id']
        start = time.monotonic()
        self.controller.remaining[root] = self.args.branches
        self.journal.write('events', event='root_submit', root_id=root, task_index=index,
                           question=task['question'],
                           mandatory_children=self.args.branches if self.args.workflow == 'sharded' else 0)
        try:
            if self.args.workflow == 'sharded':
                children = await asyncio.gather(*(self.branch(task, b, index) for b in range(self.args.branches)),
                                                return_exceptions=True)
                failures = [repr(c) for c in children if isinstance(c, BaseException)]
                if failures:
                    raise RuntimeError('Required child failure: ' + '; '.join(failures))
                self.journal.write('events', event='join_ready', root_id=root, children=self.args.branches)
                source = 'Child findings:\n' + json.dumps(children, ensure_ascii=False)
            else:
                children = []
                source = 'Source documents:\n' + json.dumps(task['documents'], ensure_ascii=False)
            messages = [
                {'role': 'system', 'content': 'You are the parent research agent. Combine all mandatory child '
                 'findings, resolve multi-hop relations, and answer the question using only their evidence. '
                 'Return a JSON object with answer (a short answer string) and citations (a list of source IDs). '
                 'No markdown, explanation or extra fields. If insufficient evidence, answer "unknown".'},
                {'role': 'user', 'content': f"Question: {task['question']}\n" + source}]
            if self.args.workflow == 'direct':
                messages[0]['content'] = messages[0]['content'].replace('Combine all mandatory child findings',
                                                                       'Read all supplied source documents')
                messages[0]['content'] = messages[0]['content'].replace('their evidence', 'the supplied evidence')
            answer = await self.model(root, root + '/parent', 'synthesis', messages, self.args.answer_tokens)
            parsed, parse_error = None, None
            try:
                parsed = json.loads(answer['text'])
                if not isinstance(parsed, dict) or not isinstance(parsed.get('answer'), str):
                    raise ValueError('Expected object with answer string')
            except (ValueError, TypeError) as exc:
                parse_error = repr(exc)
                parsed = None
            self.journal.write('roots', root_id=root, task_index=index, duration=time.monotonic() - start,
                               output=answer['text'], parsed=parsed, parse_error=parse_error,
                               children=children, error=None)
            self.journal.write('events', event='root_complete', root_id=root,
                               duration=time.monotonic() - start, valid_json=parse_error is None)
        except Exception as exc:
            self.journal.write('roots', root_id=root, task_index=index, duration=time.monotonic() - start,
                               output=None, parsed=None, error=repr(exc))
            self.journal.write('events', event='root_failed', root_id=root, error=repr(exc))


async def run(args):
    tasks = [json.loads(x) for x in args.tasks.read_text(encoding='utf-8').splitlines()]
    tasks = [t for t in tasks if t['split'] == args.split][args.offset:args.offset + args.count]
    if len(tasks) != args.count:
        raise ValueError(f'Expected {args.count} tasks; found {len(tasks)}')
    journal = Journal(args.out)
    engine = Engine(args.url, args.model, journal, args.thinking)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(task_ids=[t['task_id'] for t in tasks], started=time.time(),
                  tasks_sha256=hashlib.sha256(args.tasks.read_bytes()).hexdigest(),
                  expected_model_calls=len(tasks) * (args.branches * 2 + 1 if args.workflow == 'sharded' else 1),
                  application='controlled source-grounded multi-agent HotpotQA; not official harness',
                  source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in Path(__file__).parent.glob('*.py')})
    for name in ['server', 'model_manifest', 'model_verification', 'env']:
        path = Path('state') / (name + '.json')
        if path.exists():
            config[name] = json.loads(path.read_text())
    (args.out / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    stop = asyncio.Event()
    controller = Controller(args.policy, args.cap, engine, journal)
    try:
        journal.write('events', event='engine_health', models=await engine.health())
        metrics = await engine.sample()
        if args.policy == 'pressure' and any(metrics.get(k) is None for k in ['kv_usage', 'waiting']):
            raise RuntimeError('Required engine metrics absent; do not silently replace pressure policy')
        if not args.keep_cache:
            await engine.reset_cache()
        poll = asyncio.create_task(engine.poll(stop))
        schedule = asyncio.create_task(controller.loop())
        harness = Harness(args, engine, controller, journal)
        await asyncio.gather(*(harness.root(t, i) for i, t in enumerate(tasks)))
        controller.close()
        await schedule
        stop.set()
        await poll
        await engine.sample()
        journal.write('events', event='run_complete', model_activations=harness.activation,
                       expected_model_calls=config['expected_model_calls'])
    finally:
        stop.set()
        controller.close()
        await engine.close()
        journal.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tasks', type=Path, default=Path('datasets/hotpot/tasks.jsonl'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--url', default='http://127.0.0.1:18081')
    ap.add_argument('--model', default='qwen27b')
    ap.add_argument('--split', default='calibration', choices=['calibration', 'evaluation'])
    ap.add_argument('--workflow', choices=['sharded', 'direct'], default='sharded')
    ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--count', type=int, default=8)
    ap.add_argument('--branches', type=int, default=3)
    ap.add_argument('--top-k', type=int, default=3)
    ap.add_argument('--policy', choices=['native', 'fixed', 'pressure', 'progress'], default='native')
    ap.add_argument('--cap', type=int, default=12)
    ap.add_argument('--seed', type=int, default=1729)
    ap.add_argument('--query-tokens', type=int, default=40)
    ap.add_argument('--evidence-tokens', type=int, default=192)
    ap.add_argument('--answer-tokens', type=int, default=128)
    ap.add_argument('--thinking', action='store_true')
    ap.add_argument('--keep-cache', action='store_true')
    ap.add_argument('--arrival-interval', type=float, default=0)
    ap.add_argument('--second-wave', type=float, default=0)
    ap.add_argument('--cohort', type=int, default=4)
    ap.add_argument('--tool-profile', choices=['natural', 'controlled'], default='natural')
    ap.add_argument('--tool-delay', type=float, default=4)
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == '__main__':
    main()
