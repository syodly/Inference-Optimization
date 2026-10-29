"""Build a small public index and Chinese report from downloaded native results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUP = 'natural-dag-20261029'
LABELS = {'simple': '简单问答', 'research': '多文档调查', 'coding': '代码修复',
          'analysis': 'CSV数据分析', 'incident': '故障诊断'}
PROVENANCE = {
    'simple': '整理的一步算术任务，正确价格198美元。',
    'research': '六道原始HotpotQA问题及60份来源文档；模型只见问题和来源，不见标签。不是网络实时研究。',
    'coding': '人工整理的小型Python结账服务，含七项公开unittest测试；不是上游编码基准。',
    'analysis': '确定性生成的订单、产品、退款CSV，含重复事件与产品组合变化；不是生产数据。',
    'incident': '人工整理的日志、指标和部署记录，设定连接池配置回归；不是生产事故。',
}
RESULTS = {
    'simple': ('价格198美元', '正确回答折扣后的价格198美元，没有调用工具或子Agent。'),
    'research': ('报告已生成', '六题均给出有来源引用的答案，报告已落盘；这是原有校准题的案例观察，不报告为新的基准准确率。'),
    'coding': ('7项原测试通过', '原测试文件保持不变；模型先测得6/7失败，修复三个实现文件后7/7通过，离线复验通过。'),
    'analysis': ('核心金额核对通过', '独立核对净收入：一月8340美元、二月2700美元，减少5640美元；脚本和报告已生成。报告有“两个最便宜档位”的价位排序措辞错误，原文保留。'),
    'incident': ('报告与根因匹配', '报告识别到六副本连接池从12增至24，使连接总需求超过数据库上限，并提出回滚和验证计划；没有实际执行运维变更。'),
}


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
    note = ['# Qwen27B × 官方DSH：自然在线执行图观察', '',
            '**DAG的生成与Harness有关：模型决定下一步动作，Harness定义动作接口、执行和结果交付规则，两者共同形成实际事件图。** 本组只给初始任务及工作文件，不指定Agent数量、不预写工作流、不回放。五类成功运行都没有委派子Agent；这本身是结果，不能为得到多Agent图而补发诱导指令。', '',
            '## 实际设置与边界', '',
            '- 官方DSH 0.2.1-rc.2，固定发行源码未修改；模型为songprojgpu1上ModelScope Qwen/Qwen3.8-27B，BF16、TP2、low reasoning、temperature=0。沿用原双卡服务。',
            '- 保留默认工具、coding persona、委派深度1和每棵树8个活跃孩子的上限，没有额外限流或阶段优先级。subagent、subagent_fork和workflow在每个根请求中实际可见；没有委派尝试，也没有容量拒绝。',
            '- 默认系统提示明确要求：`Use the workflow tool ONLY when the user explicitly asks for a workflow or for large multi-agent orchestration`。本组初始任务没有该指令，因此workflow没有出现不能解释成模型不具备编排能力。',
            '- 初始任务只描述目标、文件和交付物。任务目录在科研仓库之外，不含祖先AGENTS.md；未加载原e1研究工具、固定三分支插件或派发许可。',
            '- 记录插件仅观察原生Session、模型流、工具及子Agent/Workflow生命周期，并统一采样参数；没有修改工具schema、结果或派发时机。记录的同步I/O会有开销，本组不用于性能加速归因。',
            '- 首轮4096输出上限使CSV和故障诊断触顶。原轨迹保留；仅这两类用16384上限、新Session、新工作目录和相同原始输入重新执行，没有续写、回放或补充任务。成功表使用后两次。不同输出上限不适合横向性能排名。', '',
            '## 五类完成结果', '',
            '| 场景 | Agent | 模型调用 | 工具调用 | 完整耗时/秒 | 结果 |',
            '|---|---:|---:|---:|---:|---|']
    for s in cases:
        note.append(f'| {LABELS[s["case_id"]]} | {s["agent_sessions"]} | {s["model_calls"]} | {s["tool_calls"]} | {s["duration_seconds"]:.2f} | {s["short_result_cn"]} |')
    note += ['', '成功案例共41次模型调用、108次工具调用；两次未完成首轮另有7次模型调用、15次工具调用。48个接口响应与原生模型步骤和请求就绪事件一一对应，均HTTP200；成功案例无截断。代码原测试不变且离线7/7通过。CSV核心数字核对通过，但报告有一处价位排序措辞错误，不能把程序完成当作全文完全正确。', '',
             '## 怎么读DAG的生成时刻', '',
             '一次模型请求就绪，只说明下一步推理可以提交；它未来会生成哪些工具仍未知。流式响应中首次出现工具名是意图开始可见；`tool/call`原生日志标志完整调用提交；工具执行开始、结果返回和下一模型请求分别有时间戳。模型说“接下来写报告”尚不是一个可执行写文件节点。todo列表也只是计划数据，不自动变成未来执行图。', '',
             '图保留已验证的执行依赖：模型→本步工具、工具结果→下一次模型。同一步的多个工具共享前驱，不能因日志顺序把它们画成串行链；并排也不代表已经实测同时执行。Agent创建关系与模型/工具依赖分层统计。本组没有跨Session消息，因此无需猜测消息因果边。', '',
             '所有时间来自同一服务器进程和原生事件，毫秒级墙钟；同时保存进程单调经过时间。相对时间从提交CLI算起，含启动；不是GPU内核执行时刻或工具意图在模型内部形成的时刻。在线图只表示截至当时已揭示工作，不能从最终图推断模型事先已知道完整DAG。', '',
             '## 代表性的实测变化', '']
    for s in cases:
        note += [f'### {LABELS[s["case_id"]]}', '', PROVENANCE[s['case_id']], '',
                 '| 模型步 | 请求就绪 +秒 | 响应提交 +秒 | 本步新工具 | 最后工具结束 +秒 |',
                 '|---|---:|---:|---|---:|']
        for step in s['steps']:
            tools = '、'.join(f'{k}×{v}' for k, v in step['tools'].items()) or '最终回答，无工具'
            end = step['last_tool_end_seconds']
            note.append(f'| {step["turn"]}/{step["step"]} | {step["ready_seconds"]:.3f} | {step["response_seconds"]:.3f} | {tools} | {end:.3f} |' if end is not None else f'| {step["turn"]}/{step["step"]} | {step["ready_seconds"]:.3f} | {step["response_seconds"]:.3f} | {tools} | — |')
        note += ['', RESULTS[s['case_id']][1], '',
                 f'[完整时间戳](../results/{s["run_id"]}/{s["case_id"]}/timeline.json) · [事件图与完整Prompt](../results/{s["run_id"]}/{s["case_id"]}/graph.json) · [实测统计和原始回答](../results/{s["run_id"]}/{s["case_id"]}/summary.json)', '']
    note += ['## Harness怎样改变可观察的图', '',
             '1. **工具可见性与系统指令影响动作选择。** DSH默认persona和workflow使用条件已进入实际请求。这是明确的配置事实；本组没有更换Harness或移除提示做因果对照，不能量化各自贡献。',
             '2. **调度与Session协议决定执行边。** 一次模型响应能提出多个工具，DSH执行并把结果带回下一次模型请求；只有委派工具被实际调用才会产生子Session。',
             '3. **停止规则会截断后继工作。** 首轮CSV与故障诊断在4096输出上限处以max-tokens结束，虽然模型已经描述后续计划，报告写入节点没有发生。扩大输出额度后，两次从头执行都产生了写报告节点。此处额外预算和新生成文本同时变化，不是固定文本的单变量对照。', '',
             '当前最值得保留的研究判断是：先测真实ready前沿再设计派发。在本组中模型在途峰值均为1，尽管有工具分叉，尚未形成多个Agent模型请求争用的调度场景。不能把以前人为固定三子Agent的宽图直接称作自然行为，也不能据五个整理任务就断言所有自然工作流都很窄。更大任务、其他模型、提示和Harness仍可能不同。', '',
             '## 原始证据与复现', '',
             f'- [首轮完整证据](../evidence/{GROUP}-v001-raw.tar.gz)，包含三个成功案例及两次输出触顶失败。',
             f'- [两类重新执行的完整证据](../evidence/{GROUP}-v002-raw.tar.gz)。',
             f'- [首轮哈希](../results/{GROUP}-v001/archive-index.json) · [第二轮哈希](../results/{GROUP}-v002/archive-index.json)。',
             '- 每包保存输入/输出文件、初始prompt、全部实际API请求/流式响应、原生压缩日志及解码事件、工具参数/结果、观察事件、引擎指标、配置与源码快照。',
             '- 执行入口：`natural_run.py`、`natural.patch.yml`、`natural-observer.mjs`；离线分析：`natural_analyze.py`；网页索引：`export_natural_site.py`。现有编号不覆盖。',
             '- 同批只提交一个根任务，场景依次执行；旧性能批次STOP保留。本组已结束，没有自动追加实验。', '']
    (ROOT/'notes/natural-dag-20261029.md').write_text('\n'.join(note), encoding='utf-8')
    print(json.dumps({'cases': len(cases), 'successful_calls': index['successful_model_calls'],
                      'successful_tools': index['successful_tool_calls'], 'preserved_failed_attempts': len(failures)}))


if __name__ == '__main__':
    main()
