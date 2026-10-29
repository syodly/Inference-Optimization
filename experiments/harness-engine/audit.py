"""Audit measured causal traces independently of the admission implementation."""
from collections import Counter, defaultdict
import json
from pathlib import Path

from analyze import read


def audit(directory: Path):
    config = json.loads((directory / 'config.json').read_text())
    requests = read(directory / 'requests.jsonl')
    responses = read(directory / 'responses.jsonl')
    events = read(directory / 'events.jsonl')
    tools = read(directory / 'tools.jsonl')
    roots = read(directory / 'roots.jsonl')
    violations = []
    execution_count = None
    if config.get('trace_semantics_version', 1) >= 2:
        sessions = read(directory / 'sessions.jsonl')
        starts = [s for s in sessions if s['event'] == 'agent_execution_start']
        ends = [s for s in sessions if s['event'] == 'agent_execution_end']
        execution_count = len(starts)
        ids = [s['execution_id'] for s in starts]
        if (len(ids) != config['expected_agent_executions'] or len(ids) != len(set(ids))
                or set(ids) != {s['execution_id'] for s in ends} or len(ends) != len(starts)):
            violations.append('Agent execution spans do not match the controlled research turns')
        bounds = {s['session_id']: [s['t'], next((e['t'] for e in ends
                   if e['execution_id'] == s['execution_id']), float('-inf'))] for s in starts}
        for r in [*requests, *responses, *tools]:
            a, b = bounds.get(r['node_id'], [float('inf'), float('-inf')])
            if not a <= r['t'] <= b:
                violations.append('Model/tool event is outside its Agent execution: ' + r['node_id'])
        for kind in ['model_call_start', 'model_call_end']:
            calls = [s['call_id'] for s in sessions if s['event'] == kind]
            if len(calls) != len(set(calls)) or set(calls) != {r['call_id'] for r in requests}:
                violations.append('Per-model-call spans are incomplete: ' + kind)
    if len(roots) != len(config['task_ids']) or {r['root_id'] for r in roots} != set(config['task_ids']):
        violations.append('Root records do not match submitted tasks')
    if len(requests) != config['expected_model_calls']:
        violations.append('Mandatory model call count differs from plan')
    by_node = defaultdict(list)
    for event in events:
        if 'node_id' in event:
            by_node[event['node_id']].append(event)
    for label, rows in [('requests', requests), ('responses', responses)]:
        ids = [r['call_id'] for r in rows]
        if len(ids) != len(set(ids)):
            violations.append(f'Duplicate call IDs in {label}')
    if {r['call_id'] for r in requests} != {r['call_id'] for r in responses}:
        violations.append('Requests and terminal response records differ')
    for node, rows in by_node.items():
        ready = [e['t'] for e in rows if e['event'] == 'model_ready']
        release = [e['t'] for e in rows if e['event'] == 'frontend_release']
        submit = [e['t'] for e in rows if e['event'] == 'model_submit']
        if not (len(ready) == len(release) == len(submit)):
            violations.append('Admission records missing for ' + node)
        for a, b, c in zip(ready, release, submit):
            if not a <= b <= c:
                violations.append('Causal ordering invalid for ' + node)
    for r in roots:
        if r.get('error') or config['workflow'] == 'direct':
            continue
        if config.get('dynamic_review'):
            rid = r['root_id']
            calls = [q for q in requests if q['root_id'] == rid]
            declared = [e for e in events if e.get('root_id') == rid and e['event'] == 'review_decision']
            primary = [e for e in events if e.get('root_id') == rid and e['event'] == 'model_complete'
                       and e.get('stage') == 'evidence' and e.get('node_id', '').rsplit('/', 1)[-1].startswith('child')]
            decision = [e for e in events if e.get('root_id') == rid and e['event'] == 'model_submit' and e.get('stage') == 'decision']
            if len(primary) != 3 or len(decision) != 1 or len(declared) != 1:
                violations.append('Dynamic root must join three primary children before one declared decision: '+rid)
                continue
            if max(e['t'] for e in primary) > decision[0]['t']:
                violations.append('Dynamic parent decision preceded mandatory children: '+rid)
            choice = declared[0]
            expected = {(rid+'/child'+str(i), stage) for i in range(3) for stage in ['query', 'draft', 'evidence']}
            expected.add((rid+'/parent', 'decision'))
            if choice['launch_review']:
                expected.update((rid+'/review0', stage) for stage in ['query', 'draft', 'evidence'])
                expected.add((rid+'/parent', 'synthesis'))
                review_calls = [q for q in calls if q['node_id'] == rid+'/review0']
                review_end = [e for e in events if e.get('root_id') == rid and e['event'] == 'model_complete'
                              and e.get('node_id') == rid+'/review0' and e.get('stage') == 'evidence']
                final = [e for e in events if e.get('root_id') == rid and e['event'] == 'model_submit' and e.get('stage') == 'synthesis']
                if not review_calls or min(q['t'] for q in review_calls) < choice['t'] or len(review_end) != 1 or len(final) != 1:
                    violations.append('Dynamic review expansion boundaries invalid: '+rid)
                elif review_end[0]['t'] > final[0]['t']:
                    violations.append('Final synthesis preceded optional review: '+rid)
            if {(q['node_id'], q['stage']) for q in calls} != expected or len(calls) != len(expected):
                violations.append('Dynamic root call set differs from its declared branch choice: '+rid)
            continue
        completed_children = [e for e in events if e.get('root_id') == r['root_id']
                              and e['event'] == 'model_complete' and e.get('stage') == 'evidence']
        synthesis = [e for e in events if e.get('root_id') == r['root_id']
                     and e['event'] == 'model_submit' and e.get('stage') == 'synthesis']
        if len(completed_children) != config['branches'] or len(synthesis) != 1:
            violations.append('Required join incomplete for ' + r['root_id'])
        elif max(e['t'] for e in completed_children) > synthesis[0]['t']:
            violations.append('Parent submitted before required children for ' + r['root_id'])
    for tool in tools:
        rows = by_node[tool['node_id']]
        before_stage = 'draft' if tool.get('tool_kind') == 'source_check' else 'query'
        after_stage = 'draft' if before_stage == 'query' and config['workflow'] in ['verified', 'adaptive_verified'] else 'evidence'
        query_end = [e['t'] for e in rows if e['event'] == 'model_complete' and e.get('stage') == before_stage]
        tool_start = [e['t'] for e in rows if e['event'] == 'tool_start' and e.get('tool_id') == tool['tool_id']]
        tool_end = [e['t'] for e in rows if e['event'] == 'tool_complete' and e.get('tool_id') == tool['tool_id']]
        evidence = [e['t'] for e in rows if e['event'] == 'model_submit' and e.get('stage') == after_stage]
        if not all([query_end, tool_start, tool_end, evidence]):
            violations.append('Required tool boundary event missing for ' + tool['tool_id'])
        if query_end and tool_start and tool_end and evidence and not query_end[0] <= tool_start[0] <= tool_end[0] <= evidence[0]:
            violations.append('Tool ordering invalid for ' + tool['node_id'])
        if tool['elapsed'] + .001 < tool['actual_cpu_seconds'] + tool['injected_delay_seconds']:
            violations.append('Tool duration accounting invalid for ' + tool['node_id'])
    if config['policy'] not in ['native', 'backend_priority']:
        if any(e['inflight_calls'] > e['target'] for e in events if e['event'] == 'frontend_release'):
            violations.append('New admission exceeded observed target')
    if config['policy'] in ['session_window', 'session_return']:
        admissions = [e for e in events if e['event'] == 'session_admitted']
        if any(e['active_sessions'] > config['session_cap'] for e in admissions):
            violations.append('Session working set exceeded configured window')
        released = [e for e in events if e['event'] == 'session_released']
        if {e['node_id'] for e in admissions} != {e['node_id'] for e in released}:
            violations.append('Session lease accounting incomplete')
    measured = [e for e in events if e['event'] == 'prompt_measurement_check']
    if config.get('measure_prompts'):
        if len(measured) != len(responses) or any(not e['matches'] for e in measured):
            violations.append('Measured prompt tokens do not match actual chat request usage')
    if any(e['event'] == 'history_claim_opened' for e in events):
        claims = {}
        for e in events:
            if e['event'] in ['history_claim_opened', 'history_claim_updated']:
                claims[e['node_id']] = e['history_tokens']
            elif e['event'] == 'session_released':
                released_claim = claims.pop(e['node_id'], None)
                if released_claim != e.get('released_history_tokens'):
                    violations.append('Released history claim differs from ledger')
            else:
                continue
            if sum(claims.values()) != e['total_claimed']:
                violations.append('History ledger total differs from per-Session claims')
        if claims:
            violations.append('History claims remain after all root tasks finished')
    result = {'run_id': directory.name, 'passed': not violations, 'violations': violations,
              'request_count': len(requests), 'response_count': len(responses),
              'root_count': len(roots), 'tool_count': len(tools),
              'trace_semantics_version': config.get('trace_semantics_version', 1),
              'agent_execution_count': execution_count,
              'call_stages': dict(Counter(r['stage'] for r in requests)),
              'scope': 'Causal and accounting consistency, not proof of model quality or novelty.'}
    (directory / 'audit.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import sys
    print(json.dumps(audit(Path(sys.argv[1])), indent=2))
