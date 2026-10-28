(function(){
  'use strict';
  var esc=function(v){return String(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})};
  var json=function(v){return esc(JSON.stringify(v,null,2))};
  var data={
    research:{
      title:'ODR Research · DeepResearchBench',
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
      title:'Coding Harness · LiveCodeBench',
      overview:'LiveCodeBench 提供代码题和离线评测协议，不规定 Agent 拓扑。Coding harness 在题目之后组织 Planner、并行 Writer、测试执行、可选 Reviewer、Repair 和 Selector。Topic1 的设计重点是候选宽度、测试时机、审查开关和修复深度。',
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
      title:'DeepSeek Harness · activation lifecycle',
      overview:'DeepSeek Harness 描述 Agent activation 的运行时生命周期，不负责 benchmark 质量评分。Parent 先产生 work item；Topic1 gate 根据后端资源决定何时释放；Manager 检查能力并选择 Provider；Child 返回 result / stopReason；父级随后交付结果或取消剩余任务并记录 trace。',
      intro:{purpose:'这是承载 Agent 调用的运行时生命周期：父级创建 work item，activation API 启动子任务，Manager 负责能力检查与 Provider 路由，完成后把结果或停止原因交回调用者。',flow:'父级任务 → startActivation → Manager / Provider → Child → 结果 / stopReason → 交付或释放',designSpace:'可研究：在 activation 启动边界，结合父级任务反馈与后端容量，对未启动 child 做准入、延后或分批释放，并把结果交付、取消与资源回收纳入状态记录。并发调度只有改变后续创建决策时才影响总调用数；DSH 是承载接口，不是已实现的最优 Agent 数策略。'},
      sub:'父 Agent → 资源控制门 → activation → Provider / Child → 结果回传 / 释放',
      meta:[['任务输入','Parent work items'],['运行时','DeepSeek Harness activation lifecycle'],['控制动作','release · skip · expand · stop'],['trace 字段','output · diagnostic · stopReason']],
      designs:[['释放时机','后端 grant 到达后再启动待执行 work','release timing'],['并行宽度','同时启动多少 ready child activation','active children'],['层级深度','父子 activation 的最大嵌套深度','maxDepth'],['取消与回收','记录 stopReason、dispose 时间和资源成本','cancel / dispose']],
      calls:['Parent workflow：生成 work item 并读取 backend state','Topic1 gate：决定 release / skip / expand / mode / stop','startActivation：Manager 做 capability check 与 reserve','Provider：把请求交给 local child 或 external DSH execution','Child activation：执行 prompt / work item','result：返回 output、structured、diagnostic、stopReason','delivery / dispose：交付给 parent / caller，或取消并释放资源'],
      actions:['work item 与 activation 分离：有 work 不代表已经占用资源','release timing：只在 backend grant、queue / KV / CPU 允许时启动','width：ready work 的 child activation 数量','depth：maxDepth / parent-child 层级限制','cancellation：记录 stopReason 和 dispose 成本，不把取消当免费操作'],
      params:['provider、label、childId、parent','request.prompt、cwd、agentPreset、agentOptions','signal = AbortSignal；delivery = parent / caller','outputSchema、maxDepth、structured result','Topic1 controller prompt 是建议 schema，不是 DSH 内置策略'],
      prompt:'Given backend state and ready work items, choose one action:\\nrelease(k), skip(ids), expand(template), mode(profile), or stop(reason).\\nNever claim hidden benchmark answers.\\nRecord the observed state and the decision reason.\\n\\n这是 Topic1 控制器的建议 prompt；DSH 提供 activation API，不规定该控制策略。',
      raw:{provider:'dsh-sdk',label:'research-unit-03',parent:'parent-session-001',request:{cwd:'/workspace',prompt:'research subtask',maxDepth:2},signal:'AbortSignal',delivery:'caller',result:{stopReason:'completed',output:'<child output>',diagnostic:'<optional>'},lifecycle_trace:'API shape example; not a measured runtime trace'},
      note:'DSH subagent API 提供 activation、parent、provider、result、stopReason、dispose / cancel 等运行时边界；release / expand / stop 是 Topic1 的控制策略设计空间。'
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
      parent:['父 Agent / Parent','创建 work item 并持有上层 policy；生成任务不代表 child activation 已经启动。','前接：用户请求 / 上层 workflow','后续：Topic1 资源控制门'],
      gate:['Topic1 资源控制门 / Gate','读取 queue、KV、CPU、deadline 和 ready work，决定 release、skip、expand 或 stop，再交给 activation API。','前接：Parent work items + backend state','后续：startActivation'],
      backend:['后端状态 / Backend state','提供队列、KV、CPU、deadline 与 grant 等观测，供控制门决策；本图将其作为状态输入，而非 Agent。','前接：推理引擎与资源管理器','后续：Topic1 资源控制门'],
      start:['启动 activation / startActivation','运行时入口，携带 provider、label、request、parent、signal 和 delivery，开始 child 生命周期。','前接：资源控制门的 release 决策','后续：SubagentManager'],
      manager:['子 Agent 管理器 / Manager','进行 capability check 与资源预留，并维护 parent-child catalog，再将请求路由到 Provider。','前接：startActivation 请求','后续：Local 或 External Provider'],
      local:['本地 Provider / Local provider','将 activation 路由到本地 child 执行；结果沿用统一的 result / stopReason 边界。','前接：SubagentManager','后续：Child activation'],
      external:['外部 Provider / External provider','把 activation 交给外部 DSH execution；仍通过统一的结果边界返回。','前接：SubagentManager','后续：Child activation'],
      child:['子 activation / Child','执行具体 prompt 或 work item，直到完成、报错、取消或达到 maxDepth / token 限制。','前接：Local 或 External Provider','后续：result / stopReason'],
      result:['结果与停止原因 / Result','把 output、structured、diagnostic 和 stopReason 返回父 workflow，供后续交付或扩展判断。','前接：Child activation','后续：交付给调用者，或 dispose'],
      delivery:['父级 / 调用者交付 / Delivery','将 child 结果回传给 parent 或 caller，父 workflow 据此继续执行或收束。','前接：result','后续：父 Agent 下一轮决策'],
      dispose:['释放与取消 / Dispose','停止剩余 activation 并释放资源；取消时间和成本应进入 trace。','前接：超时、停止策略或取消信号','后续：运行时资源回收'],
      catalog:['Catalog 与 trace','记录 parent-child 关系和状态变化，为后续资源决策与运行分析提供观测。','前接：Manager / activation lifecycle events','后续：后端状态与实验分析']
    }
  };
  function defs(){return '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#779286"/></marker><marker id="arrow-control" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#c4652d"/></marker><marker id="arrow-runtime" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#6a568c"/></marker></defs>'}
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
    var s='<svg viewBox="0 0 1800 700" role="img" aria-labelledby="dsh-title"><title id="dsh-title">DeepSeek Harness activation lifecycle</title>'+defs();
    s+=group(965,145,280,330,'Provider 路由边界 / PROVIDERS','本地执行或外部 DSH execution');
    s+=node('parent',25,285,190,88,'父 Agent','Parent · 创建子任务','runtime')+node('gate',250,275,205,108,'资源控制门','Topic1 · 建议策略','control')+node('backend',250,65,205,82,'后端资源状态','队列 · KV · CPU · grant','control')+node('start',500,285,205,88,'启动 activation','startActivation','runtime')+node('manager',750,285,205,88,'子 Agent 管理器','Manager · 检查 / 预留','runtime')+node('local',995,195,220,80,'本地 Provider','Local child','runtime')+node('external',995,355,220,80,'外部 Provider','DSH execution','runtime')+node('child',1280,285,205,88,'子 activation','Child · 执行 prompt','runtime')+node('result',1530,285,220,88,'结果与停止原因','result · stopReason','runtime')+node('delivery',1530,440,220,78,'父级 / 调用者','结果交付','runtime')+node('dispose',1280,545,205,78,'取消与释放','dispose · 记录成本','control')+node('catalog',750,545,205,78,'Catalog 与 trace','父子关系 · 状态记录','control');
    s+=edge('M215 329 L250 329','work item','runtime',232,316)+edge('M352 147 L352 275','资源观测','control',400,220)+edge('M455 329 L500 329','release','runtime',477,316)+edge('M705 329 L750 329','请求','runtime',728,316)+edge('M955 329 C975 329 970 235 995 235','本地','runtime',973,280)+edge('M955 329 C975 329 970 395 995 395','外部','runtime',973,370)+edge('M1215 235 C1250 235 1245 329 1280 329','执行结果','runtime',1248,268)+edge('M1215 395 C1250 395 1245 329 1280 329','','runtime')+edge('M1485 329 L1530 329','返回状态','runtime',1508,316)+edge('M1640 373 L1640 440','交付','runtime',1670,414)+edge('M1530 485 C1515 540 1460 575 1485 584','取消 / 回收','control',1510,548)+edge('M852 373 L852 545','生命周期事件','control',915,466)+edge('M1640 518 L1640 660 L120 660 L120 373','交付后进入父级下一轮','loop',810,642);
    return '<div class="dag-scroll">'+s+'</svg></div>'+meta(data.dsh)+designStrip(data.dsh)+caption('点击控制门、activation、Provider 或结果查看生命周期角色','虚线表示资源控制与取消')
  }
  function meta(d){return '<div class="graph-meta">'+d.meta.map(function(x){return '<div><b>'+esc(x[0])+'</b><span>'+esc(x[1])+'</span></div>'}).join('')+'</div>'}
  function designStrip(d){return '<div class="design-strip">'+d.designs.map(function(x,i){return '<div class="design-item"><span>设计点 0'+(i+1)+'</span><b>'+esc(x[0])+'</b><p>'+esc(x[1])+'</p><code>'+esc(x[2])+'</code></div>'}).join('')+'</div>'}
  function caption(a,b){return '<div class="graph-caption"><span class="hint">'+esc(a)+'</span><strong>'+esc(b)+'</strong></div>'}
  function moduleCards(name,selected){
    return '<div class="module-list">'+(selected?[selected].concat(Object.keys(nodeInfo[name]).filter(function(id){return id!==selected})):Object.keys(nodeInfo[name])).map(function(id){
      var info=nodeInfo[name][id],open=id===selected?' open':'';
      return '<details class="module-card" data-module="'+esc(id)+'"'+open+'><summary><span>'+esc(info[0])+'</span><small>'+esc(info[2].replace('前接：',''))+'　→　'+esc(info[3].replace('后续：',''))+'</small></summary><p>'+esc(info[1])+'</p><div class="module-links"><span><b>前序模块</b>'+esc(info[2].replace('前接：',''))+'</span><span><b>后续模块</b>'+esc(info[3].replace('后续：',''))+'</span></div></details>'
    }).join('')+'</div>'
  }
  var graphs={research:graphResearch,coding:graphCoding,dsh:graphDsh};
  function renderWorkflowOverview(name){
    var d=data[name],info=d&&d.intro,el=document.getElementById('workflow-overview');
    if(!el||!info)return;
    el.innerHTML='<div><span class="overview-kicker">WORKFLOW PURPOSE</span><h3>'+esc(d.title)+'</h3><p>'+esc(info.purpose)+'</p></div><div><h3>一次任务流程</h3><p class="overview-flow">'+esc(info.flow)+'</p></div><div><h3>Topic1 可能有的 Design 空间</h3><span class="overview-hypothesis">待验证设想 · 不等同于论文已有结论</span><p>'+esc(info.designSpace)+'</p><details class="overview-paper-boundary"><summary>与 INFRAMIND / Murakkab 的区别</summary><p><strong>INFRAMIND：</strong>任务开始时选择拓扑、Agent 数与角色；执行中调整模型路由、推理深度与队列调度。论文已将运行中按负载 / 部分结果修改拓扑列为未来工作。</p><p><strong>Murakkab：</strong>周期级联合优化模型、资源与工作流配置，支持按请求结合任务难度与系统条件选择配置；动态 coding 流程也支持测试 / 审查反馈驱动的继续或早停。</p><p><strong>Topic1 待验证：</strong>在具体工作流的执行边界，将实时后端状态与中间结果联动，重分配尚未启动的后续工作量。动态配置、增减调用或早停本身不作为独有创新；控制策略、适用边界与相对两篇论文基线的增量收益仍需验证。</p><p>论文依据：<a href="https://arxiv.org/html/2606.11440v1#S6">INFRAMIND §6</a> · <a href="https://www.usenix.org/conference/osdi26/presentation/chaudhry">Murakkab §3 / §4.4</a></p></details></div>';
  }
  Object.keys(window.Topic1WorkflowExtras||{}).forEach(function(name){
    var spec=window.Topic1WorkflowExtras[name];
    data[name]=spec.data;nodeInfo[name]=spec.nodes;
    graphs[name]=function(){return spec.graph({defs:defs,node:node,group:group,edge:edge,meta:meta,designStrip:designStrip,caption:caption},spec.data)};
  });
  var panels=[].slice.call(document.querySelectorAll('[data-panel]'));
  panels.forEach(function(panel){
    var name=panel.dataset.panel;panel.innerHTML=graphs[name]();if(name!=='research')panel.hidden=true;
    var svg=panel.querySelector('svg');
    svg.querySelectorAll('marker').forEach(function(marker){marker.id=name+'-'+marker.id});
    var edges=[].slice.call(svg.querySelectorAll('path.edge'));
    var labels=[].slice.call(svg.querySelectorAll('.edge-label'));
    var nodes=[].slice.call(svg.querySelectorAll('[data-node]'));
    edges.forEach(function(edge){
      var type=edge.classList.contains('runtime')?'arrow-runtime':(edge.classList.contains('control')||edge.classList.contains('loop')?'arrow-control':'arrow');
      edge.style.markerEnd='url(#'+name+'-'+type+')';
      svg.appendChild(edge)
    });
    nodes.forEach(function(node){svg.appendChild(node)});
    labels.forEach(function(label){svg.appendChild(label)});
  });
  var tabs=[].slice.call(document.querySelectorAll('.workflow-tab'));
  var drawer=document.getElementById('detail-drawer'),backdrop=document.getElementById('drawer-backdrop'),titleEl=document.getElementById('drawer-title'),subtitleEl=document.getElementById('drawer-subtitle');
  var panes={calls:document.querySelector('[data-drawer-pane=calls]'),params:document.querySelector('[data-drawer-pane=params]'),raw:document.querySelector('[data-drawer-pane=raw]')};
  function setWorkflow(name){tabs.forEach(function(tab){tab.setAttribute('aria-selected',String(tab.dataset.workflow===name))});panels.forEach(function(panel){var active=panel.dataset.panel===name;panel.classList.toggle('is-active',active);panel.hidden=!active});renderWorkflowOverview(name);closeDrawer()}
  tabs.forEach(function(tab){tab.addEventListener('click',function(){setWorkflow(tab.dataset.workflow)})});
  renderWorkflowOverview('research');
  function renderDrawer(name,nodeId){
    var d=data[name],info=nodeInfo[name][nodeId];
    titleEl.textContent=d.title;subtitleEl.textContent=d.sub;
    var intro='<section class="drawer-overview"><h3>工作流总览</h3><p>'+esc(d.overview)+'</p></section>';
    panes.calls.innerHTML=intro+'<h3>模块角色卡片 / Agent & module roles</h3><p class="module-help">展开任意模块查看它在前后 workflow 中承担的角色。当前点击的节点已自动展开。</p>'+moduleCards(name,nodeId)+'<h3>完整调用序列 / Calls</h3><ol class="call-list">'+d.calls.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ol><div class="drawer-box drawer-actions"><h4>Topic1 可设计动作</h4><ul class="param-list">'+d.actions.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul></div><div class="provenance">'+esc(d.note)+'</div>';
    panes.params.innerHTML='<h3>参数与 Prompt</h3><div class="drawer-grid"><div class="drawer-box"><h4>公开参数 / 配置</h4><ul class="param-list">'+d.params.map(function(x){return '<li>'+esc(x)+'</li>'}).join('')+'</ul></div><div class="drawer-box"><h4>Prompt 原文或明确标注的占位</h4><pre class="prompt-block">'+esc(d.prompt.replace(/\\n/g,'\n'))+'</pre></div></div><div class="provenance">官方 prompt、harness placeholder 与 Topic1 proposed prompt 分开标注。</div>';
    panes.raw.innerHTML='<h3>Raw data / trace schema</h3><pre class="raw-block">'+json(d.raw)+'</pre><div class="provenance">字段来自公开 query、README、源码或 API schema。标注未测量的 trace 不代表一次真实运行记录。</div>';
    document.querySelectorAll('.drawer-tab').forEach(function(tab){tab.setAttribute('aria-selected',String(tab.dataset.drawerTab==='calls'))});Object.keys(panes).forEach(function(key){panes[key].hidden=key!=='calls'});drawer.classList.add('is-open');backdrop.classList.add('is-open');drawer.setAttribute('aria-hidden','false');document.querySelector('.drawer-body').scrollTop=0
  }
  function closeDrawer(){drawer.classList.remove('is-open');backdrop.classList.remove('is-open');drawer.setAttribute('aria-hidden','true')}
  panels.forEach(function(panel){panel.addEventListener('click',function(event){var target=event.target.closest('[data-node]');if(target)renderDrawer(panel.dataset.panel,target.dataset.node)});panel.addEventListener('keydown',function(event){var target=event.target.closest('[data-node]');if(target&&(event.key==='Enter'||event.key===' ')){event.preventDefault();renderDrawer(panel.dataset.panel,target.dataset.node)}})});
  document.addEventListener('toggle',function(event){var card=event.target;if(card.matches&&card.matches('.module-card[open]')){var list=card.closest('.module-list');if(list)list.querySelectorAll('.module-card[open]').forEach(function(other){if(other!==card)other.open=false})}},true);
  document.getElementById('drawer-close').addEventListener('click',closeDrawer);backdrop.addEventListener('click',closeDrawer);document.addEventListener('keydown',function(event){if(event.key==='Escape')closeDrawer()});
  document.querySelectorAll('.drawer-tab').forEach(function(tab){tab.addEventListener('click',function(){document.querySelectorAll('.drawer-tab').forEach(function(x){x.setAttribute('aria-selected',String(x===tab))});Object.keys(panes).forEach(function(key){panes[key].hidden=key!==tab.dataset.drawerTab})})});
})();
