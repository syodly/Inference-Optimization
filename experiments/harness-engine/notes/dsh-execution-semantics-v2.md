# DSH语义核对与执行日志第二版（待下一批部署）

回查已保存的DSH包文档，`maxActiveSubagents`默认8，按每棵activation树共享，根父Agent不占名额，等待中的父执行仍计数；它不是所有用户共享引擎的全局请求限制。在当前固定三子任务、无孙任务的图里，该默认限制不会触发。我们额外比较的全局Session窗口18覆盖多个根任务，不能称为DSH原生旋钮，也不等于创新机制。另一个修正是一次研究子Agent执行包含query、检索、draft、核验和evidence等多次模型调用；旧日志的activation_start/end实际标记单次模型请求，名称不准确。第二版明确写model_call与agent_execution两层区间，后者只表示本原型的一次研究任务执行，不冒充DSH完整驻留activation生命周期。旧日志不重写，已有耗时和调用量不变；页面先修正解释，下一批完整实验再审核新跨度、工具包含关系和模型调用账目。

来源：已保存的`packages__subagent__subagent__README.md`的“Activation capacity”段，公开地址：<https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/subagent/subagent/README.md#activation-capacity>。对应受控场景是多份独立研究任务共享同一引擎，每根三个研究子Session；它没有模拟冷恢复、嵌套委派、收件箱及DSH的完整资源清理。

实现修改：`run.py`、`replay.py`、`audit.py`；配置标记`trace_semantics_version=2`。当前v017保持原代码，结束后将这些文件与额度账本第二版一起部署，避免批次内变更。
