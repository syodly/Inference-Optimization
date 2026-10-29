"""Plot audited real fixed-work comparisons; no answer-quality or CI claims."""
import argparse
import json
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=Path('results/replays'))
    ap.add_argument('--out', type=Path, default=Path('results/figures-v018'))
    args = ap.parse_args()
    names = ['v018-replay-native', 'v015-replay-session18',
             'v018-replay-return18-aging120', 'v018-replay-return12-aging120']
    labels = ['直接派发', '跨工具Session窗口18', '回流优先 · 调用上限18', '回流优先 · 调用上限12']
    rows = [json.loads((args.results / n / 'summary.json').read_text(encoding='utf-8')) for n in names]
    configs = [json.loads((args.results / n / 'config.json').read_text(encoding='utf-8')) for n in names]
    if len({c['replay']['source_config_sha256'] for c in configs}) != 1:
        raise ValueError('Compared runs must use the same frozen source trace')
    for r in rows:
        a = r['replay_accounting']
        if not (a['source_calls'] == a['identical_input_prompts'] == a['quota_matches'] == 80
                and a['live_completion_tokens'] == a['source_completion_tokens'] == 48930
                and r['trace_audit']['passed']):
            raise ValueError('Fixed-work accounting is incomplete: ' + r['run_id'])
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        plt.rcParams['font.family'] = FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.facecolor': '#f8faf6', 'figure.facecolor': 'white',
                         'axes.labelcolor': '#26382f', 'text.color': '#26382f', 'font.size': 11})
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 5.2), gridspec_kw={'width_ratios': [2.4, 1.4, 1.1]})
    y = list(range(4))
    mean = [r['root_latency_seconds']['mean'] for r in rows]
    p95 = [r['root_latency_seconds']['p95'] for r in rows]
    axes[0].barh([i-.18 for i in y], mean, height=.34, color='#17674f', label='平均任务耗时')
    axes[0].barh([i+.18 for i in y], p95, height=.34, color='#a4bfad', label='任务P95')
    for i, (a, b) in enumerate(zip(mean, p95)):
        axes[0].text(a+2, i-.18, f'{a:.2f}', va='center', fontsize=9)
        axes[0].text(b+2, i+.18, f'{b:.2f}', va='center', fontsize=9)
    axes[0].set_yticks(y, labels); axes[0].invert_yaxis(); axes[0].set_xlim(0, 252)
    axes[0].set_xlabel('完整任务耗时 / 秒')
    axes[0].legend(frameon=False, loc='lower left', bbox_to_anchor=(0,1.01), ncol=2, fontsize=9)
    cache = [r['cache_by_stage']['evidence']['cached_fraction'] * 100 for r in rows]
    preempt = [r['preemptions_delta'] for r in rows]
    for ax, values, color, title in [(axes[1], cache, '#326578', 'evidence输入命中 / %'),
                                      (axes[2], preempt, '#a56b40', '实际抢占次数')]:
        ax.barh(y, values, height=.6, color=color)
        for i, value in enumerate(values): ax.text(value+1, i, f'{value:.1f}', va='center', fontsize=10)
        ax.set_yticks(y, ['']*4); ax.invert_yaxis(); ax.set_xlabel(title)
        ax.set_xlim(0, max(values+[1])*1.35)
    for ax in axes: ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    fig.suptitle('加强普通回流排序后，窗口的独立均值优势尚未成立', fontsize=15, x=.56)
    fig.text(.04,.045, '同一真实引擎、同一来源trace：80份输入、48,930个实际解码token全部核对一致。\n'
             '回放冻结上游文本，仅用于系统归因；不验证自主闭环质量。每个设置一轮，无独立批次置信区间。',
             fontsize=10, color='#62746a')
    fig.tight_layout(rect=[0,.14,1,.92])
    args.out.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out/'strong-baselines.png', dpi=170)
    fig.savefig(args.out/'strong-baselines.svg')
    svg = args.out/'strong-baselines.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
    (args.out/'strong-baselines.json').write_text(json.dumps({
        'run_ids': names, 'summaries': rows, 'source_config_sha256': configs[0]['replay']['source_config_sha256'],
        'notice': 'Actual fixed-work diagnostic replays; no live quality evaluation or inferential confidence intervals.'
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(args.out/'strong-baselines.png')


if __name__ == '__main__':
    main()
