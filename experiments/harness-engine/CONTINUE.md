# 当前执行状态（2026-10-29，持续迭代）

## 最新接续点：服务器时间 2026-10-29 10:32

- v020七轮闭环和v021十一轮固定工作量回放已全部完成并同步本地，不要按下面早期记录重跑。新执行语义、账本和输入/配额审计全通过。
- v021的短任务独占34.89秒、混合138.43–140.50秒；痛点成立。预算137.58秒、回流24为138.17秒，预算独立收益未成立。分组对照与图已生成：`results/v021-interference.*`及`results/figures-v021/`，见两篇v020/v021结果笔记。
- 当前运行v024共享引擎八轮批次，由`continue_shared.py`（PID1889951）在前批结束后启动。状态`state/batch-shared-load-v024.json`，当时进入`v024-shared-return24`。勿另外启动争用引擎的实验。
- 已结束target-only及shared-native-a：前者目标145.76秒；后者目标236.34秒/背景257.39秒，均为完整闭环，输出量不同，尚不作同工作量因果结论。原始日志仍在远端，各控制器独立账本和Agent执行审计通过。
- 新`shared_replay.py`/`shared_replay_batch.py`及`configs/shared-replay-v025.json`准备下一批九轮同工作量共享实验，双方固定请求及解码量，单独移除一组验证干扰，再比较强回流、压力、预算、窗口。`offline_replay_inputs.py`对完整200次输入重建全通过，不把该CPU验证冒充GPU性能实验。
- `after_batch.py`负责等待v024全部完成后再启动v025；部署/启动状态请检查`state/continuation-shared-replay-v025.json`。如果状态不存在则尚未启动，勿重复创建。
- 共享实验的脚本为`shared.py`，网页已增加共享类型和两组耗时/质量，尚需拉取最新完整结果并浏览器回归验证、提交推送。没有把回放混入闭环答题表。
- `token_audit.py`新增可选`--local-tokenizer`，可使用已下载权重的CPU tokenizer；尚未执行新版，不能当作新证据。不要对正在计时的引擎额外发送批量tokenize。
- 当前引擎未重启，仍仅GPU0/1、Qwen3.8-27B BF16、vLLM0.32、64K/48seq/8192batched tokens。检查实际混合注意力缓存代码发现共享junction开关受EAGLE等条件约束，不能以打开一个无效参数声称补了后端强基线。
- 研究目标保持active，用户只要求继续，没有要求多Agent。每轮仍记录约300字，不以某一批结束为整体完成。

## 较早接续记录（保留来龙去脉，以最新段落为准）

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
- 新增自动衔接器 `continue_batches.py`，PID1306985，状态`state/continuation-v020-v021.json`目前waiting。它会等v017声明的12轮全部完成，再从`stage-v2/`部署已经上传的十个文件，先运行v020六轮闭环，再运行v021九轮固定工作量对照；不要另行手动启动这两批造成争用。每轮几分钟，批次由多轮组成。STOP阻止后续轮次，失败不会自动重跑。日志`logs/continuation-v020-v021.log`。
- `stage-v2`还包含DSH语义修复：新`run.py/replay.py`统一使用`model_calls`计数、`model_call_start/end`和`agent_execution_start/end`两层日志，配置`trace_semantics_version=2`；`audit.py`检查Agent执行区间包含全部模型/工具。必须成套部署，不要把新的run.py与旧的replay.py混用。旧v017每模型调用误名activation的原始日志保留，并在网站及notes/dsh-execution-semantics-v2.md说明。
- v017又完成：fixed18均值184.37秒/P95 219.14；session18=142.62/P95 237.84；return24测量=138.30/213.26；return24无测量=134.99/211.07；return18=137.90/203.00；size18=127.68/224.78（短58.79、长196.57）。原生无测量=168.57/216.99（短137.76、长199.38）。还不能判断历史预算收益，强排序已解释许多差距；size18的P95较差。当前size24在运行，随后history200k/history_pressure。
- 本地已同步71个闭环轮次，`compare_mixed.py`已生成results/v017-comparison.md/json，分组报告质量与工作量。v018作图代码与PNG/SVG/JSON已生成并视觉检查；网页新增展开图和DSH语义核对，Edge无窗口验证无JS错误、17节点/18箭头及原始Prompt展开。上次推送为b8f6f5d，当前新数据和第二版源代码待下一次提交。
- 当前引擎实际缓存容量282532 token，旧v010为217725；启动参数虽近似相同，不能跨重启直接归因。run.py已新增实际启动容量证据，待部署。新引擎PID1036307，仅GPU0/1。
- 后续优先项：精确 token 前缀一致性审计；八题长文的相同请求与依赖回放；确认工具回流是否损失缓存后比较 session 工作集上限、回流优先、资源/在途状态感知。若没有痛点，记录负结果并扩大结构多样性而非制造空工作。
- 所有原始 prompt/response/tools/events/metrics 和代码快照在远端 runs/；本地 results/ 同步摘要及一条完整根任务。RESEARCH_LOG.md 当前以远端为主，每批结束后拉取，避免覆盖远端新记录。
- 不并行运行争用同一引擎的实验。独立文件/日志检查可以并行。用户要求持续并未要求多 Agent，不启动子 Agent。
