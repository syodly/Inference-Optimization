"""Compare frontend and same-information engine-side admission sequentially."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from analyze import read


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', type=Path)
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    state_path = Path('state')/('batch-'+spec['batch_id']+'.json')
    completed = []
    for entry in spec['runs']:
        if Path('state/STOP').exists():
            state_path.write_text(json.dumps({'status': 'operator_stop', 'completed': completed})); return
        run_id, placement, policy = entry['run_id'], entry['placement'], entry['policy']
        state = {'batch_id': spec['batch_id'], 'status': 'running', 'current': run_id,
                 'started': time.time(), 'completed': completed}
        state_path.write_text(json.dumps(state, indent=2))
        proxy = None
        broker_directory = Path('runs')/(run_id+'-broker')
        try:
            if placement == 'broker':
                # The port is specific to this project; never attach to an existing process.
                import socket
                probe = socket.socket(); probe.bind(('127.0.0.1', 18082)); probe.close()
                with (Path('logs')/(run_id+'-broker.log')).open('w') as log:
                    proxy = subprocess.Popen([sys.executable, 'broker.py', '--out', str(broker_directory),
                                              '--policy', policy, '--cap', '24'], stdout=log, stderr=subprocess.STDOUT)
                for _ in range(60):
                    if proxy.poll() is not None: raise RuntimeError('Broker exited during startup')
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:18082/harness/status', timeout=1) as response:
                            status = json.load(response)
                        break
                    except OSError:
                        time.sleep(.25)
                else:
                    raise RuntimeError('Broker did not start; inspect its log')
            command = [sys.executable, 'replay.py', '--trace', spec['trace'], '--out', 'runs/'+run_id,
                       '--policy', 'native' if placement == 'broker' else policy,
                       '--cap', '24', '--starvation-seconds', '120']
            if placement == 'broker': command += ['--url', 'http://127.0.0.1:18082']
            elif policy in ['size_return', 'history_budget', 'history_pressure']: command += ['--measure-prompts']
            with (Path('logs')/(run_id+'.log')).open('w') as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode: raise RuntimeError('Replay failed; preserve '+run_id)
            run = Path('runs')/run_id
            summary = json.loads((run/'summary.json').read_text())
            config = json.loads((run/'config.json').read_text())
            accounting = summary['replay_accounting']
            if not (summary['trace_audit']['passed'] and summary['engine_errors'] == summary['root_errors'] == 0
                    and accounting['source_calls'] == accounting['identical_input_prompts'] == accounting['quota_matches'] == summary['expected_model_calls']
                    and accounting['live_completion_tokens'] == accounting['source_completion_tokens']):
                raise RuntimeError('Incomplete fixed-work replay; preserve the failed round')
            checks = None
            if placement == 'broker':
                with urllib.request.urlopen('http://127.0.0.1:18082/harness/status') as response:
                    status = json.load(response)
                incoming = read(run/'requests.jsonl')
                received = read(broker_directory/'requests.jsonl')
                sent = read(broker_directory/'responses.jsonl')
                by_id = {r['call_id']: r for r in received}
                client_responses = {r['call_id']: r for r in read(run/'responses.jsonl')}
                events = read(broker_directory/'events.jsonl')
                releases = [e for e in events if e['event'] == 'frontend_release']
                claims, ledger_ok = {}, True
                for event in events:
                    if event['event'] in ['history_claim_opened', 'history_claim_updated']:
                        claims[event['node_id']] = event['history_tokens']
                    elif event['event'] == 'session_released':
                        ledger_ok &= claims.pop(event['node_id'], None) == event.get('released_history_tokens')
                    else:
                        continue
                    ledger_ok &= sum(claims.values()) == event['total_claimed']
                measurements = [e for e in events if e['event'] == 'prompt_measurement_check']
                checks = {'received_calls': len(received), 'completed_calls': len(sent),
                          'identical_forwarded_payloads': sum(r['payload'] == by_id.get(r['call_id'], {}).get('payload') for r in incoming),
                          'broker_errors': sum(bool(r.get('error')) or not r.get('completed') for r in sent),
                          'unique_ids': len(by_id) == len(received) == len({r['call_id'] for r in sent}),
                          'usage_matches_client': all(r['usage'] == client_responses[r['call_id']]['usage'] for r in sent),
                          'admissions_within_cap': len(releases) == len(incoming) and all(e['inflight_calls'] <= e['target'] for e in releases),
                          'history_ledger_consistent': ledger_ok and not claims,
                          'prompt_measurements_match': all(e['matches'] for e in measurements)
                              and (len(measurements) == len(incoming) if policy in ['history_budget', 'history_pressure', 'size_return'] else True),
                          'final_status': status, 'trace_directory': str(broker_directory)}
                if not (len(incoming) == len(received) == len(sent) == checks['identical_forwarded_payloads']
                        and checks['broker_errors'] == status['running'] == status['pending'] == status['sessions'] == status['claimed_history_tokens'] == 0
                        and all(checks[k] for k in ['unique_ids', 'usage_matches_client', 'admissions_within_cap',
                                                   'history_ledger_consistent', 'prompt_measurements_match'])):
                    raise RuntimeError('Broker accounting did not close cleanly')
            info = {'placement': placement, 'effective_policy': policy, 'broker_accounting': checks,
                    'scope': 'Equivalent request/Session admission controls with the same current metadata; broker is not the native vLLM token scheduler.',
                    'frontend_ttft_notice': 'API first-token time includes gateway admission when using the broker. Underlying engine queue metrics remain separate.'}
            config['placement_comparison'] = info; summary['placement_comparison'] = info
            (run/'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
            (run/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
            destination = Path('results/replays')/run_id
            for name, value in [('config.json', config), ('summary.json', summary)]:
                (destination/name).write_text(json.dumps(value, indent=2), encoding='utf-8')
            record = (f"\n\n本轮放置对照：{placement}，有效策略{policy}。相同阶段、根任务及Session标识来自现有请求ID，"
                      '工具和依赖仍由Harness实际执行。引擎侧代理具有相同请求准入、Session跨工具计账和回流排序权限，'
                      '但没有修改vLLM逐token调度器；不把阶段优先级冒充完整同信息对照。原始API参数逐字转发，'
                      '代理等待包括在根任务和API首token时间中，后台引擎队列另行报告。此处只检验选定控制动作的放置及信息增量，不宣称前端具有不可替代优势。\n')
            for path in [run/'research_record.md', destination/'research_record.md', Path('RESEARCH_LOG.md')]:
                with path.open('a', encoding='utf-8') as f: f.write(record)
            completed.append({'run_id': run_id, 'summary': summary, 'finished': time.time()})
            state.update(status='between_rounds', completed=completed)
            state_path.write_text(json.dumps(state, indent=2))
            print('DONE', run_id, summary['root_latency_seconds'], flush=True)
        except Exception as exc:
            state.update(status='failed', error=repr(exc), finished=time.time())
            state_path.write_text(json.dumps(state, indent=2)); raise
        finally:
            if proxy is not None and proxy.poll() is None:
                proxy.terminate(); proxy.wait(timeout=15)
    state_path.write_text(json.dumps({'batch_id': spec['batch_id'], 'status': 'complete',
                                     'completed': completed, 'finished': time.time()}, indent=2))


if __name__ == '__main__':
    main()
