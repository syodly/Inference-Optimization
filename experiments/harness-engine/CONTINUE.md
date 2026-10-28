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
- v015已经全部结束。native-a/b=167.64/168.49秒；fixed12=190.87；return12=165.71；session18=155.61；backend_priority=183.86。六轮80/80输入相同、80/80解码配额相同、48930实际输出token、无错误。Session均值差距约7%，但P95=206.55，高于native的203.18/204.07，不能宣称长尾改善。结果单列results/replays，已拉回本地；不要放进闭环质量表。
- token审计已修复并部署（engine.tokenize_payload共用reasoning_content→reasoning标准化）。在v015与v016计时批次之间重跑v012 native / v014 session18 / native-repeat，三组80次实际token计数全部匹配。旧错误审计备份在远端各run内token_audit-v001-legacy-field-mismatch.json；本地results内token_audit.json已是修正版，尚未提交。
- v016已全部结束并拉回本地。校准40次测量全匹配。return18+120秒老化均值151.21秒/P95 176.32，EM=6/8、46048输出token；return24为163.73秒、6/8、47068token。强调优普通排序已接近Session窗口，不再把窗口当作独立创新证据。
- v018强基线固定工作量复核已全部结束。native=167.30秒/P95 202.83，return18=156.02秒/P95 200.00，return12=156.82秒/P95 219.41；均80/80输入和配额一致、48930输出token、无错误。return18与v015窗口18的155.61秒差不足0.5秒。结果和约300字归因记录在results/replays与notes/v018-strong-baseline-audit.md。
- v019新增history_audit.py，只分析日志，不发模型请求。v012自然24次回流平均9.25毫秒，期间零新冷draft，不能归因于“长工具等待被后续任务挤出”；需要区分已有并发工作、后端队列、混合注意力检查点保留。三组逐Session审计已同步results，说明在notes/v019-return-gap-audit.md。
- 当前后台为 `batch.py configs/mixed-history-v017.json`，PID1231297；状态state/batch-mixed-history-v017.json，日志logs/batch-mixed-history-v017.log。校准8题已完成，80调用/48工具、无审计错误、80次实际长度全匹配。首个16题native已完成：均值171.84秒、长200.42秒/5对8、短143.25秒/F1=.675、66893输出token、76抢占。无额外测量native为168.57秒、长199.38秒/7对8、短137.76秒/F1=.8、66879token、75抢占；输出总量相近但答题不同，不能由这一对比较归因为测量改善质量。当前进入fixed18。
- v017已有代码全部部署，长短混合来源清单固定，分组评分；额外加入return18和size_return18/24。size_return只按已就绪prompt大小排序，检验预算收益是否仅是短请求先完成。必须保留无额外测量的native/return强对照。历史额度在实际输出及evidence输入变大时可超出目标；校准观测峰值101920大于100000，属于软目标，不宣称硬上限或物理驻留。
- v017后执行已上传configs/tool-return-v020.json，六轮独立短实验，真实来源工具后注入12±3秒，对比native重复、return18、session18、history200k和history_pressure。注入不提供给控制器、不冒充自然工具痛点。再考虑旧v010的56调用回放及同信息/同展开权限后端强对照。不得只用阶段优先级宣称前端独有优势。
- 网页增加v018/v019关键负结果、按实际质量协议辨别v016长文、混合任务分组得分及筛选；本地索引65个闭环轮次。Edge无窗口渲染验证17节点/18箭头、展开原始prompt、混合筛选，移动端无页面溢出、无JS错误。截图在evidence/web-v019，已重拍等待关闭动画结束，显示实际16题结果。新改动即将提交推送。
- 本地另有ledger-v2测量改动待下一批部署：额度申请/增长/释放事件及总账审计、软目标超出量。不要在v017中途替换scheduler/analyze/audit，保持批次内稳定；v017结束后部署再启动v020。replay.py的分组独立对照与预算/长度测量支持已上传但尚未运行，configs/mixed-replay-v021.json也已上传，必须完整执行验证，不能把代码当实测结果。
- 当前引擎实际缓存容量282532 token，旧v010为217725；启动参数虽近似相同，不能跨重启直接归因。run.py已新增实际启动容量证据，待部署。新引擎PID1036307，仅GPU0/1。
- 后续优先项：精确 token 前缀一致性审计；八题长文的相同请求与依赖回放；确认工具回流是否损失缓存后比较 session 工作集上限、回流优先、资源/在途状态感知。若没有痛点，记录负结果并扩大结构多样性而非制造空工作。
- 所有原始 prompt/response/tools/events/metrics 和代码快照在远端 runs/；本地 results/ 同步摘要及一条完整根任务。RESEARCH_LOG.md 当前以远端为主，每批结束后拉取，避免覆盖远端新记录。
- 不并行运行争用同一引擎的实验。独立文件/日志检查可以并行。用户要求持续并未要求多 Agent，不启动子 Agent。
