# Harness–Engine 实验

在 `songprojgpu1:/home/Liangyijia_Hu/harness-engine` 运行。研究规则见 [AGENTS.md](AGENTS.md)，持续清单见 [PLAN.md](PLAN.md)，每轮记录见 [RESEARCH_LOG.md](RESEARCH_LOG.md)。

**2026-10-29：用户已暂停。** 实验、后台衔接和本项目推理服务已停止，GPU 0/1 已释放；模型、环境和原始日志保留。进展与效果见 [暂停总结](notes/paused-progress-20261029.md)，最新八轮数据见 [共享引擎结果](notes/v024-shared-outcome.md)。未完成的批次不自动恢复。

## 当前应用

暂停前服务为 Qwen3.8-27B BF16、双 A800、图执行、64K 上下文、48 条引擎序列上限、8192 batched tokens，启用前缀缓存、分块 prefill、阶段优先级和逐请求遥测。最新工作是 `verified`：三个持久子 Session 各执行 query → BM25 → draft → 来源核验 → evidence，父 Session 等待全部分支，每个根任务十次必做调用。长文来自固定版本 LongBench-v2，原始全文未截断或补字。来源核验仅判断引句出处，答案由隐藏标签离线评分；两者分别报告。

最新状态见 [CONTINUE.md](CONTINUE.md)，网页见 [真实流程与原始调用](../../LLM_Optimization_Milestone/topic1-experiments.html)。v020已完成七轮显式工具等待干预；v021已完成十一轮同输入、同生成配额的混合回放。短任务独占34.89秒、混合138.43–140.50秒，干扰成立；历史预算137.58秒与普通回流24的138.17秒近似，复杂机制的独立优势尚未成立。详见 [分组归因](notes/v021-interference-outcome.md) 与 [工具等待闭环](notes/v020-tool-delay-outcome.md)。

v024独立控制器共享引擎的八轮已完成，目标16题和背景4题均做真实工作，分别报告质量、等待和对别人的影响。v025固定双方输入和解码量的因果对照仅完成1/9轮，第2轮被暂停；完整第一轮为200份一致输入和96,905个实际解码token。v026同信息、同请求/Session准入权限的前端与引擎侧代理对照未启动；代理不是原生vLLM逐token调度器。v027可选复核和推理模式实验仅做离线结构检查，尚无GPU质量或时延结果。每个轮次仍为分钟级目标，多轮批次的总时长不等于单轮规模。

这是自行实现、与 DSH 动作相似的 Harness，**不声称复现完整 DSH**。公开 HotpotQA 上下文被固定分为三个文档分片。每个任务创建三个持久子 Session，依次执行真实模型生成检索词、真实 BM25 工具、真实模型证据整理；父 Session 等待全部子任务，调用模型给出带来源的答案。默认每任务七次模型调用，全部为必做工作。该受控 DAG 用于隔离派发行为；更复杂的动态图和质量驱动展开放在独立实验。

这里模拟多份独立研究任务共享同一引擎。DSH文档的`maxActiveSubagents=8`按每棵任务树计数，在本图三个子任务下不会触发；我们增加的全局Session窗口是实验策略。一次子Agent执行包含模型和工具多个阶段，不能等同单次模型请求。旧日志的`activation_start/end`实际是模型请求区间，保留原样并按此解释；第二版分别写`model_call`与`agent_execution`，后者也不冒充DSH完整驻留生命周期。见[语义核对](notes/dsh-execution-semantics-v2.md)。

每次调用保存完整历史、采样参数、响应、usage 和首 token 时间。另存任务、Session、activation、工具、汇合事件与真实 Prometheus 指标。`frontend_wait` 是 Harness 等待；API 首 token 时间包含后端队列、prefill 和网络开销，不直接称为服务内部排队时间。指标缺失保存为空，不能编造。父任务时延包括全部等待、工具与汇总过程。

`natural` 使用工具实测时间；`controlled` 在真实检索后增加明确记录的延迟，用于可控回流实验。调度器只看已开始工具的类型、时间与实际引擎状态，不知道注入时长或未来返回时间。答案文件仅由离线分析器读取。

## 远端命令

所有命令在项目目录执行：

```bash
python3 prepare_data.py --out datasets/hotpot
python3 serve.py
.venv-engine/bin/python run.py --out runs/calibration-native --count 8
.venv-engine/bin/python analyze.py runs/calibration-native
```

服务参数、启动资源证据及实际引擎容量保存在 `state/server.json` 和逐轮 `config.json`。早期 eager、16K 与当前图模式64K的实验分别保留，不跨引擎配置直接声称机制收益。该模型是混合注意力架构，当前对齐缓存块为784 token，不能用普通 Transformer 的每 token KV 假设代替实际计量。

四个初始基线：`native` 直接派发；`fixed --cap N` 固定在途调用数；`pressure` 根据真实引擎等待与缓存占用收缩；`progress` 同 cap 下优先汇总和接近完成的任务，保留老化。后三者均需与静态 cap 扫描比较。新机制须以测得的痛点为依据。

新增基线 `return_priority` 同 cap 优先回流与汇总；`session_window --session-cap N --cap M` 在工具等待期间继续对持久子 Session 计账，全部等待计入根任务。`backend_priority` 将阶段优先级交给真实引擎；它不是具有相同展开权限的完整后端实现。

`size_return`在同一回流优先规则下按实际prompt长度排序，用来检查混合负载的改善是否只是短请求优先。`history_budget`在长draft形成时按实际token申请虚拟历史额度，工具期间计账、回流完成释放；`history_pressure`再使用实际引擎压力收缩冷draft额度。它们不等于物理KV驻留控制。真实长度测量的开销计入根任务，并和不需要该测量的低开销基线比较。

```bash
.venv-engine/bin/python batch.py configs/verified-quality-v012.json
.venv-engine/bin/python batch.py configs/session-window-v014.json
.venv-engine/bin/python replay_batch.py configs/replay-verified-v015.json
.venv-engine/bin/python token_audit.py runs/v012-verified-long-native8
```

这些命令应顺序运行，每条独立轮次通常数分钟。回放执行真实模型、工具和依赖，但冻结上游文本与逐调用解码配额，不能证明自主闭环质量；结果单列在 `results/replays`，不混入网页的答案质量表。`token_audit.py` 通过实际聊天模板核对公共前缀，建议在计时实验之间运行。

## 数据和结果

数据固定 revision、下载地址、许可及哈希保存于 `datasets/hotpot/manifest.json`。八个校准任务与二十四个评估任务分开；这是一组短轮次初始任务清单，不构成统计充分性的声明。每轮 `config.json` 保存代码哈希、输入哈希、模型及服务配置。每轮保留所有失败，离线输出 `scored.jsonl` 和 `summary.json`，统计 EM、F1、来源标题召回、时延、调用数、token、等待与抢占。图固定不代表浮点批处理下文本必然相同，比较时须核对实际工作量。

大权重、原始 parquet、请求日志保存在远端，仓库同步配置、索引和统计摘要。不要将 `answers.jsonl` 加入运行时控制器输入。每轮通常数分钟，按批次控制规模，长尾或失败不得删去。
