"""Sequential short experiment rounds with durable state and per-round Chinese records."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from analyze import analyze
from audit import audit
from export_run import export
from history_audit import analyze_history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec', type=Path)
    args = ap.parse_args()
    specification = json.loads(args.spec.read_text(encoding='utf-8'))
    root = Path(__file__).resolve().parent
    os.chdir(root)
    completed = []
    state_path = root / 'state' / f"batch-{specification['batch_id']}.json"
    for entry in specification['runs']:
        if (root / 'state/STOP').exists():
            print('Operator STOP file detected; leaving subsequent rounds unstarted.', flush=True)
            break
        run_id = entry['run_id']
        command = [sys.executable, 'run.py', '--out', 'runs/' + run_id,
                   *specification.get('base_args', []), *entry['args']]
        state = {'batch_id': specification['batch_id'], 'current': run_id, 'command': command,
                 'started': time.time(), 'completed': completed, 'status': 'running'}
        state_path.write_text(json.dumps(state, indent=2))
        print('START', run_id, flush=True)
        log_path = root / 'logs' / (run_id + '.log')
        with log_path.open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            state.update(status='failed', returncode=result.returncode, finished=time.time())
            state_path.write_text(json.dumps(state, indent=2))
            print(log_path.read_text()[-5000:], flush=True)
            raise RuntimeError('Round execution failed: ' + run_id)
        run = root / 'runs' / run_id
        (run / 'batch_entry.json').write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding='utf-8')
        config = json.loads((run / 'config.json').read_text())
        task_path = root / config['tasks']
        summary = analyze(run, task_path.parent / 'answers.jsonl', task_path)
        summary['trace_audit'] = audit(run)
        if config['workflow'] == 'verified':
            history = analyze_history(run)
            summary['history_return_audit'] = {k: v for k, v in history.items() if k != 'records'}
        (run / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        latency = summary['root_latency_seconds']
        record = (
            f"\n\n## {run_id} · {entry['purpose']}\n\n"
            f"本轮使用固定 Qwen3.8-27B BF16 双卡引擎，选择 {config['split']} 集 {config['count']} 个任务，"
            f"采用 {config['workflow']} 流程、{config['policy']} 派发策略，在途上限参数 {config['cap']}，"
            f"检索配置为 {config['tool_profile']}，来源验证附加延迟 {config.get('verify_delay', 0)}"
            f"±{config.get('verify_jitter', 0)} 秒。完成 {summary['completed_root_records']} 个任务记录，"
            f"实际模型调用 {summary['model_calls']}/{summary['expected_model_calls']}，"
            f"回答 EM={summary['quality']['em']:.3f}、F1={summary['quality']['f1']:.3f}，"
            f"整任务平均耗时 {latency.get('mean', float('nan')):.2f} 秒、P95={latency.get('p95', float('nan')):.2f} 秒。"
            f"模型错误 {summary['engine_errors']}、任务错误 {summary['root_errors']}、JSON 错误 {summary['parse_errors']}，"
            f"长度截断 {summary['length_finishes']} 次，输出 token 共 {summary['tokens']['completion_tokens']}。"
            f"{entry['interpretation']}"
            f"此轮完整配置、实际 prompt、响应、工具结果和引擎采样保存在远端 runs/{run_id}；"
            f"统计来自离线评分，控制器未读取隐藏答案。此处只报告本轮观测，比较结论须核对其他轮次、"
            f"重复顺序和实际工作量，不能由单个数值宣称机制有效。\n")
        if summary.get('quality_by_dataset'):
            grouped = summary['quality_by_dataset']
            record += ('\n本轮混合指标不能当作同一种质量得分；分组结果：' +
                       '；'.join(f"{name}：{g['expected_roots']}题，EM={g['em']:.3f}，F1={g['f1']:.3f}，"
                                f"平均{g['root_latency_seconds'].get('mean', float('nan')):.2f}秒"
                                for name, g in grouped.items()) + '。\n')
        with (root / 'RESEARCH_LOG.md').open('a', encoding='utf-8') as log:
            log.write(record)
        (run / 'research_record.md').write_text(record, encoding='utf-8')
        export(run, root)
        completed.append({'run_id': run_id, 'summary': summary, 'finished': time.time()})
        if not summary['trace_audit']['passed']:
            state.update(completed=completed, status='invalid_trace', finished=time.time())
            state_path.write_text(json.dumps(state, indent=2))
            raise RuntimeError('Trace accounting failed; retain artifacts and repair: ' + run_id)
        state.update(completed=completed, status='between_rounds', finished=time.time())
        state_path.write_text(json.dumps(state, indent=2))
        print('DONE', json.dumps(summary, ensure_ascii=False), flush=True)
    state_path.write_text(json.dumps({'batch_id': specification['batch_id'], 'completed': completed,
                                      'status': 'complete', 'finished': time.time()}, indent=2))


if __name__ == '__main__':
    main()
