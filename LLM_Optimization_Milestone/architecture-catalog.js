// Primary homes follow optimization objects; cross links are associations, not additional counts.
const ARCHITECTURE_CATALOG = [
  {
    "id": 1,
    "short": "Efficient Inference Survey",
    "home": "overview",
    "mechanism": "模型、计算、显存与 Serving 的整体技术谱系",
    "cross": [
      "compute",
      "engine",
      "kv",
      "infra"
    ],
    "href": "paper/00_Survey_on_Efficient_Inference_for_Large_Language_Models.pdf"
  },
  {
    "id": 2,
    "short": "FlashAttention",
    "home": "compute",
    "mechanism": "IO-aware tiling，减少 Attention 中间矩阵的 HBM 读写",
    "cross": [
      "infra"
    ],
    "href": "paper/16_FlashAttention.pdf"
  },
  {
    "id": 3,
    "short": "FlashAttention-2",
    "home": "compute",
    "mechanism": "重划线程块与 warp 工作，提高 Attention 并行效率",
    "cross": [
      "infra"
    ],
    "href": "paper/17_FlashAttention_2.pdf"
  },
  {
    "id": 4,
    "short": "Speculative Decoding",
    "home": "compute",
    "mechanism": "小模型提出候选，大模型并行验证，减少串行解码步骤",
    "cross": [
      "engine"
    ],
    "href": "paper/08_Fast_Inference_from_Transformers_via_Speculative_Decoding.pdf"
  },
  {
    "id": 5,
    "short": "Speculative Sampling",
    "home": "compute",
    "mechanism": "带接受与拒绝校正的 draft-and-verify 采样",
    "cross": [
      "engine"
    ],
    "href": "paper/10_Accelerating_LLM_Decoding_with_Speculative_Sampling.pdf"
  },
  {
    "id": 6,
    "short": "Medusa",
    "home": "compute",
    "mechanism": "增加多解码头，以树状候选验证多个未来 token",
    "cross": [
      "engine"
    ],
    "href": "paper/07_Medusa.pdf"
  },
  {
    "id": 7,
    "short": "SpecInfer",
    "home": "compute",
    "mechanism": "候选 token tree 与并行验证执行",
    "cross": [
      "engine"
    ],
    "href": "paper/09_SpecInfer_ASPLOS2024.pdf"
  },
  {
    "id": 8,
    "short": "Multi-token Prediction",
    "home": "compute",
    "mechanism": "通过多 token 预测训练目标提高推理吞吐",
    "cross": [
      "engine"
    ],
    "href": "paper/13_Better_and_Faster_LLMs_via_Multi_Token_Prediction.pdf"
  },
  {
    "id": 9,
    "short": "Speculative Decoding Tutorial",
    "home": "compute",
    "mechanism": "投机解码算法、接受率与实现评测的教程整理",
    "cross": [
      "engine"
    ],
    "href": "paper/11_Speculative_Decoding_Tutorial_Proposal.pdf"
  },
  {
    "id": 10,
    "short": "GPU-Initiated Overlap",
    "home": "infra",
    "mechanism": "GPU 发起细粒度计算与 collective 通信重叠",
    "cross": [
      "compute"
    ],
    "href": "paper/12_GPU_Initiated_Fine_Grained_Overlap.pdf"
  },
  {
    "id": 11,
    "short": "Orca",
    "home": "engine",
    "mechanism": "逐 iteration 重组 batch，完成请求及时退出，新请求及时进入",
    "cross": [
      "orchestration"
    ],
    "href": "papers/paper-11.html"
  },
  {
    "id": 12,
    "short": "Response Length Perception",
    "home": "engine",
    "mechanism": "预测输出长度，组织序列批次并处理估计偏差",
    "cross": [
      "orchestration"
    ],
    "href": "papers/paper-12.html"
  },
  {
    "id": 13,
    "short": "DeepSpeed-FastGen",
    "home": "engine",
    "mechanism": "Dynamic SplitFuse：切分 Prefill 并与 Decode 融合",
    "cross": [
      "compute"
    ],
    "href": "papers/paper-13.html"
  },
  {
    "id": 14,
    "short": "Sarathi",
    "home": "engine",
    "mechanism": "Chunked Prefill 与 Decode piggybacking",
    "cross": [
      "compute"
    ],
    "href": "paper/15_Sarathi_Chunked_Prefills.pdf"
  },
  {
    "id": 15,
    "short": "Sarathi-Serve",
    "home": "engine",
    "mechanism": "以 token budget 组织混合 batch，控制生成停顿",
    "cross": [
      "orchestration"
    ],
    "href": "papers/paper-15.html"
  },
  {
    "id": 16,
    "short": "ShuffleInfer",
    "home": "engine",
    "mechanism": "分离 Prefill / Decode，并按阶段资源需求放置请求",
    "cross": [
      "infra"
    ],
    "href": "papers/paper-16.html"
  },
  {
    "id": 17,
    "short": "Splitwise",
    "home": "engine",
    "mechanism": "按 Prefill / Decode 的资源特征拆分实例",
    "cross": [
      "infra"
    ],
    "href": "paper/05_Splitwise.pdf"
  },
  {
    "id": 18,
    "short": "DistServe",
    "home": "engine",
    "mechanism": "面向 goodput 联合优化 P/D 分离、放置与传输",
    "cross": [
      "infra"
    ],
    "href": "paper/14_DistServe.pdf"
  },
  {
    "id": 19,
    "short": "vLLM / PagedAttention",
    "home": "engine",
    "mechanism": "分页 KV block、非连续显存映射与共享",
    "cross": [
      "kv"
    ],
    "href": "paper/06_vLLM_PagedAttention.pdf"
  },
  {
    "id": 20,
    "short": "Parrot",
    "home": "workflow",
    "mechanism": "Semantic Variable 暴露数据依赖和应用目标，协调执行与共享",
    "cross": [
      "orchestration",
      "engine",
      "kv"
    ],
    "href": "papers/paper-20.html"
  },
  {
    "id": 21,
    "short": "MuxServe",
    "home": "infra",
    "mechanism": "多模型共享 GPU mesh，联合空间与时间复用",
    "cross": [
      "engine",
      "orchestration"
    ],
    "href": "papers/paper-21.html"
  },
  {
    "id": 22,
    "short": "Ayo / Teola",
    "home": "workflow",
    "mechanism": "展开为 primitive graph，暴露跨阶段并行与部分执行",
    "cross": [
      "orchestration",
      "engine"
    ],
    "href": "papers/paper-22.html"
  },
  {
    "id": 23,
    "short": "KVFlow",
    "home": "orchestration",
    "mechanism": "Step Graph 指导前缀保留优先级与下一 Agent 的 KV 预取",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "papers/paper-23.html"
  },
  {
    "id": 24,
    "short": "Agentix / Autellix",
    "home": "orchestration",
    "mechanism": "以程序状态、累计服务和关键路径组织多级调度",
    "cross": [
      "engine",
      "workflow"
    ],
    "href": "papers/paper-24.html"
  },
  {
    "id": 25,
    "short": "JITServe",
    "home": "orchestration",
    "mechanism": "动态修正请求信息，联合优先级与 batch 组成满足 SLO",
    "cross": [
      "engine",
      "workflow"
    ],
    "href": "paper_1/JITServe_NSDI2026.pdf"
  },
  {
    "id": 26,
    "short": "Continuum",
    "home": "orchestration",
    "mechanism": "基于工具耗时分布选择 KV TTL，并协调会话恢复",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "papers/paper-26.html"
  },
  {
    "id": 27,
    "short": "ThunderAgent",
    "home": "orchestration",
    "mechanism": "程序 active set 与准入，协调 KV 和工具环境生命周期",
    "cross": [
      "kv",
      "infra"
    ],
    "href": "papers/paper-27.html"
  },
  {
    "id": 28,
    "short": "CONCUR",
    "home": "orchestration",
    "mechanism": "根据缓存拥塞控制活跃 Agent 数，避免 thrashing",
    "cross": [
      "kv"
    ],
    "href": "papers/paper-28.html"
  },
  {
    "id": 29,
    "short": "PASTE",
    "home": "orchestration",
    "mechanism": "提前推测工具调用，匹配后复用结果并协调会话恢复",
    "cross": [
      "workflow"
    ],
    "href": "papers/paper-29.html"
  },
  {
    "id": 30,
    "short": "Multi-Segment Attention",
    "home": "kv",
    "mechanism": "分段上下文的注意力与状态组织；沿用现有调研摘要",
    "cross": [
      "compute",
      "workflow"
    ],
    "href": "paper_8_17/2606.02964v1.pdf"
  },
  {
    "id": 31,
    "short": "Aries",
    "home": "infra",
    "mechanism": "统一测量 Agent 的模型、工具、存储与网络基础设施代价",
    "cross": [
      "workflow",
      "engine"
    ],
    "href": "paper_8_17/2607.29069.pdf"
  },
  {
    "id": 32,
    "short": "Agentic Context Engineering",
    "home": "workflow",
    "mechanism": "积累、整理并演化 Agent 可持续使用的上下文",
    "cross": [
      "kv"
    ],
    "href": "papers/paper-32.html"
  },
  {
    "id": 33,
    "short": "Beyond Accuracy",
    "home": "workflow",
    "mechanism": "测量工具集成推理中的等待、重复计算与状态管理开销",
    "cross": [
      "engine",
      "orchestration"
    ],
    "href": "papers/paper-33.html"
  },
  {
    "id": 34,
    "short": "UniCache",
    "home": "kv",
    "mechanism": "按复用收益、容量与成本统一异构负载的前缀淘汰",
    "cross": [
      "orchestration"
    ],
    "href": "papers/paper-34.html"
  },
  {
    "id": 35,
    "short": "Reasoning Serving Unveiled",
    "home": "engine",
    "mechanism": "实证分析长推理的输出长度、阶段行为与服务瓶颈",
    "cross": [
      "compute",
      "infra"
    ],
    "href": "papers/paper-35.html"
  },
  {
    "id": 36,
    "short": "Online KV Compaction",
    "home": "kv",
    "mechanism": "在线压缩与回收 Agent 的历史 KV，缓解显存压力",
    "cross": [
      "workflow"
    ],
    "href": "paper_8_17/2608.00902v1.pdf"
  },
  {
    "id": 37,
    "short": "PBKV",
    "home": "orchestration",
    "mechanism": "预测动态 workflow，联合 KV 准入、保留与传输",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "paper_8_17/PBKV.pdf"
  },
  {
    "id": 38,
    "short": "Pythia",
    "home": "orchestration",
    "mechanism": "学习 workflow 路径与 prompt 构成，协调路由、缓存和扩缩容",
    "cross": [
      "kv",
      "infra",
      "workflow"
    ],
    "href": "papers/paper-38.html"
  },
  {
    "id": 39,
    "short": "CacheScout",
    "home": "orchestration",
    "mechanism": "学习 Agent 转移，为 anchor 的保留与后台 warmup 提供依据",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "papers/paper-39.html"
  },
  {
    "id": 40,
    "short": "OasisKV",
    "home": "kv",
    "mechanism": "Decode look-ahead 预测高价值 KV 子集并预取，扩展 HBM 外容量",
    "cross": [
      "infra",
      "compute"
    ],
    "href": "papers/paper-40.html"
  },
  {
    "id": 41,
    "short": "CacheBlend",
    "home": "kv",
    "mechanism": "独立文档 KV、位置校正与选择性重算；重叠加载和计算",
    "cross": [
      "compute",
      "engine"
    ],
    "href": "papers/paper-41.html"
  },
  {
    "id": 42,
    "short": "DroidSpeak",
    "home": "kv",
    "mechanism": "跨同源模型共享 KV，结合 profiling 与选定层重算",
    "cross": [
      "compute",
      "engine"
    ],
    "href": "papers/paper-42.html"
  },
  {
    "id": 43,
    "short": "ContextPilot",
    "home": "kv",
    "mechanism": "管理重叠与重排上下文的复用，分开核算初始化和单次开销",
    "cross": [
      "workflow",
      "engine"
    ],
    "href": "papers/paper-43.html"
  },
  {
    "id": 44,
    "short": "SemShareKV",
    "home": "kv",
    "mechanism": "带位置的 embedding 匹配、KV 重排、逐层重算与保留率控制",
    "cross": [
      "compute"
    ],
    "href": "papers/paper-44.html"
  },
  {
    "id": 45,
    "short": "CacheWise",
    "home": "orchestration",
    "mechanism": "Coding trace 驱动前缀感知调度与复用时间预测淘汰",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "papers/paper-45.html"
  },
  {
    "id": 46,
    "short": "Akashic",
    "home": "workflow",
    "mechanism": "MemAttention 增量压缩、关联记忆更新与检索，并共置相关记忆",
    "cross": [
      "infra"
    ],
    "href": "papers/paper-46.html"
  },
  {
    "id": 47,
    "short": "Murakkab",
    "home": "workflow",
    "mechanism": "声明式 workflow 与 profiling，联合选择模型和硬件执行配置",
    "cross": [
      "orchestration",
      "infra"
    ],
    "href": "papers/paper-47.html"
  },
  {
    "id": 48,
    "short": "Strata",
    "home": "kv",
    "mechanism": "分层 KV 数据面与 I/O-aware 调度，避免命中后加载阻塞",
    "cross": [
      "infra",
      "engine"
    ],
    "href": "papers/paper-48.html"
  },
  {
    "id": 49,
    "short": "Helium",
    "home": "workflow",
    "mechanism": "以查询计划暴露依赖，联合共享、缓存和执行优化",
    "cross": [
      "orchestration",
      "kv"
    ],
    "href": "papers/paper-49.html"
  },
  {
    "id": 50,
    "short": "KVP",
    "home": "kv",
    "mechanism": "学习 per-head token 保留排序；属于有损裁剪",
    "cross": [
      "compute"
    ],
    "href": "papers/paper-50.html"
  },
  {
    "id": 51,
    "short": "Aragog",
    "home": "workflow",
    "mechanism": "Just-in-time model routing，适应 workflow 的质量与延迟目标",
    "cross": [
      "orchestration"
    ],
    "href": "papers/paper-51.html"
  },
  {
    "id": 52,
    "short": "Astraea",
    "home": "orchestration",
    "mechanism": "利用工具等待和阶段状态推进 workflow",
    "cross": [
      "workflow",
      "kv"
    ],
    "href": "papers/paper-52.html"
  },
  {
    "id": 53,
    "short": "NALAR",
    "home": "workflow",
    "mechanism": "以 future、managed state 与两级控制连接 Agent 和执行系统",
    "cross": [
      "engine",
      "orchestration"
    ],
    "href": "papers/paper-53.html"
  },
  {
    "id": 54,
    "short": "FlowMesh",
    "home": "workflow",
    "mechanism": "Logical / execution identity 与 lineage 支持算子去重和兼容执行",
    "cross": [
      "engine",
      "infra"
    ],
    "href": "papers/paper-54.html"
  },
  {
    "id": 55,
    "short": "SAGA",
    "home": "orchestration",
    "mechanism": "以 workflow 连续性、affinity 和公平性协调调度与缓存",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "papers/paper-55.html"
  },
  {
    "id": 56,
    "short": "TOPAS",
    "home": "orchestration",
    "mechanism": "面向剩余路径联合准入、搬运、重算和撤销",
    "cross": [
      "kv",
      "workflow"
    ],
    "href": "papers/paper-56.html"
  },
  {
    "id": 57,
    "short": "Cortex",
    "home": "infra",
    "mechanism": "按 workflow stage 划分资源池，缓解异构阶段干扰",
    "cross": [
      "orchestration",
      "workflow"
    ],
    "href": "papers/paper-57.html"
  },
  {
    "id": 58,
    "short": "Nuska",
    "home": "infra",
    "mechanism": "分阶段调度 KV 通信 flow，缓解链路竞争",
    "cross": [
      "engine",
      "kv"
    ],
    "href": "papers/paper-58.html"
  },
  {
    "id": 59,
    "short": "Back from the Future",
    "home": "kv",
    "mechanism": "用 counter-causal surprise 对历史 token 周期评分和裁剪",
    "cross": [
      "compute"
    ],
    "href": "papers/paper-59.html"
  },
  {
    "id": 60,
    "short": "HEAR",
    "home": "control",
    "mechanism": "统一工作流意图、执行控制、引擎状态与结果反馈的双向契约",
    "cross": [
      "workflow",
      "orchestration",
      "engine",
      "kv"
    ],
    "href": "papers/paper-60.html"
  },
  {
    "id": 61,
    "short": "Leyline",
    "home": "kv",
    "mechanism": "显式编辑指令，区分保留旧影响的 amortize 与重算式 forget",
    "cross": [
      "workflow",
      "engine"
    ],
    "href": "papers/paper-61.html"
  },
  {
    "id": 62,
    "short": "TokenRouter",
    "home": "engine",
    "mechanism": "常驻 subserver、pending 状态和异步执行支持 token 级模型路由",
    "cross": [
      "compute",
      "orchestration"
    ],
    "href": "papers/paper-62.html"
  },
  {
    "id": 63,
    "short": "KVTether",
    "home": "orchestration",
    "mechanism": "将 Agent 生命周期状态映射为活跃、可复用和可回收缓存",
    "cross": [
      "workflow",
      "kv"
    ],
    "href": "papers/paper-63.html"
  },
  {
    "id": 64,
    "short": "EfficientAgent",
    "home": "kv",
    "mechanism": "利用工具窗口管理 CPU 准入、后台写回和未来感知淘汰",
    "cross": [
      "orchestration",
      "infra"
    ],
    "href": "papers/paper-64.html"
  },
  {
    "id": 65,
    "short": "CADOC",
    "home": "workflow",
    "mechanism": "不可变对象与 Card 外置；按等待成本合并提交编辑，共享后缀重建",
    "cross": [
      "kv"
    ],
    "href": "papers/paper-65.html"
  },
  {
    "id": 66,
    "short": "SmoothAgent",
    "home": "orchestration",
    "mechanism": "提前转换稳定片段并准备新 KV；按前台延迟预算调度后台工作",
    "cross": [
      "workflow",
      "kv"
    ],
    "href": "papers/paper-66.html"
  },
  {
    "id": 67,
    "short": "Request Order Matters",
    "home": "kv",
    "mechanism": "固定当前 prompt、改变缓存经历，检验修复的跨轮历史敏感性",
    "cross": [
      "workflow"
    ],
    "href": "papers/paper-67.html"
  },
  {
    "id": 68,
    "short": "MemTrace",
    "home": "workflow",
    "mechanism": "记录文件、命令和测试证据版本，恢复前核验环境",
    "cross": [
      "kv"
    ],
    "href": "papers/paper-68.html"
  },
  {
    "id": 69,
    "short": "RelayCaching",
    "home": "kv",
    "mechanism": "利用连续 Decode 生成的 KV 减少重复修复",
    "cross": [
      "compute",
      "engine"
    ],
    "href": "papers/paper-69.html"
  },
  {
    "id": 70,
    "short": "AgentKV",
    "home": "kv",
    "mechanism": "以阶段 query buffer 引导 token 预算与页面回收",
    "cross": [
      "workflow",
      "compute"
    ],
    "href": "papers/paper-70.html"
  },
  {
    "id": 71,
    "short": "Retire",
    "home": "workflow",
    "mechanism": "版本发布权限、阻止旧输出、有效前缀继承与异步回收",
    "cross": [
      "engine",
      "kv"
    ],
    "href": "papers/paper-71.html"
  },
  {
    "id": 72,
    "short": "Ask the Tool, Don’t Guess",
    "home": "orchestration",
    "mechanism": "以工具运行进度指导 KV 保留和恢复时机",
    "cross": [
      "workflow",
      "kv"
    ],
    "href": "papers/paper-72.html"
  },
  {
    "id": 73,
    "short": "PatchKV",
    "home": "kv",
    "mechanism": "版本对齐、dirty region 与选择性 KV 恢复",
    "cross": [
      "workflow",
      "compute"
    ],
    "href": "papers/paper-73.html"
  },
  {
    "id": 74,
    "short": "ReCache",
    "home": "kv",
    "mechanism": "通过 resource-wise attention 和局部位置支持 tool / skill KV 组合",
    "cross": [
      "compute",
      "workflow"
    ],
    "href": "papers/paper-74.html"
  },
  {
    "id": 75,
    "short": "RR-Evict",
    "home": "kv",
    "mechanism": "轮转空闲 Agent 并从尾部淘汰，保护更多连续前缀",
    "cross": [
      "orchestration"
    ],
    "href": "papers/paper-75.html"
  },
  {
    "id": 76,
    "short": "Coda",
    "home": "kv",
    "mechanism": "协调层次 KV 准备与混合上下文执行的准入",
    "cross": [
      "engine",
      "orchestration"
    ],
    "href": "papers/paper-76.html"
  },
  {
    "id": 77,
    "short": "Self-GC",
    "home": "workflow",
    "mechanism": "对象 ID、Fold/Mask/Prune、旁路规划和缓存感知提交",
    "cross": [
      "kv"
    ],
    "href": "papers/paper-77.html"
  }
];
