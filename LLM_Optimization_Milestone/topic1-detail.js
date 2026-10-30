(function(){
  'use strict';
  var esc=function(v){return String(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})};
  var json=function(v){return esc(JSON.stringify(v,null,2))};
  var data={
    research:{
      title:'ODR Research · 机制示意，未跑DeepResearchBench',
      overview:'Open Deep Research（ODR）把研究简报交给 Supervisor，由它拆分并派发并行 Researcher。每个 Researcher 在搜索与反思循环后压缩自己的证据，再把结果交回 Supervisor 决定继续研究或生成报告。图中合并展示压缩环节，橙色的覆盖与资源判断表示 Topic1 建议接入的位置。',
      intro:{purpose:'面向开放式研究问题，主管 Agent 将任务拆成子问题，研究员并行搜索、反思并压缩带来源的证据，再交回主管决定追加研究或生成报告。',flow:'研究问题 → 主管拆分 → 并行研究 → 单元内压缩 → 主管判断 → 报告',designSpace:'可研究：每批结果返回后，结合证据缺口、后端队列 / KV 压力与剩余预算，决定下一批释放多少研究单元、哪些子问题继续深挖，以及何时进入报告。分别控制总研究单元数与同时运行数，不把降低并发等同于减少总调用。'},
      sub:'研究问题 → 主管规划 → 并行研究 → 证据压缩 → 质量判断 → 报告',
      meta:[['任务输入','DeepResearchBench · 100 条 query'],['工作流','Open Deep Research'],['并行上限','max_concurrent_research_units = 5'],['质量终点','coverage · citation · RACE / FACT']],
      designs:[['并行宽度','每批释放多少 researcher unit','max_concurrent_research_units'],['监督轮数','Supervisor 反思与追加子研究的轮数上限','max_researcher_iterations'],['工具循环深度','单个 Researcher 的工具调用迭代上限','max_react_tool_calls'],['停止 / 扩展','按证据与资源判断下一批任务；属于 Topic1 建议','ResearchComplete / iteration cap']],
      calls:['DeepResearchBench query → 可选澄清 → 结构化 research brief','Supervisor：think_tool → ConductResearch → 评估进展','当前批次：接收并行 research calls；超限调用会收到错误 ToolMessage','Researcher unit：搜索 / 浏览 / MCP 工具调用与反思循环','Compression：去重整理发现，保留来源与引用','Final report：根据 research brief 生成同语言报告'],
      actions:['width：下一批 accepted research units 的数量','depth：Supervisor 迭代与每个 researcher tool loop 的上限','tool budget：单个 unit 的 max_react_tool_calls','expand：coverage gap、证据冲突或 deadline 风险时追加 unit','stop：ResearchComplete、没有待调用工具或达到 iteration cap'],
      params:['max_concurrent_research_units = 5（默认值）','max_researcher_iterations = 6（默认值）','max_react_tool_calls = 10（默认值）','max_structured_output_retries = 3（默认值）','research / compression / final model = openai:gpt-4.1（配置可替换）'],
      prompt:'[Supervisor system prompt]\\nYou are a research supervisor. Your job is to conduct research by calling the ConductResearch tool.\\nUse think_tool before calling ConductResearch, and after each ConductResearch to assess progress.\\nMaximum {max_concurrent_research_units} parallel agents per iteration.\\n\\n[Researcher system prompt]\\nYou are a research assistant conducting research on the user input topic.\\nUse tools to gather information; after each search, reflect and plan next steps.\\nStop when the answer is sufficiently supported.\\n\\n[Compression / final report]\\nPreserve relevant statements and sources, include inline citations, and answer in the language of the human messages.',
      raw:{workload:'DeepResearchBench',task_id:1,topic:'Finance & Business',language:'zh',prompt:'收集整理目前中国9阶层实际收入和财务状况，特别研究得出中国的中产有哪些特点，实际中产人数，财力等等',odr_config:{max_concurrent_research_units:5,max_researcher_iterations:6,max_react_tool_calls:10,max_structured_output_retries:3,research_model:'openai:gpt-4.1',compression_model:'openai:gpt-4.1',final_report_model:'openai:gpt-4.1'},trace_note:'query 与配置来自公开数据 / 源码；本仓库没有测量该任务的真实运行 trace。'},
      note:'ODR 源码中，Supervisor 绑定 ConductResearch、ResearchComplete、think_tool；researcher 的工具调用可并行执行；当前批次按 max_concurrent_research_units 截取。'
    },
    coding:{
      title:'Coding Harness · 候选与修复结构示意',
      overview:'LiveCodeBench 提供代码题和离线评测协议，不规定 Agent 拓扑。此图展示一种可选的候选、测试、审查和修复编排。此前只用 DSH 修复了自编结账服务，7项原测试通过、一个 Session；LiveCodeBench / SWE-bench 均0题，图中完整多候选流程尚未实测。',
      intro:{purpose:'把编程题转换为多个候选程序，通过编译和测试发现失败，再由审查或修复流程筛选结果。LiveCodeBench 提供题目与离线质量评测，具体 Agent 流程由 harness 组织。',flow:'代码题 → 规划 → 候选生成 → 测试与执行 → 审查 / 修复 → 输出',designSpace:'可研究：每批可见测试 / 审查结果返回后，结合实时后端负载，选择追加新候选、继续修复还是结束，并调整下一批并发量。候选总数、并发数、修复轮次分开计量；隐藏测试只作离线评测。反馈迭代本身已见于 Murakkab，待验证的是资源状态参与决策的增量收益。'},
      sub:'代码题 → 规划 → 并行候选 → 测试执行 → 审查 / 修复 → 离线评测',
      meta:[['任务输入','LiveCodeBench release_v6'],['工作流','harness 层候选流程示意'],['采样与并发','n = 10 是采样数；并发宽度另设'],['评测','pass@1 / pass@5 · 隐藏测试离线']],
      designs:[['候选宽度','首轮及后续轮次启动多少 Writer','n / candidate width'],['测试时机','何时编译、跑样例或追加定向测试','test schedule'],['审查开关','哪些失败或冲突候选需要 Reviewer','reviewer enable'],['修复深度','失败反馈最多触发多少轮修复','repair depth']],
      calls:['LiveCodeBench problem → Planner 解析题目与约束','Writer A / B / N：并行生成候选代码','Tester：编译、运行样例或 targeted tests','Python sandbox：记录 stdout、stderr、timeout 与测试结果','Reviewer / ranker（可选）：比较候选与测试 trace','Repair：根据失败反馈修改候选并回到测试','Selector → Answer；hidden evaluator 离线计算 pass@1 / pass@5'],
      actions:['candidate width：首轮及下一轮 Writer 数量','reviewer enable：何时增加 critic / ranker 阶段','repair depth：失败候选最多回修多少轮','test schedule：样例、公测、定向测试的执行顺序','stop：公开测试通过后可考虑停止；hidden test 不可回流在线控制'],
      params:['release_v6 = 1055 problems（官方 README）','code generation n = 10；temperature = 0.2','metrics = pass@1 / pass@5','scenarios = codegeneration / selfrepair / testoutputprediction / codeexecution','Writer / Tester / Reviewer / Repair 是 harness 抽象，不是 benchmark 固定拓扑'],
      prompt:'[task prompt]\\nGenerate a candidate solution for the programming problem.\\n\\n[test feedback]\\nReview the public or targeted test trace and propose a repair.\\n\\n以上是 workflow schema placeholder，不是 LiveCodeBench 官方固定 prompt；实际 prompt 由选定 harness 提供。',
      raw:{benchmark:'LiveCodeBench',release:'release_v6',problems:1055,scenarios:['codegeneration','selfrepair','testoutputprediction','codeexecution'],codegeneration:{n:10,temperature:0.2},metrics:['pass@1','pass@5'],workflow_trace:{planned_candidates:'harness-defined',started_candidates:'to measure',reviewer_calls:'to measure',repair_rounds:'to measure'},hidden_test_signal:'offline only'},
      note:'LiveCodeBench 定义题目、场景和评测协议；Writer / Test / Reviewer / Repair 是 harness 工作流。hidden evaluation 只用于离线评测。'
    },
    dsh:{
      title:'Harness × Engine · DAG 展开与请求派发',
      overview:'主图是 Topic1 待验证的跨层接入示意：Harness 维护逐步显露的工作图、合法逻辑工作和工具状态；输入绑定后才形成可提交的模型请求。拟接入引擎队列、实际 KV 与执行成本，控制分波启动和提交时机；结果再推进工作图。它不表示 DSH 已有这个控制器。原生 DSH 生命周期放在下方折叠区，作为实现背景。',
      intro:{purpose:'研究前端怎样结合引擎真实状态，决定何时展开分支、何时提交模型请求，并考虑这些动作会释放多少后继工作。适用于动态工作流的共同结构；DSH 是实现载体之一，主图不是 DSH 原生功能图。',flow:'用户任务 / 已揭示 DAG → 合法逻辑工作 → 推进分支 → 输入绑定 → 引擎执行 → 结果更新依赖；工具返回后继续当前分支，满足完成条件后输出',designSpace:'D1：结合工具中工作与后端压力，分波启动必做分支；D2：选择已绑定调用的提交时机。两者先固定必做工作做 E1。D3：应用允许时，结合有效部分结果控制可选探索，作为 E2 单独验证质量。需比较同信息、同动作权限的后端策略，尚未确认性能收益或创新。'},
      sub:'逐步展开 → 输入绑定 → 派发 → 执行 → 结果更新；工具与引擎状态参与下一步决定',
      meta:[['前端可见','已揭示依赖 / 合法前沿 / 工具中工作'],['后端可见','分模型队列 / 实际 KV / 执行成本'],['E1 · 主图','必做分支分波；已绑定调用派发'],['E2 · 后续','仅可选探索改总量；独立验证质量']],
      designs:[['D1 · 分波启动','当前队列相近时，工具中工作与后继需求能否改变合适的展开时机？','release_branch(node_id)'],['D2 · 请求提交','对输入已绑定的调用放行或暂缓；计入前端等待，防止只搬动队列','submit_call(call_id)'],['D3 · 可选探索','仅在应用允许、有效验证条件成立时改变后续工作量；与 E1 分开','expand(optional_group, count)'],['同信息后端对照','给后端同样依赖、工具信息和动作权限，检验跨层控制的独立价值','E1 / E2 · 待验证']],
      calls:['用户任务初始化工作图；后继依赖与分支随执行逐步显露，不预知完整未来图','依赖满足且获得应用授权的逻辑工作进入可启动集合；D1 拟控制分波启动','推进已启动分支：可以形成模型调用，也可以进入工具阶段；不是每步都调用模型','仅在准确输入绑定、依赖满足后，将模型调用标为 READY；D2 拟选择提交时机','引擎重新核验容量、排队、安排 prefill / decode 与 KV；前端观测不代表资源预留','模型结果更新 Harness 状态与已揭示依赖；工具返回则恢复对应分支，之后才可能形成新调用','满足工作流完成条件后输出；应用允许的可选探索另由 E2 检验，不因压力删必做任务'],
      actions:['D1：release_branch(node_id)，或 defer 到事件 / 有界超时；保留必做工作与依赖','D2：submit_call(call_id)，或暂缓已绑定调用；Engine 拥有最终容量仲裁权','D3 / E2：expand(optional_group_id, count)；有效终止条件成立后可不再展开可选工作','输入：已揭示 DAG、工具类型与已等待时长、历史返回分布、真实队列 / KV / 成本及采样年龄','未知工具输出、准确返回时刻与未来完整图不作为在线已知量','对照：压力、DAG / 缓存、简单背压与同信息后端；报告任务总耗时、全部等待和真实工作量'],
      params:['E1 固定必做分支、原始配置与工作量；模型请求集固定仅适用于回放 / 受控子图','根任务 / 节点 / 请求 / 工具 / 模型 / 上下文版本分别用 ID 关联','记录逻辑就绪、分支启动、输入绑定、前端放行、引擎接受 / 执行 / 完成和工具起止','引擎状态必须带采样时间；KV fit 不等于时延保证；缺失指标显式标缺失','E2 单列可选分支与有效接受条件；公开测试在线，隐藏测试仅离线','DSH 背景版本 f3803c9：默认 activation 上限 8、工具委派深度 1；不等于引擎并发预算'],
      prompt:'[参数与 Prompt 边界，非新增 Agent prompt]\n跨层控制首先作为程序策略，不默认增加一个 LLM 调度 Agent。\n每个模型调用沿用所选真实 workflow 的 prompt、采样参数与输出上限，并关联 call_id / context_version。\n输入未绑定时不能把未知工具输出拼成虚构 prompt。\n本图没有统一的官方 prompt，也没有真实运行日志。\n\nDSH 原生 spawn / fork / delivery 的机制见折叠实现背景与源码核查页。',
      raw:{kind:'proposed_instrumentation_schema_not_executed',scope:'Harness DAG expansion and engine-aware request dispatch',measured:false,workflow:{root_id:'<task id>',node_id:'<logical node id>',known_dependencies:['<revealed predecessor>'],required_or_optional:'<application contract>',join_condition:'<application contract>'},invocation:{call_id:'<request id>',model_id:'<model>',context_version:'<bound input version>',prompt_ref:'<actual prompt reference>',generation_params:'<actual sampling and output limits>',events:['input_bound','frontend_release','engine_accept','execution_start','model_complete']},tool:{tool_id:'<tool id>',events:['tool_start','tool_complete'],online_return_time:'unknown; use elapsed time and historical distribution'},engine_observation:{sample_time:'<timestamp>',queue:'<per model>',kv_residency:'<actual telemetry or unavailable>',serving_cost:'<measured or estimated; label separately>'},controls:{E1:['release_branch','submit_call','defer'],E2_optional_only:['expand','stop_optional_with_valid_reason']},native_dsh_background:{source_commit:'f3803c96974ad4a94195fb97e5c637e9c2a3afe3',maxActiveSubagents:8,tool_default_maxDepth:1,engine_aware_dispatch:'not asserted as native capability'}},
      note:'主图、D1 / D2 / D3 与反馈通道是待验证接入方案，不是已运行 trace，也不是 DSH 自带能力。已有工作边界与实验见 topic1-harness-engine-study-20261029.md；折叠区的原生生命周期依据 DSH 固定 commit f3803c9。'
    }
  };
  var nodeInfo={
    research:{
      input:['研究问题 / Research question','外部 workload 输入，不是 Agent。它把真实 query 交给 research brief，再由 Supervisor 判断是否需要拆分。','前接：DeepResearchBench 原始任务','后续：研究简报'],
      brief:['研究简报 / Research brief','把问题整理成可执行的研究目标与约束，接在 query 后、Supervisor 前；澄清是可选步骤。','前接：研究问题 / 可选澄清','后续：Supervisor'],
      supervisor:['主管 Agent / Supervisor','规划研究并调用 think_tool、ConductResearch 或 ResearchComplete。它连接研究目标与并行 researcher，并在每批结果后判断下一步。','前接：研究简报','后续：当前批次中的 Researcher units'],
      r1:['研究员 1 / Researcher 1','处理一个子问题，使用搜索、浏览器或 MCP 工具收集证据，并在工具调用后反思。结果交给 Compression。','前接：Supervisor 分派的子问题','后续：证据压缩'],
      r2:['研究员 2 / Researcher 2','与其他 unit 并行执行搜索—反思循环。它体现当前批次的宽度，不是 benchmark 固定 Agent。','前接：Supervisor 分派的子问题','后续：证据压缩'],
      rn:['研究员 N / Researcher N','表示可扩展的并行 unit。实际数量由并行上限及资源状态共同决定，结果仍进入同一汇总阶段。','前接：Supervisor 分派的子问题','后续：证据压缩'],
      compress:['证据压缩 / Compression','在 ODR 原实现中，每个 Researcher 子图都有自己的 compress_research：它把该单元的 raw notes 整理成保留引用的发现，再返回 Supervisor。本图为便于阅读将压缩环节合并展示，并不表示原实现中只有一次全局压缩调用。','前接：每个 Researcher 的工具循环','后续：压缩结果返回 Supervisor'],
      gate:['覆盖与冲突判断 / Quality gate','这是 Topic1 建议的控制判断，而不是 ODR 自带的独立 Agent。它将 Researcher 的证据覆盖、冲突与后端资源状态结合起来，辅助 Supervisor 判断追加研究还是收束；实际接入方式仍需实验。','前接：压缩结果 + backend state','后续：Supervisor 追加研究，或生成报告'],
      backend:['后端资源状态 / Backend state','汇集队列长度、KV 使用、CPU 容量和截止时间，作为 Topic1 控制判断的输入。它本身不生成研究内容，也不替代 Researcher；其作用是在下一批子任务释放前限制或调整工作量。','前接：推理引擎 / 资源监控','后续：Topic1 覆盖与资源判断'],
      final:['最终报告 / Final report','把压缩证据组织成用户可读答案；coverage、citation 与 RACE / FACT 是质量评测关注点。','前接：质量门判断完成','后续：离线质量评测']
    },
    coding:{
      problem:['代码题 / Code problem','LiveCodeBench workload 输入，含题目与约束；benchmark 不规定 Planner、Writer 等 Agent 拓扑。','前接：任务采样 / benchmark','后续：Planner'],
      planner:['规划 Agent / Planner','解析题意和约束，决定候选生成与测试策略，随后将工作交给并行 Writer。','前接：代码题','后续：Writer A / B / C'],
      wa:['Writer A / 代码生成 Agent','根据 Planner 给出的题意分析与约束独立生成候选程序 A，然后把代码交给 Tester。它与其他 Writer 处于同一候选生成阶段；增加同类分支会增加采样和调用数量，但是否并发执行由 harness 决定。','前接：Planner 的题意与约束','后续：Tester / 候选测试'],
      wb:['Writer B / 代码生成 Agent','接收与 Writer A 相同的题目和规划，独立生成候选程序 B，再进入同一测试流程。这个分支用来增加解法多样性，是否值得启动取决于已有候选结果与后端预算，并不是 benchmark 强制要求的第二个 Agent。','前接：Planner 的题意与约束','后续：Tester / 候选测试'],
      wn:['Writer N','表示可配置的其余候选生成分支；实际数量由 harness 的 candidate width 决定。','前接：Planner 或 Repair 后的下一轮','后续：候选汇总与测试'],
      tests:['测试器 / Tester','编译候选并运行样例或 targeted tests，产生可供执行环境和 Reviewer 使用的测试结果。','前接：Writer 候选','后续：执行沙箱'],
      sandbox:['执行沙箱 / Python sandbox','这是运行代码的环境，不是质量 Agent。它产生 stdout、stderr、timeout 与测试结果。','前接：Tester 的执行请求','后续：Reviewer / Repair'],
      reviewer:['审查与排序 / Reviewer','可选地比较候选、测试 trace 与失败原因，决定接受候选还是进入 Repair。','前接：测试结果与候选代码','后续：Selector，或 Repair'],
      repair:['修复 Agent / Repair','根据测试失败反馈修改候选，再送回 Tester；repair depth 决定最多回环多少轮。','前接：Reviewer / 失败测试','后续：再次测试'],
      selector:['候选选择 / Selector','从可接受候选中选出在线输出；未通过候选可继续修复。','前接：Reviewer 接受分支','后续：Answer'],
      answer:['在线答案 / Answer','harness 返回的候选代码。它先完成在线工作流，再交给离线评测。','前接：Selector','后续：Hidden evaluation'],
      hidden:['隐藏评测 / Hidden evaluation','离线计算 pass@1 / pass@5，只提供最终质量信号，不能回流在线调度器。','前接：在线答案','后续：实验统计']
    },
    dsh:{
      dag:['已揭示工作图 / Evolving DAG','接收用户任务并维护已经揭示的依赖、汇合条件和未展开分支。模型结果回来后更新它，再确定哪些逻辑工作可以启动。未来完整图、工具结果和循环次数不预先假定已知；循环在运行轨迹中逐步展开。','前接：用户任务 / 执行结果','后续：合法逻辑工作；满足条件后结束'],
      pending:['合法逻辑工作 / Runnable work','表示依赖满足、获应用授权但尚未启动的工作，不保证下一次模型 prompt 已经形成。D1 的分波启动控制作用在这里；它可以改变工具和后续请求的产生时间，但 E1 不删必做分支。','前接：已揭示工作图','后续：推进选中的分支'],
      step:['推进已启动分支 / Agent step','执行所选逻辑工作的一步：已有足够输入时形成模型调用，需要外部信息时进入工具阶段。工具返回后恢复同一分支；一个 Agent 可以经历多次模型与工具循环，因此实例数不等于引擎活跃请求数。','前接：合法逻辑工作 / 工具返回','后续：已绑定模型调用，或工具执行'],
      ready:['已绑定模型调用 / Ready invocation','准确 prompt、模型和上下文版本已经绑定，依赖满足，才属于可以提交引擎的请求。D2 选择放行或暂缓；这里的等待也计入用户任务耗时，不能把后端排队移到这里后就声称更快。','前接：分支形成准确输入','后续：引擎准入与队列'],
      engineQueue:['引擎准入 / Engine admission','收到放行的模型请求后，引擎依据提交时的实际容量重新核验并排队。Harness 的状态快照可能过时，不代表硬资源承诺；ALL join 也不要求所有分支同时准入。','前接：已绑定调用的派发','后续：prefill / decode'],
      engineRun:['实际推理 / Prefill and decode','执行被后端准入的调用，管理 batch、KV 分配与抢占等资源行为。实际缓存复用、额外 prefill 和执行干扰决定本次请求的边际代价；结果返回 Harness，运行状态供拟接入的反馈通道采集。','前接：引擎准入与队列','后续：结果更新 / 实际状态反馈'],
      observations:['引擎状态反馈 / Proposed telemetry link','拟接入分模型队列、实际 KV 驻留与执行成本，并注明采样时间、估计值和缺失项，分别提供给 D1 与 D2。蓝色箭头表示拟接入的观测方向，不能据此认定 DSH 原生已经有引擎反馈控制。','前接：引擎实际运行与监测','后续：D1 分波启动 / D2 请求提交'],
      release:['D1 · 分波启动 / E1 proposed','结合合法前沿、工具中工作与引擎状态，决定哪些已授权分支现在启动、哪些等事件或有界超时。它作用在请求产生之前，可能改变后续回流；先固定必做工作检验其价值，并与背压和同信息后端回调对照。','前接：前沿 / 工具状态 / 引擎反馈','后续：选择合法工作的启动时机'],
      dispatch:['D2 · 请求提交 / E1 proposed','对输入已经绑定的调用决定何时提交，不假装掌握未生成的 prompt，也不代替引擎分配 GPU。单做请求重排可能被同信息后端策略复现，因此必须比较相同信息与动作权限的基线。','前接：READY 调用 / 引擎反馈','后续：实际提交或有界暂缓'],
      optional:['D3 · 可选探索 / E2 follow-up','这是主图之外的后续实验：只有应用明确允许，才根据有效部分结果与实际服务成本增加候选、继续迭代或停止可选展开。它改变总工作量，需独立报告质量—耗时—成本，并与 Murakkab、INFRAMIND 的相关机制比较。','前接：应用可选性契约 / 有效结果 / 引擎成本','后续：新的可选分支，或合法停止'],
      tools:['在途工具 / Tool stage','搜索、代码执行或测试期间，对应 Agent 可能没有活跃模型请求；这些工作仍可能在之后形成模型负载。工具返回后恢复对应分支，再绑定下一次模型输入。在线只知道工具类型、已等待时长和历史分布，不知道准确返回时刻。','前接：已启动分支的工具调用','后续：返回对应分支；状态供 D1 观察'],
      update:['结果与依赖更新 / Progress update','将模型输出交回工作流，更新已知依赖、已完成分支与汇合进度。一次短调用可能结束工作，也可能释放大量后继，这正是任务推进与未来需求需要联合观测的地方。图中是抽象流转，不规定应用如何解析结果。','前接：引擎返回的模型结果','后续：更新工作图，或满足完成条件后输出'],
      finish:['有效最终结果 / Task completion','应用定义的必做工作和接受条件满足后，返回用户结果。评价从用户任务提交开始，包含前端、引擎与工具等待；E2 的最终质量另行离线评分，不能只用单调用耗时或队列长度替代。','前接：工作流完成条件满足','后续：用户结果 / 独立质量评测'],
      parent:['父 Agent / Parent','提出具体子任务，决定新建或向已有直接子级继续发消息；当前任务需要显式传入。','前接：用户请求 / workflow','后续：新建或续接'],
      start:['新建上下文 / Spawn or fork','DSH 原生实现背景：spawn 不带父 transcript；fork 带父级已完成轮次快照，排除当前未完成轮次。这些上下文机制不等同于本轮引擎感知派发策略。','前接：父级任务','后续：startActivation 准入'],
      manager:['准入与占槽 / Manager','检查身份、能力和 activation 池。顶层 root 不占槽；后代共享默认 8 槽；满额拒绝，没有原生队列。','前接：新建或冷恢复','后续：本地 / 外部执行'],
      local:['本地 Session / Local','spawn / fork 创建持久子 Session，允许后续消息和冷恢复。一个 Session 最多一个在线 activation。','前接：Manager','后续：多轮模型与工具'],
      external:['外部一次执行 / External','ACP、Codex、Claude Code、DSH SDK 在此接口下暴露一次执行，统一管理结果与清理；此 DSH 后端不接受 follow-up。','前接：Manager','后续：外部执行'],
      child:['执行实例 / Activation','本地 activation 交替运行模型、工具和消息；一次 activation 可以有多次模型调用，不能把实例数当 GPU 调用数。','前接：本地或外部执行','后续：可选等待，或清理'],
      wait:['等待状态 / Waiting','有后代或未消费 inbox 时仍可能驻留占槽；不是所有 inactive 对象都已完成，也不是所有等待实例都在调用模型。','前接：执行产生等待','后续：有新进展再执行，或进入结算'],
      result:['Result promise 结算','清理、归还槽位和通知之后，result promise 才结算；output / structured / diagnostic / stopReason 不等同于基准任务质量。','前接：清理与通知','后续：程序消费结果或后续任务'],
      delivery:['结果交付 / Parent or caller','parent 通知可唤醒 idle 父级，busy 父级收到 Steer；caller 不发模型可见的父级完成通知，是整组等待的强基线。','前接：清理与槽位归还','后续：result 结算'],
      dispose:['清理与归还 / Cleanup','自然完成或显式 dispose / drain 会等待清理后归还槽。interrupt 仅请求停止本地当前轮次，后代继续；不能把中断确认当完整回收。','前接：完成或显式释放','后续：通知及 result 结算'],
      followup:['后续消息 / SendMessage','已有直接子级驻留时复用槽并在步骤边界接收；未驻留但可继续时冷恢复并重新占槽。外部一次执行不支持这条路径。','前接：父级后续任务','后续：驻留执行，或冷恢复准入'],
      catalog:['持久目录 / Catalog','目录保留父子成员关系，不携带完整执行状态。list_agents 的 running / inactive 仅描述轮次活动情况，不能据此判定任务成功。','前接：创建时记录成员关系','后续：发现已有子级以供继续']
    }
  };
  function defs(){return '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#779286"/></marker><marker id="arrow-control" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#c4652d"/></marker><marker id="arrow-runtime" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#6a568c"/></marker><marker id="arrow-feedback" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#2d6484"/></marker></defs>'}
  function node(id,x,y,w,h,title,sub,kind){return '<g class="clickable" tabindex="0" role="button" aria-label="'+esc(title)+'" data-node="'+id+'"><rect class="node '+(kind||'')+'" x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="11"/><text class="title" x="'+(x+w/2)+'" y="'+(y+31)+'" text-anchor="middle">'+esc(title)+'</text><text class="sub" x="'+(x+w/2)+'" y="'+(y+57)+'" text-anchor="middle">'+esc(sub)+'</text></g>'}
  function group(x,y,w,h,title,sub){return '<rect class="node group" x="'+x+'" y="'+y+'" width="'+w+'" height="'+h+'" rx="14"/><text class="group-title" x="'+(x+18)+'" y="'+(y+26)+'">'+esc(title)+'</text><text class="sub" x="'+(x+18)+'" y="'+(y+48)+'">'+esc(sub)+'</text>'}
  function edge(d,label,kind,lx,ly){return '<path class="edge '+(kind||'')+'" d="'+d+'"/>'+(label?'<text class="edge-label" x="'+lx+'" y="'+ly+'" text-anchor="middle">'+esc(label)+'</text>':'')}
  function graphResearch(){
    var s='<svg viewBox="0 0 1800 700" role="img" aria-labelledby="research-title"><title id="research-title">Open Deep Research 研究工作流</title>'+defs();
    s+=group(745,105,390,475,'并行研究批次 / RESEARCH BATCH','每个 Researcher 执行同类工具循环');
    s+=node('input',25,292,200,88,'研究问题','DeepResearchBench','eval')+node('brief',270,292,200,88,'研究简报','澄清 · 结构化目标')+node('supervisor',510,282,215,108,'主管 Agent','Supervisor · 规划 / 分派')+node('r1',795,155,285,88,'研究员 1','Researcher · 搜索 / 浏览 / MCP')+node('r2',795,292,285,88,'研究员 2','Researcher · 搜索 / 反思循环')+node('rn',795,429,285,88,'研究员 N','Researcher · 可扩展并行单元')+node('compress',1155,292,225,88,'单元内证据压缩','每个 unit 各自压缩返回')+node('gate',1400,282,175,108,'覆盖 / 冲突判断','Topic1 建议控制点','control')+node('final',1605,292,175,88,'最终报告','Final report','eval')+node('backend',1325,55,275,82,'后端资源状态','队列 · KV · CPU · 截止时间','control');
    s+=edge('M225 336 L270 336')+edge('M470 336 L510 336')+edge('M725 336 C755 336 760 199 795 199','并行分派','',762,265)+edge('M725 336 L795 336')+edge('M725 336 C755 336 760 473 795 473')+edge('M1080 199 C1125 199 1120 336 1155 336')+edge('M1080 336 L1155 336')+edge('M1080 473 C1125 473 1120 336 1155 336')+edge('M1365 336 L1400 336')+edge('M1575 336 L1605 336')+edge('M1462 137 L1495 282','资源状态','control',1490,215)+edge('M1400 380 C1290 655 620 660 620 390','证据不足：追加研究','loop',1000,642);
    return '<div class="dag-scroll">'+s+'</svg></div>'+meta(data.research)+designStrip(data.research)+caption('点击节点查看模块职责、前后关系与调用细节','橙色虚线表示可调控制')
  }
  function graphCoding(){
    var s='<svg viewBox="0 0 1900 720" role="img" aria-labelledby="coding-title"><title id="coding-title">Coding harness 代码生成与修复工作流</title>'+defs();
    s+=group(475,92,385,480,'候选生成 / CANDIDATE FAN-OUT','并行 Writer · 数量由 harness 控制')+group(880,175,690,220,'测试与审查 / TEST & REVIEW','公开测试反馈驱动接受或修复');
    s+=node('problem',20,300,190,88,'代码题','LiveCodeBench 输入','eval')+node('planner',245,300,195,88,'规划 Agent','Planner · 题意 / 约束')+node('wa',520,155,285,78,'Writer A','候选代码 A')+node('wb',520,295,285,78,'Writer B','候选代码 B')+node('wn',520,435,285,78,'Writer N','候选代码 N · 可扩展','control')+node('tests',900,295,205,88,'测试器','Tester · 编译 / 样例 / 定向')+node('sandbox',1145,295,205,88,'执行沙箱','Python · 执行 / 日志')+node('reviewer',1390,295,175,88,'审查与排序','Reviewer · 可选阶段','control')+node('selector',1640,175,190,80,'候选选择','Selector · 接受通过项')+node('answer',1640,300,190,80,'在线答案','Answer · harness 输出')+node('hidden',1640,485,190,84,'隐藏评测','pass@1 / pass@5','eval')+node('repair',1390,505,175,84,'修复 Agent','Repair · 失败修复','control');
    s+=edge('M210 344 L245 344')+edge('M440 344 C475 344 480 194 520 194')+edge('M440 344 L520 334')+edge('M440 344 C475 344 480 474 520 474')+edge('M805 194 C850 194 855 339 900 339')+edge('M805 334 L900 339')+edge('M805 474 C850 474 855 339 900 339')+edge('M1105 339 L1145 339')+edge('M1350 339 L1390 339')+edge('M1565 319 C1600 319 1600 215 1640 215','通过','',1600,270)+edge('M1735 255 L1735 300')+edge('M1735 380 L1735 485','离线评测','',1785,440)+edge('M1478 383 L1478 505','失败：修复','control',1525,455)+edge('M1390 547 C1260 650 990 645 995 383','修复后重测','loop',1185,641);
    return '<div class="dag-scroll">'+s+'</svg></div>'+meta(data.coding)+designStrip(data.coding)+caption('点击 Planner、Writer、Tester、Reviewer 或 Repair 查看职责','隐藏测试只用于离线评测')
  }
  function graphDsh(){
    var s='<svg class="harness-flow" viewBox="0 0 1800 850" role="img" aria-labelledby="harness-engine-title"><title id="harness-engine-title">Topic1 待验证接入：Harness DAG 展开、请求派发与引擎状态反馈</title>'+defs();
    s+='<text class="lane-title" x="35" y="65">HARNESS · 工作流推进（抽象结构）</text><text class="lane-title engine-label" x="1270" y="65">ENGINE · 执行与容量仲裁</text><text class="lane-note" x="35" y="111">逻辑工作获准启动，不代表下一次模型输入已经形成</text><text class="lane-note" x="1270" y="111">反馈通道拟接入 · 非 DSH 原生能力声明</text>';
    s+=node('dag',35,180,240,100,'逐步显露的 DAG','已知依赖 / 汇合 / 分支','runtime')+node('pending',335,180,245,100,'合法逻辑工作','已授权且满足启动条件','runtime')+node('step',640,180,245,100,'推进已启动分支','形成模型输入或进入工具','runtime')+node('ready',945,180,245,100,'已绑定模型调用','准确输入 / 模型 / 版本')+node('engineQueue',1270,180,205,100,'引擎准入与队列','重新核验实际容量','eval')+node('engineRun',1535,180,205,100,'实际推理','prefill / decode / KV','eval');
    s+=node('update',35,450,240,100,'结果与依赖更新','推进任务 / 揭示后继','runtime')+node('release',335,450,245,100,'D1 分波启动 · 建议','必做工作只调启动时机','control')+node('tools',640,450,245,100,'在途工具','搜索 / 执行 / 测试等待','runtime')+node('dispatch',945,450,245,100,'D2 请求提交 · 建议','放行或暂缓 READY 调用','control')+node('observations',1270,450,470,100,'引擎状态反馈 · 拟接入','分模型队列 / 实际 KV / 执行成本 / 采样时间','eval');
    s+=node('finish',35,650,240,90,'有效最终结果','按应用完成条件输出','eval')+node('optional',335,650,245,90,'D3 可选探索 · 后续','E2：独立验证质量与成本','control');
    s+='<text class="scope-label" x="650" y="684">E1 主图：固定必做工作，比较展开与派发</text><text class="scope-note" x="650" y="718">E2 另行实验：仅应用声明的可选工作允许改变总量</text>';
    s+=edge('M275 230 L335 230')+edge('M580 230 L640 230')+edge('M885 230 L945 230')+edge('M1190 230 L1270 230')+edge('M1475 230 L1535 230');
    s+=edge('M730 280 L730 450','工具调用','',677,369)+edge('M800 450 L800 280','返回后继续','',855,369)+edge('M155 450 L155 280','更新依赖','',220,369)+edge('M155 550 L155 650','满足完成条件','',220,613);
    s+=edge('M1740 230 L1775 230 L1775 805 L305 805 L305 500 L275 500','模型结果返回 Harness，更新已知工作图','',1050,834);
    s+=edge('M1637 280 L1637 450','运行状态','feedback',1694,369)+edge('M1270 500 L1190 500','','feedback')+edge('M1395 550 L1395 610 L457 610 L457 550','拟接入引擎状态，供下一波展开判断','feedback',1010,637)+edge('M762 550 L762 580 L605 580 L605 520 L580 520','工具中工作','runtime',680,573);
    s+=edge('M457 450 L457 280','分波放行','control',520,369)+edge('M1067 450 L1067 280','选择提交时机','control',1134,369);
    var notice='<div class="harness-notice"><strong>当前研究图 · 待验证接入</strong><span>实线表示抽象任务与调用流；蓝色箭头表示拟接入状态反馈；橙色虚线表示 Topic1 控制。D3 是主图之外的后续实验。<a href="topic1-harness-engine.html">问题定义与实验 →</a></span></div>';
    var native='<details class="runtime-background"><summary>实现背景：展开查看 DSH 原生子 Agent 生命周期</summary><p>以下依据固定 commit f3803c9，仅说明 Session、activation、消息与结果；不是当前研究主线。<a href="topic1-harness-lifecycle.html">查看源码核查 →</a></p>'+graphDshLifecycle()+'</details>';
    return notice+'<div class="dag-scroll">'+s+'</svg></div>'+meta(data.dsh)+designStrip(data.dsh)+caption('点击任一模块或 D1 / D2 / D3，展开角色与前后关系','尚无真实引擎实验；同信息后端策略是强对照')+native;
  }
  function graphDshLifecycle(){
    var s='<svg viewBox="0 0 1800 700" role="img" aria-labelledby="dsh-native-title"><title id="dsh-native-title">实现背景：DeepSeek Harness 原生子 Agent 生命周期</title>'+defs();
    s+=node('parent',25,300,190,88,'父 Agent','Parent · 具体子任务','runtime')+node('start',255,300,210,88,'新建上下文','spawn / fork · 原生机制','runtime')+node('manager',510,300,235,88,'准入与占槽','startActivation · 满额拒绝','runtime')+node('local',810,150,210,80,'本地 Session','可多轮 / 冷恢复','runtime')+node('external',810,420,210,80,'外部一次执行','此接口不接受追问','runtime')+node('child',1090,300,200,88,'执行实例','模型 / 工具 / 消息','runtime')+node('dispose',1340,300,190,88,'清理与归还','自然结束 / dispose','runtime')+node('delivery',1580,300,200,88,'结果交付','parent 通知 / caller','runtime')+node('result',1580,520,200,88,'result 结算','output / stopReason','runtime')+node('followup',270,50,300,90,'给已有本地子级发消息','驻留接收 / 未驻留冷恢复','runtime')+node('wait',1060,525,250,88,'等待后代或输入','可选等待 · 仍可能占槽','runtime')+node('catalog',510,525,235,88,'持久目录','成员关系，不是完成状态','runtime');
    s+=edge('M215 344 L255 344','','runtime')+edge('M465 344 L510 344','','runtime')+edge('M745 344 C780 344 775 190 810 190','本地','runtime',779,255)+edge('M745 344 C780 344 775 460 810 460','外部','runtime',779,417)+edge('M1020 190 C1055 190 1050 344 1090 344','','runtime')+edge('M1020 460 C1055 460 1050 344 1090 344','','runtime')+edge('M1290 344 L1340 344','','runtime')+edge('M1530 344 L1580 344','','runtime')+edge('M1680 388 L1680 520','清理 / 通知之后','runtime',1680,458)+edge('M1180 388 L1180 525','需要等待','runtime',1246,466)+edge('M1060 568 L1035 568 L1035 385 L1090 370','有新进展','runtime',990,526)+edge('M120 300 L120 95 L270 95','','runtime')+edge('M570 95 L1188 95 L1188 300','已驻留：复用槽','runtime',855,76)+edge('M420 140 L420 230 L625 230 L625 300','未驻留：冷恢复需准入','runtime',641,211)+edge('M625 388 L625 525','记录成员','runtime',687,470);
    return '<div class="dag-scroll">'+s+'</svg></div>'+meta({meta:[['原生对象','任务 / Session / activation / 模型请求'],['原生容量','每树默认 8；满额拒绝不排队'],['工具委派深度','默认 1；与 activation 容量分别控制'],['证据版本','DSH f3803c9 · 2026-10-28']]})+caption('原生流程：先清理并归还槽位，再通知及结算 result','源码背景，不承担本轮研究动机')
  }
  function meta(d){return '<div class="graph-meta">'+d.meta.map(function(x){return '<div><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div>'}
  function designStrip(d){return '<div class="design-strip">'+d.designs.map(function(x,i){return '<div class="design-item"><span>设计点 0'+(i+1)+'</span><b>'+esc(x[0])+'</b><p>'+esc(x[1])+'</p><code>'+esc(x[2])+'</code></div>'}).join('')+'</div>'}
  function caption(a,b){return '<div class="graph-caption"><span class="hint">'+esc(a)+'</span><strong>'+esc(b)+'</strong></div>'}
  function moduleCards(name,selected){
    function cards(ids){return '<div class="module-list">'+(selected&&ids.indexOf(selected)!==-1?[selected].concat(ids.filter(function(id){return id!==selected})):ids).map(function(id){
      var info=nodeInfo[name][id],open=id===selected?' open':'';
      return '<details class="module-card" data-module="'+esc(id)+'"'+open+'><summary><span>'+esc(info[0])+'</span><small>'+esc(info[2].replace('前接：',''))+'　→　'+esc(info[3].replace('后续：',''))+'</small></summary><p>'+esc(info[1])+'</p><div class="module-links"><span><b>前序模块</b>'+esc(info[2].replace('前接：',''))+'</span><span><b>后续模块</b>'+esc(info[3].replace('后续：',''))+'</span></div></details>'
    }).join('')+'</div>'}
    var ids=Object.keys(nodeInfo[name]);
    if(name!=='dsh')return cards(ids);
    var nativeIds=['parent','start','manager','local','external','child','wait','result','delivery','dispose','followup','catalog'];
    var selectedNative=nativeIds.indexOf(selected)!==-1;
    var background='<details class="module-background"'+(selectedNative?' open':'')+'><summary>DSH 原生模块 · 实现背景</summary>'+cards(nativeIds)+'</details>';
    var current=cards(ids.filter(function(id){return nativeIds.indexOf(id)===-1}));
    return selectedNative?background+current:current+background;
  }
  var graphs={research:graphResearch,coding:graphCoding,dsh:graphDsh};
  function traceLink(name){
    var ids={research:'odr',gptr:'gptr'};
    if(ids[name])return '<p class="provenance"><strong>已有 Qwen27B 原生运行：</strong><a href="topic1-dag-observation.html?framework='+ids[name]+'#frameworks">查看实际分支、时间戳、完整 Prompt 和原始证据 →</a>。本结构图仍为源码概览；下方公开题目与真实运行分别标注。</p>';
    if(name==='coding')return '<p class="provenance"><a href="topic1-dag-observation.html#coding">查看已有 DSH 代码修复实测 →</a>（人工小型服务，非 LiveCodeBench 题目）。</p>';
    if(name==='crag')return '<p class="provenance"><a href="topic1-dag-observation.html#frameworks">查看官方条件路由核对与三组边界记录 →</a>。未复现训练评估器及完整 CRAG 生成。</p>';
    return '';
  }
  function renderWorkflowOverview(name){
    var d=data[name],info=d&&d.intro,el=document.getElementById('workflow-overview');
    if(!el||!info)return;
    el.innerHTML='<div><span class="overview-kicker">'+(name==='dsh'?'HARNESS × ENGINE · PROPOSED INTEGRATION':'WORKFLOW PURPOSE')+'</span><h3>'+esc(d.title)+'</h3><p>'+esc(info.purpose)+'</p>'+ (name==='dsh'?'<p><a href="topic1-harness-engine.html">查看当前痛点、已有覆盖与实验方案 →</a></p>':'')+'</div><div><h3>一次任务流程</h3><p class="overview-flow">'+esc(info.flow)+'</p></div><div><h3>Topic1 可能有的 Design 空间</h3><span class="overview-hypothesis">待验证设想 · 不等同于论文已有结论</span><p>'+esc(info.designSpace)+'</p><details class="overview-paper-boundary"><summary>与 INFRAMIND / Murakkab 的区别</summary><p><strong>INFRAMIND：</strong>任务开始时选择拓扑、Agent 数与角色；执行中调整模型路由、推理深度与队列调度。论文已将运行中按负载 / 部分结果修改拓扑列为未来工作。</p><p><strong>Murakkab：</strong>周期级联合优化模型、资源与工作流配置，支持按请求结合任务难度与系统条件选择配置；动态 coding 流程也支持测试 / 审查反馈驱动的继续或早停。</p><p><strong>Topic1 待验证：</strong>'+esc(name==='dsh'?'先固定必做工作，验证工具中工作、已知后继需求与引擎状态能否共同指导分波展开和请求提交。TOPAS / SAGA / Coda / Nalar、简单背压和同信息后端策略均是近邻或强基线；前端位置、动态并发与可选探索本身不作为独有创新。':'在具体工作流的执行边界，将实时后端状态与中间结果联动，重分配尚未启动的后续工作量。动态配置、增减调用或早停本身不作为独有创新；控制策略、适用边界与相对两篇论文基线的增量收益仍需验证。')+'</p><p>论文依据：<a href="https://arxiv.org/html/2606.11440v1#S6">INFRAMIND §6</a> · <a href="https://www.usenix.org/conference/osdi26/presentation/chaudhry">Murakkab §3 / §4.4</a></p></details></div>';
  }
  var overviewRenderer=renderWorkflowOverview;
  renderWorkflowOverview=function(name){overviewRenderer(name);var first=document.querySelector('#workflow-overview>div');if(first)first.insertAdjacentHTML('beforeend',traceLink(name));};
  Object.keys(window.Topic1WorkflowExtras||{}).forEach(function(name){
    var spec=window.Topic1WorkflowExtras[name];
    data[name]=spec.data;nodeInfo[name]=spec.nodes;
    graphs[name]=function(){return spec.graph({defs:defs,node:node,group:group,edge:edge,meta:meta,designStrip:designStrip,caption:caption},spec.data)};
  });
  var panels=[].slice.call(document.querySelectorAll('[data-panel]'));
  panels.forEach(function(panel){
    var name=panel.dataset.panel;panel.innerHTML=graphs[name]();if(name!=='research')panel.hidden=true;
    panel.querySelectorAll('svg').forEach(function(svg,index){
    var prefix=name+'-'+index;
    svg.querySelectorAll('marker').forEach(function(marker){marker.id=prefix+'-'+marker.id});
    var edges=[].slice.call(svg.querySelectorAll('path.edge'));
    var labels=[].slice.call(svg.querySelectorAll('.edge-label'));
    var nodes=[].slice.call(svg.querySelectorAll('[data-node]'));
    edges.forEach(function(edge){
      var type=edge.classList.contains('feedback')?'arrow-feedback':(edge.classList.contains('runtime')?'arrow-runtime':(edge.classList.contains('control')||edge.classList.contains('loop')?'arrow-control':'arrow'));
      edge.style.markerEnd='url(#'+prefix+'-'+type+')';
      svg.appendChild(edge)
    });
    nodes.forEach(function(node){svg.appendChild(node)});
    labels.forEach(function(label){svg.appendChild(label)});
    });
  });
  var tabs=[].slice.call(document.querySelectorAll('.workflow-tab'));
  var drawer=document.getElementById('detail-drawer'),backdrop=document.getElementById('drawer-backdrop'),titleEl=document.getElementById('drawer-title'),subtitleEl=document.getElementById('drawer-subtitle');
  var panes={calls:document.querySelector('[data-drawer-pane=calls]'),params:document.querySelector('[data-drawer-pane=params]'),raw:document.querySelector('[data-drawer-pane=raw]')};
  function setWorkflow(name){tabs.forEach(function(tab){tab.setAttribute('aria-selected',String(tab.dataset.workflow===name))});panels.forEach(function(panel){var active=panel.dataset.panel===name;panel.classList.toggle('is-active',active);panel.hidden=!active});renderWorkflowOverview(name);document.getElementById('workflow-legend-hint').textContent=name==='dsh'?'实线 = 抽象调用流 · 蓝色箭头 = 拟接入状态反馈 · 橙色虚线 = Topic1 控制':'实线 = 执行路径 · 橙色虚线 = Topic1 控制点 · 点击节点 = 详情抽屉';document.getElementById('workflow-blue-label').textContent=name==='dsh'?'引擎 / 状态':'benchmark / evaluation';document.getElementById('workflow-violet-label').textContent=name==='dsh'?'Harness / DSH 背景':'runtime';closeDrawer()}
  function workflowFromHash(){var name=window.location.hash.slice(1);if(name==='harness-engine'||name==='dsh')return 'dsh';return Object.prototype.hasOwnProperty.call(graphs,name)?name:'research'}
  tabs.forEach(function(tab){tab.addEventListener('click',function(){var name=tab.dataset.workflow;setWorkflow(name);window.history.replaceState(null,'','#'+(name==='dsh'?'harness-engine':name))})});
  window.addEventListener('hashchange',function(){setWorkflow(workflowFromHash())});
  setWorkflow(workflowFromHash());
  function renderDrawer(name,nodeId){
    var d=data[name],info=nodeInfo[name][nodeId];
    titleEl.textContent=d.title;subtitleEl.textContent=d.sub;
    var intro='<section class="drawer-overview"><h3>工作流总览</h3><p>'+esc(d.overview)+'</p>'+traceLink(name)+'</section>';
    panes.calls.innerHTML=intro+'<h3>模块角色卡片 / Agent & module roles</h3><p class="module-help">展开任意模块查看它在前后 workflow 中承担的角色。当前点击的节点已自动展开。</p>'+moduleCards(name,nodeId)+'<h3>'+(name==='dsh'?'抽象推进序列 / Proposed integration':'完整调用序列 / Calls')+'</h3><ol class="call-list">'+d.calls.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ol><div class="drawer-box drawer-actions"><h4>Topic1 可设计动作</h4><ul class="param-list">'+d.actions.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul></div><div class="provenance">'+esc(d.note)+'</div>';
    panes.params.innerHTML='<h3>参数与 Prompt</h3><div class="drawer-grid"><div class="drawer-box"><h4>'+(name==='dsh'?'拟接入参数与实验约束':'公开参数 / 配置')+'</h4><ul class="param-list">'+d.params.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul></div><div class="drawer-box"><h4>Prompt 原文或明确标注的占位</h4><pre class="prompt-block">'+esc(d.prompt.replace(/\\n/g,'\n'))+'</pre></div></div><div class="provenance">官方 prompt、harness placeholder 与 Topic1 proposed prompt 分开标注。</div>';
    panes.raw.innerHTML='<h3>'+(name==='dsh'?'拟埋点 Schema · 非真实运行数据':'Raw data / trace schema')+'</h3><pre class="raw-block">'+json(d.raw)+'</pre><div class="provenance">'+(name==='dsh'?'以下是待实现的埋点与控制契约，不是 DSH 原生完整 API，也不是已采集的 raw trace。':'字段来自公开 query、README、源码或 API schema。标注未测量的 trace 不代表一次真实运行记录。')+'</div>';
    panes.raw.insertAdjacentHTML('afterbegin',traceLink(name));
    panes.params.insertAdjacentHTML('afterbegin','<p class="provenance">本结构图中的 Prompt 为摘要或占位；逐次实际 messages、工具定义和参数请打开实测入口。</p>'+traceLink(name));
    document.querySelectorAll('.drawer-tab').forEach(function(tab){tab.setAttribute('aria-selected',String(tab.dataset.drawerTab==='calls'))});Object.keys(panes).forEach(function(key){panes[key].hidden=key!=='calls'});drawer.classList.add('is-open');backdrop.classList.add('is-open');drawer.setAttribute('aria-hidden','false');document.querySelector('.drawer-body').scrollTop=0
  }
  function closeDrawer(){drawer.classList.remove('is-open');backdrop.classList.remove('is-open');drawer.setAttribute('aria-hidden','true')}
  panels.forEach(function(panel){panel.addEventListener('click',function(event){var target=event.target.closest('[data-node]');if(target)renderDrawer(panel.dataset.panel,target.dataset.node)});panel.addEventListener('keydown',function(event){var target=event.target.closest('[data-node]');if(target&&(event.key==='Enter'||event.key===' ')){event.preventDefault();renderDrawer(panel.dataset.panel,target.dataset.node)}})});
  document.addEventListener('toggle',function(event){var card=event.target;if(card.matches&&card.matches('.module-card[open]')){var list=card.closest('.module-list');if(list)list.querySelectorAll('.module-card[open]').forEach(function(other){if(other!==card)other.open=false})}},true);
  document.getElementById('drawer-close').addEventListener('click',closeDrawer);backdrop.addEventListener('click',closeDrawer);document.addEventListener('keydown',function(event){if(event.key==='Escape')closeDrawer()});
  document.querySelectorAll('.drawer-tab').forEach(function(tab){tab.addEventListener('click',function(){document.querySelectorAll('.drawer-tab').forEach(function(x){x.setAttribute('aria-selected',String(x===tab))});Object.keys(panes).forEach(function(key){panes[key].hidden=key!==tab.dataset.drawerTab})})});
})();
