# Harness 实验准备：先记录真实执行

本目录包含任务清单与规范化日志审计器；没有 DSH 启动器、collector、模型输出或性能结果。官方 API 的事件不足以直接导出以下所有字段，需要在固定源码版本增加适配器。审计器单元测试的手工事件只用于检查计算正确性，不能当成研究证据。

固定 DSH revision：`f3803c96974ad4a94195fb97e5c637e9c2a3afe3`。

## 先跑什么

`tasks.json` 是六个真实源码／文档核查问题与两次续接问题，模拟用户截图里的分工检查。它不是标准 benchmark。工作目录应是固定 revision 的 DSH checkout，或具有相同路径的只读快照。每个任务输出结论、文件／行号、限制及不确定性；评分依据见独立的 `rubric.md`，不要传给在线控制器。

E1 对照：全部新 spawn、全部新 full fork、仅对允许追问续接同一子 Session、简单固定规则。固定模型、preset、权限、工具与证据集，当前问题在所有模式下都显式传入。对初始六题的隔离约束保持相同；不能将本来要求独立审查的任务强制复用。

E2 对照：原生 parent delivery；caller delivery＋程序全等；caller＋澄清立即交付；小型固定窗口。先用真实记录核查父级是否多次只是在等，再做闭环比较。所有消息完整保留；未知／控制消息立即交付。澄清任务另加一个可验证的中途提问，不要只跑全等组就宣称动态依赖收益。

E3 条件实验：默认深度 1 和显式深度 2 分开记录，不能让默认值悄悄产生递归。先量出等后代、停留 inbox 和清理占槽的比例；没有问题就不实现挂起。中断、静止、后代停止、释放分别记录。

先做短历史／实际长历史、冷／暖缓存的配对小样本，交错运行顺序；只在能量到实际缓存行为的后端使用缓存维度。远程模型 API 没有该字段就标 unknown。不要把累计输入 token 当成未命中 prefill，更不要换模型获得“上下文策略收益”。

## 规范化 JSONL：拟议导出格式

每行都含 `run_id`、`policy`、`ts_ms` 和 `event`，`ts_ms` 是同一 run 的单调时间轴。run 指一次完整试验，policy 不得在同一 run 中变化。这里的事件名是**本实验拟议的导出格式，不是 DSH 原生事件名**。

| event | 其他字段 | 导出位置／边界 |
|---|---|---|
| `delegate` | `task_id`, `child_id`, `mode` | 委派适配器；mode 为 spawn / fork / continue |
| `task_start` / `task_end` | `task_id`; end 有 `success`，可另存 score | 任务驱动与离线评分；不要把一次 activation 结束当任务成功 |
| `llm_end` | `request_id`, `actor`（parent / child）, `input_tokens`, `output_tokens`, `cached_tokens` | 模型适配器实际 usage；缺项用 null。重试请求要有独立身份 |
| `artifact_read` | `task_id`, `artifact_id`, `version`, `bytes` | 工具适配器；同文件同版本多次读取才计重读 |
| `message_accepted` | `message_id`, `kind` | 在 inbox 接受后记；接受不是对方完成 |
| `message_consumed` | `message_id`, `request_id` | 首次消费并映射到实际看见该消息的父模型请求；不能扫描整段历史重复计数 |
| `activation_reserved` | `activation_id`, `child_id` | pool 实际占槽成功后；同 Session 每次冷恢复使用新 activation id |
| `activation_state` | `activation_id`, `state` | 对执行状态、ownedChildren、inbox 与清理分别观测；不是仅凭 list_agents 推断 |
| `activation_released` | `activation_id` | 清理完成后真正归还槽位 |
| `activation_rejected` | `reason` | 满额等实际拒绝路径 |

state 取 `materializing`、`running`、`wait_tool`、`wait_children`、`parked_inbox`、`stopping` 或 `other`；状态是导出适配器的分类，不是声称 DSH 已有一套同名公开状态机。分类依据必须随原日志一起保存。只要还没有 release，就在截止时刻报告未释放，不能补成“已完成”。

每个 trial 另外保存实际任务 prompt、逐次消息／输出、路由与 preset 的版本、上下文指纹、文件内容哈希及随机种子。它们放在本地制品中；审计器只需身份和数值，不读取或伪造 prompt。峰值 RSS、Engine 请求起止、实际 KV 与 prefill 时间应独立导出，当前脚本不从 activation 槽位推算它们。

## 审计日志

```powershell
python analyze_trace.py path/to/real-normalized-trace.jsonl --out audit.json
python -m unittest discover -s . -p "test_*.py"
```

脚本输出每个 run 的任务耗时、实际 usage 覆盖率、父级请求数、消息首次消费等待、文件重读和各状态的槽位时间。缺失 token 项输出 null，并列出覆盖率；未完成任务、未消费消息、未释放实例保留为未完成，不能被当成零耗时或已丢失。

它不推断哪次推理“没用”、哪些 token 可省，也不跨不同任务／缓存条件自动比较策略胜负。因果收益需从相同任务、同资源的配对真实闭环实验获得。
