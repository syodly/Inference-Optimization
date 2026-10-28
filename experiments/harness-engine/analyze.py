"""Offline scoring. The runtime and request controller never import or read gold."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import statistics
import string


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def normalize(answer):
    text = ''.join(c for c in answer.lower() if c not in string.punctuation)
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text).split())


def quality(pred, gold):
    a, b = normalize(pred), normalize(gold)
    if (a in ['yes', 'no', 'noanswer'] or b in ['yes', 'no', 'noanswer']) and a != b:
        return 0., 0.
    common = sum((Counter(a.split()) & Counter(b.split())).values())
    f1 = 2 * common / (len(a.split()) + len(b.split())) if common else float(a == b)
    return float(a == b), f1


def distribution(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return {'n': 0}
    def q(p):
        pos = (len(values) - 1) * p
        lo = int(pos)
        return values[lo] + (values[min(lo + 1, len(values) - 1)] - values[lo]) * (pos - lo)
    return {'n': len(values), 'mean': statistics.mean(values), 'p50': q(.5), 'p95': q(.95),
            'min': values[0], 'max': values[-1]}


def analyze(run, gold_path, tasks_path):
    config = json.loads((run / 'config.json').read_text())
    answers = {r['task_id']: r for r in read(gold_path)}
    tasks = {r['task_id']: r for r in read(tasks_path)}
    roots, responses, events, metrics = [read(run / f'{n}.jsonl') for n in ['roots', 'responses', 'events', 'metrics']]
    scored = []
    for row in roots:
        gold = answers[row['root_id']]
        parsed = row.get('parsed') or {}
        pred = parsed.get('answer', '')
        em, f1 = quality(pred, gold['answer'])
        if row.get('error') or row.get('parse_error'):
            em = f1 = 0.
        source_titles = {d['doc_id']: d['title'] for d in tasks[row['root_id']]['documents']}
        citations = parsed.get('citations', [])
        if not isinstance(citations, list):
            citations = []
        predicted_titles = {source_titles[c] for c in citations if isinstance(c, str) and c in source_titles}
        support = set(gold['supporting_facts']['title'])
        recall = len(predicted_titles & support) / len(support) if support else 0.
        scored.append({**row, 'gold_answer': gold['answer'], 'predicted_answer': pred, 'em': em,
                       'f1': f1, 'support_title_recall': recall,
                       'valid_citations': len(predicted_titles), 'support_titles': sorted(support)})
    response_groups = defaultdict(list)
    for r in responses:
        response_groups[r['stage']].append(r)
    totals = {key: sum(r.get('usage', {}).get(key, 0) or 0 for r in responses)
              for key in ['prompt_tokens', 'completion_tokens', 'total_tokens']}
    releases = [e for e in events if e['event'] == 'frontend_release']
    submits = [e for e in events if e['event'] == 'root_submit']
    ends = [e for e in events if e['event'] in ['root_complete', 'root_failed']]
    valid_metrics = lambda key: [m[key] for m in metrics if m.get(key) is not None]
    counter_delta = lambda key: (valid_metrics(key)[-1] - valid_metrics(key)[0]) if valid_metrics(key) else None
    summary = {
        'run_id': run.name, 'policy': config['policy'], 'cap': config['cap'],
        'expected_roots': len(config['task_ids']), 'completed_root_records': len(scored),
        'engine_errors': sum(bool(r.get('error')) for r in responses),
        'root_errors': sum(bool(r.get('error')) for r in roots),
        'parse_errors': sum(bool(r.get('parse_error')) for r in roots),
        'model_calls': len(responses), 'expected_model_calls': config['expected_model_calls'],
        'length_finishes': sum(r.get('finish_reason') == 'length' for r in responses),
        'quality': {k: sum(r[k] for r in scored) / len(config['task_ids'])
                    for k in ['em', 'f1', 'support_title_recall']},
        'root_latency_seconds': distribution([r['duration'] for r in roots]),
        'valid_json_root_latency_seconds': distribution([r['duration'] for r in roots
                                                        if not r.get('error') and not r.get('parse_error')]),
        'exact_correct_root_latency_seconds': distribution([r['duration'] for r in scored if r['em'] == 1]),
        'batch_makespan_seconds': max(e['t'] for e in ends) - min(e['t'] for e in submits) if ends else None,
        'frontend_wait_seconds': distribution([e['frontend_wait'] for e in releases]),
        'model_ttft_seconds': distribution([r.get('ttft') for r in responses]),
        'stage': {s: {'calls': len(rows), 'latency': distribution([r['duration'] for r in rows]),
                      'ttft': distribution([r.get('ttft') for r in rows])} for s, rows in response_groups.items()},
        'tokens': totals,
        'engine': {k: distribution(valid_metrics(k)) for k in ['running', 'waiting', 'kv_usage']},
        'preemptions_delta': counter_delta('preemptions'),
        'prefix_queries_delta': counter_delta('prefix_queries'), 'prefix_hits_delta': counter_delta('prefix_hits'),
        'max_frontend_inflight_calls': max([e['inflight_calls'] for e in releases], default=0),
        'max_frontend_pending': max([e['pending'] for e in events if 'pending' in e], default=0),
        'max_tools_inflight': max([e['tools_inflight'] for e in events if 'tools_inflight' in e], default=0),
        'limitation': 'Fixed mandatory DAG, actual greedy outputs may differ under floating point batching; compare traces/tokens.'}
    fingerprints = {r['call_id']: {'stage': r['stage'],
                    'messages_sha256': hashlib.sha256(json.dumps(r['payload']['messages'], sort_keys=True).encode()).hexdigest()}
                    for r in read(run / 'requests.jsonl')}
    for r in responses:
        fingerprints[r['call_id']].update(output_sha256=hashlib.sha256(r.get('text', '').encode()).hexdigest(),
                                          usage=r.get('usage', {}))
    (run / 'workload_fingerprints.json').write_text(json.dumps(fingerprints, indent=2))
    (run / 'scored.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in scored), encoding='utf-8')
    (run / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('run', type=Path)
    ap.add_argument('--gold', type=Path, default=Path('datasets/hotpot/answers.jsonl'))
    ap.add_argument('--tasks', type=Path, default=Path('datasets/hotpot/tasks.jsonl'))
    args = ap.parse_args()
    print(json.dumps(analyze(args.run, args.gold, args.tasks), ensure_ascii=False, indent=2))
