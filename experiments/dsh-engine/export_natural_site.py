"""Export measured data. The single research report is maintained separately."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUP = 'natural-dag-20261029'
LABELS = {'simple': '简单问答', 'research': '多文档调查', 'coding': '代码修复',
          'analysis': 'CSV数据分析', 'incident': '故障诊断'}
PROVENANCE = {
    'simple': '任务来源：Codex自编的一步折扣算术题；数据集：无。正确价格198美元。',
    'research': '任务来源：六道HotpotQA distractor/validation原题及60份原始context；外层合并调查、写报告的任务由Codex编写。模型不见标签，非官方评测协议，非实时联网研究。',
    'coding': '任务与输入来源：Codex自编的小型Python结账服务，附带七项可见unittest；数据集：无。LiveCodeBench / SWE-bench未测试。',
    'analysis': '任务与输入来源：Codex自编；确定性合成订单、产品、退款CSV。数据集：无；不是生产数据。',
    'incident': '任务与输入来源：Codex自编日志、指标和部署记录，设定连接池配置回归。数据集：无；不是生产事故。',
}
RESULTS = {
    'simple': ('价格198美元', '正确回答折扣后的价格198美元，没有调用工具或子Agent。'),
    'research': ('报告已生成', '六题均给出有来源引用的答案，报告已落盘；这是原有校准题的案例观察，不报告为新的基准准确率。'),
    'coding': ('7项原测试通过', '原测试文件保持不变；模型先测得6/7失败，修复三个实现文件后7/7通过，离线复验通过。'),
    'analysis': ('核心金额核对通过', '独立核对净收入：一月8340美元、二月2700美元，减少5640美元；脚本和报告已生成。报告有“两个最便宜档位”的价位排序措辞错误，原文保留。'),
    'incident': ('报告与根因匹配', '报告识别到六副本连接池从12增至24，使连接总需求超过数据库上限，并提出回滚和验证计划；没有实际执行运维变更。'),
}


def overlap_peak(intervals):
    """Peak overlapping observed dispatch spans; ties finish before starting."""
    live = peak = 0
    for _, delta in sorted([(a, 1) for a, b in intervals if b > a]
                           + [(b, -1) for a, b in intervals if b > a]):
        live += delta
        peak = max(peak, live)
    return peak


def execution_summary(graph):
    tools = [n for n in graph['nodes'] if n['kind'] == 'tool']
    spans = [(n['tool_started_at'], n['ended_at']) for n in tools
             if n.get('tool_started_at') is not None and n.get('ended_at') is not None]
    return {'peak_tool_dispatches': overlap_peak(spans), 'observed_tool_spans': len(spans),
            'interval_definition': 'tools/execute wrapper entry to return; host wall-clock milliseconds, not CPU/GPU simultaneous execution.',
            'pinned_parallel_safe_tools': ['read'],
            'pinned_exclusive_tools': ['bash', 'edit', 'write', 'todo_write'],
            'classification_scope': 'Only tools observed in these five cases; declarations verified at pinned DSH source.',
            'default_max_parallel_tool_calls': 10}


def main():
    output = ROOT/'results'/GROUP
    output.mkdir(exist_ok=True)
    cases, failures = [], []
    for case in LABELS:
        version = 'v001' if case in ['simple', 'research', 'coding'] else 'v002'
        run = GROUP+'-'+version
        summary = json.loads((ROOT/'results'/run/case/'summary.json').read_text(encoding='utf-8'))
        assert summary['exit_code'] == 0 and summary['output_truncations'] == 0
        assert summary['audit']['delegation_tools_available'] and summary['audit']['initial_task_present_unchanged']
        graph = json.loads((ROOT/'results'/run/case/'graph.json').read_text(encoding='utf-8'))
        summary['execution'] = execution_summary(graph)
        summary.update(run_id=run, provenance_cn=PROVENANCE[case], short_result_cn=RESULTS[case][0], result_cn=RESULTS[case][1],
                       paths={'graph': f'../{run}/{case}/graph.json', 'timeline': f'../{run}/{case}/timeline.json',
                              'summary': f'../{run}/{case}/summary.json', 'input': f'../{run}/{case}/initial-task.txt',
                              'raw': f'../../evidence/{run}-raw.tar.gz'})
        cases.append(summary)
    for case in ['analysis', 'incident']:
        run = GROUP+'-v001'
        s = json.loads((ROOT/'results'/run/case/'summary.json').read_text(encoding='utf-8'))
        assert s['exit_code'] != 0 and s['output_truncations'] == 1
        failures.append({'case_id': case, 'run_id': run, 'duration_seconds': s['duration_seconds'],
                         'model_calls': s['model_calls'], 'max_output_tokens': s['max_output_tokens'],
                         'reason': '单次输出达到4096，DSH以max-tokens结束，报告未生成。',
                         'summary': f'../{run}/{case}/summary.json', 'timeline': f'../{run}/{case}/timeline.json',
                         'raw': f'../../evidence/{run}-raw.tar.gz'})
    index = {'group': GROUP, 'conclusion': '五类成功执行全部由1个根Agent完成，未自然创建子Agent；模型／工具事件图随读取、测试、修正逐步增长。此结果只描述这些任务和官方DSH默认提示下的一次观察。',
             'cases': cases, 'failed_attempts': failures,
             'successful_model_calls': sum(s['model_calls'] for s in cases),
             'successful_tool_calls': sum(s['tool_calls'] for s in cases),
             'no_predefined_graph': True, 'no_prescribed_agent_count': True, 'no_replay': True}
    (output/'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'successful_calls': index['successful_model_calls'],
                      'successful_tools': index['successful_tool_calls'], 'preserved_failed_attempts': len(failures)}))


if __name__ == '__main__':
    main()
