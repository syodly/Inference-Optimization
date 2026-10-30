# 官方 DSH × Qwen 部署与原生轨迹

**当前批次：按用户确认，只观察官方DSH执行的六道公开原题，已结束并归档。** 统一DSH→vLLM→Qwen3.8-27B，没有运行ODR/GPT/CRAG算法。研究题为DeepResearchBench #19/#93，代码题为LiveCodeBench abc387_c/f，检索问答为CRAG材料中的两道PopQA原题及原始段落。六题均未自主委派子Agent；两道研究题工具在途峰值2。代码中等题公开3/3、隐藏40/40，难题8192输出预算截断、无代码；PopQA两题答案别名匹配通过。研究工具缺搜索凭据，#19输出未验证，#93重试后停止，不能称作六题成功或正常联网研究质量评测。

先看[本轮原题与可播放流程](../../LLM_Optimization_Milestone/topic1-dag-observation.html#observation)，完整结论在[总报告开头](notes/natural-dag-20261029.md)，数据在[六题结果索引](results/public-tasks-20261030-v001/index.json)、[来源哈希](results/public-tasks-20261030-v001/source-manifest.json)与[单一原始包入口](evidence/public-tasks-20261030-v001/index.json)。逐次Prompt、参数、工具结果和中国时间可在图中展开。`python -X utf8 experiments/dsh-engine/dataset_observation.py export`仅从已收取原包离线生成视图，不请求模型；`verify_natural_web.py`核对新六题与旧视图。未扩样。

以下保留部署与此前各批次的历史进展；旧覆盖统计只针对当时批次。

**2026-10-29 已在 `songprojgpu1` 部署官方 DeepSeek Harness，接现有 Qwen3.8-27B。官方源码未修改。** 普通对话、原生 Bash 工具、三个原生子 Agent 的资料读取与父汇总均已通过验收；Web 页面经浏览器验证为 HTTP 200、无页面脚本错误。这是部署验收，不是调度性能实验。

旧 `harness-engine` 是自行实现的受控 Harness，不是官方 DSH。它的实验批次继续暂停，原 STOP 保留；新部署独立使用 `/home/Liangyijia_Hu/dsh-lab`，当前 GPU 0/1 用于 Qwen 服务。之前“拿不到 DSH 完整源码”的表述已纠正：官方仓库提供 MIT 源码。

**随后按用户最新要求完成了最小八题对照组：直接派发、固定12、实际压力反馈12，各一轮。** 平均每题分别为48.43、60.70、60.47秒；压力策略未触发收缩，尚无反馈收益。这里只做这组小实验，不恢复原v025等大批次。详见 [完整结果及边界](notes/e1-small-20261029.md)。

三轮已接入[网页实验选择器](../../LLM_Optimization_Milestone/topic1-experiments.html#dsh-e1-small-native)，默认显示官方DSH；每轮八题均可切换，流程节点可展开完整messages、API参数、模型返回和派发时的真实引擎状态。浏览器数据由 `python experiments/dsh-engine/export_results_web.py` 从已归档证据离线导出，不重跑模型；`verify_results_web.py` 检查全部24个逐题流程及旧实验切换。

**最新：完成五类只给初始任务的自然DAG观察。** 简单问答、多文档调查、代码修复、CSV分析、故障诊断没有指定Agent数量或未来步骤。五类均自然选择一个根Agent，模型调用数为1、13、6、16、5；工具依赖图随执行增长。保留两次4096输出触顶的首轮，再以更大输出上限从头执行两类。详见[观察报告与时间点](notes/natural-dag-20261029.md)及[时间轴页面](../../LLM_Optimization_Milestone/topic1-dag-observation.html)。全部原始调用与事件均归档，没有恢复旧性能批次。

**10月30日来源复核：** ODR 的7次、GPT Researcher的5次是Codex自编编排核对题的诊断尝试，包含失败和重跑；均未做公开研究数据集。页面ODR三个标签是v005/v006/v007变体，不是三类数据。DSH18次分为HotpotQA六题合并调查7次、架构核对3次、源码审查2次、四份虚构资料2次、算术2次、开放调查2次。只有第一类含公开原题，外层报告任务自编。“四组件”不是DSH真实四组件。**CRAG完整LLM流程、公开Coding基准尚未完成**；既有函数核对和自编小服务修复仅为局部验证。

所有逐次来源、原始任务、变量和归档位置集中在[统一实验索引](results/natural-dag-20261029/frameworks/experiment-catalogue.json)，可读说明集中在[总报告](notes/natural-dag-20261029.md)，交互展示复用原[观察页](../../LLM_Optimization_Milestone/topic1-dag-observation.html#frameworks)。只有两个当前原始包入口：[DSH18次](evidence/autonomy-20261030-v002/index.json)、[原生ODR/GPT12次](evidence/upstream-workflows-20261030-v003/index.json)；旧快照按run_id去重，不重复计数。原工作流结构图保持互通。`export_natural_site.py`导出旧DSH数据，`export_framework_observation.py`导出原生框架与来源索引；均为离线导出，不请求模型。未改公共环境，未恢复旧批次，本轮未推送。

## 当前安装

| 项目 | 实际配置 |
|---|---|
| 官方运行包 | `@deepseek-ai/dsh@0.2.1-rc.2`，不是内部 SDK 入口替代品 |
| 对应源码 | 标签 `dsh-v0.2.1-rc.2`，提交 `687f282e8625c6b8d11ff58211a90524be2e4317` |
| 独立 Node | `v24.22.2`，不覆盖服务器原有 Node |
| 模型 | ModelScope `Qwen/Qwen3.8-27B`，复用此前已下载、校验的 BF16 权重 |
| 引擎 | vLLM `0.32.0`，TP=2，GPU 0/1，64K，48 sequences，8192 batched tokens |
| Qwen 解析 | `qwen3_xml` 工具解析、`qwen3` reasoning 解析、low reasoning |
| 模型接口 | `127.0.0.1:18082`；观测转发 `127.0.0.1:18083` |
| 官方 Web | `127.0.0.1:13080`，只通过 SSH 转发访问 |
| 独立会话目录 | `/home/Liangyijia_Hu/dsh-lab/home` |

安装时也保存了更新的 master 快照 `f3803c9…`，但它不是本次运行包对应源码。所有能力判断优先依据上述固定发行版本。完整来源见 [源码清单](evidence/deployment-20261029/source.json)。

实际调用链是：**DSH 原生 Agent 循环 → 记录原始流量的 HTTP 转发 → vLLM → Qwen**。转发器只记录，不改 prompt、响应、优先级或派发顺序；常驻Web配置未加反馈调度。随后的小组实验另用 `e1-plugin.mjs` 在官方 `agent/request` 扩展点等待派发许可，使用静态上限或真实引擎压力基线；这些都是实验基线，不是已提出的新机制。

## 验收到底执行了什么

公开 HotpotQA 问题：“英国水猎犬和爱沙尼亚猎犬，哪个更早培育？”将原有十篇资料按文档轮转分给三份文件。父 Agent 必须调用三次原生 `subagent`；每个子 Agent 使用真实 `read` 读取自己的分片，调用 `send_message` 汇报，再结束。父 Agent 接收报告和原生完成通知后汇总，最终答案实体与隐藏标签相符。该单题不代表数据集准确率；输出对“17 世纪”的界定含间接推断，不能据此宣称证据推理完全可靠。

| 执行者 | 模型调用 | 实际工具 |
|---|---:|---|
| 父 Agent | 8 | `glob` ×1，`subagent` ×3，`list_agents` ×1 |
| 子 Agent 0 | 3 | `read` ×1，`send_message` ×1 |
| 子 Agent 1 | 3 | `read` ×1，`send_message` ×1 |
| 子 Agent 2 | 3 | `read` ×1，`send_message` ×1 |
| 标题生成 | 1 | 辅助模型调用，单独计账 |

合计 **17 次 Agent 调用 + 1 次标题调用**，该任务的 18 个接口响应均为 HTTP 200，所有工具结果无错误。父 Agent 的消息/结束通知会触发后续模型步骤，因此不能套用旧框架“每任务固定十次调用”的计数。普通对话和单次 Bash 验收另列，不能混入这个 18 次统计。

可直接检查 [完整验收报告](evidence/deployment-20261029/acceptance/report.json)、[父 prompt](evidence/deployment-20261029/acceptance/subagent-prompt.txt)、[浏览器验收](evidence/deployment-20261029/web/report.json)和 [官方界面截图](evidence/deployment-20261029/web/official-dsh-web.png)。[原始证据压缩包](evidence/deployment-20261029/deployment-20261029-raw.tar.gz)保存完整模型请求/流式响应、所有原生会话事件、输入分片、子 Agent prompt、工具参数/结果、离线标签及 npm lockfile；[索引](evidence/deployment-20261029/deployment-20261029-index.json)提供 SHA256。Web 登录 token 不入仓库。

## 与旧系统的区别及论文定位

| 项目 | 旧自建 Harness | 本次官方 DSH |
|---|---|---|
| 流程来源 | Python 固定三分支 DAG | Qwen 使用原生委派、工具与消息机制 |
| Agent 生命周期 | 实验内简化的执行区间 | 官方 Session、activation、收件箱、完成通知与清理 |
| 调用数量 | `verified` 每根十次必做调用 | 本次实测父 8、各子 3；随实际模型动作变化 |
| 派发控制 | 已有静态窗口、回流、压力等实验策略 | 常驻Web保持原生；最小组另接静态/压力基线插件 |
| 用途 | 隔离变量、回放、对照 | 测量真实 Harness 行为并承载后续机制 |

建议在官方 DSH 上用插件或最小补丁实现研究机制。Session 管理、创建/取消/恢复 Agent、每棵树的容量限制都已经存在，不应重做后当成贡献。`workflow` 工具的 `parallel/pipeline` 已可表达汇合，兼容接口也已有 `vllmPriority`；“合并父唤醒”或“设置优先级”本身同样不足以构成创新。

候选问题应是：**多个工作流共享推理引擎时，如何同时利用已知依赖/工具状态和实际引擎压力，选择下一步推进哪个合法工作，使完整任务更早完成？** 是否必须在前端决策、需要哪些后端信息、简单静态策略能否替代，都须验证。只看到当前这条原生轨迹，尚不能宣称性能痛点或新颖性成立。详细边界、对照要求和可落地接口见 [研究定位](RESEARCH_POSITION.md)。

## 使用和复现

SSH 登录服务器后，直接使用官方 CLI：

```bash
cd /home/Liangyijia_Hu/dsh-lab
./dsh --version
./dsh --profile headless --json 'Reply with exactly: QWEN_DSH_READY'
```

本机另开终端转发 Web：

```powershell
ssh -N -L 13080:127.0.0.1:13080 songprojgpu1
```

登录地址从服务器 `dsh-lab/logs/web.log` 读取，将其中端口保持为 `13080` 后在本机浏览器打开；地址带当前进程的登录 token，普通无 token URL 初次访问返回 401 属于预期。用户自己的登录地址不应写入公开页面。

当前服务已运行，不要重复启动。需要重启时，先只停止 `state/{engine,observer,web}.json` 记录且确认属于本部署的进程，再按顺序运行：

```bash
cd /home/Liangyijia_Hu/dsh-lab
python3 start_engine.py
# 等 logs/qwen-engine.log 显示服务就绪，并确认 /health 返回 200
python3 start_services.py
```

此目录的 `start_engine.py`、`start_services.py`、`observe_api.py` 和 `qwen.patch.yml` 是相应文件；重启脚本不恢复旧实验。采集已完成验收的证据执行 `python3 collect_evidence.py`，不会发出新模型请求。本机执行 `python experiments/dsh-engine/verify_web.py` 可做临时 SSH 隧道和浏览器复验，检查结束关闭隧道。

重新安装官方运行包时，在服务器独立 `runtime` 目录使用证据包内的 `package.json` / `package-lock.json`，将独立 Node 加入 PATH 后执行 `npm ci`。Node Linux x64 压缩包来自官方 `https://nodejs.org/dist/v24.22.2/node-v24.22.2-linux-x64.tar.xz`，SHA256 为 `48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75`。模型环境仍依赖旧目录已校验的权重和 `.venv-engine`，没有重复下载几十 GB 模型。

部署和验收记录见 [RESEARCH_LOG.md](RESEARCH_LOG.md)。
