"""Export measured exploratory comparisons; no inferred confidence intervals."""
import argparse
import json
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', type=Path, default=Path('results'))
    ap.add_argument('--reference', required=True)
    ap.add_argument('--prefix', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    paths = [args.results / args.reference / 'summary.json', *sorted(args.results.glob(args.prefix + '*/summary.json'))]
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in paths]
    ids = [r['run_id'] for r in rows]
    args.out.mkdir(parents=True, exist_ok=True)
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    if font_path.exists():
        plt.rcParams['font.family'] = FontProperties(fname=str(font_path)).get_name()
    plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.facecolor': '#f8faf6', 'figure.facecolor': '#ffffff',
                         'axes.labelcolor': '#26382f', 'text.color': '#26382f', 'font.size': 10})
    labels = [r['run_id'].replace(args.prefix + '-', '').replace('v012-verified-long-', 'reference-') for r in rows]
    friendly = {'reference-native8': '直接派发\n首次', 'backend-priority-natural': '后端\n阶段优先',
                'fixed12-natural': '调用上限\n12', 'fixed18-natural': '调用上限\n18',
                'native-repeat': '直接派发\n重复', 'return12-natural': '回流优先\n调用上限12',
                'session12-natural': 'Session窗口\n12', 'session18-natural': 'Session窗口\n18'}
    x = list(range(len(rows)))
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1, 1]})
    mean = [r['root_latency_seconds']['mean'] for r in rows]
    p95 = [r['root_latency_seconds']['p95'] for r in rows]
    axes[0].bar([i-.2 for i in x], mean, width=.4, color='#17674f', label='平均任务耗时')
    axes[0].bar([i+.2 for i in x], p95, width=.4, color='#99bba5', label='任务 P95')
    axes[0].set_ylabel('用户提交 → 最终回答 / 秒'); axes[0].legend(frameon=False)
    for i, v in enumerate(mean):axes[0].text(i-.2,v+2,f'{v:.1f}',ha='center',fontsize=9)
    fractions = [r.get('cache_by_stage', {}).get('evidence', {}).get('cached_fraction') for r in rows]
    cache = [100*v if v is not None else float('nan') for v in fractions]
    axes[1].bar(x, cache, color='#326578'); axes[1].set_ylabel('证据续写输入命中 / %'); axes[1].set_ylim(0,100)
    preempt = [r['preemptions_delta'] for r in rows]
    axes[2].bar(x, preempt, color='#a56b40');axes[2].set_ylabel('抢占次数');axes[2].set_ylim(0,max(preempt+[1])*1.3)
    axes[2].set_xticks(x, [friendly.get(label,label) for label in labels], rotation=0, ha='center')
    for ax in axes:ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('真实长文引用核验工作图：相同八题、每题十次必做模型调用',fontsize=15)
    foot = '；'.join(f"{labels[i]}: {r['quality']['em']*r['expected_roots']:.0f}/{r['expected_roots']}, {r['tokens']['completion_tokens']} 输出 token" for i,r in enumerate(rows))
    import textwrap
    fig.text(.07,.015,'每个柱是一轮共享引擎实验，没有独立批次置信区间。答案正确率、输出工作量也需同时核对。\n'+
             '\n'.join(textwrap.wrap(foot,115)),fontsize=8,va='bottom')
    fig.tight_layout(rect=[0,.12,1,.96])
    fig.savefig(args.out/'measured-rounds.png',dpi=170)
    fig.savefig(args.out/'measured-rounds.svg')
    (args.out/'measured-rounds.json').write_text(json.dumps({'round_ids':ids,'source_files':[str(p) for p in paths],
        'notice':'Exploratory single-batch comparisons; no independent repeat CI.','summaries':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(args.out/'measured-rounds.png')


if __name__=='__main__':main()
