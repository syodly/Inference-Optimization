# 当前执行状态（2026-10-29，持续迭代）

用户要求在 songprojgpu1 真实实验，短轮次，逐项验证痛点，先证据后机制，每轮约 300 字记录，直到用户手动停止。完整约束见 AGENTS.md。当前目标仍为 active，不要把阶段结果当作任务完成。

- 远端目录 `/home/Liangyijia_Hu/harness-engine`；SSH 配置已经可用。模型和隔离环境已装好，不重复下载。
- 运行服务 Qwen3.8-27B BF16，GPU 0/1，vLLM 图模式，64K，48 sequences，8192 batched tokens，priority 调度。
- v010 八题长文实验全部结束；原生两次平均 110.27 / 109.44 秒，压力反馈 105.34 秒，EM 都为 6/8。暂属小幅观察，不能声明有效。fixed16 平均 105.05 秒但 5/8；需要固定请求回放排除输出工作量差异。
- v011 将七调用工作图扩展为十调用引用核验工作图：query → 真检索 → draft → 真来源验证 → evidence → parent join。验证工具没有 gold；受控延迟单独标记，不冒充生产测量。
- 为 v011 已重启本项目服务，启用 per-request metrics、prompt cached token 明细、cache residency metrics；server-v010-before-telemetry.json 保存前一配置。启动日志为 logs/engine-graph.log，新进程 PID 存 state/server.json。
- v011 完成：短文单题与八题共同任务的命中完全相同，不能把总体比例降低当缓存退化；引擎缓存块 784 token。长文全被 Markdown 围栏误判解析失败，该轮不合格。v012 已修复完整围栏解析。
- v012全部结束。自然八题80调用、EM=5/8、平均169.41秒、evidence命中0、22次抢占。延迟八题167.67秒、命中0、5次抢占。四题校准命中81.9%、零抢占。
- v014全部结束。fixed12=181.49秒/0命中；return12=166.64秒/44.8%命中；session12=157.15秒但P95=207.95；session18=151.35秒/P95=183.07/32.2%命中；fixed18=162.84秒/0命中；backend_priority=168.72秒/0命中/13抢占；native重复171.21秒/0命中/12抢占。Session18与首个native都是5/8、49176/48930输出token，不能以单次比较宣称加速。
- 当前远端后台运行 `replay_batch.py configs/replay-verified-v015.json`，PID1127348，日志 `logs/batch-replay-verified-v015.log`，状态 `state/batch-replay-verified-v015.json`。已完成native-a=167.64秒，80/80输入相同、80/80配额相同，48930实际解码token。后续fixed12/return12/session18/backend/native-b顺序运行。
- v015完成后优先修正token审计并在计时批次之间重跑。新版token_audit.py已在本地修复历史reasoning_content→reasoning标准化，但尚未部署；/tokenize接口与Chat接口旧行为不一致，旧长文token_audit.json的匹配字段为false，不能作精确前缀证据。实际usage命中数不受影响。
- 后续跑v016自然/延迟下的Session窗口和回流强基线，并加强回流排序的老化参数对照；再跑旧v010的56调用replay-v013。回放不得进入闭环质量表。图与网页已生成，待提交推送并核对外部入口。
- 当前引擎实际缓存容量282532 token，旧v010为217725；启动参数虽近似相同，不能跨重启直接归因。run.py已新增实际启动容量证据，待部署。新引擎PID1036307，仅GPU0/1。
- 后续优先项：精确 token 前缀一致性审计；八题长文的相同请求与依赖回放；确认工具回流是否损失缓存后比较 session 工作集上限、回流优先、资源/在途状态感知。若没有痛点，记录负结果并扩大结构多样性而非制造空工作。
- 所有原始 prompt/response/tools/events/metrics 和代码快照在远端 runs/；本地 results/ 同步摘要及一条完整根任务。RESEARCH_LOG.md 当前以远端为主，每批结束后拉取，避免覆盖远端新记录。
- 不并行运行争用同一引擎的实验。独立文件/日志检查可以并行。用户要求持续并未要求多 Agent，不启动子 Agent。
