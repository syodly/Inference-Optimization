// Paper summaries and thematic classification.

const PAPERS = [
  [
    1,
    "A Survey on Efficient Inference for Large Language Models",
    "foundation",
    "2024",
    "Survey",
    "todo",
    "P2"
  ],
  [
    2,
    "FlashAttention",
    "foundation",
    "2022",
    "NeurIPS 2022",
    "todo",
    "P2"
  ],
  [
    3,
    "FlashAttention-2",
    "foundation",
    "2023",
    "2023 arXiv",
    "todo",
    "P2"
  ],
  [
    4,
    "Fast Inference from Transformers via Speculative Decoding",
    "foundation",
    "2022",
    "2022 arXiv",
    "todo",
    "P1"
  ],
  [
    5,
    "Accelerating LLM Decoding with Speculative Sampling",
    "foundation",
    "2023",
    "2023 arXiv",
    "todo",
    "P1"
  ],
  [
    6,
    "Medusa",
    "foundation",
    "2024",
    "2024 arXiv",
    "todo",
    "P1"
  ],
  [
    7,
    "SpecInfer",
    "foundation",
    "2023",
    "ASPLOS 2024",
    "todo",
    "P1"
  ],
  [
    8,
    "Better & Faster Large Language Models via Multi-token Prediction",
    "foundation",
    "2024",
    "2024 arXiv",
    "todo",
    "P2"
  ],
  [
    9,
    "Tutorial Proposal: Speculative Decoding for Efficient LLM Inference",
    "foundation",
    "2025",
    "Tutorial proposal",
    "todo",
    "P3"
  ],
  [
    10,
    "GPU-Initiated Fine-Grained Overlap / Fused Computation-Collective Operations",
    "foundation",
    "2023",
    "2023 arXiv",
    "todo",
    "P3"
  ],
  [
    11,
    "Orca: A Distributed Serving System for Transformer-Based Generative Models",
    "serving",
    "2022",
    "OSDI 2022",
    "done",
    "P1"
  ],
  [
    12,
    "Response Length Perception and Sequence Scheduling",
    "serving",
    "2023",
    "NeurIPS 2023",
    "done",
    "P1"
  ],
  [
    13,
    "DeepSpeed-FastGen",
    "serving",
    "2024",
    "Technical report / arXiv",
    "done",
    "P1"
  ],
  [
    14,
    "Sarathi: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills",
    "serving",
    "2023",
    "2023 arXiv",
    "todo",
    "P1"
  ],
  [
    15,
    "Sarathi-Serve",
    "serving",
    "2024",
    "OSDI 2024",
    "done",
    "P1"
  ],
  [
    16,
    "Inference without Interference / ShuffleInfer",
    "serving",
    "2024",
    "ACM TACO 2025",
    "done",
    "P1"
  ],
  [
    17,
    "Splitwise: Efficient Generative LLM Inference Using Phase Splitting",
    "serving",
    "2024",
    "2024 arXiv / systems work",
    "todo",
    "P1"
  ],
  [
    18,
    "DistServe: Disaggregating Prefill and Decoding for Goodput-optimized LLM Serving",
    "serving",
    "2024",
    "2024 arXiv / systems work",
    "todo",
    "P1"
  ],
  [
    19,
    "vLLM PagedAttention",
    "serving",
    "2023",
    "2023 arXiv / vLLM system paper",
    "todo",
    "P1"
  ],
  [
    20,
    "Parrot: Efficient Serving of LLM-based Applications with Semantic Variables",
    "workflow",
    "2024",
    "OSDI 2024",
    "done",
    "P1"
  ],
  [
    21,
    "MuxServe: Flexible Spatial-Temporal Multiplexing for Multiple LLM Serving",
    "workflow",
    "2024",
    "ICML 2024",
    "done",
    "P1"
  ],
  [
    22,
    "Towards End-to-End Optimization of LLM-based Applications with Ayo (preprint: Teola)",
    "workflow",
    "2024",
    "ASPLOS 2025",
    "done",
    "P1"
  ],
  [
    23,
    "KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows",
    "workflow",
    "2025",
    "NeurIPS 2025",
    "done",
    "P1"
  ],
  [
    24,
    "Agentix: An Efficient Serving Engine for LLM Agents as General Programs (preprint: Autellix)",
    "workflow",
    "2025",
    "NSDI 2026",
    "partial",
    "P1"
  ],
  [
    25,
    "JITServe: SLO-aware LLM Serving with Imprecise Request Information",
    "workflow",
    "2025",
    "NSDI 2026",
    "todo",
    "P1"
  ],
  [
    26,
    "Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache TTL",
    "workflow",
    "2025-11",
    "ICLR 2026 Lifelong Agent Workshop",
    "done",
    "P1"
  ],
  [
    27,
    "ThunderAgent: A Fast, Simple, and Program-Aware Agentic Inference System",
    "workflow",
    "2026",
    "ICML 2026",
    "done",
    "P1"
  ],
  [
    28,
    "CONCUR: High-Throughput Agentic Batch Inference via Congestion-Based Concurrency Control",
    "workflow",
    "2026",
    "ICML 2026",
    "done",
    "P1"
  ],
  [
    29,
    "PASTE: Accelerating LLM-based Agentic Workflows with Predictive Tool Execution",
    "workflow",
    "2026-03-19",
    "2026 arXiv",
    "done",
    "P1"
  ],
  [
    30,
    "Multi-Segment Attention",
    "workflow",
    "2026-06-01",
    "2026 arXiv",
    "todo",
    "P2"
  ],
  [
    31,
    "Aries: Rethinking AI Cloud Infrastructure for Agentic Serving Systems",
    "workflow",
    "2026-07-31",
    "2026 arXiv",
    "todo",
    "P2"
  ],
  [
    32,
    "Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models",
    "kv",
    "2026",
    "ICLR 2026",
    "done",
    "P2"
  ],
  [
    33,
    "Beyond Accuracy: Unveiling Inefficiency Patterns in Tool-Integrated Reasoning",
    "kv",
    "2026",
    "ACL 2026",
    "done",
    "P2"
  ],
  [
    34,
    "UniCache: Unifying Prefix Cache Eviction for Heterogeneous LLM Serving Workloads",
    "kv",
    "2026",
    "SIGMETRICS 2026",
    "done",
    "P1"
  ],
  [
    35,
    "Reasoning Language Model Inference Serving Unveiled: An Empirical Study",
    "kv",
    "2025",
    "ICLR 2026",
    "done",
    "P2"
  ],
  [
    36,
    "Practical Online KV Cache Compaction for LLM Agents",
    "kv",
    "2026-08-02",
    "2026 arXiv",
    "todo",
    "P1"
  ],
  [
    37,
    "PBKV: Efficient Serving for Dynamic Agent Workflows with Prediction-based KV Cache Management",
    "kv",
    "2026-05",
    "2026 arXiv",
    "todo",
    "P1"
  ],
  [
    38,
    "Pythia: Exploiting Workflow Predictability for Efficient Agent-Native LLM Serving",
    "kv",
    "2026-04-28",
    "2026 arXiv",
    "done",
    "P1"
  ],
  [
    39,
    "CacheScout: Learning Agent Execution for KV-Cache Management",
    "kv",
    "2026-07-16",
    "2026 arXiv",
    "done",
    "P1"
  ],
  [
    40,
    "OasisKV: Scaling In-Decode KV Cache Beyond HBM",
    "kv",
    "2026-08-08",
    "2026 arXiv",
    "done",
    "P1"
  ],
  [
    41,
    "CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion",
    "kv",
    "2024",
    "EuroSys 2025",
    "done",
    "P1"
  ],
  [
    42,
    "DroidSpeak: KV Cache Sharing for Cross-LLM Communication and Multi-LLM Serving",
    "kv",
    "2024-11",
    "arXiv；沿用已读版本",
    "done",
    "P1"
  ],
  [
    43,
    "ContextPilot: Fast Long-Context Inference via Context Reuse",
    "kv",
    "2025-11",
    "MLSys 2026",
    "done",
    "P1"
  ],
  [
    44,
    "SemShareKV: Efficient KVCache Sharing for Semantically Similar Prompts via Token-Level LSH Matching",
    "kv",
    "2025",
    "IJCNLP-AACL 2025",
    "done",
    "P1"
  ],
  [
    45,
    "CacheWise: Understanding Workloads and Optimizing KVCache Management for Efficiently Serving LLM Coding Agents",
    "kv",
    "2026-06-15",
    "arXiv 2606.16824v1",
    "done",
    "P1"
  ],
  [
    46,
    "Akashic: A Low-Overhead LLM Inference Service with MemAttention",
    "kv",
    "2026-07-07",
    "arXiv 2607.05708v1",
    "done",
    "P1"
  ],
  [
    47,
    "Murakkab",
    "workflow",
    "2025-08",
    "OSDI 2026",
    "done",
    "P1"
  ],
  [
    48,
    "Strata",
    "kv",
    "2026",
    "OSDI 2026",
    "done",
    "P1"
  ],
  [
    49,
    "Helium",
    "workflow",
    "2026",
    "SIGMOD 2026",
    "done",
    "P1"
  ],
  [
    50,
    "KVP: Learning to Evict from Key-Value Cache",
    "kv",
    "2026-02",
    "论文页标注 ICML 2026",
    "done",
    "P1"
  ],
  [
    51,
    "Aragog",
    "workflow",
    "2025",
    "arXiv",
    "done",
    "P1"
  ],
  [
    52,
    "Astraea",
    "workflow",
    "2025",
    "arXiv",
    "done",
    "P1"
  ],
  [
    53,
    "NALAR: An Agent Serving Framework",
    "workflow",
    "2026-01",
    "arXiv 2601.05109",
    "done",
    "P1"
  ],
  [
    54,
    "FlowMesh",
    "workflow",
    "2025-10",
    "arXiv 2510.26913",
    "done",
    "P1"
  ],
  [
    55,
    "SAGA",
    "workflow",
    "2026-05",
    "arXiv 2605.00528",
    "done",
    "P1"
  ],
  [
    56,
    "TOPAS",
    "workflow",
    "2026-08",
    "arXiv 2608.25523",
    "done",
    "P1"
  ],
  [
    57,
    "Cortex",
    "workflow",
    "2025-10",
    "arXiv 2510.14126",
    "done",
    "P1"
  ],
  [
    58,
    "Nuska",
    "workflow",
    "2026-03",
    "arXiv 2603.17456",
    "done",
    "P1"
  ],
  [
    59,
    "Back from the Future",
    "kv",
    "2026-07",
    "arXiv 2607.27600",
    "done",
    "P1"
  ],
  [
    60,
    "HEAR: Can Agent Harnesses and Inference Engines Hear Each Other?",
    "workflow",
    "2026-10-05",
    "arXiv 2610.06597v1",
    "done",
    "P1"
  ],
  [
    61,
    "Leyline: KV Cache Directives for Agentic Inference",
    "kv",
    "2026-05-31",
    "arXiv 2606.01065v1",
    "done",
    "P1"
  ],
  [
    62,
    "TokenRouter: Efficient Serving System for Token-Level LLM Routing",
    "workflow",
    "2026-10-08",
    "PDF 首页标注 NeurIPS 2026",
    "done",
    "P1"
  ],
  [
    63,
    "KVTether",
    "kv",
    "2026-09",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    64,
    "EfficientAgent",
    "kv",
    "2026-09",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    65,
    "CADOC: Cache-Aware Dynamic Object Context for Long-Horizon Agents",
    "kv",
    "2026-09-29",
    "arXiv 预印本",
    "done",
    "P1"
  ],
  [
    66,
    "SmoothAgent: Efficient Long-Horizon LLM-Based Agent Serving with Lookahead Context Engineering",
    "serving",
    "2026-06-30",
    "arXiv 预印本",
    "done",
    "P1"
  ],
  [
    67,
    "Request Order Matters",
    "kv",
    "2026-10",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    68,
    "MemTrace",
    "kv",
    "2026-10",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    69,
    "RelayCaching",
    "kv",
    "2026-03",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    70,
    "AgentKV",
    "kv",
    "2026-09",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    71,
    "Retire: Serving a Revisable World",
    "kv",
    "2026-10",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    72,
    "Ask the Tool, Don’t Guess",
    "kv",
    "2026-09",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    73,
    "PatchKV: Recovery for Dynamically Edited Contexts",
    "kv",
    "2026-09",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    74,
    "ReCache",
    "kv",
    "2026-08",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    75,
    "RR-Evict",
    "kv",
    "2026-09",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    76,
    "Coda",
    "kv",
    "2026-10",
    "arXiv；待精读",
    "partial",
    "P1"
  ],
  [
    77,
    "Self-GC: Self-Governing Context for Long-Horizon LLM Agents",
    "kv",
    "2026-07-01",
    "arXiv 预印本",
    "done",
    "P1"
  ]
];

const MILESTONES = [
  {
    "id": 11,
    "date": "2022-07",
    "stage": "请求 → Token",
    "title": "Orca: A Distributed Serving System for Transformer-Based Generative Models",
    "subtitle": "OSDI 2022 · 把一次生成拆成可调度的迭代级工作",
    "problem": "传统 request-level batching 要等整条请求完成，短请求会被长请求拖住；系统也无法在 token 生成过程中动态调整 batch。",
    "method": "提出 iteration-level scheduling：每轮只为仍活跃的请求生成一个 token，并用 continuous batching 动态加入/退出请求。",
    "shift": "优化对象从“整条请求”转为“每轮 token 迭代”，奠定后续 LLM serving scheduler 的基本执行模型。"
  },
  {
    "id": 12,
    "date": "2023-05-22",
    "stage": "长度感知",
    "title": "Response Length Perception and Sequence Scheduling",
    "subtitle": "NeurIPS 2023 · arXiv:2305.13144",
    "problem": "输出长度事前未知，静态 batch 会产生大量 padding 和无效计算；但如果等到生成结束才知道长度，已经错过调度时机。",
    "method": "用轻量模型预测请求的 response length，把长度相近的请求组成 micro-batch，减少不同结束时间造成的尾部浪费。",
    "shift": "在 token-level serving 之上加入“未来工作量预测”：调度开始从反应式执行走向预测式分组。"
  },
  {
    "id": 13,
    "date": "2024-01-09",
    "stage": "Prefill / Decode",
    "title": "DeepSpeed-FastGen",
    "subtitle": "arXiv:2401.08671 · Dynamic SplitFuse",
    "problem": "大 Prefill 会突然阻塞 Decode，造成 TTFT 和 TBT 互相牺牲；固定的 prefill/decode 优先级无法适应在线混合负载。",
    "method": "Dynamic SplitFuse 将长 Prefill 动态切成适合当前轮次的片段，与 Decode 请求交错执行，并用 token budget 控制每轮干扰。",
    "shift": "调度问题从“谁先运行”变为“每一轮允许运行多少 Prefill”，为后续 chunked prefill 和 stall-free serving 铺路。"
  },
  {
    "id": 21,
    "date": "2024-04-02",
    "stage": "资源复用",
    "title": "MuxServe: Flexible Spatial-Temporal Multiplexing for Multiple LLM Serving",
    "subtitle": "ICML 2024 · arXiv:2404.02015",
    "problem": "多个模型同时服务时，静态 GPU 切分会造成显存和计算资源浪费；模型热度和请求阶段随时间变化。",
    "method": "以 LLM unit 为放置粒度，结合 popularity-aware placement、Prefill/Decode job 拆分、ADBS 调度和 SM 粒度资源管理，在空间复用与时间复用之间动态切换。",
    "shift": "补上 application/workflow 之下的集群资源层：不仅要知道请求依赖什么，还要决定不同模型在哪张 GPU、以什么资源比例运行。"
  },
  {
    "id": 22,
    "date": "2024-06-29",
    "stage": "Primitive DAG",
    "title": "Ayo（预印本名 Teola）: Towards End-to-End Optimization of LLM-based Applications",
    "subtitle": "ASPLOS 2025 · arXiv:2407.00326",
    "problem": "只优化 LLM 节点并不能优化 RAG 的端到端延迟；Embedding、检索、数据库和多个 LLM 阶段之间有细粒度依赖与可并行空间。",
    "method": "把高层 workflow 展开为 query-specific primitive graph，执行 dependency pruning、stage decomposition、prefill splitting 和 decode pipelining，并用 topology-aware batching 调度。",
    "shift": "动态图优化从“请求之间的 DAG”下沉到“模块内部 primitive 之间的 dataflow”，开始联合非 LLM 操作和就绪时间。"
  },
  {
    "id": 20,
    "date": "2024-07",
    "stage": "应用 DAG",
    "title": "Parrot: Efficient Serving of LLM-based Applications with Semantic Variables",
    "subtitle": "OSDI 2024 · 应用级依赖第一次进入 serving engine",
    "problem": "Chain、MapReduce 和 Multi-agent 中的多个 LLM 请求有依赖关系，但 serving engine 只看到孤立 request；中间结果绕回客户端，且无法区分整组吞吐目标和单请求延迟目标。",
    "method": "用 Semantic Variable 显式表达生产者、消费者、Prompt 前缀和最终性能目标；服务端据此构造跨请求 DAG、直接传递变量、共享 prefix KV，并按 application objective 调度。",
    "shift": "优化对象从“单个 LLM 请求”上移为“由多个请求组成的应用图”，动态图推理优化主线由此开始。"
  },
  {
    "id": 23,
    "date": "2025-07-10",
    "stage": "已知 Step Graph",
    "title": "KVFlow: Efficient Prefix Caching for Accelerating LLM-Based Multi-Agent Workflows",
    "subtitle": "NeurIPS 2025 · arXiv:2507.07400",
    "problem": "LRU 只知道过去何时访问过 KV，不知道 Agent workflow 下一步会访问谁；刚完成但暂时不用的 KV 可能挤掉马上要恢复的 Agent。",
    "method": "把 workflow 表示为 Agent Step Graph，为 KV 节点计算距离下一次执行的 step 数；按未来距离做 eviction，并在下一 Agent 运行前异步 prefetch。",
    "shift": "Agent 优化第一次明确进入 KV cache：缓存策略从“最近访问”转为“未来 workflow 位置”，形成 workflow-aware KV 分支。"
  },
  {
    "id": 24,
    "date": "2025",
    "stage": "动态 Program",
    "title": "Agentix: An Efficient Serving Engine for LLM Agents as General Programs",
    "subtitle": "NSDI 2026 · 早期预印本名 Autellix · 部分整理",
    "problem": "Agent 的后续调用由模型输出和工具结果动态产生，完整 DAG 无法提前写出；request-level 调度会产生 request-level 和 program-level 两层队头阻塞。",
    "method": "把 Agent program 作为调度对象；PLAS 面向串行程序按累计服务量调度，ATLAS 根据已观察依赖链在线近似关键路径，再通过多级队列、抢占和 anti-starvation 执行。",
    "shift": "动态图优化不再假设完整 DAG 已知，而是转向运行时维护 program state，并用在线关键路径近似指导调度。"
  },
  {
    "id": 26,
    "date": "2025-11-04",
    "stage": "工具等待",
    "title": "Continuum: Efficient and Robust Multi-Turn LLM Agent Scheduling with KV Cache Time-to-Live",
    "subtitle": "arXiv:2511.02230 · ICLR 2026 Lifelong Agent Workshop",
    "problem": "Agent 在工具调用期间暂停：立即释放 KV 会导致下一轮重算，永久保留又会占住 HBM；工具时延还具有明显长尾。",
    "method": "按工具历史时长分布估计返回概率，为每轮 KV 设定 TTL；同时把多轮 Agent 作为 program 调度，减少恢复后的重新排队和无效等待。",
    "shift": "KV 管理从“已知图上的未来 step”扩展到“未知工具间隔下的概率性生命周期”，开始显式建模等待时间。"
  },
  {
    "id": 28,
    "date": "2026-01-30",
    "stage": "拥塞控制",
    "title": "CONCUR: High-Throughput Agentic Batch Inference of LLM via Congestion-Based Concurrency Control",
    "subtitle": "ICML 2026 · arXiv:2601.22705",
    "problem": "离线 Agent batch 中并发过高会造成 KV thrashing：显存看似占满，但大量 GPU 时间用于驱逐和 Prefill 重算。",
    "method": "在线监测 KV 使用率、命中率和拥塞状态，按 Agent-level admission 控制并发，让活跃工作集保持在可服务区间。",
    "shift": "研究重点从单轮调度转到整个 Agent batch 的拥塞与 admission，开始用系统状态决定“允许多少 Agent 同时推进”。"
  },
  {
    "id": 27,
    "date": "2026-02-14",
    "stage": "Program-aware",
    "title": "ThunderAgent: A Fast, Simple, and Program-Aware Agentic Inference System",
    "subtitle": "ICML 2026 · arXiv:2602.13692",
    "problem": "Agent 的 Reasoning、Acting 和工具环境会造成 KV 重算、GPU 空闲与存储膨胀；只围绕单次请求调度看不到程序级资源浪费。",
    "method": "维护 active set 控制工作集，用 global queue 平衡多节点资源，并对 Acting 期间暂时不用的 KV 做时间衰减，同时管理工具环境。",
    "shift": "把 program-aware 调度从“请求优先级”扩展到 KV、GPU 和工具环境的联合生命周期管理。"
  },
  {
    "id": 29,
    "date": "2026-03-19",
    "stage": "工具并行",
    "title": "PASTE: Parallelizing Tool Execution and LLM Generation for Low-Latency Agent Serving",
    "subtitle": "arXiv:2603.18897 · Predictive Tool Execution",
    "problem": "工具调用时间占 Agent 关键路径；但必须等 LLM 输出完整的工具名和参数后才能执行，LLM 与工具天然串行。",
    "method": "从历史轨迹学习局部工具转移，提前 speculatively 执行参数已经确定的工具；工具结果完成后，再由 LLM-side scheduler 控制何时恢复 session。",
    "shift": "动态图优化进一步越过 LLM serving 边界，把工具执行也纳入预测和调度，目标从减少 GPU 等待变成隐藏跨系统等待。"
  },
  {
    "id": 38,
    "date": "2026-04-28",
    "stage": "Workflow 预测",
    "title": "Pythia: Exploiting Workflow Predictability for Efficient Agent-Native LLM Serving",
    "subtitle": "arXiv:2604.25899",
    "problem": "Agent workflow 虽然动态，但角色、依赖和主要路径通常有规律；被动路由、LRU 和反应式 autoscaling 无法利用这种规律。",
    "method": "从 workflow 生成 predicted path，用路径上的 lineage 做 KV 保留，用预测请求做 prefill warmup 和全局调度，并让 autoscaling 对齐 workflow wavefront。",
    "shift": "将预测从单个后继/单个请求提升到整个 workflow，并把同一预测同时用于缓存、调度和扩缩容。"
  },
  {
    "id": 34,
    "date": "2026-06",
    "stage": "异构缓存",
    "title": "UniCache: Unifying Prefix Cache Eviction for Heterogeneous LLM Serving Workloads",
    "subtitle": "SIGMETRICS 2026 · 会议月份",
    "problem": "不同 workload 对 KV 的价值定义不同：聊天、RAG、Agent 和长上下文不能都用同一种 LRU/TTL 策略。",
    "method": "统一不同 workload 的 prefix cache eviction 目标和多队列管理，在命中收益、占用空间和未来复用之间做通用权衡。",
    "shift": "KV cache 研究从 Agent 专用策略走向异构 workload 的统一缓存接口，强调策略可泛化与公平比较。"
  },
  {
    "id": 39,
    "date": "2026-07-16",
    "stage": "转移学习",
    "title": "CacheScout: Learning Agent Execution for KV-Cache Management",
    "subtitle": "arXiv:2608.14624",
    "problem": "动态 Agent 没有完整 DAG，LRU 又看不到下一个 Agent；但相邻 Agent 转移往往存在局部规律，可以用来判断谁会再次出现。",
    "method": "在线统计 Agent-to-Agent transition matrix，用稀疏高概率边做 BFS 估计 anchor 的 survival；以 survival、age 和 block size 联合 eviction，并用标准 prefill request 做受限 warmup。",
    "shift": "在 KVFlow 的显式图与 Pythia 的完整 workflow 预测之间，加入不要求先验 DAG 的在线局部学习。"
  },
  {
    "id": 40,
    "date": "2026-08-08",
    "stage": "Token / Block",
    "title": "OasisKV: Scaling In-Decode KV Cache Beyond HBM with Lookahead Sparse Prefetching",
    "subtitle": "arXiv:2608.08097",
    "problem": "长上下文 decode 的 KV 规模超过 GPU HBM；把全部历史 KV 搬到 GPU 会受容量和带宽限制，但只保留固定窗口又可能丢失远处证据。",
    "method": "用 draft token/lookahead 预测下一步 attention 重要的 KV token/block，仅从 CPU 或远端层级稀疏预取需要的部分，并与 decode overlap。",
    "shift": "缓存控制从 workflow/Agent 哪个阶段会被用到，下沉到当前 decode step 具体读取哪些 token/block，形成更底层的选择性读取路线。"
  },
  {
    "id": 41,
    "date": "2024",
    "title": "CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion",
    "subtitle": "EuroSys 2025",
    "stage": "KV / Codesign",
    "problem": "重复文档位于不同前文之后，连续前缀不能覆盖这些复用。",
    "method": "独立文档 KV、位置校正与选择性 token 重算，并重叠加载和计算。",
    "shift": "额外独立构建、修复和搬运必须计入；追加历史完整驻留时原生前缀已经有效。"
  },
  {
    "id": 45,
    "date": "2026-06-15",
    "title": "CacheWise: Understanding Workloads and Optimizing KVCache Management for Efficiently Serving LLM Coding Agents",
    "subtitle": "arXiv 2606.16824v1",
    "stage": "KV / Codesign",
    "problem": "并发 coding 会话长历史增长、工具等待与容量竞争导致重复 prefill。",
    "method": "前缀感知调度与复用时间预测驱逐。",
    "shift": "长度与 cache_read 不能唯一恢复文本、编辑关系或 KV 因果有效性。"
  },
  {
    "id": 60,
    "date": "2026-10-05",
    "title": "HEAR: Can Agent Harnesses and Inference Engines Hear Each Other?",
    "subtitle": "arXiv 2610.06597v1",
    "stage": "KV / Codesign",
    "problem": "Harness 掌握依赖与未来意图，Engine 掌握真实缓存与压力，两侧割裂。",
    "method": "四类消息与控制语义连接两侧；在线缓存协调与冻结角色配置作为实例。",
    "shift": "性能回放与真实任务质量分开；协议承接策略，不提出非前缀修复。"
  },
  {
    "id": 61,
    "date": "2026-05-31",
    "title": "Leyline: KV Cache Directives for Agentic Inference",
    "subtitle": "arXiv 2606.01065v1",
    "stage": "KV / Codesign",
    "problem": "主动删除、替换与压缩历史让普通前缀缓存失效。",
    "method": "显式编辑四元组；amortize 保留旧影响、校正位置，forget 重新 prefill。",
    "shift": "MLA kernel 是主要验证路径；旋转不消除旧因果影响；两条实验不能合并。"
  }
];

const MILESTONE_DETAILS = {
  "11": {
    "authors": "Gyeong-In Yu et al.",
    "affiliation": "Seoul National University",
    "keywords": [
      "Iteration-level Scheduling",
      "Selective Batching",
      "Continuous Batching"
    ],
    "motivation": "传统 request-level batching 要等整批请求全部结束，已经完成的请求不能及时释放，新到请求也无法使用空出的 batch 位置。不同请求的输入长度、生成进度和 KV 状态还会让动态合批变得困难。",
    "design": "提出 iteration-level scheduling，每轮只推进活跃请求的一个生成迭代，并在每轮重新选择 batch。Linear、LayerNorm 等算子采用 selective batching，Attention 仍按请求分别读取 KV，再把结果合并回批次。调度使用 iteration-level FCFS，并受 max batch size 和 KV slot 约束。",
    "result": "在 175B 模型、相近 normalized latency 下，Orca 的吞吐最高达到 FasterTransformer 的 36.9 倍，并支持从单 GPU 到 32 GPU、最大 341B 模型的在线生成。",
    "limitations": "KV 空间按声明的最大生成长度预留，显存利用率仍有限；选择性 batching 需要对执行引擎和 Attention 数据路径进行改造。"
  },
  "12": {
    "authors": "Zangwei Zheng et al.",
    "affiliation": "Cornell University",
    "keywords": [
      "Response Length Prediction",
      "Sequence Scheduling",
      "Static Batching"
    ],
    "motivation": "静态 batch 要被最长输出拖住，短序列后续轮次会产生 padding 和冗余计算。输出长度在生成前未知，使按长度分组无法直接实施。",
    "design": "用 LoRA 微调 Vicuna-7B 预测回答的最大长度区间，按预测长度排序并组成 micro-batch。FCR 将预测不足的请求收集后重算，VBS 为短回答分配更大的 batch，减少尾部空转。",
    "result": "Alpaca 上吞吐从 1.22 提升到 2.27 samples/s，增幅 86%；平均每个 batch 的处理 token 从 377 降到约 208，Instruction-in-the-Wild 上达到 1.24 samples/s。",
    "limitations": "依赖先积累 256 条请求，属于 grouped static batching；预测模型本身有额外成本，在低并发或动态图场景下可能增加等待。"
  },
  "13": {
    "authors": "Connor Holmes et al.",
    "affiliation": "Microsoft DeepSpeed",
    "keywords": [
      "Dynamic SplitFuse",
      "Chunked Prefill",
      "Token Budget"
    ],
    "motivation": "Decode-only batch 的 token 数太少，GPU 利用率不高；完整长 Prefill 又会在一个 iteration 内阻塞正在生成的请求。固定 Prefill 优先或 Decode 优先都无法同时稳定 TTFT 和 TBT。",
    "design": "Dynamic SplitFuse 将长 Prompt 切成多个 Prefill chunk，分散到多个 iteration，并与 Decode token 共同填充本轮 token budget。系统根据每轮可处理的总 token 数控制计算规模，再集成到 DeepSpeed-Inference 和 MII 的分布式 serving 中。",
    "result": "相对实验中的 vLLM，effective throughput 最高提升约 2.3 倍，平均 latency 最多降低约 2 倍，P95 per-token generation latency 最多降低约 3.7 倍。",
    "limitations": "核心收益依赖合适的 token budget 和负载分布；论文主要关注混合 Prefill 与 Decode，复杂 Agent 依赖和跨工作流优先级不是主要处理对象。"
  },
  "15": {
    "authors": "Amey Agrawal et al.",
    "affiliation": "Cornell University",
    "keywords": [
      "Chunked Prefill",
      "Stall-free Batching",
      "TBT SLO",
      "Pipeline Parallelism"
    ],
    "motivation": "完整 Prefill 会打断正在生成的 Decode，产生用户可感知的 generation stall。平均 latency 无法反映严重的尾部 TBT，且不稳定的 iteration 工作量会在 Pipeline Parallel 中形成 bubble。",
    "design": "将长 Prompt 切成固定大小的 chunk，优先保证活跃 Decode 请求每轮生成一个 token，再用剩余 token budget 填充 Prefill。通过离线 profiling 根据 P99 TBT SLO 选择 token budget，并构造近似均匀计算量的 batch。",
    "result": "相对 vLLM，Mistral-7B 的 serving capacity 最高提升 2.6 倍，Yi-34B 最高提升 3.7 倍；Pipeline Parallel 场景下相对 Orca 最高提升 6.31 倍，并保持更低的 P99 TBT。",
    "limitations": "Prefill chunk 过小会增加调度和 kernel 开销；token budget 需要针对模型、硬件和 SLO profiling，系统后端也需要支持 chunked prefill。"
  },
  "16": {
    "authors": "C.-C. Hu et al.",
    "affiliation": "Chinese Academy of Sciences",
    "keywords": [
      "Prefill-Decode Disaggregation",
      "Resource Interference",
      "Two-level Scheduling"
    ],
    "motivation": "Prefill 和 Decode 对计算、显存容量及带宽的需求不同，混合在同一实例可能产生 Prefill-Prefill、Prefill-Decode 和 Decode-Decode 干扰。只按请求放置还会制造 Decode hotspot 与队头阻塞。",
    "design": "将 Prefill 与 Decode 拆到独立实例，用固定 chunk 让 Prefill 实例接近计算饱和，再按 Prompt 和 Decode 特征分组。两级 scheduler 根据预测资源使用选择实例，动态协调分离后的请求，减少异构负载互相干扰。",
    "result": "在混合 downstream workload 上，相对基线减少 38% 资源，平均 TTFT 降低 97%，平均 job completion time 降低 47%，同时提升 performance per dollar。",
    "limitations": "分离部署引入 KV 传输和跨实例协调成本；收益依赖请求特征预测，不能简单代表所有当前 serving engine 的端到端表现。"
  },
  "20": {
    "authors": "Chaofan Lin et al.",
    "affiliation": "Shanghai Jiao Tong University",
    "keywords": [
      "Semantic Variable",
      "Dataflow Analysis",
      "Application Scheduling",
      "Prefix Sharing"
    ],
    "motivation": "Chain、Map-Reduce 和 Multi-agent 应用由多个相互依赖的 LLM 请求组成，但普通 serving 只能看到孤立 request。中间结果需要绕回客户端，共享 Prompt 也会被重复计算，单请求目标还可能与整条应用目标冲突。",
    "design": "用 Semantic Variable 暴露请求生产者、消费者、Prompt 前缀和最终性能目标，由 Manager 构造跨请求 DAG。服务端直接传递中间变量，识别共享 prefix 并复用 KV，再按 application objective 组织 Task Group 和 engine placement。",
    "result": "在 Chain、Map-Reduce、多 Agent 和混合负载中，相对 vLLM 最高取得 2.38 倍、2.37 倍和 11.7 倍加速；共享 Prompt 和 application-centric scheduling 是主要收益来源。",
    "limitations": "需要开发者提前声明 SemanticFunction 和依赖；条件分支、Python native function 和动态控制流仍需客户端参与，实验规模主要为单机或小型多 GPU。"
  },
  "21": {
    "authors": "Jiangfei Duan et al.",
    "affiliation": "Cornell University",
    "keywords": [
      "Multi-model Serving",
      "Spatial-temporal Multiplexing",
      "Adaptive Batching",
      "GPU Sharing"
    ],
    "motivation": "多模型服务中的模型热度随时间变化，静态 GPU 切分会让热门模型排队、冷门模型占用空闲资源。单纯时间复用也无法利用 Prefill 和 Decode 不同的资源特征。",
    "design": "以 LLM Unit 表示共置模型和 GPU mesh，依据模型流行度生成并行候选配置并完成放置。在 Unit 内拆分 Prefill 和 Decode job，通过 ADBS 调整 batch，再由统一资源管理器控制 SM、显存和空间时间复用。",
    "result": "相对静态放置和传统时间复用，MuxServe 提升多模型 serving 的 GPU 利用率与吞吐，并减少模型间资源干扰；核心收益来自模型热度互补和 Decode 余量利用。",
    "limitations": "需要预先获得模型请求率和 profiling 数据；放置和资源管理主要面向多模型 serving，不直接处理动态 Agent program 的依赖关系。"
  },
  "22": {
    "authors": "Xin Tan et al.",
    "affiliation": "The Chinese University of Hong Kong",
    "keywords": [
      "Primitive-level DAG",
      "Graph Optimization",
      "Pipeline Parallelism",
      "Topology-aware Batching"
    ],
    "motivation": "RAG 等 LLM 应用同时包含 Embedding、检索、数据库、Reranking 和多个 LLM 阶段，只优化 LLM 请求无法解释端到端延迟。粗粒度串行执行还会隐藏跨模块并行空间。",
    "design": "把高层应用展开为 query-specific primitive graph，进行 dependency pruning 和 stage decomposition，使用 partial prefill、partial decoding 及 pipeline 变换暴露并行性，再用两级 runtime 和 topology-aware batching 推进 ready primitive。",
    "result": "在 search-augmented generation、Naive RAG、Advanced RAG 和 Contextual Retrieval 上分别取得最高 1.79 倍、1.67 倍、2.09 倍和 1.59 倍加速；topology-aware batching 使多查询 latency 最多降低 19.2%。",
    "limitations": "需要对后端引擎加入 Partial Prefilling 和结构化 Partial Decoding；当前 topology 主要依据节点 depth，尚未完整建模执行时间、slack 和真实关键路径。"
  },
  "23": {
    "authors": "Zaifeng Pan et al.",
    "affiliation": "University of California, San Diego",
    "keywords": [
      "Workflow-aware Prefix Caching",
      "Agent Step Graph",
      "KV Eviction",
      "Proactive Prefetching"
    ],
    "motivation": "LRU 只依据过去的访问时间，无法知道多 Agent workflow 下一步将使用哪个角色的 KV。刚完成但暂时未访问的 Agent anchor 可能被错误驱逐，恢复时又暴露 Prefill 和 KV 传输延迟。",
    "design": "将 workflow 表示为带 AND/OR 语义的 Agent Step Graph，计算每个 KV 节点距离下一次执行的 step 数，并将优先级传播到共享 KV tree。系统按未来距离淘汰缓存，在下一 Agent 执行前从 CPU 异步预取，并调度其他 ready request 隐藏加载时间。",
    "result": "单 workflow 场景相对 GPU-only SGLang 最高提升 2.91 倍，相对 HiCache 最高提升 1.83 倍；并发场景仍有收益，但在短 prefix 负载上的增益明显较小。",
    "limitations": "依赖开发者提供较稳定的 Step Graph；实验以单 GPU 为主，没有完整覆盖跨 GPU KV 通信、动态分支和复杂工具生命周期。"
  },
  "24": {
    "authors": "Michael Luo et al.",
    "affiliation": "University of California, Berkeley",
    "keywords": [
      "Dynamic Agent Programs",
      "Program-level Scheduling",
      "Online Critical Path",
      "KV Locality"
    ],
    "motivation": "Agent 的后续调用由模型输出、工具结果和控制流动态产生，完整 DAG 无法提前写出。request-level 调度会同时造成调用级和 program 级队头阻塞，无法直接优化整个 Agent 的完成时间。",
    "design": "用 Process Table 按 program ID 跟踪请求。PLAS 对串行程序按累计 GPU service 调度，ATLAS 根据已观察依赖链在线估计并行程序的关键路径，再结合多级队列、time quantum、抢占和 anti-starvation 推进程序。路由同时兼顾负载和长调用的 KV locality。",
    "result": "在动态串行和并行 Agent 上减少程序完成时间，并在 program progress、engine load、KV 复用和公平性之间取得平衡；核心贡献是把动态 Agent 作为 serving engine 的调度单位。",
    "limitations": "在线关键路径只能依据已经观察到的依赖链，无法预知尚未展开的分支；程序优先级、抢占和 KV locality 之间仍存在明显权衡。"
  },
  "26": {
    "authors": "Hanchen Li et al.",
    "affiliation": "University of California, Berkeley",
    "keywords": [
      "Multi-turn Agent",
      "KV Cache TTL",
      "Program-level FCFS",
      "Tool Latency"
    ],
    "motivation": "Agent 在工具调用期间会暂停，立即释放 KV 会让下一轮重复 Prefill，永久保留又会占用 HBM。工具时长还具有长尾，固定 TTL 无法同时适应短工具和慢工具。",
    "design": "按工具类型记录历史耗时分布，用经验累积分布估计不同 TTL 下的返回概率。系统联合 KV reload 成本、显存占用和程序顺序价值选择 TTL，再以 program-level FCFS 调度恢复请求，并在 pinned KV 导致死锁风险时执行恢复。",
    "result": "跨模型、GPU 和 SWE-Bench、BFCL 等轨迹，平均响应时间最高降低约 2 倍；随着 workflow 轮数增加，相对原始 vLLM 的优势最高扩大到 3.7 倍，调度开销基本保持不变。",
    "limitations": "TTL 预测依赖工具历史样本；跨节点恢复主要依赖重算，尚未完整解决 KV 传输、复杂工具依赖和多租户公平性。"
  },
  "27": {
    "authors": "Hao Kang et al.",
    "affiliation": "Georgia Institute of Technology",
    "keywords": [
      "Program-aware Serving",
      "Active Set",
      "Global Queue",
      "Tool Environment"
    ],
    "motivation": "工业 Agent 服务通常把 LLM engine 和工具容器分开管理，双方都看不到完整程序生命周期。工具暂停会导致 KV thrashing、节点显存不均和工具环境准备延迟。",
    "design": "维护 Agent program 的 active set 控制工作集，用 global queue 在多个节点间平衡请求；对 Acting 阶段暂时不用的 KV 做时间管理，同时把沙箱、磁盘、端口和依赖环境纳入程序生命周期。",
    "result": "在高并发 Agent 和强化学习 rollout 中降低 KV 重算与节点资源不均衡，并通过提前管理工具环境减少 LLM 等待；系统强调简单的 program-aware 运行时集成。",
    "limitations": "跨节点 KV 恢复仍可能退化为重算，工具环境预置增加基础设施复杂度；与 Continuum 的对比依赖不同实验配置，不能直接横向比较绝对数值。"
  },
  "28": {
    "authors": "Qiaoling Chen et al.",
    "affiliation": "Cornell University",
    "keywords": [
      "Agentic Batch Inference",
      "Congestion Control",
      "KV Thrashing",
      "Admission Control"
    ],
    "motivation": "离线 Agent batch 中并发越高不一定越快。活跃工作集超过 KV 容量后，系统会频繁驱逐和 Prefill 重算，GPU 看似繁忙，实际有效吞吐下降。",
    "design": "在线监测 KV 使用率、命中率和拥塞状态，把 Agent-level admission 作为控制变量，动态调整同时推进的 Agent 数量。目标是让活跃工作集停留在可服务区间，避免进入 KV thrashing 区域。",
    "result": "相对无控制的高并发执行，CONCUR 在 Agent batch 上减少缓存颠簸并提升整批完成效率；实验重点验证了通过并发控制换取更高有效吞吐的可行性。",
    "limitations": "主要评估离线 batch inference，不能直接替代在线服务中的 JCT、P99 SLO 和 starvation 分析；控制效果依赖负载与 KV 使用率反馈。"
  },
  "29": {
    "authors": "Yifan Sui et al.",
    "affiliation": "Shanghai Jiao Tong University",
    "keywords": [
      "Predictive Tool Execution",
      "Speculative Execution",
      "Tool-LLM Overlap",
      "Agent Serving"
    ],
    "motivation": "工具调用通常必须等待 LLM 完整生成工具名和参数后才能开始，工具执行与下一轮 LLM 生成天然串行，长工具延迟会直接暴露在 Agent 关键路径上。",
    "design": "从历史轨迹学习局部工具转移，在工具名和参数已有足够确定性时提前执行候选调用。推测结果保存在受控环境中，等 LLM 生成权威调用后进行匹配；匹配则复用，不匹配则丢弃，并用 LLM-side scheduler 控制 session 恢复。",
    "result": "通过把部分工具执行时间隐藏在 LLM 生成阶段，降低工具密集型 Agent 的端到端 latency；论文重点展示了预测工具调用与权威调用校验结合的执行路径。",
    "limitations": "错误预测会产生额外工具开销，需要限制并发、CPU、内存和网络预算；对具有副作用、参数不稳定或不可回滚的工具需要更严格的隔离。"
  },
  "34": {
    "authors": "Bei Ouyang et al.",
    "affiliation": "Rice University",
    "keywords": [
      "Prefix Cache Eviction",
      "Heterogeneous Workloads",
      "Cache Utility",
      "Unified Policy"
    ],
    "motivation": "聊天、RAG、Agent 和长上下文 workload 对 KV 的价值不同，统一采用 LRU 或 TTL 会忽略未来复用、重算成本和 block 大小差异，导致缓存空间分配不公平。",
    "design": "统一描述不同 workload 的 prefix cache utility，将命中收益、占用容量和未来复用纳入 eviction 决策，并通过多队列组织异构请求的缓存状态，使同一策略接口可以适配不同访问模式。",
    "result": "论文展示了统一 eviction 在异构 LLM serving workload 上比单一 LRU/TTL 更稳定的缓存利用效果，重点贡献是提供跨 workload 比较和策略泛化的系统框架。",
    "limitations": "通用策略仍需要为 workload 特征和代价模型提供准确输入；对 Agent 动态路径的专门预测能力不如 KVFlow、Pythia 或 CacheScout。"
  },
  "38": {
    "authors": "Shan Yu et al.",
    "affiliation": "University of California, Los Angeles",
    "keywords": [
      "Workflow Profiling",
      "Speculative Cache",
      "Global Scheduling",
      "Autoscaling"
    ],
    "motivation": "生产 Agent workflow 虽有动态分支，但角色转移、输出长度和 Prompt 组成通常存在稳定规律。被动路由、LRU 和反应式 autoscaling 无法利用这些规律，导致重复 Prefill、负载不均和 fan-out 后扩容滞后。",
    "design": "Gateway 中的 Workflow Profiler 从 request/response log 学习路径、长度分布和 Prompt composition，形成带分支与循环的 predicted path。缓存根据 lineage 保留和释放 KV，调度按容量上界和 workflow 价值排序，autoscaler 沿工作流 wavefront 提前准备副本。",
    "result": "在 coding assistant 和 Deep Research workload 上，平均 JCT 最高降低 2.9 倍，P95 JCT 最高降低 2.02 倍，吞吐最高提升 1.96 倍；部分 Deep Research 场景的 TTFT 从约 4.1 s 降至约 1.4 s。",
    "limitations": "依赖 workflow metadata、历史 trace 和相对稳定的主导路径；新 workflow、版本变化和强随机流程需要 reactive fallback。多租户公平、单 workflow P99 SLO 和完整生产 trace 仍未充分验证。"
  },
  "39": {
    "authors": "Rui Zhang et al.",
    "affiliation": "University of California, Santa Cruz",
    "keywords": [
      "Agent Anchor",
      "Transition Learning",
      "Predictive Eviction",
      "Background Prefetch"
    ],
    "motivation": "Agent 的 system prompt、工具定义和 skills 组成稳定的 anchor，跨轮次和跨 session 的复用价值高于 session history。LRU 看不到 block 所属 Agent，也不知道未来哪个 Agent 会再次出现。",
    "design": "在线统计 Agent-to-Agent transition matrix，从高概率边构造稀疏图并用 BFS 得到候选 Agent 的 hop distance。KV block 综合 survival、age 和 block size 做 eviction；预测足够可靠时，Coordinator 通过标准 Prefill request 对下一 Agent 的 anchor 做后台 warmup。",
    "result": "四类 workload 上 KV hit rate 达到 81%–85%，比 vLLM 提升 10–18 个百分点，平均 TTFT 降低 18%–45%，平均每轮延迟降低 29%–38%。预测 eviction 是主要收益，prefetch 在有时间空隙的场景提供额外加速。",
    "limitations": "一阶 Markov 模型主要使用相邻 Agent，难以表达长历史依赖；冷启动、Selector 策略变化和 prompt fingerprint 漂移会影响准确率，跨节点路由与复杂工具生命周期尚未完整验证。"
  },
  "40": {
    "authors": "Can Xiao et al.",
    "affiliation": "Imperial College London",
    "keywords": [
      "Lookahead Sparse Prefetch",
      "Decode-time KV",
      "CPU Offload",
      "HBM Scaling"
    ],
    "motivation": "长上下文 decode 的 KV 规模可能超过 HBM，把全部历史 KV 放在 GPU 受容量和带宽限制；全部从 CPU 或远端内存搬运又会让每个 decode step 被传输拖慢。",
    "design": "利用 draft token 传播 look-ahead query，预测下一步 Attention 最可能读取的 top-K KV token 或 block，只预取必要子集，并把预测、数据传输和前台 decode overlap。系统将完整 KV 放在容量层，GPU 只保留当前 step 的高价值部分。",
    "result": "相邻 decode step 的 top-20 attention 位置平均有 83.9% 重合，look-ahead 预测与真实下一 token query 的 top-K 一致率平均达到 98.74%，验证了稀疏预取和多层 KV 扩展的可行性。",
    "limitations": "收益依赖 attention 稀疏性和 look-ahead 预测准确率；极端分布变化、传输链路竞争以及稀疏读取对模型质量和 kernel 实现的影响仍需进一步评估。"
  },
  "41": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "重复文档位于不同前文之后，连续前缀不能覆盖这些复用。",
    "design": "独立文档 KV、位置校正与选择性 token 重算，并重叠加载和计算。",
    "result": "原论文在 RAG 的 QA／摘要任务中同时评价质量与 TTFT。",
    "limitations": "额外独立构建、修复和搬运必须计入；追加历史完整驻留时原生前缀已经有效。"
  },
  "42": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "协作模型对相同背景重复 prefill，而不同模型的 KV 不直接兼容。",
    "design": "离线 profiling 选择连续重算层，并传输额外中间状态。",
    "result": "同源模型对的长上下文质量与系统实验。",
    "limitations": "配置依赖模型对；profiling 和额外状态成本不能忽略。"
  },
  "43": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "重复上下文不总是连续前缀。",
    "design": "管理上下文重叠、重排和复用；需核验上下文重叠和复用条件。",
    "result": "长上下文复用与开销实验，分别报告冷启动和单请求开销。",
    "limitations": "重叠识别、初始化成本与模型依赖要分开核算。"
  },
  "44": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "语义近似但 token 序列不同的请求难以精确复用。",
    "design": "带位置的 embedding 匹配、KV 重排、逐层重算与 token retention。",
    "result": "参考文本删改实验和保留率消融。",
    "limitations": "模糊匹配与裁剪均有误差；不能解释为任意位置移动无须校正。"
  },
  "45": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "并发 coding 会话长历史增长、工具等待与容量竞争导致重复 prefill。",
    "design": "前缀感知调度与复用时间预测驱逐。",
    "result": "公开脱敏 trace 有长度与时间信息；不等于公开真实 prompt 和任务答案。",
    "limitations": "长度与 cache_read 不能唯一恢复文本、编辑关系或 KV 因果有效性。"
  },
  "46": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "长轮交互历史不断增长；粗粒度记忆压缩、维护和碎片读取抵消缩短输入的收益。",
    "design": "MemAttention 增量压缩、关联块联合更新与检索，并将相关记忆共置以减少碎片读取。",
    "result": "原论文评估语义记忆、内存占用与服务开销。",
    "limitations": "语义记忆整理与 KV 数值复用不同；必须计入生成、维护和检索记忆的成本。"
  },
  "47": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "工作流、模型与硬件配置写死在应用中。",
    "design": "声明式 workflow、profiling 优化与运行时配置。",
    "result": "多目标端到端配置实验。",
    "limitations": "不是新的 KV 数值复用方法。"
  },
  "48": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "分层缓存命中后加载仍可能阻塞 batch。",
    "design": "分层 KV 数据面与 I/O-aware scheduler。",
    "result": "长上下文、多层存储的系统评测。",
    "limitations": "加载收益受带宽和缓存状态约束。"
  },
  "49": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "孤立模型调用丢失应用数据依赖。",
    "design": "查询计划、共享与缓存感知执行。",
    "result": "可组合应用的端到端优化。",
    "limitations": "计划结构不等于任意动态 coding 历史。"
  },
  "50": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "固定 token 重要性规则难泛化。",
    "design": "离线学习 per-head 保留排序。",
    "result": "多缓存预算下的质量实验。",
    "limitations": "有损 token 裁剪不等于前缀缓存 LRU。"
  },
  "51": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "固定模型映射难适应 workflow 质量和延迟目标。",
    "design": "just-in-time model routing。",
    "result": "模型配置与任务执行评估。",
    "limitations": "跨模型 KV 转换不是默认免费的。"
  },
  "52": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "工具等待与阶段状态影响工作流调度。",
    "design": "state-aware workflow scheduling。",
    "result": "状态与调度策略实验。",
    "limitations": "需与已有预测与暂停恢复方案比对。"
  },
  "53": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "普通调用接口隐藏依赖和可管理状态。",
    "design": "future、managed state 与两级控制。",
    "result": "端到端延迟、吞吐及控制面实验。",
    "limitations": "显式状态接口不直接证明 KV 兼容。"
  },
  "54": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "跨工作流共享缺少可核验身份。",
    "design": "logical identity、execution identity 与 lineage。",
    "result": "多租户工作流执行实验。",
    "limitations": "算子逻辑相同不代表任意 KV 可以共享。"
  },
  "55": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "逐请求调度丢失 workflow 连续性。",
    "design": "工作流级调度、affinity、公平性和缓存管理。",
    "result": "完成时间与吞吐的权衡。",
    "limitations": "更好完成时间可能牺牲峰值吞吐。"
  },
  "56": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "保留长前缀与推进 ready 请求争用显存。",
    "design": "联合入场、搬运、重算与撤销，以剩余路径为目标。",
    "result": "合成和 MetaGPT 类 workflow。",
    "limitations": "依赖可用的工作流结构与代价估计。"
  },
  "57": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "异构阶段混跑产生资源干扰。",
    "design": "按 workflow stage 划分资源池。",
    "result": "架构及有限原型证据。",
    "limitations": "证据强度不足以与完整系统加速并列。"
  },
  "58": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "不同阶段的 KV 通信竞争同一链路。",
    "design": "分阶段 flow 与优先级调度。",
    "result": "disaggregated serving 的 TTFT SLO。",
    "limitations": "后端通信优化，不管理应用上下文语义。"
  },
  "59": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "过去 attention 不足以判断历史的独有信息。",
    "design": "counter-causal surprise 与周期评分。",
    "result": "长上下文与多模型质量测量。",
    "limitations": "token 近似裁剪；需要核算评分成本。"
  },
  "60": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "Harness 掌握依赖与未来意图，Engine 掌握真实缓存与压力，两侧割裂。",
    "design": "四类消息与控制语义连接两侧；在线缓存协调与冻结角色配置作为实例。",
    "result": "SCBench Guard-40 整体 1.61×；BCP／DRB 所选配置 1.23×／2.45×。",
    "limitations": "性能回放与真实任务质量分开；协议承接策略，不提出非前缀修复。"
  },
  "61": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "主动删除、替换与压缩历史让普通前缀缓存失效。",
    "design": "显式编辑四元组；amortize 保留旧影响、校正位置，forget 重新 prefill。",
    "result": "splice 命中＋11.2 pp／延迟最多−241 ms；debug-gym 策略＋14.3 pp。",
    "limitations": "MLA kernel 是主要验证路径；旋转不消除旧因果影响；两条实验不能合并。"
  },
  "62": {
    "keywords": [
      "Application–Engine Codesign"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "token 路由算法节省的大模型计算被模型切换与组批开销抵消。",
    "design": "独立 subserver、pending 状态、异步执行和延迟组批。",
    "result": "AIME 与 SWE-Smith 负载；生成吞吐和请求延迟。",
    "limitations": "各模型保留自己的 KV，不互换数值；不能推断端到端 SWE 解决率。"
  },
  "63": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的生命周期与状态变化。",
    "design": "harness 消息操作与子 agent 生命周期映射为活跃、闲置和死亡缓存。",
    "result": "coding trace 的多层缓存实验。",
    "limitations": "内容死亡与 KV 因果有效是两回事。"
  },
  "64": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的生命周期与状态变化。",
    "design": "复用工作集与 CPU admission，避免写入后未读就淘汰。",
    "result": "SWE-bench／OpenHands；回放与真实运行分开。",
    "limitations": "CPU 相同预算不代表有效缓存机会相同。"
  },
  "65": {
    "keywords": [
      "上下文编辑",
      "批量提交",
      "缓存成本"
    ],
    "authors": "Junjie Yao、Zhangchen Zhou、Zhi-Qin John Xu",
    "affiliation": "上海交通大学",
    "motivation": "结构化工具结果可外置，但每次替换都会使编辑点之后的前缀缓存失效；立即缩短输入未必降低输入成本。",
    "design": "原始对象保留不可变版本，Card 支持按需精确取回；将可替换与正式提交分开，累计等待成本达到共享后缀重建成本时批量提交。",
    "result": "Terminal-Bench 2.1、LongMemEval-V2、SWE-bench Verified 连续任务链的加权输入成本分别减少 47.13%、42.40%、34.12%；完成数为 36/89、10/18、29/50。",
    "limitations": "指标是缓存读取权重下的输入成本，不能等同 GPU 加速；相对 FULL，两组代码任务完成数略降。"
  },
  "66": {
    "keywords": [
      "Lookahead",
      "上下文转换",
      "前后台协同"
    ],
    "authors": "Zaifeng Pan、Qianxu Wang、Zhengding Hu、Chang Chen、Yue Guan、Yanbo Zhou、Steven Swanson、Yufei Ding",
    "affiliation": "加州大学圣迭戈分校",
    "motivation": "达到上下文阈值后才同步转换并重建 KV，会使长轮 Agent 在转换点出现 TTFT 尖峰。",
    "design": "主状态继续执行，lookahead 状态提前转换稳定片段并准备 KV；引擎按前台 TTFT/TBT 预算准入后台 chunk，抑制干扰。",
    "result": "28 步 MiniAgent 代码库分析中，Qwen3-8B/32B 的转换点 tail TTFT 平均降低 62.0%/61.5%；摘要策略最高改善 11.9 倍。",
    "limitations": "收益针对转换点 TTFT，不是完整任务加速；需要可分段转换及额外计算、KV 容量。PDF 的 PVLDB 信息为占位格式，当前按 arXiv 记录。"
  },
  "67": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的修复与状态变化。",
    "design": "固定当前 prompt 后改变缓存经历，检验修复跨轮历史敏感性。",
    "result": "滚动文档字段提取，不是 coding。",
    "limitations": "分叉输入的 F1 不能隔离缓存状态误差。"
  },
  "68": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的版本与状态变化。",
    "design": "记录文件、符号和测试证据版本，恢复前核验仓库。",
    "result": "DeepSWE／SWE-EVO／SWE-Milestone。",
    "limitations": "证据有效不等于 KV 精确有效。"
  },
  "69": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的修复与状态变化。",
    "design": "使用生产者 decode 已生成 KV，交给接收者修复。",
    "result": "GSM8K、MMLU、HumanEval；效率另设受控负载。",
    "limitations": "不保证普通追加会话有额外收益。"
  },
  "70": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的生命周期与状态变化。",
    "design": "阶段 query buffer 指导 token 保留与物理页面回收。",
    "result": "BFCL、τ²-bench；吞吐另设 workload。",
    "limitations": "有损 token 淘汰与前缀缓存淘汰不同。"
  },
  "71": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的版本与状态变化。",
    "design": "版本发布权限、旧输出阻止、有效前缀继承与异步回收。",
    "result": "修订与回收压力场景。",
    "limitations": "需区分版本发布、执行取消与 KV 状态保留的语义。"
  },
  "72": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的生命周期与状态变化。",
    "design": "读取工具运行进度指导缓存保留与恢复。",
    "result": "SWE trace 的工具尾部等待。",
    "limitations": "提前恢复属于预取机制，收益取决于工具进度与恢复时机。"
  },
  "73": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的编辑与状态变化。",
    "design": "版本对齐、dirty region 与选择性恢复。",
    "result": "构造的编辑 QA、多模型。",
    "limitations": "profile 与元数据有成本；不是长轮 coding 的完整证明。"
  },
  "74": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的修复与状态变化。",
    "design": "resource-wise attention 与局部位置让 tool／skill KV 可组合。",
    "result": "公开工具与 skill 数据源。",
    "limitations": "需要训练适配，不能直接用于任意冻结模型。"
  },
  "75": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的生命周期与状态变化。",
    "design": "轮转 idle agent、从尾部淘汰，保护更多连续前缀。",
    "result": "SGLang 的追加历史竞争。",
    "limitations": "先检查较好的精确保留基线，再判断近似复用机会。"
  },
  "76": {
    "keywords": [
      "KV State / Reuse"
    ],
    "authors": "见原论文",
    "affiliation": "研究对象与机制见下文",
    "motivation": "关注 Agent 上下文的生命周期与状态变化。",
    "design": "层次 KV 准备与混合上下文执行的 admission 协调。",
    "result": "coding agent serving。",
    "limitations": "独立构建异步化可能只是适配修正。"
  },
  "77": {
    "keywords": [
      "对象生命周期",
      "恢复指针",
      "旁路规划"
    ],
    "authors": "Xubin Hao、Hongjin Meng、Xin Yin、Jiawei Zhu、Chenpeng Cao",
    "affiliation": "小红书",
    "motivation": "长轮工具轨迹包含精确路径、URL、表格值和编辑产物；按时间裁剪或自由摘要可能丢失后续依赖及恢复入口。",
    "design": "为历史对象分配稳定 ID；旁路 LLM 规划 Fold、Mask、Prune，harness 验证与预演后在安全边界提交，Fold 保留原文 sidecar 和恢复指针。",
    "result": "332 条生产会话上三个 planner 删除 31.04%–33.98% token，未来依赖 no-impact 为 91.27%–94.58%；在线主 Agent 平均输入减少约 10%–15%。",
    "limitations": "no-impact 是离线裁判对依赖保留的判断，不是任务成功率；原始生产轨迹不公开，在线分组非随机。"
  }
};

const PAPER_NOTES = {
  "1": "综述 LLM 推理优化的完整技术谱系，覆盖模型、计算、显存、并行和 serving，为后续工作提供问题地图。",
  "2": "通过 IO-aware tiling 将 attention 的中间矩阵留在片上 SRAM，减少 HBM 读写，建立高效 attention kernel 的底层基础。",
  "3": "重新设计 FlashAttention 的并行划分和工作分配，提升长序列和多 GPU 场景下的 GPU 利用率。",
  "4": "用小模型先生成候选 token，再由大模型一次性验证，在保持自回归结果分布的同时减少大模型串行解码步数。",
  "5": "将 speculative sampling 系统化为 draft-and-verify 流程，分析候选长度、接受率与实际解码加速之间的关系。",
  "6": "在目标模型顶部增加多个轻量 decoding heads，让一个 forward 同时提出多个未来 token，并用树结构验证候选。",
  "7": "把多个候选序列组织成 token tree，在一次并行验证中完成 speculative decoding，适合 beam search 和结构化生成。",
  "8": "训练模型预测多个未来 token，使单次 forward 能产生更长候选，探索训练目标与推理吞吐的联合优化。",
  "9": "系统梳理 speculative decoding 的算法、接受率、实现和评测方法，作为该方向的教程型补充。",
  "10": "让 GPU 发起更细粒度的计算与 collective 通信重叠，减少分布式执行中的同步等待和通信空洞。",
  "14": "首次提出 chunked prefill 与 decode piggybacking：将 Prefill 切块后嵌入 Decode 批次，降低长 Prefill 对在线生成的阻塞。",
  "17": "将 Prefill 与 Decode 放到不同实例，按阶段特征分别扩展资源，缓解混合负载互相干扰。",
  "18": "围绕 goodput 将 Prefill/Decode 解耦部署，并联合 placement 与传输代价决定两类实例的资源比例。",
  "19": "用分页式 KV block 管理非连续显存，降低碎片和过度预留，是后续多数 prefix cache 与 serving 系统的底层依托。",
  "25": "在请求信息不完整、动态图逐步展开的情况下在线修正长度和依赖估计，用 GMAX 联合选择优先级与 batch composition 以满足端到端 SLO。",
  "30": "将长上下文拆成具有不同生命周期或访问模式的 segment，研究跨 segment 的注意力与缓存组织。",
  "31": "通过 Aries 实验框架重新测量 Agentic serving 的云基础设施代价，把模型服务、工具环境、存储和网络放入统一实验视角。",
  "32": "研究 Agent 如何持续积累、更新和组织上下文，强调上下文工程与缓存/长上下文系统之间的基础联系。",
  "33": "从工具集成推理轨迹中测量效率损失，揭示工具等待、重复 Prefill、KV 驱逐等成本不能由 accuracy 单一指标反映。",
  "34": "针对聊天、RAG、Agent 和长上下文等异构负载，统一 prefix cache eviction 的收益、容量和复用判断。",
  "35": "实证分析 reasoning language model 的输出长度、阶段行为和 serving 瓶颈，为长思维链推理的资源配置提供测量依据。",
  "36": "面向 Agent 的在线 KV 压缩，在运行过程中回收或压缩不再有价值的上下文，降低多轮执行的显存压力。",
  "37": "利用预测信息管理动态 Agent workflow 的 KV admission、保留和传输，连接 workflow pattern 与缓存系统控制。",
  "41": "独立文档 KV、位置校正与选择性 token 重算，并重叠加载和计算。 额外独立构建、修复和搬运必须计入；追加历史完整驻留时原生前缀已经有效。",
  "42": "离线 profiling 选择连续重算层，并传输额外中间状态。 配置依赖模型对；profiling 和额外状态成本不能忽略。",
  "43": "管理上下文重叠、重排和复用；需核验上下文重叠和复用条件。 重叠识别、初始化成本与模型依赖要分开核算。",
  "44": "带位置的 embedding 匹配、KV 重排、逐层重算与 token retention。 模糊匹配与裁剪均有误差；不能解释为任意位置移动无须校正。",
  "45": "前缀感知调度与复用时间预测驱逐。 长度与 cache_read 不能唯一恢复文本、编辑关系或 KV 因果有效性。",
  "46": "MemAttention 增量压缩、关联块联合更新与检索，并将相关记忆共置以减少碎片读取。 语义记忆整理与 KV 数值复用不同；必须计入生成、维护和检索记忆的成本。",
  "47": "声明式 workflow、profiling 优化与运行时配置。 不是新的 KV 数值复用方法。",
  "48": "分层 KV 数据面与 I/O-aware scheduler。 加载收益受带宽和缓存状态约束。",
  "49": "查询计划、共享与缓存感知执行。 计划结构不等于任意动态 coding 历史。",
  "50": "离线学习 per-head 保留排序。 有损 token 裁剪不等于前缀缓存 LRU。",
  "51": "just-in-time model routing。 跨模型 KV 转换不是默认免费的。",
  "52": "state-aware workflow scheduling。 需与已有预测与暂停恢复方案比对。",
  "53": "future、managed state 与两级控制。 显式状态接口不直接证明 KV 兼容。",
  "54": "logical identity、execution identity 与 lineage。 算子逻辑相同不代表任意 KV 可以共享。",
  "55": "工作流级调度、affinity、公平性和缓存管理。 更好完成时间可能牺牲峰值吞吐。",
  "56": "联合入场、搬运、重算与撤销，以剩余路径为目标。 依赖可用的工作流结构与代价估计。",
  "57": "按 workflow stage 划分资源池。 证据强度不足以与完整系统加速并列。",
  "58": "分阶段 flow 与优先级调度。 后端通信优化，不管理应用上下文语义。",
  "59": "counter-causal surprise 与周期评分。 token 近似裁剪；需要核算评分成本。",
  "60": "四类消息与控制语义连接两侧；在线缓存协调与冻结角色配置作为实例。 性能回放与真实任务质量分开；协议承接策略，不提出非前缀修复。",
  "61": "显式编辑四元组；amortize 保留旧影响、校正位置，forget 重新 prefill。 MLA kernel 是主要验证路径；旋转不消除旧因果影响；两条实验不能合并。",
  "62": "独立 subserver、pending 状态、异步执行和延迟组批。 各模型保留自己的 KV，不互换数值；不能推断端到端 SWE 解决率。",
  "63": "harness 消息操作与子 agent 生命周期映射为活跃、闲置和死亡缓存。 内容死亡与 KV 因果有效是两回事。",
  "64": "复用工作集与 CPU admission，避免写入后未读就淘汰。 CPU 相同预算不代表有效缓存机会相同。",
  "65": "原始对象保留不可变版本，Card 支持按需精确取回；将可替换与正式提交分开，累计等待成本达到共享后缀重建成本时批量提交。 指标是缓存读取权重下的输入成本，不能等同 GPU 加速；相对 FULL，两组代码任务完成数略降。",
  "66": "主状态继续执行，lookahead 状态提前转换稳定片段并准备 KV；引擎按前台 TTFT/TBT 预算准入后台 chunk，抑制干扰。 收益针对转换点 TTFT，不是完整任务加速；需要可分段转换及额外计算、KV 容量。PDF 的 PVLDB 信息为占位格式，当前按 arXiv 记录。",
  "67": "固定当前 prompt 后改变缓存经历，检验修复跨轮历史敏感性。 分叉输入的 F1 不能隔离缓存状态误差。",
  "68": "记录文件、符号和测试证据版本，恢复前核验仓库。 证据有效不等于 KV 精确有效。",
  "69": "使用生产者 decode 已生成 KV，交给接收者修复。 不保证普通追加会话有额外收益。",
  "70": "阶段 query buffer 指导 token 保留与物理页面回收。 有损 token 淘汰与前缀缓存淘汰不同。",
  "71": "版本发布权限、旧输出阻止、有效前缀继承与异步回收。 需区分版本发布、执行取消与 KV 状态保留的语义。",
  "72": "读取工具运行进度指导缓存保留与恢复。 提前恢复属于预取机制，收益取决于工具进度与恢复时机。",
  "73": "版本对齐、dirty region 与选择性恢复。 profile 与元数据有成本；不是长轮 coding 的完整证明。",
  "74": "resource-wise attention 与局部位置让 tool／skill KV 可组合。 需要训练适配，不能直接用于任意冻结模型。",
  "75": "轮转 idle agent、从尾部淘汰，保护更多连续前缀。 先检查较好的精确保留基线，再判断近似复用机会。",
  "76": "层次 KV 准备与混合上下文执行的 admission 协调。 独立构建异步化可能只是适配修正。",
  "77": "为历史对象分配稳定 ID；旁路 LLM 规划 Fold、Mask、Prune，harness 验证与预演后在安全边界提交，Fold 保留原文 sidecar 和恢复指针。 no-impact 是离线裁判对依赖保留的判断，不是任务成功率；原始生产轨迹不公开，在线分组非随机。"
};

const PHASE_GROUPS = [
  {
    "number": "PHASE 01",
    "period": "2022-07 → 2024-03",
    "title": "单次请求：从生成循环到高效 Serving Engine",
    "thesis": "研究对象仍是一条 LLM 请求，但系统开始获得 token 级调度、输出长度预测以及 Prefill / Decode 阶段意识。",
    "lanes": [
      {
        "title": "Serving 执行与资源调度",
        "ids": [
          11,
          12,
          13,
          14,
          15,
          16,
          17,
          18,
          19,
          1,
          10
        ]
      },
      {
        "title": "单请求计算与生成加速",
        "ids": [
          2,
          3,
          4,
          5,
          6,
          7,
          8,
          9
        ]
      }
    ]
  },
  {
    "number": "PHASE 02",
    "period": "2024-04 → 2025-07",
    "title": "静态应用 DAG：从请求调度到端到端工作流",
    "thesis": "系统开始理解多个请求之间的生产者、消费者和数据依赖；优化目标从单请求延迟扩展到整条应用图。",
    "lanes": [
      {
        "title": "应用 DAG 与端到端执行",
        "ids": [
          20,
          21,
          22
        ]
      },
      {
        "title": "已知 Workflow 的 KV 管理",
        "ids": [
          23
        ]
      }
    ]
  },
  {
    "number": "PHASE 03",
    "period": "2025-11 → 2026-08",
    "title": "动态图 Agent：从运行时调度到预测式 KV 协同",
    "thesis": "这一阶段的论文都以动态 Agent workflow 为场景：系统先处理运行时程序状态、工具等待和实时拥塞，再逐步利用历史轨迹与 workflow 规律主动准备资源，并将控制下沉到 token / block 级 KV。",
    "lanes": [
      {
        "title": "运行时程序调度与资源协调",
        "ids": [
          24,
          25,
          26,
          27,
          28
        ]
      },
      {
        "title": "工具执行与局部协同",
        "ids": [
          29
        ]
      },
      {
        "title": "Workflow 预测与主动资源管理",
        "ids": [
          32,
          33,
          34,
          35,
          37,
          38,
          39
        ]
      },
      {
        "title": "Token / Block 级 KV 与 Agent 基础设施",
        "ids": [
          30,
          31,
          36,
          40
        ]
      }
    ]
  },
  {
    "number": "PHASE 04",
    "period": "专题分类 · 块级复用与执行成本",
    "title": "从前缀复用到块级修复与完整 Agent 执行",
    "thesis": "按优化对象归类；论文首次公开时间见每条记录。区分缓存命中、计算节省、任务质量与端到端收益。",
    "lanes": [
      {
        "title": "块级、语义与跨模型 KV 复用",
        "ids": [
          41,
          42,
          43,
          44,
          67,
          69,
          74
        ]
      },
      {
        "title": "Coding 负载、缓存执行与数据面",
        "ids": [
          45,
          46,
          48,
          64,
          75,
          76
        ]
      },
      {
        "title": "Workflow 表达、配置与整体执行",
        "ids": [
          47,
          49,
          51,
          52,
          53,
          54,
          55,
          56,
          57,
          58,
          62
        ]
      }
    ]
  },
  {
    "number": "PHASE 05",
    "period": "专题分类 · 跨层协同与状态生命周期",
    "title": "Harness–Engine 协同与 Agent 上下文生命周期",
    "thesis": "按 Harness 与推理引擎协同、上下文演化及 KV 状态生命周期组织相关论文，区分接口、调度策略与状态管理机制。",
    "lanes": [
      {
        "title": "Harness–Engine 协同",
        "ids": [
          60
        ]
      },
      {
        "title": "上下文演化与 KV 状态",
        "ids": [
          61,
          65,
          66,
          73,
          77,
          63
        ]
      },
      {
        "title": "相关运行时与状态管理工作",
        "ids": [
          50,
          59,
          68,
          70,
          71,
          72
        ]
      }
    ]
  }
];
