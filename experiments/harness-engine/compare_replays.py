"""Summarize fixed-work diagnostic runs separately from live quality experiments."""
import argparse
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--results',type=Path,default=Path('results/replays'))
    ap.add_argument('--prefix',required=True)
    args=ap.parse_args()
    summaries=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(args.results.glob(args.prefix+'*/summary.json'))]
    lines=['# 固定工作量回放：'+args.prefix,'',
           '真实引擎执行所有输入和解码配额，工具与依赖重新执行；上游文本冻结。此表不验证自主闭环质量，不与网页答题得分混合。','',
           '| 轮次 | 平均任务耗时/s | P95/s | evidence命中 | 抢占 | 实际输出token | 相同输入 | 配额匹配 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        a=s['replay_accounting'];c=s['cache_by_stage']['evidence']['cached_fraction']
        lines.append(f"| {s['run_id']} | {s['root_latency_seconds']['mean']:.2f} | {s['root_latency_seconds']['p95']:.2f} | "
                     f"{c*100:.1f}% | {s['preemptions_delta']:.0f} | {s['tokens']['completion_tokens']} | "
                     f"{a['identical_input_prompts']}/{a['source_calls']} | {a['quota_matches']}/{a['source_calls']} |")
    lines+=['','单批中的八个根任务相互影响，不是八次独立系统重复；平均值改善也不代表P95同步改善。',
            '每轮真实输入、输出、工具、冻结文本哈希与源代码快照保存在远端runs目录；此处保留完整参数及统计索引。']
    args.results.mkdir(parents=True,exist_ok=True)
    (args.results/(args.prefix+'-comparison.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (args.results/(args.prefix+'-comparison.json')).write_text(json.dumps({'prefix':args.prefix,'kind':'fixed-work causal replay',
          'quality_evaluation':False,'summaries':summaries},ensure_ascii=False,indent=2),encoding='utf-8')
    print('\n'.join(lines))


if __name__=='__main__':main()
