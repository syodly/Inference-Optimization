"""Offline measurements of actual history-return gaps and competing admissions.

The controller never reads this analysis or later response usage. Cache misses
alone do not identify eviction; exact-prefix audits and interventions are separate.
"""
import argparse
import json
from pathlib import Path

from analyze import distribution, read


def analyze_history(run):
    config = json.loads((run / 'config.json').read_text())
    requests = read(run / 'requests.jsonl')
    responses = read(run / 'responses.jsonl')
    events = read(run / 'events.jsonl')
    metrics = read(run / 'metrics.jsonl')
    tools = read(run / 'tools.jsonl')
    request_map = {(r['node_id'], r['stage']): r for r in requests}
    response_map = {(r['node_id'], r['stage']): r for r in responses}
    ready_map = {(r['node_id'], r['stage']): r for r in events if r['event'] == 'model_ready'}
    cold = [r for r in requests if r['stage'] == 'draft']
    token_path = run / 'token_audit.json'
    prefixes = ({r['call_id']: r for r in json.loads(token_path.read_text())['records']}
                if token_path.exists() else {})
    rows = []
    for draft in cold:
        node = draft['node_id']
        returned = request_map.get((node, 'evidence'))
        completed = response_map.get((node, 'draft'))
        evidence = response_map.get((node, 'evidence'))
        if returned is None or completed is None or evidence is None:
            continue
        start, end = completed['t'], returned['t']
        gap_cold = [r for r in cold if start < r['t'] < end and r['node_id'] != node]
        lifetime_cold = [r for r in cold if draft['t'] < r['t'] < end and r['node_id'] != node]
        samples = [m for m in metrics if start <= m['t'] <= end]
        # A millisecond natural tool gap may have no quarter-second samples.
        before = [m for m in metrics if m['t'] <= start]
        after = [m for m in metrics if m['t'] >= end]
        boundary = ([before[-1]] if before else []) + ([after[0]] if after else [])
        counters = [m.get('preemptions') for m in boundary if m.get('preemptions') is not None]
        details = evidence.get('usage', {}).get('prompt_tokens_details') or {}
        previous_details = completed.get('usage', {}).get('prompt_tokens_details') or {}
        checked = next((t for t in tools if t['node_id'] == node and t.get('tool_kind') == 'source_check'), None)
        prefix = prefixes.get(returned['call_id'], {})
        ready = ready_map[(node, 'evidence')]['t']
        rows.append({
            'root_id': draft['root_id'], 'node_id': node,
            'draft_submitted_t': draft['t'], 'draft_completed_t': start,
            'return_ready_t': ready, 'return_submitted_t': end,
            'draft_to_return_gap_seconds': end - start,
            'ready_to_submit_seconds': end - ready,
            'source_check_seconds': checked['elapsed'] if checked else None,
            'injected_source_check_delay_seconds': checked['injected_delay_seconds'] if checked else None,
            'cold_drafts_submitted_in_gap': len(gap_cold),
            'cold_drafts_submitted_since_draft_start': len(lifetime_cold),
            'other_prompt_tokens_submitted_in_gap': sum(
                response_map[(r['node_id'], r['stage'])].get('usage', {}).get('prompt_tokens', 0) or 0
                for r in requests if start < r['t'] < end and r['node_id'] != node
                and (r['node_id'], r['stage']) in response_map),
            'gap_metric_samples': len(samples),
            'gap_max_observed_kv_usage': max((m['kv_usage'] for m in samples if m.get('kv_usage') is not None), default=None),
            'preemption_delta_at_enclosing_metric_samples': counters[-1] - counters[0] if len(counters) == 2 else None,
            'draft_prompt_tokens': completed.get('usage', {}).get('prompt_tokens'),
            'draft_created_cache_tokens': previous_details.get('created_cache_tokens'),
            'return_prompt_tokens': evidence.get('usage', {}).get('prompt_tokens'),
            'return_cached_tokens': details.get('cached_tokens'),
            'common_input_prefix_tokens': prefix.get('common_input_prefix_tokens'),
            'return_engine_queue_seconds': (evidence.get('server_metrics') or {}).get('queue_time_ms', 0) / 1000
                if (evidence.get('server_metrics') or {}).get('queue_time_ms') is not None else None,
        })
    summary = {
        'run_id': run.name, 'policy': config['policy'], 'complete_history_returns': len(rows),
        'expected_history_returns': config.get('branches', 3) * config['count'],
        'returns_with_zero_cache': sum(r['return_cached_tokens'] == 0 for r in rows),
        'returns_with_unknown_cache': sum(r['return_cached_tokens'] is None for r in rows),
        'returns_exposed_to_new_cold_drafts_in_gap': sum(r['cold_drafts_submitted_in_gap'] > 0 for r in rows),
        'token_prefix_audit_available': bool(prefixes),
        **{key: distribution([r[key] for r in rows]) for key in [
            'draft_to_return_gap_seconds', 'ready_to_submit_seconds', 'source_check_seconds',
            'cold_drafts_submitted_in_gap', 'other_prompt_tokens_submitted_in_gap',
            'return_engine_queue_seconds']},
        'scope': 'Post-run exposure measurements, not an eviction event attribution or an online predictor. '
                 'Observed metric boundaries can enclose unrelated work. Actual cache accounting is reported separately '
                 'from common input prefixes and from provenance/answer quality.',
        'records': rows,
    }
    (run / 'history_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', type=Path, nargs='+')
    args = ap.parse_args()
    for run in args.runs:
        result = analyze_history(run)
        print(json.dumps({k: v for k, v in result.items() if k != 'records'}, ensure_ascii=False))
