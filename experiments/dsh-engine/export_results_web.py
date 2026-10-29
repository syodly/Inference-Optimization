"""Export every completed small-group task from archived evidence for the site.

This is an offline presentation adapter. It sends no model requests.
"""
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parent
GROUP = 'e1-small-20261029'
RESULTS = ROOT/'results'/GROUP
EVIDENCE = ROOT/'evidence'/GROUP


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def parse_response(raw):
    content, reasoning, calls, usage = '', '', {}, {}
    for line in raw.splitlines():
        if not line.startswith('data: {'):
            continue
        chunk = json.loads(line[6:])
        usage = chunk.get('usage') or usage
        for choice in chunk.get('choices', []):
            delta = choice.get('delta', {})
            content += delta.get('content') or ''
            reasoning += delta.get('reasoning_content') or delta.get('reasoning') or ''
            for call in delta.get('tool_calls', []):
                item = calls.setdefault(call['index'], {'id': '', 'type': 'function',
                                                        'function': {'name': '', 'arguments': ''}})
                item['id'] += call.get('id') or ''
                for key in ['name', 'arguments']:
                    item['function'][key] += call.get('function', {}).get(key) or ''
    return {'content': content, 'reasoning_content': reasoning,
            'tool_calls': [calls[index] for index in sorted(calls)]}, usage


def export_run(run_id):
    directory = RESULTS/run_id
    summary = json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    scored = json.loads((directory/'scored.json').read_text(encoding='utf-8'))
    audits = json.loads((directory/'native-audit.json').read_text(encoding='utf-8'))
    wire = json.loads((directory/'wire-index.json').read_text(encoding='utf-8'))
    assert summary['audit_pass'] and len(scored) == 8
    out = RESULTS/'web'/run_id
    tasks = []
    with tarfile.open(EVIDENCE/f'{run_id}-raw.tar.gz') as archive:
        def read(name):
            return archive.extractfile(f'{run_id}/{name}').read().decode('utf-8')

        def rows(name):
            return [json.loads(line) for line in read(name).splitlines() if line.strip()]

        dispatch = [row for row in rows('dispatch.jsonl') if row['event'] == 'admit']
        tools = rows('tools.jsonl')
        for score in scored:
            identifier = score['task_id']
            audit = next(row for row in audits if row['task_id'] == identifier)
            root = audit['root_session']
            events = rows(f'tasks/{identifier}/native-plugin.jsonl')
            task = json.loads(read(f'tasks/{identifier}/task.json'))
            sessions = {row['session_id']: row for row in audit['agents']}
            calls_by_session = {}
            for call in wire:
                if call['task_id'] == identifier:
                    calls_by_session.setdefault(call['session_id'], []).append(call)
            requests, responses = [], []
            for session, calls in calls_by_session.items():
                calls.sort(key=lambda call: call['call_id'])
                assert len(calls) == 2
                for index, call in enumerate(calls):
                    stage = (['plan', 'synthesis'] if session == root else ['query', 'evidence'])[index]
                    prefix = f"wire/{call['call_id']}/"
                    payload = json.loads(read(prefix+'request.body'))
                    metadata = json.loads(read(prefix+'response.json'))
                    message, usage = parse_response(read(prefix+'response.body'))
                    permit = next(row for row in dispatch if row['agent_id'] == session and row['stage'] == stage)
                    assert usage == call['usage']
                    requests.append({'call_id': call['call_id'], 'node_id': session, 'stage': stage,
                                     'payload': payload, 'dispatch': permit})
                    responses.append({'call_id': call['call_id'], 'node_id': session, 'stage': stage,
                                      'duration': metadata['duration_seconds'],
                                      'ttft': metadata['first_body_seconds'], 'usage': usage,
                                      'message': message, 'metadata': metadata, 'finishes': call['finishes']})
            searches = [dict(row, node_id=row['agent_id'], tool_kind='bm25',
                             tool_id=f"{row['agent_id']}/search", actual_cpu_seconds=row['duration_seconds'])
                        for row in tools if row['task_id'] == identifier]
            assert len(requests) == 8 and len(searches) == 3
            children = [None]*3
            for session, agent in sessions.items():
                if agent['role'] == 'child':
                    children[agent['branches'][0]] = session
            start = next(row for row in events if row['event'] == 'workflow_start')
            end = next(row for row in events if row['event'] == 'workflow_result')
            parent_events = rows(f'native-events/{root}.jsonl')
            workflow = {'name': 'research_workflow', 'arguments': {},
                        'duration_seconds': end['wall_time']-start['wall_time'],
                        'result': end['result'],
                        'native_tool_events': [row for row in parent_events if row['type'] in ['tool/call', 'tool/result']]}
            sample = {'framework': 'official-dsh', 'root_id': root, 'task': task,
                      'task_id': identifier, 'scoring': score, 'child_sessions': children,
                      'workflow': workflow, 'streams': {'requests': requests, 'responses': responses,
                                                       'tools': searches, 'roots': [score]},
                      'source_archive': f'{run_id}-raw.tar.gz'}
            filename = f'{run_id}/{identifier}.json'
            dump(out/f'{identifier}.json', sample)
            tasks.append({'task_id': identifier, 'question': task['question'], 'path': filename})
    return {'run_id': run_id, 'official_dsh': True, 'summary': summary,
            'paths': {'config.json': f'../{run_id}/config.json', 'scored.json': f'../{run_id}/scored.json',
                      'native-audit.json': f'../{run_id}/native-audit.json',
                      'raw-archive': f'../../../evidence/{GROUP}/{run_id}-raw.tar.gz'},
            'tasks': tasks}


def main():
    comparison = json.loads((RESULTS/'comparison.json').read_text(encoding='utf-8'))
    index = [export_run(row['run_id']) for row in comparison['rounds']]
    dump(RESULTS/'web/index.json', index)
    print(json.dumps({'rounds': len(index), 'task_examples': sum(len(row['tasks']) for row in index),
                      'model_calls': sum(row['summary']['wire_calls'] for row in index),
                      'gpu_requests_sent': 0}))


if __name__ == '__main__':
    main()
