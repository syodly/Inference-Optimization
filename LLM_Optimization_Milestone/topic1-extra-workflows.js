(function(){
  'use strict';
  function info(title,description,before,after){return [title,description,'前接：'+before,'后续：'+after]}
  function finish(h,d,svg,hint,boundary){return '<div class="dag-scroll">'+svg+'</svg></div>'+h.meta(d)+h.designStrip(d)+h.caption(hint,boundary)}
  var gptr={
    data:{
      title:'GPT Researcher · Recursive Deep Research',
      sub:'主题 → 搜索查询 → 子研究 → 发现与后续问题 → 递归或收束 → 报告',
      overview:'这里关注 GPT Researcher 的 Deep Research，而不是把它画成另一个 ODR。已保存的 deep_research.py 暴露 breadth、depth 与 concurrency_limit；子研究产生 learnings、来源和后续问题，并在剩余深度允许时继续递归。图中的两个子研究只表示同类分支，递归回边表示进入下一层，不表示把整个流程从头重跑。函数模块不等于独立 Agent。',
      intro:{purpose:'面向需要多轮检索的开放问题：系统先生成一组搜索查询，研究结果提炼出发现与后续问题，再按剩余深度递归展开，最终汇总跨层证据和来源。',flow:'主题 → 本层查询 → 并发子研究 → 新发现 / 后续问题 → 递归下一层或返回报告',designSpace:'可研究：一层结果返回后，结合新增证据、后续问题价值与后端压力，为尚未展开的子树重分配广度、剩余深度与并发额度，或停止低收益分支。三者分别影响总工作量、路径长度与同时占用，不能只用一个 Agent 数替代。'},
      meta:[['结构类型','递归研究 / 逐层展开'],['对比 ODR','批次宽度之外，还有递归层级'],['证据','固定 commit 的 deep_research.py'],['执行状态','结构核对；未采集真实 trace']],
      designs:[['搜索广度','每层生成多少查询；与运行中并发数分开记录','deep_research_breadth'],['递归深度','后续问题最多向下探索多少层','deep_research_depth'],['并发上限','限制同时研究的分支，不等于减少总分支','deep_research_concurrency'],['增量停止 · 建议','下一层启动前结合新增信息、预算与截止时间判断','Topic1 proposed: expand / stop']],
      calls:['主题进入 DeepResearch；读取 breadth、depth 和 concurrency 配置','generate_search_queries：生成本层搜索查询','对查询执行子研究，受并发上限约束','process_research_results：提取 learnings 与 follow-up questions，积累来源','剩余深度允许时，使用后续问题递归调用 deep_research','递归结果向上合并，交给报告生成阶段'],
      actions:['已有机制：广度、深度与并发上限分别控制，不把三者混为 Agent 数','Topic1 建议：只在尚未启动的下一层或查询上做 release / skip','Topic1 建议：新增信息有限时停止继续扩展，但保留已获得来源','必须记录 planned queries、started queries、实际层级和重复来源'],
      params:['源码快照默认 deep_research_breadth = 4','源码快照默认 deep_research_depth = 2','源码快照默认 deep_research_concurrency = 2','默认值是源码配置回退值，不是所有任务的最优设置','breadth 是探索广度；concurrency 是同时运行上限'],
      prompt:'[说明性占位，非官方 prompt 原文]\n根据当前研究主题生成搜索查询。\n从搜索结果提取有来源支持的发现和后续问题。\n只在剩余层级与预算允许时展开后续问题；最后汇总来源。\n\n实际 prompt 以固定源码快照中的消息构造为准。',
      raw:{kind:'illustrative schema; not a measured execution',workflow:'GPT Researcher Deep Research',source_commit:'3582a6841fe7dc801e2a34e34ee408641aea9bce',source_path:'gpt_researcher/skills/deep_research.py',snapshot_defaults:{breadth:4,depth:2,concurrency:2},proposed_trace_fields:['request_id','parent_query_id','depth_remaining','planned_queries','started_queries','learnings','follow_up_questions','source_urls','stop_reason'],local_evidence:['R02_GPTR_deep.txt','S17_GPTResearcher_Deep.txt'],measured:false},
      note:'证据：GPT Researcher 固定 commit 的 deep_research.py，以及 Deep Research 文档。递归与配置属于原有机制；按资源和信息增益停止下一层属于 Topic1 建议。图不声称进行了真实运行或取得性能收益。'
    },
    nodes:{
      topic:info('研究主题 / Topic','用户主题是输入，不是一个 Agent。与现有证据一起进入查询生成。','用户任务','本层查询生成'),
      queries:info('本层查询生成 / Queries','generate_search_queries 生成本层查询。breadth 控制探索范围，不代表这些查询都同时运行。','主题，或上一层后续问题','受并发约束的子研究'),
      qa:info('子研究 A / Query research','针对一个查询收集资料并交给结果处理。A、B 是同类分支示意，不是固定两个角色。','本层查询','发现与后续问题'),
      qb:info('子研究 B / Query research','与其他查询分支探索不同方向；同时运行数量受 concurrency_limit 约束。','本层查询','发现与后续问题'),
      findings:info('提取发现 / Learnings','process_research_results 提取 learnings 与 follow-up questions；积累来源后，为下一层探索提供输入。','各查询的研究结果','递归边界'),
      recurse:info('递归边界 / Recurse or return','剩余深度允许时继续 deep_research；递归结果向上汇总。图中的回边代表下一层，不是同层无限循环。','发现、后续问题与剩余深度','下一层查询，或汇总报告'),
      report:info('汇总报告 / Report','合并递归得到的发现与来源，交给报告生成。此节点不提供某个 benchmark 的固定评分。','向上返回的研究结果','用户报告'),
      budget:info('扩展预算 / Topic1 proposed','建议在下一层启动前观察队列、预算、截止时间与新增信息。该资源控制器不是 GPT Researcher 自带的已验证策略。','后端观测与当前发现','约束尚未启动的递归扩展')
    },
    graph:function(h,d){
      var s='<svg viewBox="0 0 1800 700" role="img" aria-labelledby="gptr-title"><title id="gptr-title">GPT Researcher 递归研究结构</title>'+h.defs();
      s+=h.group(490,105,315,435,'查询分支 / QUERY FAN-OUT','同类研究调用 · 非固定 Agent 数');
      s+=h.node('topic',25,300,185,88,'研究主题','Topic / user input','eval')+h.node('queries',255,300,205,88,'本层查询生成','generate_search_queries')+h.node('qa',525,170,245,88,'子研究 A','搜索 / 阅读 / 来源')+h.node('qb',525,390,245,88,'子研究 B / …','并发上限另行约束')+h.node('findings',850,300,230,88,'发现与后续问题','learnings / follow-up')+h.node('recurse',1155,300,225,88,'递归边界','剩余深度 / 返回')+h.node('report',1500,300,245,88,'汇总报告','合并发现与来源','eval')+h.node('budget',1115,65,305,88,'扩展预算 · 建议','Topic1 / 未启动 work','control');
      s+=h.edge('M210 344 L255 344')+h.edge('M460 344 C490 344 490 214 525 214')+h.edge('M460 344 C490 344 490 434 525 434')+h.edge('M770 214 C815 214 810 344 850 344')+h.edge('M770 434 C815 434 810 344 850 344')+h.edge('M1080 344 L1155 344')+h.edge('M1380 344 L1500 344','收束 / 返回','',1440,323)+h.edge('M1267 388 L1267 615 L357 615 L357 388','后续问题 → 下一层（原有递归）','',820,650)+h.edge('M1267 153 L1267 300','限制下一层释放','control',1355,230);
      return finish(h,d,s,'点击节点查看递归层级、来源和调用边界','实线回边 = 原有递归；橙色虚线 = 建议控制')
    }
  };
  var crag={
    data:{
      title:'CRAG · Corrective Retrieval Routing',
      sub:'问题 → 检索 → 质量评估 → Correct / Incorrect / Ambiguous → 知识构造 → 生成',
      overview:'CRAG 的代表性在于条件数据流，而不是增加 Agent 数。论文 Algorithm 1 根据检索质量触发三种动作：Correct 使用精炼后的内部知识；Incorrect 改写查询并使用外部网页知识；Ambiguous 同时使用内部精炼与外部知识。图中只执行被选中的路径，不表示三路总是并行运行。',
      intro:{purpose:'用于纠正检索增强生成里的“检索到但不相关”问题。系统先评估文档质量，再决定保留并精炼内部资料、改写查询搜索外部资料，或同时结合两种来源后回答。',flow:'问题 → 检索文档 → 相关性评估 → 条件分支 → 知识精炼 / 网页搜索 → 生成',designSpace:'可研究：在原有相关性判断之后，结合证据缺口与后端负载，调整尚未启动的外部查询数量、知识精炼批次与派发时机。相关性分支属于 CRAG 原有机制；这里研究额外工作量的资源感知控制，不把模块数当 Agent 数，也不因拥塞把证据不足改判为正确。'},
      meta:[['结构类型','检索质量驱动的条件路由'],['对比候选并行','不是所有分支都要启动'],['证据','CRAG 论文 Algorithm 1'],['类型边界','检索方法；不要求多 Agent']],
      designs:[['分支判定','依据原有质量判定选择三路动作，不由负载随意覆盖','Correct / Incorrect / Ambiguous'],['知识精炼','分解、筛选并重组有效内部知识','Knowledge_Refine'],['外部检索预算 · 建议','资源状态约束网页检索投入，但不能伪装证据充分','Topic1 proposed: search budget'],['不可用时回退 · 建议','缺少必要证据时标注不确定性，不假装完成纠错','Topic1 proposed: defer / abstain']],
      calls:['输入问题与检索文档','Retrieval Evaluator：逐文档估计相关性并形成动作判定','Correct：Knowledge_Refine，使用内部精炼知识','Incorrect：改写查询，Web_Search，使用外部知识','Ambiguous：内部精炼知识 + 外部搜索知识','Generator：基于问题与所选知识生成回答'],
      actions:['原有机制：保留三路动作与知识来源区别','Topic1 建议：控制尚未启动的检索批次和外部调用预算','资源不足不能把 Incorrect 强行改为 Correct，也不能把缺证据说成已经验证','记录判定、实际检索工作量、内部/外部来源和最终质量'],
      params:['论文定义 upper / lower thresholds；此处不填未经核对的数值','Correct：至少有一个检索文档的相关性高于上阈值','Incorrect：所有检索文档的相关性低于下阈值','Ambiguous：无法归入上述明确情况，组合内部与外部知识','网页检索预算为接入侧建议，不是论文新增的第四种动作'],
      prompt:'[说明性占位，非官方 prompt 原文]\n仅使用条件路由选择出的知识回答问题。\n内部知识精炼与网页知识分别保留来源。\n若必要来源不足，明确说明不确定性。\n\n检索质量评估器是模型组件，不应伪装成统一的聊天 Agent prompt。',
      raw:{kind:'algorithm summary and proposed trace schema; not measured',method:'CRAG',source:'S13_CRAG.txt / Algorithm 1',routing:{Correct:'Knowledge_Refine(question, documents)',Incorrect:'Web_Search(rewritten_question)',Ambiguous:'internal_knowledge + external_knowledge'},proposed_trace_fields:['query_id','retrieval_scores','action','internal_sources','external_sources','search_calls','answer_quality'],threshold_values:'not asserted',measured:false},
      note:'证据：已保存的 CRAG 论文正文，Algorithm 1 与 Action Trigger 小节。三路逻辑属于论文机制；后端资源预算、等待与不确定性回退属于 Topic1 接入建议，尚未验证性能。'
    },
    nodes:{
      question:info('输入问题 / Question','问题与待评估的检索结果共同决定后续路径。','用户任务','初始检索'),
      retrieve:info('初始检索 / Retrieve','从语料得到候选文档。检索到不等于文档相关，必须继续评估。','问题与语料','Retrieval Evaluator'),
      evaluate:info('检索质量评估 / Evaluator','评估问题与各文档的相关性，并形成 Correct、Incorrect 或 Ambiguous 动作判定。它是模型组件，不必是一个 Agent。','问题与候选文档','三路条件动作之一'),
      correct:info('Correct / 内部知识路径','当至少一个文档超过上阈值时，进入内部知识精炼。并不表示把原文档不加筛选地全部塞给生成器。','检索质量判定','Knowledge_Refine'),
      incorrect:info('Incorrect / 外部纠错路径','当所有文档低于下阈值时，不依赖不相关内部文档，改写查询并搜索外部知识。','检索质量判定','改写查询与网页检索'),
      ambiguous:info('Ambiguous / 双路路径','质量判定不明确时，组合内部精炼与外部搜索。此图把双路知识构造合并成一个模块，不声称新增一个官方 Agent。','检索质量判定','内部精炼 + 外部知识'),
      refine:info('内部知识精炼 / Refine','通过分解与重组提取有效知识，减少无关文档内容。','Correct 路径','所选知识'),
      web:info('外部网页检索 / Web search','按改写后的问题检索外部知识，用于 Incorrect，或作为 Ambiguous 的组成部分。','Incorrect 路径的改写查询','所选知识'),
      both:info('双路知识构造 / Both','执行 Knowledge_Refine 与 Web_Search，再合并内部和外部知识；图中是 Algorithm 1 的折叠表示。','Ambiguous 路径','所选知识'),
      knowledge:info('所选知识 / Knowledge','合并的是当前判定对应的知识，不是始终把三条互斥路径的结果全量相加。','当前选中路径','Generator'),
      answer:info('生成回答 / Generator','依据问题与所选知识生成回答。此页面未运行模型或报告准确率提升。','所选知识与输入问题','用户输出 / 离线评测'),
      budget:info('检索预算 / Topic1 proposed','建议限制尚未启动的外部调用预算。若预算不够，应等待或明确缺证据，不能改变原算法的质量判定来伪造成功。','后端与工具资源观测','尚未启动的外部检索')
    },
    graph:function(h,d){
      var s='<svg viewBox="0 0 1800 700" role="img" aria-labelledby="crag-title"><title id="crag-title">CRAG 三路条件检索纠错</title>'+h.defs();
      s+=h.node('question',20,300,180,88,'输入问题','Question','eval')+h.node('retrieve',240,300,205,88,'初始检索','Retrieved documents')+h.node('evaluate',485,300,235,88,'检索质量评估','Retrieval Evaluator')+h.node('correct',795,90,230,88,'Correct','使用内部知识')+h.node('incorrect',795,300,230,88,'Incorrect','转向外部知识')+h.node('ambiguous',795,510,230,88,'Ambiguous','组合两种知识')+h.node('refine',1090,90,245,88,'内部知识精炼','Knowledge_Refine')+h.node('web',1090,300,245,88,'改写与网页检索','Rewrite / Web_Search')+h.node('both',1090,510,245,88,'内部 + 外部','Refine + Web_Search')+h.node('knowledge',1390,300,165,88,'所选知识','Selected path')+h.node('answer',1600,300,180,88,'生成回答','Generator','eval')+h.node('budget',1370,565,355,88,'外部检索预算 · 建议','Topic1 / 不覆盖质量判定','control');
      s+=h.edge('M200 344 L240 344')+h.edge('M445 344 L485 344')+h.edge('M720 344 C755 344 755 134 795 134','质量较高','',752,200)+h.edge('M720 344 L795 344')+h.edge('M720 344 C755 344 755 554 795 554','不确定','',752,490)+h.edge('M1025 134 L1090 134')+h.edge('M1025 344 L1090 344')+h.edge('M1025 554 L1090 554')+h.edge('M1335 134 C1370 134 1350 344 1390 344')+h.edge('M1335 344 L1390 344')+h.edge('M1335 554 C1370 554 1350 344 1390 344')+h.edge('M1555 344 L1600 344')+h.edge('M1370 609 L1212 609 L1212 388','限制尚未启动的搜索','control',1200,650);
      return finish(h,d,s,'点击三个动作查看知识来源；三路不是默认并行','质量路由 = 论文机制；橙色虚线 = 建议控制')
    }
  };
  var tau={
    data:{
      title:'τ²-bench · Stateful Tool Interaction',
      sub:'任务与策略 → Agent / 用户交互 → 工具执行 → 环境与观测 → 下一轮或终止评测',
      overview:'这里展示 τ²-bench 的参考交互边界，不把 benchmark 说成固定 Agent 编排器。已保存的 README 定义了领域 policy、tools、tasks，以及可选的 user tools。Agent 与用户模拟器交互，工具调用产生环境相关结果，观测再影响下一轮。图选择文本轮次交互，不混入语音并发；不同领域和版本的工具及评测设置必须固定。',
      intro:{purpose:'用于评测 Agent 在航班、零售、电信等工具环境里能否按领域规则完成真实任务。Agent 需要与用户模拟器多轮沟通，再调用会改变环境状态的工具，并根据真实返回继续决策。',flow:'领域任务 / Policy → Agent 与用户交互 → 工具调用 → 环境状态变化 → 返回观测 → 下一轮或结束',designSpace:'可研究：在用户 / 工具观测返回后，结合后端压力，对已就绪、已授权且未启动的下一次调用做准入或延后，并评估等待期间的 KV 保留 / 恢复。该结构可调整的空间更受依赖约束，不能随意增加角色、跳过必要步骤或重放有副作用的操作；先验证时延与资源收益。'},
      meta:[['结构类型','有状态工具 / 多轮交互'],['对比独立候选','输入随用户与工具结果改变'],['展示范围','参考文本交互边界，非固定拓扑'],['证据','已保存 τ²-bench README 快照']],
      designs:[['依赖优先','未得到必要用户输入或工具结果时，下一步不能假定就绪','dependency / ready state'],['安全派发 · 建议','只对已授权、未启动且依赖满足的动作做准入','Topic1 proposed: admit / defer'],['副作用边界','不可把写操作当作可任意跳过或取消的候选','policy / side effects'],['终止与评测','按原任务协议结束并评测，不拿评分答案在线调度','original task evaluation']],
      calls:['加载固定领域的任务、policy、tools 与初始环境','Agent 与用户模拟器交换消息，获得必要任务信息','Agent 选择工具，环境执行并返回结果；部分领域允许用户工具','工具结果与对话观测更新后续决策所能看到的信息','继续对话或工具步骤，直到达到原框架终止条件','原任务评测使用规定的运行结果；此页面不虚构评分或成功率'],
      actions:['Topic1 建议：在模型调用或工具动作开始前做 admission，保留依赖与授权','等待用户或工具期间可研究 KV 保留 / 恢复，但不能偷看未来回复','有副作用的运行中动作不能按普通 research 分支随意取消或重放','用户工具只在所选领域提供时存在，不要求所有任务都有双侧工具','记录等待、动作顺序、环境版本与终止原因；环境版本 trace 字段为接入建议'],
      params:['固定 domain、task、Agent、user simulator、工具环境与版本','本图只展示文本轮次模式，不代表语音全双工执行','policy / tools / tasks 是 README 明确的领域边界','user tools 为可选，不是所有领域都必须提供','不硬填默认最大轮数、模型或奖励公式；以选定版本配置为准'],
      prompt:'[说明性占位，非官方 Agent 或用户模拟器 prompt]\nAgent：遵循所选领域 policy，基于已收到的用户消息和工具结果采取动作。\n用户模拟器：按任务和模拟器协议回应；仅在领域支持时使用用户工具。\n\n不得将未发生的用户回复、隐藏评测答案或未来工具结果提前注入在线决策。',
      raw:{kind:'reference interaction boundaries and proposed trace; not measured',benchmark:'tau2-bench',source_snapshot:'S20_tau2bench.txt',mode_scope:'text turn-based only',domain_boundaries:['policy','tools','tasks','optional user tools'],proposed_trace_fields:['task_id','domain','turn','actor','observation','action','environment_version','tool_started','tool_finished','wait_time','stop_reason'],evaluation:'use the selected benchmark version; not defined by this diagram',measured:false},
      note:'证据：本地保存的 sierra-research/tau2-bench README 快照。快照与当前线上版本可能不同，实验需固定版本。本图抽象交互边界，不声称是官方完整调用图；资源准入、KV 与环境版本记账是 Topic1 建议。'
    },
    nodes:{
      task:info('任务与初始状态 / Task','任务、领域策略、工具和初始环境是运行的前提，不是预先已知的完整对话 DAG。','固定领域与任务配置','Agent 的初始输入'),
      agent:info('Agent 决策 / Agent','根据已获得的对话与工具结果选择下一条消息或工具动作。未知用户回复和未来结果不得当作已知输入。','当前观测、policy 与任务','用户交互，或工具调用'),
      user:info('用户模拟器 / User','按任务和模拟器协议与 Agent 交互。本图展示文本轮次，双向连线不表示同时运行。','Agent 消息与模拟器任务','回复 Agent；可选用户工具'),
      usertools:info('可选用户工具 / User tools','README 明确部分领域可给用户模拟器提供工具。连线表示可选边界，不要求每次对话都调用。','用户模拟器','领域环境'),
      tools:info('Agent 工具 / Tools','执行所选领域允许的动作。读写、副作用和幂等性取决于实际工具，不能一概当作可交换的独立分支。','Agent 已授权的工具动作','领域环境'),
      environment:info('领域环境 / Environment','工具与领域状态相互作用；后续请求的有效性取决于此前动作与返回。此节点是交互抽象，不虚构某个统一数据库实现。','Agent 工具或可选用户工具','结果与观测'),
      observation:info('结果与观测 / Observation','将实际收到的结果交回下一轮决策。尚未完成的动作必须等待，不能把未来内容提前绑定。','环境执行与对话进展','Agent 下一轮，或终止评测'),
      evaluation:info('终止与原基准评测 / Evaluation','运行按所选框架版本结束，再执行原任务评测。图不把隐藏评分结果当在线控制信号，也不提供自造奖励公式。','已完成的任务运行','离线结果与报告'),
      policy:info('领域策略 / Policy','README 中每个领域定义 policy。资源调度不能覆盖任务规则与用户授权。','固定领域配置','Agent 与工具约束'),
      admission:info('安全派发 / Topic1 proposed','建议只准入已就绪、已授权、尚未开始的动作；运行中的有副作用操作不能通过 skip 或普通取消语义抹掉。','依赖、权限与后端状态','未启动动作的 admit / defer')
    },
    graph:function(h,d){
      var s='<svg viewBox="0 0 1800 700" role="img" aria-labelledby="tau-title"><title id="tau-title">有状态工具与用户交互边界</title>'+h.defs();
      s+=h.node('task',20,300,190,88,'任务 / 初始状态','Domain / task','eval')+h.node('agent',285,300,220,88,'Agent 决策','当前消息 / 观测')+h.node('user',285,65,220,88,'用户模拟器','User simulator')+h.node('usertools',775,65,275,88,'可选用户工具','仅限支持的领域')+h.node('tools',615,300,235,88,'Agent 工具','Tools / policy-bound')+h.node('environment',935,300,235,88,'领域环境','状态与执行结果')+h.node('observation',1240,300,225,88,'结果与观测','Actual observation')+h.node('evaluation',1530,300,245,88,'终止 / 原基准评测','End / task evaluation','eval')+h.node('policy',285,500,220,88,'领域策略','Policy / constraints')+h.node('admission',615,500,285,88,'安全派发 · 建议','依赖满足 / 授权 / 预算','control');
      s+=h.edge('M210 344 L285 344')+h.edge('M395 300 L395 153','Agent 消息','',445,238)+h.edge('M285 109 L245 109 L245 255 L320 255 L320 300','用户回复','',213,215)+h.edge('M505 109 L775 109','领域支持时','',640,94)+h.edge('M1050 109 L1052 300')+h.edge('M505 344 L615 344')+h.edge('M850 344 L935 344')+h.edge('M1170 344 L1240 344')+h.edge('M1465 344 L1530 344','终止后','',1497,323)+h.edge('M1352 388 L1352 640 L550 640 L550 370 L505 370','观测返回下一轮','',1060,672)+h.edge('M395 500 L395 388')+h.edge('M757 500 L757 388','仅约束未启动动作','control',840,460);
      return finish(h,d,s,'用户工具为可选；图展示交互边界而非固定 Agent 拓扑','橙色虚线 = 安全准入建议；不任意取消副作用')
    }
  };
  window.Topic1WorkflowExtras={gptr:gptr,crag:crag,tau:tau};
})();
