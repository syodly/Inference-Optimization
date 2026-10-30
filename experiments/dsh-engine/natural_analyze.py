"""Reconstruct observed event DAGs from completed native runs, never replay them."""
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
NODE = ROOT/'toolchain/node-v24.22.2-linux-x64/bin/node'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def text(blocks):
    return '\n'.join(block.get('text', '') for block in blocks if block.get('type') == 'text')


def wire_response(path):
    identifier, usage, finish, content, reasoning, calls = None, {}, None, '', '', {}
    for line in path.read_text().splitlines():
        if not line.startswith('data: {'):
            continue
        chunk = json.loads(line[6:]);identifier = chunk.get('id') or identifier
        usage = chunk.get('usage') or usage
        for choice in chunk.get('choices', []):
            finish = choice.get('finish_reason') or finish
            delta = choice.get('delta', {})
            content += delta.get('content') or ''
            reasoning += delta.get('reasoning_content') or delta.get('reasoning') or ''
            for call in delta.get('tool_calls', []):
                target = calls.setdefault(call['index'], {'id': '', 'name': '', 'arguments': ''})
                target['id'] += call.get('id') or ''
                target['name'] += call.get('function', {}).get('name') or ''
                target['arguments'] += call.get('function', {}).get('arguments') or ''
    return identifier, usage, finish, {'content': content, 'reasoning': reasoning, 'tool_calls': list(calls.values())}


def analyze_case(record, spec):
    directory = record/spec['case_id']
    complete = json.loads((directory/'completion.json').read_text())
    max_tokens = json.loads((record/'plan.json').read_text())['max_output_tokens']
    observed = rows(directory/'observer.jsonl')
    native = {}
    for path in (directory/'home').rglob('session.v4.jsonl.zstd'):
        raw = subprocess.check_output([str(NODE), '-e',
            "const f=require('node:fs'),z=require('node:zlib');process.stdout.write(z.zstdDecompressSync(f.readFileSync(process.argv[1])))", str(path)])
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
        session = events[0]['id'];native[session] = events
        (directory/'native-events').mkdir(exist_ok=True)
        (directory/'native-events'/f'{session}.jsonl').write_bytes(raw)
    cli = rows(directory/'cli.jsonl')
    root = next(row['sessionId'] for row in cli if row['type'] == 'session')
    finals = [row['text'] for row in cli if row['type'] == 'final']
    ready = [row for row in observed if row['event'] == 'model_request_ready']
    model_events = [(session, event) for session, events in native.items() for event in events
                    if event['type'] == 'assistant/message' and event['data']['message'].get('source', {}).get('kind') == 'model']
    by_response = {event['data']['message']['source']['replayState']['response']['responseId']: (session, event)
                   for session, event in model_events}
    wires = {}
    for path in (ROOT/'artifacts/wire').iterdir():
        meta = json.loads((path/'request.json').read_text())
        if not complete['started_wall_time'] <= meta['started_wall_time'] <= complete['finished_wall_time']:
            continue
        identifier, usage, finish, response = wire_response(path/'response.body')
        session_event = by_response.get(identifier)
        if not session_event:
            raise ValueError(f'Unmapped request in isolated interval: {path}')
        shutil.copytree(path, directory/'wire'/path.name, dirs_exist_ok=True)
        wires[identifier] = {'call_id': path.name, 'request': json.loads((path/'request.body').read_text()),
                             'response': response, 'usage': usage, 'finish': finish,
                             'wire_start': meta['started_wall_time'],
                             'metadata': json.loads((path/'response.json').read_text())}
    nodes, edges, changes = [], [], []
    base = complete['started_wall_time']

    def stamp(at):
        return {'time': at, 'relative_seconds': round(at-base, 6),
                'timestamp_utc': datetime.fromtimestamp(at, timezone.utc).isoformat(timespec='milliseconds'),
                'timestamp_china': datetime.fromtimestamp(at, timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')}

    def change(at, kind, **payload):
        changes.append({**stamp(at), 'kind': kind, **payload})

    def node(identifier, kind, label, session, at, end=None, **payload):
        item = {'id': identifier, 'kind': kind, 'label': label, 'session_id': session,
                'revealed_at': at, 'ended_at': end, **payload}
        nodes.append(item);change(at, 'node_added', node_id=identifier, label=label, session_id=session)
        if end is not None:
            change(end, 'node_completed', node_id=identifier, label=label, session_id=session)
        return item

    edge_keys = set()

    def edge(a, b, relation, at):
        key = (a, b, relation)
        if a == b or key in edge_keys:
            return
        edge_keys.add(key)
        item = {'source': a, 'target': b, 'relation': relation, 'revealed_at': at}
        edges.append(item);change(at, 'edge_added', **item)

    task = node('initial-task', 'task', 'Initial user task', root, base, initial_task=spec['initial_task'])
    create_nodes = {}
    for session, events in native.items():
        header = events[0];created = header['createdAt']/1000
        create_nodes[session] = node('agent:'+session, 'agent', 'Root Agent' if session == root else 'Child Agent',
                                     session, created, header=header)
        if session == root:
            edge(task['id'], create_nodes[session]['id'], 'task creates root', created)
    models = {}
    for session, event in model_events:
        turn, step = event['data']['turn'], event['data']['step']
        request = next(row for row in ready if (row['session_id'], row['turn'], row['step']) == (session, turn, step))
        response_id = event['data']['message']['source']['replayState']['response']['responseId']
        wire = wires[response_id]
        item = node(f'model:{session}:{turn}:{step}', 'model', f'Model turn {turn} step {step}',
                    session, request['wall_time'], event['time']/1000, turn=turn, step=step,
                    response_id=response_id, **wire)
        models[(session, turn, step)] = item
    starts = {row['call_id']: row for row in observed if row['event'] == 'tool_start'}
    ends = {row['call_id']: row for row in observed if row['event'] in ['tool_end', 'tool_throw']}
    tools = {}
    for session, events in native.items():
        for event in events:
            if event['type'] != 'tool/call':
                continue
            data = event['data'];call = data['callId'];start = starts.get(call);end = ends.get(call)
            at = event['time']/1000
            arguments = json.loads(data['arguments'])
            committed_result = next((e['data']['message'] for e in events if e['type'] == 'tool/result'
                                     and e['data']['message'].get('toolCallId') == call), None)
            tool = node('tool:'+call, 'tool', data['name'], session, at,
                        end['wall_time'] if end else None, arguments=arguments,
                        tool_started_at=start['wall_time'] if start else None,
                        result=end.get('result') if end else None, error=end.get('error') if end else None,
                        committed_result=committed_result, turn=data['turn'], step=data['step'], native_call=event)
            tools[call] = tool
            parent = models[(session, data['turn'], data['step'])]
            edge(parent['id'], tool['id'], 'model generates tool call', at)
            if data['name'] in ['subagent', 'subagent_fork', 'workflow', 'send_message', 'interrupt_agent', 'todo_write']:
                change(at, 'model_action', node_id=tool['id'], session_id=session,
                       tool=data['name'], arguments=arguments)
    # Add only executable dependencies: sibling tools share a model predecessor;
    # log order alone does not turn parallel tools into a serial chain.
    for session in native:
        sequence = sorted((n for n in models.values() if n['session_id'] == session), key=lambda n: n['revealed_at'])
        previous = None
        for item in sequence:
            if previous is None:
                edge(create_nodes[session]['id'], item['id'], 'agent begins model work', item['revealed_at'])
            else:
                prior_tools = [tool for tool in tools.values() if tool['session_id'] == session
                               and (tool['turn'], tool['step']) == (previous['turn'], previous['step'])]
                if prior_tools:
                    for tool in prior_tools:
                        edge(tool['id'], item['id'], 'tool result before next model step', item['revealed_at'])
                else:
                    edge(previous['id'], item['id'], 'same session continuation', item['revealed_at'])
            previous = item
    for session, events in native.items():
        for event in events:
            if event['type'] == 'subagent/catalog':
                child = event['data']['childId'];at = event['time']/1000
                candidates = [tool for tool in tools.values() if tool['session_id'] == session
                              and tool['label'] in ['subagent', 'subagent_fork', 'workflow']
                              and tool['revealed_at'] <= at
                              and (tool['ended_at'] is None or at <= tool['ended_at']+.1)]
                if child in create_nodes and candidates:
                    source = max(candidates, key=lambda n: n['revealed_at'])
                    edge(source['id'], create_nodes[child]['id'], 'harness publishes child', at)
                change(at, 'child_published', session_id=session, child_session=child, native_event=event)
            if event['type'] in ['user/message', 'agent/inbox/spliced']:
                data = event['data'];serialized = json.dumps(data)
                if any(mark in serialized for mark in ['subagent-settled', 'agent-message', 'subagent-completed']):
                    change(event['time']/1000, 'message_or_settlement', session_id=session, native_event=event)
    seen_tool_names = set()
    for row in observed:
        if row['event'] in ['subagent/start', 'subagent/end', 'workflow/start', 'workflow/end',
                            'workflow/agent-start', 'workflow/agent-end', 'agent_error']:
            change(row['wall_time'], row['event'], observed=row)
        if row['event'] == 'assistant_frame':
            frame = row['frame'];chunk = frame.get('chunk', {})
            # DSH stream deltas repeat the accumulated name. Only the first
            # appearance of each native call ID reveals a new tool intent.
            key = (row.get('session_id'), chunk.get('id'))
            if chunk.get('type') == 'tool-call-delta' and chunk.get('name') and key not in seen_tool_names:
                seen_tool_names.add(key)
                change(row['wall_time'], 'tool_name_first_observed', session_id=row['session_id'],
                       tool=chunk['name'], call_id=chunk.get('id'),
                       note='Streamed tool name; arguments may still be incomplete.')
        if row['event'] == 'tool_start':
            change(row['wall_time'], 'tool_execution_started', session_id=row.get('session_id'),
                   tool=row['tool'], node_id='tool:'+row['call_id'])
    changes.sort(key=lambda row: (row['time'], row['kind']))
    model_intervals = [(n['revealed_at'], n['ended_at']) for n in models.values()]
    live = peak_models = 0
    for _, delta in sorted([(a, 1) for a, b in model_intervals]+[(b, -1) for a, b in model_intervals]):
        live += delta;peak_models = max(peak_models, live)
    indegree = Counter(edge['target'] for edge in edges)
    outgoing = defaultdict(list)
    for e in edges:
        outgoing[e['source']].append(e['target'])
    pending = [n['id'] for n in nodes if not indegree[n['id']]];visited = []
    while pending:
        current = pending.pop();visited.append(current)
        for target in outgoing[current]:
            indegree[target] -= 1
            if indegree[target] == 0:pending.append(target)
    audit = {'native_sessions': len(native), 'native_model_steps': len(model_events), 'wire_responses': len(wires),
             'ready_events': len(ready), 'unmapped_tool_starts': sorted(set(starts)-set(tools)),
             'graph_is_acyclic': len(visited) == len(nodes),
             'wire_configuration_valid': all((w['request'].get('max_tokens'), w['request'].get('temperature'),
                                               w['request'].get('reasoning_effort')) == (max_tokens, 0, 'low') for w in wires.values()),
             'all_http_200': all(w['metadata'].get('status') == 200 for w in wires.values()),
             'watchdog_triggered': complete['watchdog_triggered']}
    first_request = min(wires.values(), key=lambda w: w['wire_start'])['request']
    audit['first_request_available_tools'] = [t.get('function', {}).get('name') for t in first_request.get('tools', [])]
    audit['delegation_tools_available'] = all(name in audit['first_request_available_tools'] for name in ['subagent', 'subagent_fork', 'workflow'])
    audit['initial_task_present_unchanged'] = any(m.get('role') == 'user' and m.get('content') == spec['initial_task']
                                                 for m in first_request['messages'])
    assert audit['graph_is_acyclic'] and audit['wire_configuration_valid']
    assert len(model_events) == len(wires) == len(ready)
    counts = Counter(tool['label'] for tool in tools.values())
    summary = {'case_id': spec['case_id'], 'title': spec['title'], **complete,
               'root_session': root, 'agent_sessions': len(native), 'child_sessions': len(native)-1,
               'model_calls': len(model_events), 'tool_calls': len(tools), 'tool_counts': dict(counts),
               'tool_errors': sum(bool((tool['result'] or {}).get('isError') or tool['error']) for tool in tools.values()),
               'peak_outstanding_model_steps': peak_models,
               'generated_tokens': sum(w['usage'].get('completion_tokens', 0) for w in wires.values()),
               'output_truncations': sum(w['finish'] == 'length' for w in wires.values()),
               'first_child_seconds': min((n['revealed_at']-base for n in nodes if n['kind'] == 'agent' and n['session_id'] != root), default=None),
               'last_new_tool_seconds': max((n['revealed_at']-base for n in tools.values()), default=None),
               'dag_nodes': len(nodes), 'dag_edges': len(edges), 'initial_task': spec['initial_task'],
               'max_output_tokens': max_tokens,
               'provenance': spec['provenance'], 'final_text': finals[-1] if finals else '', 'audit': audit}
    summary['steps'] = []
    for model in sorted(models.values(), key=lambda n: n['revealed_at']):
        called = [tool for tool in tools.values() if tool['session_id'] == model['session_id']
                  and (tool['turn'], tool['step']) == (model['turn'], model['step'])]
        summary['steps'].append({'node_id': model['id'], 'session_id': model['session_id'],
                                  'turn': model['turn'], 'step': model['step'],
                                  'ready_seconds': round(model['revealed_at']-base, 3),
                                  'response_seconds': round(model['ended_at']-base, 3),
                                  'tools': dict(Counter(tool['label'] for tool in called)),
                                  'first_tool_seconds': min((tool['revealed_at']-base for tool in called), default=None),
                                  'last_tool_end_seconds': max((tool['ended_at']-base for tool in called if tool['ended_at']), default=None),
                                  'model_text': model['response']['content'],
                                  'bash_exit_codes': [tool['result']['value']['exitCode'] for tool in called
                                                      if tool['label'] == 'bash' and tool.get('result', {}).get('value', {}).get('kind') == 'foreground']})
    summary['max_tools_proposed_in_one_response'] = max((sum(step['tools'].values()) for step in summary['steps']), default=0)
    summary['bash_nonzero_exits'] = sum(code != 0 for step in summary['steps'] for code in step['bash_exit_codes'])
    summary['quality_checks'] = {'scope': 'Offline output checks only; one curated task per scenario is not benchmark accuracy.'}
    if spec['case_id'] == 'simple':
        summary['quality_checks']['expected_198_in_answer'] = '198' in summary['final_text']
    if spec['case_id'] == 'analysis':
        import csv
        with (directory/'input/products.csv').open() as file:
            products = {r['product_id']: r for r in csv.DictReader(file)}
        with (directory/'input/orders.csv').open() as file:
            orders = {r['order_id']: r for r in csv.DictReader(file)}
        with (directory/'input/refunds.csv').open() as file:
            refunds = {r['refund_id']: r for r in csv.DictReader(file)}
        totals = {}
        for month in ['2026-01', '2026-02']:
            paid = {k: r for k, r in orders.items() if r['status'] == 'paid' and r['paid_date'].startswith(month)}
            gross = sum(int(r['quantity'])*int(products[r['product_id']]['unit_price']) for r in paid.values())
            returned = sum(int(r['amount']) for r in refunds.values() if r['order_id'] in paid)
            totals[month] = {'gross': gross, 'refunds': returned, 'net': gross-returned}
        report = directory/'output/report.md'
        summary['quality_checks'].update(expected_monthly_totals=totals,
                                          report_present=report.exists(),
                                          report_text=report.read_text() if report.exists() else None)
    if spec['case_id'] == 'incident':
        report = directory/'output/incident-report.md'
        summary['quality_checks'].update(report_present=report.exists(),
                                          expected_mechanism='6*24 + 18 exceeds database connection limit 100 after 09:03 rollout; edge rollback does not resolve it.',
                                          report_text=report.read_text() if report.exists() else None)
    if spec['case_id'] == 'research':
        report = directory/'output/report.md'
        summary['quality_checks'].update(report_present=report.exists(),
                                          report_text=report.read_text() if report.exists() else None)
    if spec['case_id'] == 'coding':
        result = subprocess.run(['python3', '-m', 'unittest', '-v'], cwd=directory/'output', capture_output=True, text=True)
        summary['offline_test_exit_code'] = result.returncode
        summary['offline_test_output'] = result.stdout+result.stderr
        summary['quality_checks']['original_tests_unchanged'] = (directory/'input/test_checkout.py').read_bytes() == (directory/'output/test_checkout.py').read_bytes()
    dump(directory/'summary.json', summary)
    dump(directory/'timeline.json', changes)
    dump(directory/'graph.json', {'nodes': nodes, 'edges': edges,
                                 'interpretation': 'Observed event DAG, not a complete precomputed plan. Cross-session message causality is recorded in timeline; only verified execution dependencies are drawn.'})
    return summary


def main():
    import sys
    record = ROOT/'runs'/sys.argv[1]
    plan = json.loads((record/'plan.json').read_text())
    summaries = []
    for spec in plan['cases']:
        if not (record/spec['case_id']/'completion.json').exists():continue
        summaries.append(analyze_case(record, spec))
    output = ROOT/'artifacts'/record.name
    output.mkdir(parents=True, exist_ok=True)
    dump(output/'comparison.json', {'batch_id': record.name, 'cases': summaries,
                                   'replay': False, 'agent_count_fixed': False, 'predefined_graph': False})
    for name in ['plan.json', 'engine.json', 'source.json', 'research-data.json']:
        shutil.copy2(record/name, output/name)
    for summary in summaries:
        directory = output/summary['case_id'];directory.mkdir(exist_ok=True)
        for name in ['summary.json', 'timeline.json', 'graph.json', 'initial-task.txt', 'completion.json', 'output-sha256.json']:
            shutil.copy2(record/summary['case_id']/name, directory/name)
    archive = ROOT/'artifacts'/f'{record.name}-raw.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(record, arcname=record.name)
    dump(output/'archive-index.json', {'archive': archive.name, 'bytes': archive.stat().st_size,
                                      'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    print(json.dumps([{'case': s['case_id'], 'agents': s['agent_sessions'], 'calls': s['model_calls'],
                       'tools': s['tool_counts'], 'seconds': s['duration_seconds']} for s in summaries], indent=2))


if __name__ == '__main__':
    main()
