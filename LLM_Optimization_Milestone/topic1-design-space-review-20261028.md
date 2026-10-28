# Topic1 方向评估、边界拆分与最小 Demo

日期：2026-10-28

## 结论

目前没有足够证据支持把“按后端资源动态增减 Agent”作为论文主张。这个表述同时混合了任务拓扑、Harness activation 和 Engine admission，而且直接撞上了多条已有路线：CONCUR 控制活跃 Agent 数；Coda 已做 readiness-informed admission、bounded reordering 和 execution grouping；INFRAMIND 调整拓扑与逐步路由；TOPAS、SAGA、Maestro 已把 workflow 进度、KV 或任务完成时间带进调度。把场景换成在线、多 root 或 ODR，本身不能消除这些重合。

建议先只验证一个更窄的问题：**当多个独立 workflow/Harness root 共享同一 Engine 时，本地 delegation cap 与 Engine 的真实资源边界之间是否产生可观测的跨 root 排队、饥饿或无效状态准备？** 这是动机假设，不是 novelty claim。第一版固定逻辑子任务和模型请求集，只调度 READY frontiers 的派发时机，使用 ODR 的 researcher fan-out 做主要 workload；若强基线已经解决问题，及时停止“新调度器”路线。

当前最值得做的是“机会审计 + 强基线 demo”，不是继续扩展设计清单。只有 workload trace 显示损失确实存在、而且经过调优的 Coda/压力感知/公平工作流调度基线仍无法解释或消除时，才把剩余机制发展成论文方向。HTML demo 已作为可运行的机制沙盒，具体输入是合成 ODR 式负载，不能作为论文性能结果。

## 先把对象分层

| 层 | 例子 | 决定什么 / 负责什么 |
|---|---|---|
| Task / benchmark | DeepResearchBench、SWE-bench | 输入问题、环境与最终质量评分；不定义唯一 Agent workflow |
| Application workflow | Open Deep Research（ODR）、OpenHands coding graph | work item、依赖/授权、分支与 join、可选性、结果如何影响下一步 |
| Workflow runtime / orchestrator | LangGraph 在 ODR 中的 StateGraph；各 coding agent orchestrator | 执行 workflow 图、维护应用状态、收到结果后推进后继节点；它本身可能带 Harness 功能 |
| Agent Harness / runtime | DeepSeek Harness（DSH） | Session/Agent、child activation 生命周期、provider、局部容量、结果交付、取消和释放 |
| Inference Engine | vLLM / SGLang 等 | 模型请求执行、batch、GPU 与 KV 分配、底层队列和可观测资源 |
| Cross-root admission controller（候选） | 尚未实现 | 接收多个 root 的合法 READY 调用，在共享 Engine 边界上选择放行顺序/数量 |

术语要按实际实现标注：LangGraph 等应用 workflow runtime 不等同于 DSH；“Harness”常被论文宽泛使用，不能把 workflow DAG、child lifecycle 和 serving scheduler 写成同一层。DSH 也不是 benchmark 或应用 workflow。

不能把“Agent 数”简单拆成总量和并发两个数，还要区分计数单位：

| 量 | 含义 | 与其他量的关系 |
|---|---|---|
| `N_child` | 一项任务创建的逻辑子任务/child activation 数 | ODR 的 researcher 数属于此项；改变它可能改变研究覆盖和最终质量 |
| `N_llm` | 所有 Agent 最终发出的模型请求总数 | 一个 researcher 会反复调用模型和工具，所以一般不等于 `N_child` |
| `A_tree(t)` | Harness 中 live/materializing activation 数 | DSH 可能把 tool wait、pending inbox、stopping child 仍计数，不等于正在推理的请求数 |
| `C_llm(t)` | 同时在途或正在执行的模型请求数（需明确选哪一层） | 一个 activation 等工具时可仍占 DSH 槽位，但不占 Engine 的 active-request slot |

第一轮回放固定 `N_child`、`N_llm` 和实际请求集，只调派发时机。当前 HTML 把一个 researcher 简化成一次 Engine 调用，因此只能演示 `C_llm(t)` 的 proxy，不能评估真实 DSH 的 `A_tree(t)`、跨工具等待的连续性或 Agent 总数变化。真实 trace 必须同时记录这四个量。

**两个实际不同的控制点：**在 `startActivation` 前限制 child 创建控制的是 Harness activation admission；在每次模型请求前限制调用控制的是 invocation admission。前者与 CONCUR 的 Agent-level 控制相邻，后者与 Coda 的 ready-call 控制相邻。不能在图里画成同一个“调整 Agent 数”旋钮。

## 候选价值排序

| 排名 | 候选 | 论文动机 / 重合判断 | 当前建议 |
|---|---|---|---|
| 1（先测，不先立题） | 多个 root 共用 Engine 时的 READY frontier admission：固定 N，按共享资源放行具体 child | 真实多租户/多 Harness 的局部 cap 与共享 Engine 容量是否脱节，动机可测；但 CONCUR、Coda、SAGA、Maestro、TOPAS 已覆盖核心调度信号 | 做 trace 机会审计和强基线回放；创新度目前偏低，只有出现这些基线处理不了的实测损失才继续 |
| 2（只有冲突 trace 成立后再做） | 当前已知执行段的条件兑现：KV 准备→调用准入的联合核验、分波/fallback、失效重规划 | 比“调 cap”有更具体的机制空间；但 HEAR 可表达控制语义，TOPAS/TokenCake/Crossflow 已覆盖联合调度、预留和 lease | 只保留为待证伪的进一步机制候选；需要实测 single-action 控制之间的失效成本，不能把 plan/ticket 本身当 novelty |
| 3（工程基线） | DSH 每 root activation 上限与跨 root Engine 预算映射 | 可能减少过量物化/拒绝，但局部限额协调与 agent-level admission 已有前例 | 正确实现与测量，不单独作为顶会贡献 |
| 4（高重合） | 按 workload/资源改变 workflow 拓扑或 Agent 总数 | INFRAMIND Planner 和 Murakkab per-request/dynamic pipeline 已直接相邻；质量反馈增减分支也非空白 | 暂不做主线 |
| 5（高重合） | ready-call 次序、关键路径、fairness 或 KV 感知缓存保留 | Coda、TOPAS、SAGA、Maestro、TokenCake 已有直接机制 | 仅作为强基线/必要执行细节，不重命名为新贡献 |
| 6（范围过大） | 新建通用 Harness–Engine 协议、联合 KV 管理、投机与拓扑优化的一体化 Coordinator | HEAR 已定义跨层语义，Nalar/Policy Runtime 与各类 scheduler 覆盖大量抽象和机制 | 从首轮 demo 移除，避免把工程底座当研究问题 |

当前没有任何一项达到“已确认不重合且足以支撑顶会”的等级。rank 1 的价值在于可用低成本数据验证，不代表它是最可能的新颖算法。

## 近期重合与当前判断

| 候选 | 相关工作 | 判断 |
|---|---|---|
| KV/queue 压力改变 Agent admission / 活跃并发 | CONCUR | 控制动作直接重合；在线交互/多 root 可作为新动机假设，但需证明不是简单 workload transfer |
| READY call 的受限重排和 execution grouping | Coda | 直接强重合：readiness-informed admission、Tiered-Aging state admission、compatibility-aware execution admission 与 worker routing；Coding 不适合作为本文首要创新场景 |
| 请求开始时选拓扑、角色、Agent 数 | INFRAMIND Planner；Murakkab per-request 配置 | 直接重合 |
| 每个模型调用按实时状态选路由 / 执行方式 | INFRAMIND Executor；Engine scheduler | 直接重合 |
| 利用中间结果增减候选、修复、停止 | LAS；Murakkab dynamic coding | 直接相邻 |
| 运行中按 partial output 和负载重构拓扑 | INFRAMIND §6 将其列为 future work | 不是空白，必须说明比该扩展多出的机制和实验证据 |
| 用 workflow stage / DAG 做成本估计、fairness、cache 和排队 | SAGA；Maestro | 高度相邻 |
| 单独新建统一 runtime/orchestrator 中间层 | Policy-Driven Runtime Layer；另有 HEAR 类接口工作 | 抽象层本身不新 |

### 唯一先测的问题

> 在多个独立 workflow/Harness root 同享一个 Engine 时，已有的 per-root activation limit 与 Engine 实际 KV/队列状态之间是否产生了可重复的 head-of-line delay、root starvation 或无效启动？调优过的 global FCFS、pressure-only 和 Coda/TOPAS/SAGA 风格 workflow-aware policy 是否已经足够？

差异必须来自实测的失效模式和相对强基线的收益，不能只说“同时用了 Harness 和 Engine”。Coda 已经明确处理 ready-call 的 admission 灵活性，所以这个问题也有较高的排重风险。若 trace 上没有局部 cap/共享池冲突，或者强基线能解决，则停止该候选。

### 把候选机制落到可实现的动作

| 项目 | 第一版定义 |
|---|---|
| 触发 | 输入/工具返回使一个模型 invocation 变 READY；调用完成；或共享 Engine pressure 跨越阈值。事件合并处理，周期轮询只做丢事件保护 |
| 合法候选 | 来自已获准 activation、prompt/model/context version 已绑定、依赖满足、尚未提交 Engine 的 invocation ID；不推测未知工具结果/未来 call |
| 输入 | `root_id/activation_id/invocation_id`、READY 时间、已揭示 parent/join、等待时长、输入 token 和输出上界；Engine 的 model queue/KV blocks/free headroom/采样时间；Harness lifecycle 只作为语义观测 |
| 动作 | 在模型 provider adapter 中放行/暂缓具体 invocation IDs，其余留在 controller 队列；只调 `C_llm(t)`，不增减 activation 或模型请求集 |
| 硬约束 | Engine 容量与 workflow 依赖；已存在 activation 的模型调用不再申请 DSH child 槽位，更不能因 tree 已满而把它一起阻塞；最大 READY 等待作为保护，容量拒绝须退避 |
| 评价 | DeepResearchBench 任务分数非劣；同时报 root/task JCT P50/P95、goodput/SLO、每 root 最大等待、Engine queue、实际 KV eviction/recompute、拒绝/重试、准入控制开销 |

这是第一版 invocation-level probe 的定义。若以后专门测试 activation admission，则单独在 `startActivation` 前加 gate，检查新的 DSH 槽位；它是另一组实验，不能和 invocation gate 混为一个计数。Engine 硬容量、预测 headroom 和 latency/SLO 估算要分别标识，KV fit 不等于完成时间保证。

## 可单独复用的抽象，与可能的机制贡献

可以抽象出**当前已知、输入绑定的执行段**：它包含有限个合法 READY 调用、明确依赖、准确 context/model/version、资源上界、可接受的分波或冷 prefill fallback。它不包含未知未来子树，不自动修改 workflow 语义。这个对象可用于 ODR、coding 或其他 Harness 的 adapter，是统一计量/对照的工具；HEAR 已有依赖、requirements、controls、outcomes 语义，因此不能称“首次通用跨层接口”。

进一步的候选机制应只在确实观测到以下问题后保留：多个独立 Harness 基于相同旧快照分别做 KV prepare / request admission，造成无效准备、反复恢复、重算或 join 长尾；相同 Engine 的调优全局队列和单动作控制仍解决不了。此时比较：独立单项 controls → 在 Engine allocator 一致性点上对当前执行段 `reserve-and-enqueue` → 条件失效后局部重规划。

这不是默认 gang scheduling。ALL join 不要求所有 child 同时启动；只对当前有界 wave 做容量记账，工具等待释放执行额度，KV retention 单独说明。未使用 grant 可到期；已开始执行的硬 grant 不能静默撤回。单 Engine 原子 `reserve-and-enqueue` 若够用，不应为了协议名词添加 Prepare/Commit RTT。

真正可调且能做消融的点只有四个：

1. **核验粒度**：单调用，还是当前明确依赖的少量 prepare→call 动作；不预约未知未来。
2. **可执行备选**：当前 wave 大小 `k=1…|READY|`、共享前缀分组、冷 prefill fallback；语义工作集不变。
3. **有限承诺生命周期**：何时扣账、何时释放、准备失败怎么回退，取消需等实际释放确认。
4. **重规划触发**：依赖完成、capacity/context version 变化、动作失败；与固定周期对照，并计同步/控制开销。

这些点的研究价值仍未确认。TOPAS 已联合 prefix residency 与请求调度；TokenCake 已协调 pressure/reservation 和 tool-boundary cache；Crossflow 已有短期多资源 lease 与原子记账。剩余差异若只是换成“plan/ticket”名称，或者 Engine 原生已经处理这种一致性，就停止。详情与边界依据见工作区 `codesign/evidence/topic1-20261019/plan-contract-scope-review.md` 和 `protocol-gap-review.md`。

## Harness 与 workflow 各自能设计什么

### DSH 已有能力：作为 baseline

DSH subagent API 管理 activation 生命周期。官方 package reference 的 `maxActiveSubagents` 默认是 8：一个 top-level parent 建立本地与外部 descendants 共用的 activation-tree pool，root 不占槽；创建和 cold resume 在让出控制前预留槽，清理完成后才释放。等待父级、pending inbox 和 stopping activation 仍计数。达到上限时新的创建/cold resume 会拒绝，不会自动排队；配置在每次新 activation 或 cold resume 前重新采样，下调不终止现存 child。容量是进程本地值，不是跨进程共享 GPU 预算。

所以准确边界是：每个 top-level root 有独立 Harness tree pool；多个 root 的局部上限可以合计超过同一个 Engine 的有效 KV/队列容量。DSH 自己不会把 Engine 压力映射成全局准入许可。它是需保留的 Harness baseline，不是候选新设计。

来源： [DSH subagent package reference](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/subagent/README.md)（2026-10-28 在线核查）；本地 activation API 快照见 `codesign/evidence/agent-fanout-20261027/DSH_subagent.md`。demo 中“达到每树 cap 后保留 READY item 并等待”的行为属于包在 DSH 外的 wrapper 假设；DSH 原生语义是拒绝，不能把 wrapper 队列说成 Harness 自带功能。

## Demo：先做排重和现象检验

可立即打开的交互原型：[多根任务共享引擎准入实验室](topic1-admission-lab.html)。它把固定 11 个 ODR 式 researcher 工作项各简化成一个调用，对比每 root 调用 cap、全局 FCFS、压力反馈、workflow+pressure 的派发结果；可以调整局部 cap、KV 容量和到达/压力场景。这个原型只演示“READY 调用怎样进 Engine、哪些约束挡住它、root join 有何变化”，不能模拟真实 researcher 的多轮调用。

当前 demo 的局部 cap 是活跃模型调用的 wrapper proxy，不是 DSH 的 activation cap；真实 DSH 达到 activation 上限会拒绝，已驻留 child 的模型请求则复用其 activation。它也没有模拟 KV 驱逐/恢复、continuous batching 或 pressure-induced slowdown。下一步需用真实多轮 ODR traces，分别记录 activation 与 invocation 两条时间线。

本轮已检查 3 个场景 × 3 档局部上限 × 8 档 KV 容量 × 4 档全局上限 × 4 个策略，共 1,152 次仿真，全部满足固定且唯一的 11 个调用、READY 顺序、波次依赖、局部/全局上限和硬 KV 预算；Chrome 桌面及 390 px 窄屏检查无脚本错误/整页横向溢出。当前示例参数下 workflow+pressure 未优于 pressure-only，部分场景更慢。因为模型没有加入 thrashing/真实执行干扰成本，这既不是实际性能优势的证据，也不能用于否定真实压力控制方法；它只说明不能通过示例页自动制造研究收益。

### 强基线

1. DSH 原生每个 top-level root 的 activation tree cap + Engine 原生调度；保留拒绝与重试事实。
2. 相同执行资源下的全局 FCFS/aging queue，避免只与 per-tree cap 这个弱对照比较。
3. 压力反馈上限（CONCUR-inspired proxy，不声称复现 CONCUR）。
4. 就绪成本、aging 和 context compatibility 基线（Coda-inspired proxy；Coding trace 上必须比较）。
5. workflow critical-path / prefix-aware 基线（TOPAS/SAGA/Maestro-inspired proxy）。
6. 待检验的 cross-root 控制：从同一合法 READY 集合选具体 child，输出 global active grant；保留每 root 最低进度/最大等待保护。

第 3–5 组是机制近似，需固定论文机制和本地实现差异，不能声称复现原系统。所有策略共用相同 trace、Engine、到达、容量、work item 集和评分集；做 pressure-only / workflow-only / combined 消融，并报告每种 policy 看到了哪些字段。

### 主 workload 与边界 case

- **主 workload：ODR × DeepResearchBench**。仓库已有 ODR LangGraph graph；其 Supervisor 通过 `ConductResearch` 并行运行 researcher subgraph，结果返回后再继续规划/join。采集每个 researcher/model call 的 ready/start/end、父子/波次、工具等待、token 长度和最终 report score。质量评分是离线任务级信号，不假装有可靠在线 researcher 质量真值。
- **Coding × SWE-bench/OpenHands：强重合对照而非创新主场**。Coda 已直接研究 coding-agent ready-call admission 与 execution grouping；Murakkab/LAS 又覆盖动态 coding pipeline。用于测外推/退化，不承担主 novelty。
- GPT Researcher、CRAG 暂不进入首轮实现；保留原工作流图谱作为覆盖范围记录，不再为每个例子另添一个 design 点。

### 只做两个具体场景

| 场景 | 固定输入和扰动 | 要测的问题 |
|---|---|---|
| A. Fan-out burst | 一批 N 个 ODR research children 同时 READY；分别设置低 / 中 / 高真实 KV 压力 | 固定 N 时比较 static cap、FCFS、pressure-only、combined 的 active 曲线、join wait、P95 |
| B. 运行中负载突变 | 两个 root 共享模型队列；首批未完成时引入可复现外部负载，再逐步卸载 | 是否避免 admission 震荡、拒绝风暴、per-root starvation；只用真实 Engine trace 或受控负载，不杜撰 telemetry |
固定 work set，不改变 Agent/模型调用总量，不根据中间质量猜测删任务。先采集实际 READY frontier 大小和工具间隔，再决定是否有调度空间。若只能在模拟压力上跑，报告必须标为机制 demo，不是性能 evidence。

### 继续 / 停止判据

- 最强对照不只是 FCFS，还包括压力感知、Coda 风格 admission 和 TOPAS/SAGA 风格 workflow-aware 强基线。
- Combined 必须在多个 seed、不同 KV 容量、突发强度、长度分布及 cost 估计误差下稳定优于调优后的最强 baseline。
- ODR/coding 最终原始质量分数要在预先设定的非劣约束内，同时报告 task completion、SLO、调用数、KV/重算、饥饿和控制器开销。
- 若 pressure-only 已覆盖 combined 的收益，或收益只来自把任务做少了，或 READY frontier 很少，则不要声称通用 Topic1 创新。
- 若只证明可把 DSH 静态 cap 变成动态 cap，那是产品/集成 demo，不是顶会贡献。

## 当前原型覆盖范围

| 原型 | 已验证 | 未验证 |
|---|---|---|
| codesign/topic1_demo | CPU PyTorch 张量、cache/取消语义、同输入输出核验；10 项测试通过 | 手写 workflow、未训练模型；不是真实 GPU / benchmark 质量结果，也没有 DSH ready-child fan-out 数量控制实验 |
| codesign/topic1_sim | 651 条 CacheWise normalized 请求的离散事件仿真；6 项机制测试通过 | 无 prompt/有效任务质量；等待和服务成本需假设；对照策略排序随容量与等待假设变化 |
| codesign/topic1_gpu | 有资源保护的真实 Engine 实验入口 | 此前记录的 GPU 实验未运行；本轮未重试服务器。不支持“已实测加速”结论，也尚未测 Agent 总数变化 |

因此应在现有原型上增加独立的 activation admission trace mode，不要把 cache predictor、KV offload、workflow speculation、dynamic N 和 stop policy 一次全堆进同一个 demo。

## 后续研究页面结构建议

将当前五个展示项按三个层次组织：

1. Workflow workload：ODR / research 与 coding 为主；GPT Researcher / CRAG 为 transfer 或负例。
2. Harness Runtime：独立展示 DSH 的真实 activation 生命周期、capacity behavior、拒绝/取消/释放。
3. Candidate Controller：分别标明 input state、触发事件、合法 READY set、输出动作、baseline 和指标；所有控制点用“待测”标记。

每个设计卡只保留四项：层级、触发事件、具体可调变量、关键指标。旁边单独列已有工作和本实验真正检验的差异。这样页面从并列功能清单收敛成一个研究问题、一个主负载和边界对照。

## 本轮排重参考

- [CONCUR: High-Throughput Agentic Batch Inference of LLM via Congestion-Based Concurrency Control](https://arxiv.org/abs/2601.22705), arXiv:2601.22705（2026-10-28 abstract 页题名；本地旧快照标题为 *Proactive Agent-Level Admission Control for Efficient Agentic Batch Inference*）。
- Coda 原文题名为 *Coda: Exploiting Admission Flexibility for Coding-Agent Serving*, arXiv:2610.03088v1。其 Tiered-Aging state admission、Compatibility-Aware execution admission 和多 worker routing 是 readiness admission 的直接强基线。
- InfraMind: Infrastructure-Aware Multi-Agent Orchestration, arXiv:2606.11440。
- Murakkab, OSDI 2026，workflow optimization 与 dynamic coding pipeline。
- LLM-as-Scheduler: Agentic Workflow Dynamic Scheduling, ACL 2026, 2026.acl-long.581。
- A Policy-Driven Runtime Layer for Agentic LLM Serving, arXiv:2605.27744。
- Maestro: Workload-Aware Cross-Cluster Scheduling for LLM-Based Multi-Agent Systems, arXiv:2606.12950。
- SAGA: Workflow-Atomic Scheduling for AI Agent Inference on GPU Clusters, arXiv:2605.00528。
- [Can Agent Harnesses and Inference Engines Hear Each Other? The HEAR Protocol for Agentic LLM Serving](https://arxiv.org/abs/2610.06597), arXiv:2610.06597。
- [TOPAS: Workflow-Aware Prefix-State Scheduling for Multi-Agent LLM Serving](https://arxiv.org/abs/2608.25523), arXiv:2608.25523。
- TokenCake: A KV-Cache-centric Serving Framework for LLM-based Multi-Agent Applications；本地全文 `codesign/evidence/topic1-20261019/sources/TokenCake.txt`。
- [Crossflow: Prefill-Decode Elasticity for Agentic LLM Serving](https://arxiv.org/abs/2609.27085), arXiv:2609.27085。
- DeepSeek Harness [subagent package reference](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/subagent/README.md) and [activation API](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/subagent.md) (checked 2026-10-28); local source snapshots in codesign/evidence/agent-fanout-20261027/.
