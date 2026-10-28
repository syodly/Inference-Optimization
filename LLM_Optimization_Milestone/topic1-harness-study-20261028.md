# Topic1：从子 Agent 的一般动作寻找 Harness 痛点

2026-10-28。研究方向筛查与实验准备；尚未运行真实 DSH 实验，尚未确认论文创新或性能收益。

> 2026-10-29 范围修订：当前重心是 [Harness 请求与 DAG 如何结合引擎状态展开和派发](topic1-harness-engine.html)，详见 [新问题定义与实验方案](topic1-harness-engine-study-20261029.md)。本文作为 DSH 实现边界核查保留；以下截图衍生候选和八题实验不再作为研究主线或首轮实验。

## 先给判断

将重心从“固定 11 次调用的排队演示”移到真实 Harness 的委派边界是合理的。优先审计 **上下文如何交接**，其次审计 **结果什么时候值得唤醒父 Agent**；**等待子树的驻留与回收**作为有条件后备。不要同时新建调度器、KV 管理器、持久消息系统和通用协调协议。

用户截图提供了一个具体工作模式：父 Agent 委派六个不同职责的子任务，再整合发现。截图不能证明六者同时运行，也不能把界面累计 token 数解释成重复 prefill、同时驻留的 KV 或可节省成本。以下把这个模式作为待采样的 workload，不把截图当性能 trace。

核对的是 DeepSeek Harness commit [`f3803c96974ad4a94195fb97e5c637e9c2a3afe3`](https://github.com/deepseek-ai/deepseek-harness/tree/f3803c96974ad4a94195fb97e5c637e9c2a3afe3)，包含用户指定的中文 subsystem 文档、英文 package contract 和实现。原文快照及 SHA256 manifest 保存在工作区 `codesign/evidence/harness-lifecycle-20261028/`。

## 一般动作与对象

| 对象 | 在这里是什么意思 | 不能混同什么 |
|---|---|---|
| 逻辑子任务 | 例如核查一篇论文、检查某模块、补充一项结论 | 不必每次新建 Agent |
| 子 Session | 持久身份和历史，已有子任务可在之后继续 | Session 留在目录中，不表示实例仍驻留 |
| Activation | 这次被创建或冷恢复的在线执行实例 | 一个实例可以有多次模型调用与工具等待 |
| 模型请求 | 实际提交到推理服务的一次请求 | 等待中的 Agent 不必占用运行中的模型请求槽位 |

1. **选择创建方式。** `spawn` 使用新对话，不带父对话；preset 仍可带 prompt 和工具定义。`fork` 带父级截至上一个完整轮次的历史，排除当前未完成轮次；它是一次性快照，不会自动跟随父级更新。已有本地子 Session 可以经 `sendMessage` 续接。
2. **检查并创建实例。** `startActivation` 检查能力、身份和 activation 容量；本地创建或冷恢复占槽。同一顶层父级下的后代共享进程内池，默认上限 8，顶层 root 不占槽。工具委派默认深度 1；深度与容量分别控制。
3. **运行模型／工具，收发消息。** 本地子 Agent 可多轮运行。给运行中的子 Agent 发消息会在步骤边界 Steer；给不在线的可继续直接子 Agent 发消息会冷恢复。`sendMessage` 返回接受身份，不返回对方完成结果。外部 ACP／Codex 等执行在该 DSH 接口下是一次性的，不能据此断言这些产品本身不能多轮。
4. **等待或被打断。** 等后代、未消费 inbox、停止清理中的实例仍占 activation 槽。`interrupt_agent` 对本地对象只请求停止当前轮次：未消费消息可以保留，后代继续运行；确认收到中断不等于已经安静或资源已经回收。
5. **自然结算与释放。** Agent 活动、待处理输入和所属后代结束后，Manager 复核、清理 handle、归还槽位并发送通知，随后结算 result。完成子 Agent 不是默认永久驻留；持久 Session 仍可用于之后冷恢复。
6. **交回结果。** `delivery: 'parent'` 发父级完成通知，空闲父级会被唤醒，忙父级收到 Steer；通知本身是追加内容，不意味着旧前缀全部失效。`delivery: 'caller'` 不发模型可见的父级完成通知，由程序消费方等待结果。多个通知可能被同一轮处理，不能预设 N 个通知一定产生 N 次父级请求。

## P1 · 首选：委派时到底带多少历史、复用哪个子 Session

**事实。** DSH 已有 spawn、fork 和冷续接，但它们只是可选机制。fork 的完整继承历史可能得到精确前缀复用；spawn 更短，却可能需要重新读文件和补背景。已完成子 Session 的冷恢复也不保证 GPU KV 仍在。

**待测痛点。** 在“同库、多角色、随后追问”的真实任务中，固定使用一种模式是否出现可观测的两难：全 fork 带入大量无关历史；全 spawn 重复读取证据；不断新建则反复重做已经完成的定位工作。三者谁更便宜取决于任务所需证据、上下文长度、实际缓存命中和恢复成本。

**具体动作。** 首版只决定 `create_spawn / create_fork / continue(child_id)`；模式内保留 DSH 原生上下文规则。当前任务要求必须显式传入，因为 fork 不包含当前未完成轮次。续接仅限允许继续的任务；需要独立视角或隔离的任务不能为了省 token 强行复用。记录任务需要的文件版本、实际继承前缀指纹和已读证据。暂不把任意压缩、跨模型 KV 转换、换模型和全局调度混进来。

**E1。** 先做“六个分工核查＋两次明确追问”，全部使用同模型、同 preset、相同工具和权限，比较全新 spawn、原生 full fork、追问续接，以及简单固定规则。对短／长父历史、缓存冷／暖和相关／独立追问分层，记录实际输入 token、缓存 token、重读工具调用、子任务耗时与依据正确率。只有 serving 实际提供时才报告未命中 prefill token／时间，不从界面 token 数推算。

**继续条件。** 同质量约束下存在稳定的模式优劣交叉，并且代价感知选择超过“独立任务 spawn、原任务追问续接”的简单规则。若一种原生模式或这条规则已稳定占优，就保留为使用建议，不继续包装成论文。随后才扩展到固定任务子集的 SWE-bench 等真实质量评测；当前六题核查仅是机制审计，不等同于标准 benchmark。

**排重。** 缩短／压缩上下文本身与 Topic2、上下文管理工作重合；Helium 的前缀与跨调用复用也直接相关。可能的区分点是有证据依赖约束的委派／续接选择与实际复用成本，而非“首次共享上下文”。当前未做上下文委派选择领域的穷尽检索，不能认定此点新颖。

## P2 · 低成本并行审计：每个子结果都值得父 Agent 推理一次吗

**事实。** 默认工具委派使用 parent delivery；通知到达空闲父级会启动模型请求，忙父级则 Steer。DSH 已支持 caller delivery，程序可以一次等齐一组结果。这是必须包含的强对照。

**待测痛点。** 六个核查结果错开返回时，父 Agent 是否反复只做“已收到，继续等”，增加输入增长与推理；或者为了合并而等齐，反过来延误子 Agent 的澄清请求。先从日志量出这两类情况，不从通知条数推算浪费。

**具体动作。** 首版只控制可延后结果的交付／唤醒边界，完整保留消息、发送者和顺序。程序接收结果后可按组一次交付，或用有上界的小时间窗合并。依赖其他答案才能继续的澄清、错误及用户控制消息立即交付；未知类型默认即时，不依靠另一次模型调用给每条消息分类。消息类型与组完成条件需要显式契约，不能只靠盲等“足够多结果”。

**E2。** 使用同一组真实子执行结果先审计默认模式，再做真实闭环执行：A 类六个结果互不依赖且必须全部汇总；B 类至少一个子 Agent 中途需要澄清、父级回复后它才能继续。对比原生 parent、原生 caller＋程序全等、caller＋显式澄清立即交付、固定短窗口、候选的依赖感知交付。窗口只扫少量预先固定值，不先拟合一套复杂预测器。

**指标。** 父级真实模型请求数、父级输入／输出 token、消息接受到首次消费的时间、澄清响应时延、最终完成耗时、消息遗漏／重复与最终质量。记录每次父请求首次消费了哪些新消息；不把整个历史里反复出现的消息算成再次交付。

**停止条件。** 如果 caller＋显式澄清立即交付已达到效果，或固定窗口足够，停止“自适应唤醒”研究。单纯 Promise.all／通知 batching 既有工程实现，也不是天然顶会贡献。固定全等组本身不足以支撑新论文，需要真实动态依赖中的剩余问题。

## P3 · 后备：等待子树占槽与中断后的资源回收

**事实。** 等待父实例、未消费 inbox、停止清理都可能继续计槽。满额创建直接拒绝，没有原生准入队列。源码明确选择不排队，以避免父级持槽等待后代造成槽位依赖。正常完成的子实例已经自动释放。

**待测痛点。** 非默认深度至少 2 的递归委派、闲置的 parked inbox 或较慢清理，是否导致一批 slot 被不能推进的实例占住，同时新的有效工作被拒绝。默认深度 1、六个独立子任务未必会触发此问题。满额拒绝不等于死锁。

**E3 先观测。** 对照默认深度 1 与显式深度 2，分别统计运行、等工具、等后代、parked inbox、清理的 activation 槽位时间，记录拒绝、重试、实际 RSS 和释放耗时。GPU 请求时间与 GPU KV 必须另记。中断实验单列 request-stop、实际静止、后代结束和 slot 释放四个时刻。

**只有审计成立才设计。** 根据真正的等待原因决定是否需要可恢复挂起或更细的额度；挂起必须先持久保存待处理消息和 continuation，保证回信可唤醒父方，再释放驻留实例。不能直接删 inbox、dispose 父级使有效后代丢失，也不能通过无限加槽回避相同内存预算。比较原生拒绝＋不新建／退避、合理增大静态上限、深度／工作量保持一致的简单策略与完整挂起方案。

**排重与停止。** Nalar 已有 future／状态及迁移；actor／durable-workflow 系统是必须补查的基础。只加持久 mailbox、lease 或静态队列是常规工程。用户修订后的旧输出封锁、版本继承与异步回收已有 Retire，不能把“中断＋保留 KV”当空白。若真实工作负载不存在等待占槽和有害拒绝，停止此线。

## 共享的最小记录与首轮执行顺序

准备文件位于 [experiments/harness-audit/README.md](experiments/harness-audit/README.md)，包含 8 个核查／追问任务、对照矩阵、规范化日志格式和日志审计工具。**这是实验准备，不是已经接好的 DSH collector**；需要在固定 revision 的 DSH 运行环境增加导出适配器。没有凭空填入真实 prompt 输出、硬件指标或性能数字。

1. 导出 session／activation／model-request 三种身份，模式、父子关系、消息接受／首次消费、槽位占用原因、实际 usage、工具读取和任务结果。
2. 第一轮只跑原生模式，检查六任务案例中 P1／P2 是否存在。所有输入和输出保存到本地制品；质量判定使用任务清单的文档／源码依据，禁止在线控制器读取评分答案。
3. 实际质量任务做配对运行、调换执行顺序、多个固定 seed，独立报告缓存冷／暖条件。共享 GPU、模型、上下文上限和原生 Engine 设置，不靠换模型或少做任务获得“收益”。
4. 采集后预登记最小值得做的效应、质量非劣容差与更多任务子集，再设计复杂 policy。第一轮不预先宣布 P1 或 P2 一定能写论文。

## 与网站原有路线的关系

- Workflow 决定研究／编码过程的逻辑任务、依赖与质量目标。
- Harness 决定这些任务怎样落实为带历史的子 Session、在线实例、消息和清理动作。本轮固定任务分解，改变这个实现边界。
- Engine 决定真实请求排队、批处理和 KV 放置；有可观测的实际复用成本时再作为控制输入。
- HEAR 已有双向语义与具体 policy 实例，不能概括为“只传消息而没有决策”；它可作为跨层信号基底。INFRAMIND／Murakkab 已覆盖多种拓扑、角色／模型与工作流配置选择。本轮也不能仅靠把选择动作移到 Harness 就宣称创新。
- 原准入演示保留为历史教学材料，不再承担当前研究动机。

## 核查来源

以下 GitHub 链接均固定 revision，行号对应本轮保存的源文件。

1. [中文 subsystem：本地 activation](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/docs/subsystems/subagent.zh.md#L128-L176)：身份、结果、消息与冷恢复。
2. [package contract](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent/README.md#L47-L73)：默认深度、容量 8、拒绝不排队、delivery、清理；[通知与限制](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent/README.md#L163-L213)。
3. [fork 的上下文／缓存边界](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent-fork-in-process/README.md#L105-L143)；[spawn 边界](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent-spawn-in-process/README.md#L105-L140)。
4. [控制工具](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/tool-subagent-control/README.md#L45-L63)：send、interrupt、list；[inactive 不是任务完成及目录成本](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/tool-subagent-control/README.md#L146-L170)。
5. [Manager 结算判断](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent/src/manager.ts#L1099-L1109)、[清理／通知／结果顺序](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent/src/manager.ts#L1194-L1218)、[满额拒绝](https://github.com/deepseek-ai/deepseek-harness/blob/f3803c96974ad4a94195fb97e5c637e9c2a3afe3/packages/subagent/subagent/src/activation.ts#L14-L34)。
6. [HEAR](https://arxiv.org/abs/2610.06597)、[Helium](https://arxiv.org/abs/2603.16104)、[Nalar](https://arxiv.org/abs/2601.05109)、[Retire](https://arxiv.org/abs/2610.01160)。本轮查了线上摘要并复用已有正文笔记；不是新做的系统性排重检索。
