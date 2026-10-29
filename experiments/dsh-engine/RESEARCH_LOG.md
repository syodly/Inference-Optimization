# 官方 DSH 部署、验收与研究边界记录

## dsh-deploy-v001 · 2026-10-29 · 官方发行版与独立环境

本轮将官方 DeepSeek Harness 部署到 songprojgpu1 的独立 dsh-lab，纠正此前“没有完整源码”和将自建框架近似称为 DSH 的表述。安装固定发行包 0.2.1-rc.2，并保存对应源码标签与提交；更新的 master 快照另存，不混同实际运行版本。服务器原 Node 过旧，使用独立 Node 24.22.2，不改系统环境。复用此前经 ModelScope 下载校验的 Qwen3.8-27B 权重和 vLLM 环境，在确认 GPU 0/1 空闲后启动独立接口，加入 Qwen XML 工具调用解析。原实验 STOP 保持不变，不恢复性能批次。本轮没有修改官方源码，也没有植入新调度器；成果是建立可追溯的真实系统基线，安装成功不作为性能或创新证据。

配置：[qwen.patch.yml](qwen.patch.yml)、[start_engine.py](start_engine.py)；来源：[source.json](evidence/deployment-20261029/source.json)。

## dsh-accept-v001 · 2026-10-29 · 原生委派与真实模型调用

本轮在官方 CLI 中以 Qwen 执行真实验收。先验证自动工具参数解析和普通对话，再使用公开 HotpotQA 的一题，把十篇原始资料分成三份文件，要求父 Agent 创建三个原生子 Agent。原生会话日志证明每个孩子各读一个分片、发送报告、正常结束，无嵌套委派、网络访问或工具错误；父 Agent 接收报告及完成通知后汇总。模型调用实际为父八次、各子三次，共十七次，另有一次标题生成，不能沿用旧固定十调用 DAG 的账目。最终答案实体与隐藏标签相符，但十七世纪的时间界定含间接推断，单题不代表准确率。全部主任务请求、响应、prompt、工具参数、原生事件和资料均已归档。这只能证明原生多 Agent 路径可运行，尚未证明共享负载痛点或调度收益。

证据：[验收报告](evidence/deployment-20261029/acceptance/report.json)、[完整原始证据](evidence/deployment-20261029/deployment-20261029-raw.tar.gz)。

## dsh-accept-v002 · 2026-10-29 · Web、Shell 与定位复核

本轮通过临时 SSH 隧道打开官方 Web，完成进程 token 与浏览器会话的登录交换，页面 HTTP 200、无脚本错误，界面显示本地 Qwen 及 low reasoning。复验不发送模型 prompt，检查后关闭隧道；登录 token 不写入仓库。另让官方 CLI 真正调用一次 Bash 输出常量，工具和最终回复均成功，确认不只是文件读取可用。源码复核发现 activation 容量、完成通知、workflow 并行汇合和 vLLM 优先级本已存在，不能作为我们的贡献。研究建议收敛为工作流已知依赖与动态引擎压力共同决定合法推进顺序；先比较原生 subagent、workflow 和简单静态策略，再判断是否值得设计新机制。当前留存官方服务供后续使用，GPU 用于模型服务，旧实验继续暂停。

证据：[Web 报告](evidence/deployment-20261029/web/report.json)、[官方界面](evidence/deployment-20261029/web/official-dsh-web.png)、[研究定位与固定版本源码](RESEARCH_POSITION.md)。Shell 的完整日志随原始证据压缩包归档。
