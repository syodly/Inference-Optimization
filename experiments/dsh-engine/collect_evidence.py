"""Export the isolated deployment acceptance, including native durable events.

Run on songprojgpu1. Reads completed runs only; it starts no model requests.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import time


ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
NODE = ROOT/'toolchain/node-v24.22.2-linux-x64/bin/node'
OUT = ROOT/'artifacts/deployment-20261029'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def native_events(session):
    path, = (ROOT/'home/sessions').rglob(session+'/session.v4.jsonl.zstd')
    script = "const z=require('node:zlib'),f=require('node:fs');process.stdout.write(z.zstdDecompressSync(f.readFileSync(process.argv[1])).toString())"
    raw = subprocess.check_output([str(NODE), '-e', script, str(path)])
    destination = OUT/'sessions'/session
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination/path.name)
    (destination/'events.jsonl').write_bytes(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def response_id(path):
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('data: {'):
            return json.loads(line[6:]).get('id')
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('id')
    except json.JSONDecodeError:
        return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cli = [json.loads(line) for line in (ROOT/'artifacts/subagent.jsonl').read_text().splitlines()]
    session_event = next(row for row in cli if row['type'] == 'session')
    root_id = session_event.get('sessionId') or session_event.get('id')
    assert root_id
    parent = native_events(root_id)
    children = [row['data']['childId'] for row in parent if row['type'] == 'subagent/catalog']
    assert len(children) == len(set(children)) == 3
    records = {root_id: parent, **{child: native_events(child) for child in children}}
    model_sessions, session_reports, timeline = {}, {}, []
    for session, rows in records.items():
        calls = [row for row in rows if row['type'] == 'tool/call']
        tools = Counter(row['data']['name'] for row in calls)
        errors = [row for row in rows if row['type'] == 'tool/result'
                  and row['data']['message'].get('isError')]
        models = [row for row in rows if row['type'] == 'assistant/message'
                  and row['data']['message'].get('source', {}).get('kind') == 'model']
        for row in models:
            identifier = row['data']['message']['source']['replayState']['response']['responseId']
            model_sessions[identifier] = session
        session_reports[session] = {'model_calls': len(models), 'tools': dict(tools),
                                    'tool_errors': len(errors),
                                    'turns': len([row for row in rows if row['type'] == 'turn/end'])}
        if session == root_id:
            assert tools == Counter(glob=1, subagent=3, list_agents=1)
        else:
            assert tools == Counter(read=1, send_message=1)
            assert rows[0]['parentSession'] == root_id
        assert not errors
        assert rows[-1]['type'] == 'turn/end'
        assert rows[-1]['data']['reason']['kind'] == 'completed'
        for row in rows:
            if row['type'] in ('turn/start', 'turn/end', 'step/start', 'step/end',
                               'tool/call', 'subagent/catalog'):
                timeline.append({'session': session, **row})
    final = next(row['text'] for row in reversed(cli) if row['type'] == 'final')
    assert 'English Water Spaniel' in final
    task = json.loads((ROOT/'workspaces/hotpot-acceptance/task.json').read_text())
    assert 'answer' not in task
    wire = []
    start = json.loads((ROOT/'state/subagent-acceptance.json').read_text())['started']
    end = parent[-1]['time']/1000
    for path in sorted((ROOT/'artifacts/wire').iterdir()):
        info = json.loads((path/'request.json').read_text())
        if not start <= info['started_wall_time'] <= end:
            continue
        request = json.loads((path/'request.body').read_text())
        response = json.loads((path/'response.json').read_text())
        identifier = response_id(path/'response.body')
        session = model_sessions.get(identifier)
        title = any('Generate the session title from this JSON array' in str(m.get('content'))
                    for m in request.get('messages', []))
        assert session or title, path.name
        assert response.get('status') == 200, response
        assert not any(k.lower() in ('authorization', 'cookie') for k in info['headers'])
        shutil.copytree(path, OUT/'wire'/path.name, dirs_exist_ok=True)
        wire.append({'call_id': path.name, 'session': session,
                     'kind': 'session_title' if title else 'agent_step',
                     'response_id': identifier, 'model': request['model'],
                     'message_count': len(request['messages']), 'max_tokens': request.get('max_tokens'),
                     'reasoning_effort': request.get('reasoning_effort'), **response,
                     'started_wall_time': info['started_wall_time']})
    assert sum(row['kind'] == 'agent_step' for row in wire) == sum(
        report['model_calls'] for report in session_reports.values())
    write(OUT/'acceptance/calls.json', wire)
    write(OUT/'acceptance/timeline.json', sorted(timeline, key=lambda row: row['time']))
    dataset = Path('/home/Liangyijia_Hu/harness-engine/datasets/hotpot')
    gold = next(json.loads(line) for line in (dataset/'answers.jsonl').read_text().splitlines()
                if json.loads(line)['task_id'] == task['task_id'])
    contains_gold = gold['answer'].lower() in final.lower()
    write(OUT/'acceptance/report.json', {
        'kind': 'deployment_acceptance_only', 'root_session': root_id,
        'children': children, 'dataset_task_id': task['task_id'],
        'session_reports': session_reports, 'agent_model_calls': len(model_sessions),
        'auxiliary_title_calls': sum(row['kind'] == 'session_title' for row in wire),
        'total_recorded_api_requests': len(wire), 'all_recorded_requests_http_200': True,
        'final_answer_contains_hidden_gold': contains_gold,
        'quality_scope': 'One answer matches the gold entity; not a benchmark score. The 17th-century bound is indirect and not an explicit founding date.',
        'performance_claim': None, 'official_source_modified': False,
        'final_text': final})
    for name in ['subagent.jsonl', 'subagent-prompt.txt', 'basic.jsonl', 'tool-call-probe.json']:
        shutil.copy2(ROOT/'artifacts'/name, OUT/'acceptance'/name)
    for name in ['subagent.stderr', 'basic.stderr']:
        shutil.copy2(ROOT/'logs'/name, OUT/'acceptance'/name)
    smoke_reports = {}
    smoke_intervals = []
    for name in ['basic', 'shell']:
        rows = [json.loads(line) for line in (ROOT/'artifacts'/f'{name}.jsonl').read_text().splitlines()]
        smoke_session = next(row['sessionId'] for row in rows if row['type'] == 'session')
        smoke_events = native_events(smoke_session)
        smoke_intervals.append((smoke_events[0]['createdAt']/1000, smoke_events[-1]['time']/1000))
        final_smoke = next(row['text'].strip() for row in reversed(rows) if row['type'] == 'final')
        expected = 'DSH_SHELL_READY' if name == 'shell' else 'QWEN_DSH_READY'
        assert final_smoke == expected
        tool_calls = [row for row in rows if row['type'] == 'tool_call']
        if name == 'shell':
            assert len(tool_calls) == 1 and tool_calls[0]['tool'] == 'bash'
        smoke_reports[name] = {'session': smoke_session, 'expected': expected,
                               'final': final_smoke, 'tool_calls': tool_calls}
        for file in [f'{name}.jsonl', f'{name}-prompt.txt']:
            source = ROOT/'artifacts'/file
            if source.exists():
                shutil.copy2(source, OUT/'acceptance'/file)
        shutil.copy2(ROOT/'logs'/f'{name}.stderr', OUT/'acceptance'/f'{name}.stderr')
    write(OUT/'acceptance/smoke-report.json', smoke_reports)
    for path in sorted((ROOT/'artifacts/wire').iterdir()):
        info = json.loads((path/'request.json').read_text())
        if any(lo <= info['started_wall_time'] <= hi for lo, hi in smoke_intervals):
            shutil.copytree(path, OUT/'wire-smoke'/path.name, dirs_exist_ok=True)
    write(OUT/'acceptance/smoke-wire-note.json', {
        'scope': 'Only requests inside the basic and Bash smoke intervals; later research requests are excluded.',
        'basic_title_request': 'DSH closed while the auxiliary title request streamed; observer records ConnectionResetError. The basic agent conversation completed successfully.',
        'multiagent_report_excludes_smoke_requests': True})
    shutil.copytree(ROOT/'workspaces/hotpot-acceptance', OUT/'task', dirs_exist_ok=True)
    shutil.copy2(dataset/'manifest.json', OUT/'task/data-manifest.json')
    write(OUT/'acceptance/offline-gold.json', gold)
    for name in ['source.json', 'engine.json', 'subagent-acceptance.json', 'deployment.json']:
        shutil.copy2(ROOT/'state'/name, OUT/name)
    shutil.copy2(ROOT/'runtime/package.json', OUT/'package.json')
    shutil.copy2(ROOT/'runtime/package-lock.json', OUT/'package-lock.json')
    for name in ['model_revision.json', 'model_manifest.json', 'model_verification.json', 'env.json']:
        destination = OUT/'environment'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path('/home/Liangyijia_Hu/harness-engine/state')/name, destination)
    for name in ['start_engine.py', 'start_services.py', 'observe_api.py', 'qwen.patch.yml']:
        destination = OUT/'configuration'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, destination)
    # A self-contained compressed bundle retains complete prompts, SSE, native logs and input.
    archive = ROOT/'artifacts/deployment-20261029-raw.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(OUT, arcname='deployment-20261029')
    index = {'archive': archive.name, 'bytes': archive.stat().st_size,
             'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
             'generated_wall_time': time.time(), 'includes_web_login_token': False,
             'includes_complete_native_session_events': True,
             'includes_complete_multiagent_api_request_and_response_bodies': True}
    write(ROOT/'artifacts/deployment-20261029-index.json', index)
    print(json.dumps(index))
    print((OUT/'acceptance/report.json').read_text())


if __name__ == '__main__':
    main()
