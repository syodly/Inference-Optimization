# Harness–Engine 实验

在 `songprojgpu1:/home/Liangyijia_Hu/harness-engine` 运行。研究规则见 [AGENTS.md](AGENTS.md)，持续清单见 [PLAN.md](PLAN.md)，每轮记录见 [RESEARCH_LOG.md](RESEARCH_LOG.md)。

## 当前应用

这是自行实现、与 DSH 动作相似的 Harness，**不声称复现完整 DSH**。公开 HotpotQA 上下文被固定分为三个文档分片。每个任务创建三个持久子 Session，依次执行真实模型生成检索词、真实 BM25 工具、真实模型证据整理；父 Session 等待全部子任务，调用模型给出带来源的答案。默认每任务七次模型调用，全部为必做工作。该受控 DAG 用于隔离派发行为；更复杂的动态图和质量驱动展开放在独立实验。

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

服务默认双卡 BF16、16K 上下文、48 活跃序列上限、8192 批 token、前缀缓存和分块 prefill，先使用 eager 模式；完整参数及启动资源证据保存到 `state/server.json`。后续需要在相同配置下单独比较图执行模式，不能把 eager 校准结论当作引擎最高性能。

四个初始基线：`native` 直接派发；`fixed --cap N` 固定在途调用数；`pressure` 根据真实引擎等待与缓存占用收缩；`progress` 同 cap 下优先汇总和接近完成的任务，保留老化。后三者均需与静态 cap 扫描比较。新机制须以测得的痛点为依据。

## 数据和结果

数据固定 revision、下载地址、许可及哈希保存于 `datasets/hotpot/manifest.json`。八个校准任务与二十四个评估任务分开；这是一组短轮次初始任务清单，不构成统计充分性的声明。每轮 `config.json` 保存代码哈希、输入哈希、模型及服务配置。每轮保留所有失败，离线输出 `scored.jsonl` 和 `summary.json`，统计 EM、F1、来源标题召回、时延、调用数、token、等待与抢占。图固定不代表浮点批处理下文本必然相同，比较时须核对实际工作量。

大权重、原始 parquet、请求日志保存在远端，仓库同步配置、索引和统计摘要。不要将 `answers.jsonl` 加入运行时控制器输入。每轮通常数分钟，按批次控制规模，长尾或失败不得删去。
