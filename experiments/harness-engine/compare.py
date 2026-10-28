"""Compare complete batches; paired roots are diagnostics, not independent batch repeats."""
import argparse
import json
from pathlib import Path

from analyze import read


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=Path('results'))
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--reference', required=True)
    args = ap.parse_args()
    reference = json.loads((args.results / args.reference / 'summary.json').read_text())
    reference_fingerprints = json.loads((args.results / args.reference / 'workload_fingerprints.json').read_text())
    comparisons = []
    for path in sorted(args.results.glob(args.prefix + '*/summary.json')):
        s = json.loads(path.read_text())
        f = json.loads((path.parent / 'workload_fingerprints.json').read_text())
        shared = set(f) & set(reference_fingerprints)
        same_input = sum(f[k]['messages_sha256'] == reference_fingerprints[k]['messages_sha256'] for k in shared)
        same_output = sum(f[k].get('output_sha256') == reference_fingerprints[k].get('output_sha256') for k in shared)
        stages = {}
        for stage in ['query', 'evidence', 'synthesis']:
            keys = [k for k in shared if f[k]['stage'] == stage]
            stages[stage] = {'calls': len(keys),
                             'same_input': sum(f[k]['messages_sha256'] == reference_fingerprints[k]['messages_sha256'] for k in keys),
                             'same_output': sum(f[k].get('output_sha256') == reference_fingerprints[k].get('output_sha256') for k in keys)}
        comparisons.append({'run_id': s['run_id'], 'policy': s['policy'], 'cap': s['cap'],
                            'mean_seconds': s['root_latency_seconds']['mean'],
                            'p95_seconds': s['root_latency_seconds']['p95'],
                            'makespan_seconds': s['batch_makespan_seconds'],
                            'mean_change_percent': (s['root_latency_seconds']['mean'] /
                                                    reference['root_latency_seconds']['mean'] - 1) * 100,
                            'f1': s['quality']['f1'], 'calls': s['model_calls'],
                            'completion_tokens': s['tokens']['completion_tokens'],
                            'engine_wait_max': s['engine']['waiting'].get('max'),
                            'kv_max': s['engine']['kv_usage'].get('max'), 'preemptions': s['preemptions_delta'],
                            'trace_audit_passed': s['trace_audit']['passed'],
                            'same_call_ids': len(shared), 'same_prompt_count': same_input,
                            'same_output_count': same_output, 'stage_fingerprint_comparison': stages})
    out = args.results / (args.prefix + '-comparison.json')
    out.write_text(json.dumps({'reference': args.reference, 'runs': comparisons,
                               'uncertainty': 'One shared batch contains correlated roots; batch repeats are needed for inferential CI.'}, indent=2))
    lines = ['# ' + args.prefix + ' 实验对照', '', f'参考轮次：`{args.reference}`。', '',
             '| 轮次 | 平均任务耗时/s | P95/s | 批完成/s | F1 | 输出 token | 后端等待峰值 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for s in comparisons:
        lines.append(f"| {s['run_id']} | {s['mean_seconds']:.2f} | {s['p95_seconds']:.2f} | "
                     f"{s['makespan_seconds']:.2f} | {s['f1']:.3f} | {s['completion_tokens']} | {s['engine_wait_max']} |")
    lines += ['', '每轮为完整任务闭环；包含前端等待、模型和工具时间。单批内任务相互干扰，不能把任务数当作独立重复次数。',
              '相同调用图不保证批处理下 prompt 和输出逐字相同；JSON 文件逐阶段列出相同输入与输出数量。',
              '速度差异须结合质量、token、截断、失败和系统漂移判断。']
    out.with_suffix('.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
