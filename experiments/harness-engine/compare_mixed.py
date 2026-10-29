"""Compare long/short task groups without averaging unlike quality scores."""
import argparse
import json
from pathlib import Path


def compare(results, prefix, reference):
    reference_summary = json.loads((results / reference / 'summary.json').read_text(encoding='utf-8'))
    reference_config = json.loads((results / reference / 'config.json').read_text(encoding='utf-8'))
    rows = []
    for path in sorted(results.glob(prefix+'*/summary.json')):
        config = json.loads((path.parent / 'config.json').read_text(encoding='utf-8'))
        if config['split'] != 'evaluation' or config.get('replay'):
            continue
        summary = json.loads(path.read_text(encoding='utf-8'))
        groups = summary['quality_by_dataset']
        row = {'run_id': summary['run_id'], 'policy': config['policy'],
               'measured_prompts': config.get('measure_prompts', False),
               'same_root_tasks_as_reference': config['task_ids'] == reference_config['task_ids'],
               'trace_audit_passed': summary['trace_audit']['passed'],
               'mean_seconds': summary['root_latency_seconds']['mean'],
               'p95_seconds': summary['root_latency_seconds']['p95'],
               'model_calls': summary['model_calls'], 'expected_model_calls': summary['expected_model_calls'],
               'completion_tokens': summary['tokens']['completion_tokens'],
               'preemptions': summary['preemptions_delta'],
               'evidence_cache_fraction': summary['cache_by_stage']['evidence']['cached_fraction'],
               'prompt_measurement': summary.get('prompt_measurement'),
               'groups': groups,
               'history_claim_peak_tokens': summary['control_observations']['max_history_claimed_tokens'],
               'history_soft_target_overshoot_tokens': summary['control_observations'].get('max_history_soft_target_overshoot_tokens')}
        row['group_mean_change_percent'] = {
            k: (v['root_latency_seconds']['mean'] /
                reference_summary['quality_by_dataset'][k]['root_latency_seconds']['mean'] - 1) * 100
            for k, v in groups.items()}
        rows.append(row)
    system = ['# 混合长短上下文：'+prefix, '', '参考：`'+reference+'`。只纳入已完成评估轮次，校准另列。', '',
              '| 轮次 | 总体平均/s | 长文平均/s | 短文平均/s | 总体P95/s | 抢占 | evidence命中 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        g = r['groups']
        system.append(f"| {r['run_id']} | {r['mean_seconds']:.2f} | "
                      f"{g['longbench-v2']['root_latency_seconds']['mean']:.2f} | "
                      f"{g['hotpot']['root_latency_seconds']['mean']:.2f} | {r['p95_seconds']:.2f} | "
                      f"{r['preemptions']:.0f} | {r['evidence_cache_fraction']*100:.1f}% |")
    system += ['', '质量和真实工作量单列，不能用一个混合得分掩盖某一组变化。', '',
               '| 轮次 | 长文准确率 | 短文EM | 短文F1 | 长/短输出token | 模型调用 | 实际长度测量 |',
               '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        g, m = r['groups'], r['prompt_measurement']
        measurement = f"{m['checked_calls']}次，{m['mismatches']}不符" if m else '未添加额外测量'
        system.append(f"| {r['run_id']} | {g['longbench-v2']['em']:.3f} | {g['hotpot']['em']:.3f} | "
                      f"{g['hotpot']['f1']:.3f} | {g['longbench-v2']['completion_tokens']}/{g['hotpot']['completion_tokens']} | "
                      f"{r['model_calls']}/{r['expected_model_calls']} | {measurement} |")
    system += ['', '所有任务包含前端等待、实际模型、真实工具和父汇合。无额外测量的原生/回流策略作为净收益强对照。',
               '生成文本与工作量可能随批处理改变；纯系统归因另看冻结输入及解码配额的真实回放。',
               '单批中的任务相互干扰，不是独立系统重复；本表不报告推断置信区间，也不预设任何机制优于调优排序。']
    path = results / (prefix+'-comparison')
    path.with_suffix('.md').write_text('\n'.join(system)+'\n', encoding='utf-8')
    path.with_suffix('.json').write_text(json.dumps({'reference': reference, 'runs': rows,
        'scope': 'Exploratory complete closed-loop runs, group quality and workload reported separately; no independent batch CI.'},
        ensure_ascii=False, indent=2), encoding='utf-8')
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=Path('results'))
    ap.add_argument('--prefix', default='v017')
    ap.add_argument('--reference', default='v017-mixed-native16-unmeasured')
    args = ap.parse_args()
    rows = compare(args.results, args.prefix, args.reference)
    print('Compared complete evaluation rounds:', len(rows))
