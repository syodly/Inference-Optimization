"""Plot exact-work group interference; export the data beside PNG and SVG."""
import json
from pathlib import Path


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    data = json.loads(Path('results/v021-interference.json').read_text(encoding='utf-8'))
    if not data['fixed_work_verified']:
        raise ValueError('Run the per-call work comparison before plotting')
    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        plt.rcParams['font.family'] = FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.facecolor': '#f7faf5', 'text.color': '#26382f', 'font.size': 11})
    lookup = {r['name']: r for r in data['runs']}
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.1), gridspec_kw={'width_ratios': [1, 1.6]})
    labels = ['短任务 · 单独', '短任务 · 混合', '长任务 · 单独', '长任务 · 混合']
    keys = [('short-alone', 'hotpot'), ('mixed-native-a', 'hotpot'),
            ('long-alone', 'longbench-v2'), ('mixed-native-a', 'longbench-v2')]
    vals = [lookup[n]['groups'][g]['root_latency_seconds']['mean'] for n, g in keys]
    axes[0].barh(range(4), vals, color=['#a4bfad', '#17674f', '#b7cbd2', '#326578'], height=.57)
    for i, v in enumerate(vals): axes[0].text(v+2, i, f'{v:.2f}', va='center', fontsize=10)
    axes[0].set_yticks(range(4), labels); axes[0].invert_yaxis(); axes[0].set_xlim(0, 235)
    axes[0].set_title('移除另一组工作，干扰明显下降', fontsize=13, pad=40)
    names = ['mixed-native-a', 'mixed-return24', 'mixed-size18', 'mixed-session-return18', 'mixed-history200k']
    labels = ['直接派发', '普通回流优先24', '短输入优先18', 'Session窗口18＋回流', '历史预算200k']
    for offset, group, color, label in [(-.17, 'hotpot', '#17674f', '短任务'), (.17, 'longbench-v2', '#326578', '长任务')]:
        values = [lookup[n]['groups'][group]['root_latency_seconds']['mean'] for n in names]
        axes[1].barh([i+offset for i in range(len(names))], values, height=.3, color=color, label=label)
        for i, v in enumerate(values): axes[1].text(v+2, i+offset, f'{v:.1f}', va='center', fontsize=9)
    axes[1].set_yticks(range(len(names)), labels); axes[1].invert_yaxis(); axes[1].set_xlim(0, 241)
    axes[1].set_title('历史预算暂未超越普通回流排序', fontsize=13, pad=40)
    axes[1].legend(frameon=False, ncol=2, loc='lower left', bbox_to_anchor=(0, 1.01))
    for ax in axes:
        ax.set_xlabel('从任务提交开始计算的平均耗时 / 秒'); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    fig.suptitle('固定输入和生成量：混合干扰存在，复杂机制的增量仍待证明', fontsize=15, y=.99)
    fig.text(.035, .04, '真实Qwen3.8-27B双卡推理；混合轮次160份输入、66,893个解码token。单独运行保留原到达索引。\n'
             '上游文本冻结，仅用于系统归因，不报告闭环答案质量。各策略少量轮次，未作独立批次置信区间。', fontsize=10, color='#62746a')
    fig.tight_layout(rect=[0,.14,1,.93])
    out = Path('results/figures-v021'); out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out/'mixed-interference.png', dpi=170)
    fig.savefig(out/'mixed-interference.svg')
    svg = out/'mixed-interference.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
    (out/'mixed-interference.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out/'mixed-interference.png')


if __name__ == '__main__':
    main()
