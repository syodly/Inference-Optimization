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


def quality(pred, gold, answer_format=None):
    if answer_format == 'multiple_choice':
        score = float(pred.strip().upper() in 'ABCD' and len(pred.strip()) == 1 and pred.strip().upper() == gold.strip().upper())
        return score, score
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
    tools = read(run / 'tools.jsonl')
    scored = []
    for row in roots:
        gold = answers[row['root_id']]
        parsed = row.get('parsed') or {}
        pred = parsed.get('answer', '')
        em, f1 = quality(pred, gold['answer'], gold.get('format'))
        if row.get('error') or row.get('parse_error'):
            em = f1 = 0.
        source_titles = {d['doc_id']: d['title'] for d in tasks[row['root_id']]['documents']}
        citations = parsed.get('citations', [])
        if not isinstance(citations, list):
            citations = []
        predicted_titles = {source_titles[c] for c in citations if isinstance(c, str) and c in source_titles}
        support = set(gold['supporting_facts']['title'])
        recall = len(predicted_titles & support) / len(support) if support else None
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
        'empty_content_completions': sum(not r.get('text', '').strip() and not r.get('error') for r in responses),
        'quality': {k: sum(r[k] for r in scored) / len(config['task_ids']) for k in ['em', 'f1']},
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
        'control_observations': {
            'admissions_by_target': dict(Counter(str(e['target']) for e in releases)),
            'admissions_with_nonzero_wait': sum(e['frontend_wait'] > .01 for e in releases),
            'max_active_child_sessions': max([e.get('active_sessions', 0) for e in events], default=0),
            'session_wait_seconds': distribution([e['session_wait'] for e in events if e['event'] == 'session_admitted']),
        },
        'limitation': 'Fixed mandatory DAG, actual greedy outputs may differ under floating point batching; compare traces/tokens.'}
    support_scores = [r['support_title_recall'] for r in scored if r['support_title_recall'] is not None]
    summary['quality']['support_title_recall'] = statistics.mean(support_scores) if support_scores else None
    # A missing per-request counter is unknown, rather than a measured zero.
    cached_tokens = lambda row: (row.get('usage', {}).get('prompt_tokens_details') or {}).get('cached_tokens')
    summary['cache_by_stage'] = {}
    for stage, rows in response_groups.items():
        measured = [r for r in rows if cached_tokens(r) is not None]
        prompt = sum(r['usage'].get('prompt_tokens', 0) for r in measured)
        hits = sum(cached_tokens(r) for r in measured)
        summary['cache_by_stage'][stage] = {
            'calls': len(rows), 'calls_with_cache_accounting': len(measured),
            'cached_prompt_tokens': hits if measured else None,
            'accounted_prompt_tokens': prompt if measured else None,
            'cached_fraction': hits / prompt if prompt else None,
            'cached_tokens_per_call': distribution([cached_tokens(r) for r in measured]),
            'created_cache_tokens': sum((r.get('usage', {}).get('prompt_tokens_details') or {}).get('created_cache_tokens', 0) or 0
                                       for r in measured) if measured else None,
        }
    source_checks = [t for t in tools if t.get('tool_kind') == 'source_check']
    if source_checks:
        checks = [c for t in source_checks for c in t['results'].get('checks', [])]
        valid = sum(bool(c.get('valid')) for c in checks)
        summary['source_verification'] = {
            'tool_calls': len(source_checks), 'draft_parse_errors': sum(bool(t['results'].get('parse_error')) for t in source_checks),
            'quote_checks': len(checks), 'valid_quotes': valid,
            'valid_quote_fraction': valid / len(checks) if checks else None,
            'actual_cpu_seconds': distribution([t['actual_cpu_seconds'] for t in source_checks]),
            'elapsed_seconds': distribution([t['elapsed'] for t in source_checks]),
            'injected_delay_seconds': distribution([t['injected_delay_seconds'] for t in source_checks]),
            'scope': 'Source provenance only; answer correctness is scored separately.',
        }
    summary['quality_protocol'] = config.get('data_manifest', {}).get('quality_protocol', 'HotpotQA normalized EM/F1')
    datasets = sorted({tasks[k]['dataset_id'] for k in config['task_ids'] if tasks[k].get('dataset_id')})
    if datasets:
        summary['quality_by_dataset'] = {}
        for dataset in datasets:
            ids = {k for k in config['task_ids'] if tasks[k].get('dataset_id') == dataset}
            scores = [r for r in scored if r['root_id'] in ids]
            calls = [r for r in responses if r['root_id'] in ids]
            summary['quality_by_dataset'][dataset] = {
                'expected_roots': len(ids), 'completed_roots': len(scores),
                'em': sum(r['em'] for r in scores) / len(ids),
                'f1': sum(r['f1'] for r in scores) / len(ids),
                'root_latency_seconds': distribution([r['duration'] for r in scores]),
                'model_calls': len(calls),
                'prompt_tokens': sum(r.get('usage', {}).get('prompt_tokens', 0) or 0 for r in calls),
                'completion_tokens': sum(r.get('usage', {}).get('completion_tokens', 0) or 0 for r in calls),
            }
    measured_queue = [r['server_metrics']['queue_time_ms'] / 1000 for r in responses
                      if r.get('server_metrics') and r['server_metrics'].get('queue_time_ms') is not None]
    summary['measured_engine_queue_seconds'] = distribution(measured_queue)
    measurements = [e for e in events if e['event'] == 'prompt_measurement_check']
    if measurements:
        summary['prompt_measurement'] = {
            'checked_calls': len(measurements), 'mismatches': sum(not e['matches'] for e in measurements),
            'tokenization_overhead_seconds': distribution([e['duration'] for e in events if e['event'] == 'prompt_tokens_measured'])}
    summary['control_observations']['max_history_claimed_tokens'] = max(
        [e.get('total_claimed', e.get('history_claimed_tokens', 0)) for e in events], default=0)
    summary['control_observations']['max_history_soft_target_overshoot_tokens'] = max(
        [max(0, e.get('total_claimed', e.get('history_claimed_tokens', 0)) - e['history_target_tokens'])
         for e in events if 'history_target_tokens' in e], default=0)
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
