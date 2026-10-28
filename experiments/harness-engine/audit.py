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
        if r.get('error') or config['workflow'] != 'sharded':
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
        query_end = [e['t'] for e in rows if e['event'] == 'model_complete' and e.get('stage') == 'query']
        tool_start = [e['t'] for e in rows if e['event'] == 'tool_start']
        tool_end = [e['t'] for e in rows if e['event'] == 'tool_complete']
        evidence = [e['t'] for e in rows if e['event'] == 'model_submit' and e.get('stage') == 'evidence']
        if query_end and tool_start and tool_end and evidence and not query_end[0] <= tool_start[0] <= tool_end[0] <= evidence[0]:
            violations.append('Tool ordering invalid for ' + tool['node_id'])
        if tool['elapsed'] + .001 < tool['actual_cpu_seconds'] + tool['injected_delay_seconds']:
            violations.append('Tool duration accounting invalid for ' + tool['node_id'])
    if config['policy'] not in ['native', 'backend_priority']:
        if any(e['inflight_calls'] > e['target'] for e in events if e['event'] == 'frontend_release'):
            violations.append('New admission exceeded observed target')
    result = {'run_id': directory.name, 'passed': not violations, 'violations': violations,
              'request_count': len(requests), 'response_count': len(responses),
              'root_count': len(roots), 'tool_count': len(tools),
              'call_stages': dict(Counter(r['stage'] for r in requests)),
              'scope': 'Causal and accounting consistency, not proof of model quality or novelty.'}
    (directory / 'audit.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    import sys
    print(json.dumps(audit(Path(sys.argv[1])), indent=2))
