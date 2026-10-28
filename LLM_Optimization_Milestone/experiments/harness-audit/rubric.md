# 离线核查依据：不传入在线控制器

以下是八题必须核对的事实清单，不是模型已生成的结果。评分同时核对结论与固定 revision 的引用。按题报告通过／不通过及缺项；不要只检查关键词是否出现。

- context：spawn 不带父 transcript；fork 只带完整轮次、不带当前 in-flight turn；不是 live sharing；缓存复用依赖相同请求前缀／模型等条件。
- capacity：默认 8；顶层 root 不占；后代共池；满额拒绝不排队；默认工具深度 1；activation 与 Engine 调用并发不同。
- delivery：parent 有通知、caller 无；idle 父会唤醒、busy 父 Steer；多通知与多次父推理不能直接等同。
- interrupt：本地只停止当前轮次，确认不是完成；未消费消息可停留，后代继续；dispose/drain 是清理与归还边界；不能把运行中有副作用工具当可免费回滚。
- catalog：running/inactive 是轮次活动情况，均不等于任务质量或完成；成员目录不含执行状态；快照不是送达承诺；没有分页／删除会增加历史枚举成本。
- resume：需要持久化与 Session query，合法直接父子身份、可恢复 descriptor；本地会重建 activation；DSH 接口下外部一次执行不可 follow-up；不能推广为外部产品没有多轮。
- capacity-followup：降上限不杀既有实例；阻止新的创建／冷恢复直至低于上限；向驻留 child 发消息复用槽。
- interrupt-followup：文档明确 cancellation convergence 中的 wake gap；已接受输入可能停留到另一次 waking send；不能把接受身份解释成已经处理。

这些题目是源码理解与机制审计。即使全通过也不能替代 SWE-bench 的代码修复率或研究报告质量评测。
