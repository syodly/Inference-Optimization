"""Compare exact fixed-work tasks alone and mixed, with group trade-offs."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=Path('results/replays'))
    ap.add_argument('--out', type=Path, default=Path('results/v021-interference'))
    args = ap.parse_args()
    names = ['mixed-native-a', 'short-alone', 'long-alone', 'mixed-return18', 'mixed-return24',
             'mixed-size18', 'mixed-size24', 'mixed-session-return12', 'mixed-session-return18',
             'mixed-history200k', 'mixed-native-b']
    entries = []
    reference_fingerprints = json.loads((args.results/'v021-replay-mixed-native-a/workload_fingerprints.json').read_text(encoding='utf-8'))
    source_hashes = set()
    for name in names:
        directory = args.results/('v021-replay-'+name)
        s = json.loads((directory/'summary.json').read_text(encoding='utf-8'))
        config = json.loads((directory/'config.json').read_text(encoding='utf-8'))
        fingerprints = json.loads((directory/'workload_fingerprints.json').read_text(encoding='utf-8'))
        source_hashes.add(config['replay']['source_config_sha256'])
        a = s['replay_accounting']
        if not (s['trace_audit']['passed'] and s['engine_errors'] == s['root_errors'] == 0
                and a['source_calls'] == a['identical_input_prompts'] == a['quota_matches']
                and a['source_completion_tokens'] == a['live_completion_tokens']
                and all(v['messages_sha256'] == reference_fingerprints[k]['messages_sha256']
                        and v['usage']['completion_tokens'] == reference_fingerprints[k]['usage']['completion_tokens']
                        for k, v in fingerprints.items())):
            raise ValueError('Do not compare incompletely matched workload: '+name)
        entries.append({'run_id': s['run_id'], 'name': name, 'calls': s['model_calls'],
                        'mean': s['root_latency_seconds']['mean'], 'p95': s['root_latency_seconds']['p95'],
                        'completion_tokens': s['tokens']['completion_tokens'],
                        'preemptions': s['preemptions_delta'], 'groups': s['latency_by_dataset']})
    if len(source_hashes) != 1:
        raise ValueError('These rounds do not use one source trace')
    lookup = {r['name']: r for r in entries}
    interference = {}
    for group, alone in [('hotpot', 'short-alone'), ('longbench-v2', 'long-alone')]:
        standalone = lookup[alone]['groups'][group]['root_latency_seconds']['mean']
        mixed = [lookup[n]['groups'][group]['root_latency_seconds']['mean'] for n in ['mixed-native-a', 'mixed-native-b']]
        interference[group] = {'alone_mean_seconds': standalone, 'mixed_native_means_seconds': mixed,
                               'mixed_over_alone': [x/standalone for x in mixed]}
    lines = ['# v021 · 同一任务的混合干扰与强基线', '',
             '所有混合轮次均为同一160份输入和66,893个实际解码token；两组单独运行保持原任务到达索引。',
             '逐调用复核输入哈希、实际输出配额及完整依赖。回放冻结上游输出，不用于自主闭环质量评价。', '',
             '| 策略/轮次 | 全部平均/s | 短任务平均/s | 长任务平均/s | 全部P95/s | 抢占 |',
             '|---|---:|---:|---:|---:|---:|']
    for r in entries:
        values = [r['groups'].get(k, {}).get('root_latency_seconds', {}).get('mean') for k in ['hotpot', 'longbench-v2']]
        short, long = [f'{v:.2f}' if v is not None else '—' for v in values]
        lines.append(f"| {r['name']} | {r['mean']:.2f} | {short} | {long} | {r['p95']:.2f} | {r['preemptions']:.0f} |")
    lines += ['', '## 归因', '',
              '短任务单独34.89秒，混合原生138.43–140.50秒：同样请求存在约4倍任务干扰，痛点成立。长任务由170.90秒变为196.55–198.62秒。',
              '短输入优先的混合均值最低，但长任务195.32–202.62秒，弱于普通回流的182.20–182.30秒；不能把均值当作两组同时改善。',
              '历史预算137.58秒，普通回流24为138.17秒，差约0.43%，P95却是212.47对206.33秒。此轮不支持预算独立优于强调优排序。',
              '固定Session加回流18为142.42秒；窗口12提高命中但均值150.09、P95 235.42秒。缓存指标不能替代用户任务指标。',
              '原生重复给出批次内稳定性线索，但各策略仍只有少量轮次、同一任务集，尚不报告总体显著性。', '',
              '下一步集中检查独立请求共享引擎时的压力反馈增量、同信息后端强对照，以及不同来源前端是否需要协同；不继续围绕已被普通排序解释的差距堆机制。']
    args.out.with_suffix('.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    args.out.with_suffix('.json').write_text(json.dumps({'source_config_sha256': next(iter(source_hashes)),
        'fixed_work_verified': True, 'quality_evaluation': False, 'interference': interference,
        'runs': entries, 'notice': 'Matched-work diagnostic, not independent repetition inference.'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(interference, indent=2))


if __name__ == '__main__':
    main()
