"""Offline scoring and durable/native/wire audit of a completed DSH round."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import string
import subprocess
import tarfile
import shutil

ROOT = Path('/home/Liangyijia_Hu/dsh-lab')
OLD = Path('/home/Liangyijia_Hu/harness-engine')
NODE = ROOT/'toolchain/node-v24.22.2-linux-x64/bin/node'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def normalized(text):
    text = ''.join(character for character in text.lower() if character not in string.punctuation)
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text).split())


def score(predicted, gold):
    predicted, gold = normalized(predicted), normalized(gold)
    exact = float(predicted == gold)
    if (predicted in ['yes', 'no', 'noanswer'] or gold in ['yes', 'no', 'noanswer']) and not exact:
        return 0., 0.
    overlap = sum((Counter(predicted.split()) & Counter(gold.split())).values())
    f1 = 2*overlap/(len(predicted.split())+len(gold.split())) if overlap else exact
    return exact, f1


def stats(values):
    values = sorted(values)
    if not values:
        return {'n': 0, 'mean': None, 'p95': None, 'max': None}
    position = (len(values)-1)*.95
    lower = int(position)
    upper = min(lower+1, len(values)-1)
    return {'n': len(values), 'mean': statistics.mean(values),
            'p95': values[lower]+(values[upper]-values[lower])*(position-lower), 'max': values[-1]}


def response(path):
    identifier, usage, finishes, text = None, {}, [], ''
    for line in path.read_text().splitlines():
        if not line.startswith('data: {'):
            continue
        chunk = json.loads(line[6:])
        identifier = chunk.get('id') or identifier
        usage = chunk.get('usage') or usage
        for choice in chunk.get('choices', []):
            if choice.get('finish_reason'):
                finishes.append(choice['finish_reason'])
            text += choice.get('delta', {}).get('content') or ''
    return identifier, usage, finishes, text


def analyze(directory):
    shutil.copy2(Path(__file__), directory/'sources/e1_analyze.py')
    config = json.loads((directory/'config.json').read_text())
    completed = json.loads((directory/'completion.json').read_text())
    gold = {row['task_id']: row for row in rows(OLD/'datasets/hotpot/answers.jsonl')}
    root_finishes = {row['task_id']: row for row in rows(directory/'roots.jsonl') if row['event'] == 'task_finished'}
    scored, audits, response_sessions = [], [], {}
    native_directory = directory/'native-events'
    native_directory.mkdir(exist_ok=True)
    for task_directory in sorted((directory/'tasks').iterdir()):
        task = json.loads((task_directory/'task.json').read_text())
        identifier = task['task_id']
        cli = rows(task_directory/'cli.jsonl')
        root_id = next((row['sessionId'] for row in cli if row['type'] == 'session'), None)
        final = next((row['text'] for row in reversed(cli) if row['type'] == 'final'), '')
        parse_error, value = None, {}
        try:
            value = json.loads(final.strip())
            assert isinstance(value['answer'], str)
        except (ValueError, KeyError, AssertionError) as error:
            parse_error = repr(error)
        em, f1 = score(value.get('answer', ''), gold[identifier]['answer'])
        documents = {document['doc_id']: document for document in task['documents']}
        predicted_titles = {documents[doc_id]['title'] for doc_id in value.get('supporting_doc_ids', []) if doc_id in documents}
        expected_titles = set(gold[identifier]['supporting_facts']['title'])
        support = len(predicted_titles & expected_titles)/len(expected_titles)
        scored.append({'task_id': identifier, 'question': task['question'], 'answer': value.get('answer'),
                       'gold': gold[identifier]['answer'], 'em': em, 'f1': f1, 'support_title_recall': support,
                       'parse_error': parse_error, 'final_text': final, **root_finishes[identifier]})
        logs = list(task_directory.rglob('session.v4.jsonl.zstd'))
        agent_reports = []
        for path in logs:
            command = "const fs=require('node:fs'),z=require('node:zlib');process.stdout.write(z.zstdDecompressSync(fs.readFileSync(process.argv[1])).toString())"
            raw = subprocess.check_output([str(NODE), '-e', command, str(path)])
            events = [json.loads(line) for line in raw.splitlines() if line.strip()]
            session = events[0]['id']
            (native_directory/f'{session}.jsonl').write_bytes(raw)
            tool_calls = [row for row in events if row['type'] == 'tool/call']
            models = [row for row in events if row['type'] == 'assistant/message'
                      and row['data']['message'].get('source', {}).get('kind') == 'model']
            for row in models:
                message = row['data']['message']
                response_id = message['source']['replayState']['response']['responseId']
                response_sessions[response_id] = {'task_id': identifier, 'session_id': session}
            tool_errors = [row for row in events if row['type'] == 'tool/result'
                           and row['data']['message'].get('isError')]
            tools = Counter(row['data']['name'] for row in tool_calls)
            finished = events[-1]['type'] == 'turn/end' and events[-1]['data']['reason']['kind'] == 'completed'
            expected_tools = Counter(research_workflow=1) if session == root_id else Counter(bench_search=1)
            branches = [json.loads(row['data']['arguments'])['branch'] for row in tool_calls
                        if row['data']['name'] == 'bench_search']
            agent_reports.append({'session_id': session, 'role': 'parent' if session == root_id else 'child',
                                  'model_calls': len(models), 'tools': dict(tools), 'tool_errors': len(tool_errors),
                                  'finished': finished, 'branches': branches,
                                  'valid': tools == expected_tools and len(models) == 2 and not tool_errors and finished})
        valid = (len(agent_reports) == 4 and all(row['valid'] for row in agent_reports)
                 and sorted(branch for row in agent_reports for branch in row['branches']) == [0, 1, 2]
                 and root_finishes[identifier]['exit_code'] == 0 and not parse_error)
        audits.append({'task_id': identifier, 'root_session': root_id, 'agents': agent_reports, 'valid': valid})
    wire_directory = directory/'wire'
    wire_directory.mkdir(exist_ok=True)
    wire, wire_errors = [], []
    for path in sorted((ROOT/'artifacts/wire').iterdir()):
        request_info = json.loads((path/'request.json').read_text())
        if not (completed['started_wall_time'] <= request_info['started_wall_time'] <= completed['finished_wall_time']):
            continue
        if not (path/'response.json').exists():
            wire_errors.append({'call_id': path.name, 'error': 'missing response metadata'})
            continue
        response_id, usage, finishes, _text = response(path/'response.body')
        if response_id not in response_sessions:
            wire_errors.append({'call_id': path.name, 'error': 'not mapped to native Agent session', 'response_id': response_id})
            continue
        shutil.copytree(path, wire_directory/path.name, dirs_exist_ok=True)
        metadata = json.loads((path/'response.json').read_text())
        body = json.loads((path/'request.body').read_text())
        wire.append({'call_id': path.name, 'response_id': response_id, **response_sessions[response_id],
                     'usage': usage, 'finishes': finishes, 'max_tokens': body.get('max_tokens'),
                     'temperature': body.get('temperature'), 'reasoning_effort': body.get('reasoning_effort'),
                     'status': metadata.get('status'), 'error': metadata.get('error')})
    metrics = rows(directory/'metrics.jsonl')
    dispatch = [row for row in rows(directory/'dispatch.jsonl') if row['event'] == 'admit']
    def generated_total(name):
        values = []
        for line in (directory/name).read_text().splitlines():
            match = re.match(r'vllm:generation_tokens_total(?:\{[^}]*\})?\s+([-+\d.eE]+)$', line)
            if match:
                values.append(float(match[1]))
        return sum(values) if values else None
    before, after = [generated_total(name) for name in ['metrics-start.prom', 'metrics-end.prom']]
    summary = {'run_id': directory.name, 'policy': config['policy'], 'cap': config['cap'],
               'tasks': len(scored), 'completed_tasks': len(root_finishes),
               'task_duration_seconds': stats([row['duration_seconds'] for row in scored]),
               'round_duration_seconds': completed['duration_seconds'],
               'quality': {'em': statistics.mean(row['em'] for row in scored),
                           'f1': statistics.mean(row['f1'] for row in scored),
                           'support_title_recall': statistics.mean(row['support_title_recall'] for row in scored)},
               'agents': sum(len(row['agents']) for row in audits), 'agent_model_calls': len(response_sessions),
               'expected_agent_model_calls': config['expected_agent_model_calls'], 'wire_calls': len(wire),
               'bm25_calls': len(rows(directory/'tools.jsonl')),
               'decoded_tokens': sum(row['usage'].get('completion_tokens', 0) for row in wire),
               'engine_generation_tokens_delta': after-before if None not in [before, after] else None,
               'prompt_tokens': sum(row['usage'].get('prompt_tokens', 0) for row in wire),
               'length_finishes': sum('length' in row['finishes'] for row in wire),
               'max_engine_waiting': max(row['waiting'] for row in metrics),
               'max_engine_running': max(row['running'] for row in metrics),
               'max_kv_usage': max(row['kv_usage'] for row in metrics),
               'preemptions': metrics[-1].get('preemptions', 0)-metrics[0].get('preemptions', 0),
               'frontend_wait_seconds': stats([row['frontend_wait'] for row in dispatch]),
               'feedback_reduced_admissions': sum(row['target'] < config['cap'] for row in dispatch) if config['policy'] == 'pressure' else 0,
               'runtime_errors': rows(directory/'errors.jsonl'), 'wire_errors': wire_errors,
               'native_workflow_audit_pass': all(row['valid'] for row in audits),
               'all_wire_http_200': all(row['status'] == 200 and not row['error'] for row in wire),
               'actual_request_configuration_consistent': all(
                   (row['max_tokens'], row['temperature'], row['reasoning_effort']) == (2048, 0, 'low')
                   for row in wire),
               'one_independent_round_only': True}
    summary['audit_pass'] = (summary['native_workflow_audit_pass'] and summary['all_wire_http_200']
                             and summary['actual_request_configuration_consistent']
                             and not summary['runtime_errors'] and not wire_errors
                             and len(wire) == config['expected_agent_model_calls']
                             and summary['bm25_calls'] == config['expected_bm25_calls']
                             and summary['engine_generation_tokens_delta'] == summary['decoded_tokens']
                             and completed['remaining_permits'] == completed['queued_permits'] == 0)
    dump(directory/'summary.json', summary)
    dump(directory/'native-audit.json', audits)
    dump(directory/'scored.json', scored)
    dump(directory/'wire-index.json', wire)
    archive = directory.parent/(directory.name+'-raw.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        for name in ['config.json', 'completion.json', 'roots.jsonl', 'events.jsonl', 'dispatch.jsonl',
                     'metrics.jsonl', 'metrics-start.prom', 'metrics-end.prom', 'tools.jsonl', 'summary.json',
                     'native-audit.json', 'scored.json', 'wire-index.json', 'sources', 'native-events', 'wire']:
            tar.add(directory/name, arcname=directory.name+'/'+name)
        for work in (directory/'tasks').iterdir():
            for name in ['task.json', 'prompt.txt', 'cli.jsonl', 'native-plugin.jsonl', 'stderr.log']:
                tar.add(work/name, arcname=directory.name+'/tasks/'+work.name+'/'+name)
    dump(directory/'archive-index.json', {'archive': archive.name, 'bytes': archive.stat().st_size,
                                        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                                        'all_api_requests_responses_included': True,
                                        'all_native_session_events_included': True})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == '__main__':
    import sys
    result = analyze(ROOT/'runs'/sys.argv[1])
    if not result['audit_pass']:
        raise SystemExit('Native DSH round audit failed; evidence retained')
