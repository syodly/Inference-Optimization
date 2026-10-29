/* Measured artifacts only. No simulated performance or invented prompts. */
const base='../experiments/harness-engine/results/';
const dshBase='../experiments/dsh-engine/results/e1-small-20261029/web/';
const $=id=>document.getElementById(id), esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(x,n=2)=>x==null?'—':Number(x).toFixed(n);
let rounds=[],current=null,loadVersion=0,nodeData=new Map(),edges=[],lastFocus=null,closeTimer,currentSamples=null;
const datasetKind=r=>r.official_dsh?'dsh':r.summary.quality_by_tenant?'shared':r.summary.quality_by_dataset?'mixed':(/option|LongBench/i.test(r.summary.quality_protocol||'')||r.run_id.includes('long')?'long':'short');
const isLong=r=>datasetKind(r)==='long';
const runLabel=r=>r.official_dsh?`官方 DSH · ${{native:'直接派发',fixed:'固定在途 12',pressure:'压力反馈 12'}[r.summary.policy]}`:r.run_id;
function qualityText(r){
 const s=r.summary,g=s.quality_by_dataset;
 if(s.quality_by_tenant){const t=s.quality_by_tenant.target.quality_by_dataset,b=s.quality_by_tenant.background;return `目标长 ${fmt(t['longbench-v2']?.em*100,1)}% · 短 ${fmt(t.hotpot?.f1*100,1)}%${b?` · 背景 ${fmt(b.quality_by_dataset['longbench-v2']?.em*100,1)}%`:' · 无背景'}`;}
 return g?`长 ${fmt(g['longbench-v2']?.em*100,1)}% · 短 ${fmt(g.hotpot?.f1*100,1)}%`:`${fmt((isLong(r)?s.quality.em:s.quality.f1)*100,1)}%`;
}
const roles={
 root:'这是用户的一次逻辑任务，由 Harness 按本轮固定规则创建研究子 Session。这里没有额外的规划模型调用；父模型在全部必做子任务汇合后回答。分支启动时机是 D1 的控制位置。',
 query:'这是研究子 Agent 在本次研究执行中的第一次模型调用。它根据问题和自己负责的来源标题生成检索词，随后把控制权交给 BM25 工具。后面的证据整理继续使用同一 Session，同一次子 Agent 执行会包含模型调用和工具等待。',
 bm25:'这是实际运行的本地 BM25 检索。工具在这个子 Agent 的文档分片中排序并返回来源，结果成为后续模型调用的输入。图中分别显示实际检索耗时与人为延迟处理；工具不调用模型，也不读取隐藏答案。',
 draft:'同一个研究子 Agent 阅读工具返回的来源，起草正面事实、原文引句和相关性说明。它随后等待引用检查工具；这个阶段已经形成了较长的 Session 历史，后续 activation 有可能复用前缀。',
 source_check:'实际工具逐条检查草稿中的引用是否出现在给定来源，忽略纯空白差异，并把成功或失败结果返回原 Session。它只检查引用来源，不证明推理或最终答案正确。等待中的下一次模型调用尚未进入引擎队列。',
 evidence:'研究子 Agent 整理自己分片的事实、实体关系和来源编号，交给父任务。带来源验证的流程会先消费检查结果，再继续这次模型调用。父任务必须等待全部必做分支结束，才能开始汇总。这里是 D2 请求派发的控制位置。',
 synthesis:'父 Agent 等待全部必做子 Session，关联它们的部分事实，生成带来源的最终答案。集中阅读对照则直接给它全部原文。任务耗时从用户提交开始计算，包括 Harness 等待、工具与模型时间；答案在执行后独立评分。'
};
const stageNames={plan:'父 Agent 发起原生工作流',query:'生成检索词',draft:'起草事实与原文引用',evidence:'整理证据并返回',synthesis:'汇合并生成最终答案'};
async function json(path){const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error(`${r.status} ${path}`);return r.json();}
function visible(){return rounds.filter(r=>$('dataset').value==='all'||datasetKind(r)===$('dataset').value);}
function table(){
 const list=visible();$('rounds').innerHTML=list.map(r=>{const s=r.summary,latency=r.official_dsh?s.task_duration_seconds:s.root_latency_seconds;return `<tr class="${r.run_id===current?'selected':''}"><td><button data-run="${esc(r.run_id)}">${esc(runLabel(r))}</button></td><td>${r.official_dsh?`${s.completed_tasks}/${s.tasks}`:`${s.completed_root_records}/${s.expected_roots}`}</td><td>${r.official_dsh?s.agent_model_calls:s.model_calls}</td><td>${esc(qualityText(r))}</td><td>${fmt(latency.mean)}</td><td>${fmt(latency.p95)}</td><td>${fmt(r.official_dsh?s.preemptions:s.preemptions_delta,0)}</td></tr>`}).join('');
 $('rounds').querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>selectRun(b.dataset.run));
}
function selectOptions(){const list=visible();$('run').innerHTML=list.map(r=>`<option value="${esc(r.run_id)}">${esc(runLabel(r))}</option>`).join('');table();if(list.length)selectRun(list.some(r=>r.run_id===current)?current:list[list.length-1].run_id);}
function cardDetails(title,data){return `<details><summary>${esc(title)}</summary><pre>${esc(typeof data==='string'?data:JSON.stringify(data,null,2))}</pre></details>`;}
function openNode(key){
 const n=nodeData.get(key);if(!n)return;clearTimeout(closeTimer);lastFocus=document.activeElement;
 let content=`<p class="eyebrow">${esc(n.kind==='root'?'逻辑任务':n.kind==='model'?'真实模型调用':'真实工具执行')}</p><h2 id="drawer-title">${esc(n.title)}</h2><p class="role">${esc(n.role||roles[n.stage])}</p>`;
 if(n.kind==='model'){
  const response=n.response||{},payload=n.request.payload,params={...payload};delete params.messages;
  content+=`<p>API 耗时 ${fmt(response.duration)} 秒 · ${n.request.dispatch?'首个响应数据块':'首 token'} ${fmt(response.ttft)} 秒 · 输出 ${response.usage?.completion_tokens??'—'} token</p>`;
  const cached=response.usage?.prompt_tokens_details?.cached_tokens;
  if(cached!=null)content+=`<p>引擎实际命中 ${cached} / ${response.usage.prompt_tokens} 个输入 token。首 token 时间包含排队与准备；缓存命中不直接等于任务加速。</p>`;
  if(response.server_metrics?.queue_time_ms!=null)content+=`<p>引擎报告的队列等待 ${fmt(response.server_metrics.queue_time_ms/1000)} 秒。</p>`;
  if(n.request.dispatch){const d=n.request.dispatch;content+=`<p>前端派发等待 ${fmt(d.frontend_wait)} 秒 · 当时许可上限 ${d.target} · 引擎运行 ${d.engine.running}、等待 ${d.engine.waiting} · KV ${fmt(d.engine.kv_usage*100,1)}%</p>`+cardDetails('派发时的真实后端状态与控制动作',d);}
  content+=cardDetails('完整 Prompt · 实际 messages',payload.messages)+cardDetails('完整采样与 API 参数',params)+cardDetails('模型真实返回与测量',response);
 }else content+=cardDetails(n.kind==='root'?'原始任务与最终记录':'完整工具参数与结果',n.raw);
 $('drawer-content').innerHTML=content;$('drawer').hidden=false;$('drawer').setAttribute('aria-labelledby','drawer-title');
 requestAnimationFrame(()=>$('drawer').classList.add('open'));$('backdrop').classList.add('open');document.body.style.overflow='hidden';$('close').focus();
}
function closeDrawer(){ clearTimeout(closeTimer);$('drawer').classList.remove('open');$('backdrop').classList.remove('open');document.body.style.overflow='';closeTimer=setTimeout(()=>$('drawer').hidden=true,200);if(lastFocus?.isConnected)lastFocus.focus(); }
function drawEdges(){
 const flow=$('flow'),svg=flow.querySelector('svg');if(!svg)return;const box=flow.getBoundingClientRect();svg.setAttribute('viewBox',`0 0 ${box.width} ${box.height}`);
 let paths='<defs><marker id="experiment-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#5d8770"/></marker></defs>';
 for(const [a,b] of edges){const from=document.getElementById(a),to=document.getElementById(b);if(!from||!to)continue;const x=from.getBoundingClientRect(),y=to.getBoundingClientRect(),sx=x.left+x.width/2-box.left,sy=x.bottom-box.top+2,tx=y.left+y.width/2-box.left,ty=y.top-box.top-5,mid=(sy+ty)/2;paths+=`<path d="M ${sx} ${sy} V ${mid} H ${tx} V ${ty}" fill="none" stroke="#5d8770" stroke-width="1.8" marker-end="url(#experiment-arrow)"/>`;}
 svg.innerHTML=paths;
}
function graph(config,sample){
 nodeData=new Map();edges=[];const flow=$('flow'),streams=sample.streams,requests=streams.requests||[],responses=streams.responses||[],tools=streams.tools||[],root=sample.root_id;
 const direct=config.workflow==='direct',verified=config.workflow==='verified',branches=direct?1:config.branches;flow.style.gridTemplateColumns=`repeat(${branches},minmax(220px,1fr))`;flow.style.minWidth=direct?'480px':`${branches*250+60}px`;flow.innerHTML='<svg aria-hidden="true"></svg>';
 function node(id,row,col,title,stage,kind,detail,pin=''){
  const n={title,stage,kind,...detail};nodeData.set(id,n);const b=document.createElement('button');b.type='button';b.id=id;b.className=`flow-node ${kind==='tool'?'tool':''} ${kind==='root'?'logical':''} ${stage==='synthesis'?'parent':''}`;b.style.gridRow=row;b.style.gridColumn=col;
  let meta='';if(kind==='model')meta=n.response?.error?'调用失败，展开查看':`${fmt(n.response?.duration)} 秒 · ${n.response?.usage?.completion_tokens??'—'} 输出 token`;
  if(kind==='tool')meta=`工具实耗 ${fmt((n.raw.actual_cpu_seconds||0)*1000,1)} ms${n.raw.injected_delay_seconds?` · 附加 ${fmt(n.raw.injected_delay_seconds)} s`:''}`;
  if(kind==='root')meta='Harness 按固定规则展开必做工作';
  b.innerHTML=`<span class="type">${kind==='model'?'QWEN · 模型调用':kind==='tool'?'TOOL · 工具':'ROOT · 任务'}</span><strong>${esc(title)}</strong><small>${esc(meta)}</small>${pin?`<span class="pin">${esc(pin)}</span>`:''}`;b.onclick=()=>openNode(id);flow.append(b);return id;
 }
 function model(stage,session,row,col,title,pin){const req=requests.find(r=>r.node_id===session&&r.stage===stage);if(!req)return null;return node(`n-${nodeData.size}`,row,col,title,stage,'model',{request:req,response:responses.find(r=>r.call_id===req.call_id)},pin);}
 function tool(kind,session,row,col,title){const raw=tools.find(t=>t.node_id===session&&(t.tool_kind===kind||(kind==='bm25'&&t.tool_id.endsWith('/search'))));return raw?node(`n-${nodeData.size}`,row,col,title,kind,'tool',{raw},kind==='source_check'?'工具在途 → 后续回流':''):null;}
 function edge(a,b){if(a&&b)edges.push([a,b]);}
 const start=node('task-root',1,'1 / -1','用户任务提交与固定分支展开','root','root',{raw:{task:sample.task,final:streams.roots?.[0]}},'D1 · 分支启动时机');
 if(direct){edge(start,model('synthesis',root+'/parent',2,1,'父 Agent · 读取全部原文并回答','集中上下文质量对照'));}
 else{
  const ends=[];for(let b=0;b<branches;b++){const session=`${root}/child${b}`,col=b+1,q=model('query',session,2,col,`子 Agent ${b+1} · 检索词`),search=tool('bm25',session,3,col,'BM25 · 检索原始来源');edge(start,q);edge(q,search);let before=search,row=4;
   if(verified){const draft=model('draft',session,4,col,`子 Agent ${b+1} · 引用草稿`),check=tool('source_check',session,5,col,'来源检查 · 核对原文引句');edge(search,draft);edge(draft,check);before=check;row=6;}
   const evidence=model('evidence',session,row,col,`同一子 Agent ${b+1} · 证据报告`,'D2 · 请求准入与排序');edge(before,evidence);ends.push(evidence);
  }
  const final=model('synthesis',root+'/parent',verified?7:5,'1 / -1','父 Agent · 等待全部分支并汇总','收敛优先 · 已有基线');ends.forEach(e=>edge(e,final));
 }
 $('graph-caption').textContent=`这是此轮一个完整任务的实际调用：${requests.length} 次模型请求、${tools.length} 次工具执行。${direct?'集中阅读使用一个父 Session。':`${branches} 个子 Session 各完成一次持续研究执行，包含多次模型调用与工具等待，另有父 Session；Agent 数与模型请求数不同。`} 点击节点查看说明和原始数据。`;
 requestAnimationFrame(drawEdges);
}
function dshGraph(sample){
 nodeData=new Map();edges=[];const flow=$('flow');flow.style.gridTemplateColumns='repeat(3,minmax(220px,1fr))';flow.style.minWidth='810px';flow.innerHTML='<svg aria-hidden="true"></svg>';
 const {requests,responses,tools}=sample.streams;
 function node(id,row,col,title,stage,kind,detail,pin=''){
  const n={title,stage,kind,...detail};nodeData.set(id,n);const b=document.createElement('button');b.type='button';b.id=id;b.className=`flow-node ${kind==='tool'?'tool':''} ${col==='1 / -1'?'parent':''}`;b.style.gridRow=row;b.style.gridColumn=col;
  const meta=kind==='model'?`${fmt(n.response.duration)} 秒 · 前端等待 ${fmt(n.request.dispatch.frontend_wait)} 秒`:kind==='tool'?`真实 CPU 检索 ${fmt(n.raw.actual_cpu_seconds*1000,2)} ms`:kind==='workflow'?'官方 Workflow 引擎 · 三个必做子 Agent':'4 个原生 Agent · 8 次模型调用 · 3 次检索';
  b.innerHTML=`<span class="type">${kind==='model'?'QWEN · 模型调用':kind==='tool'?'TOOL · 工具':kind==='workflow'?'DSH · 原生工作流':'ROOT · 任务'}</span><strong>${esc(title)}</strong><small>${esc(meta)}</small>${pin?`<span class="pin">${esc(pin)}</span>`:''}`;b.onclick=()=>openNode(id);flow.append(b);return id;
 }
 const dshRoles={
  root:'这是官方 DSH 执行的一道真实 HotpotQA 问题。父 Agent 先生成工作流工具调用，再由原生 Workflow 引擎创建三个孩子；全部报告完成后父 Agent 继续同一 Session 汇总。这里的规划调用真实存在，与旧自建框架直接展开分支的流程不同。',
  plan:'父 Agent 的第一次真实模型调用。模型根据任务要求发起 research_workflow 工具，随后等待工具完成。工具在官方 Workflow 引擎中运行三分支并行应用，父 Agent 不会自行检索。',
  workflow:'research_workflow 是我们编写的科研应用工具，内部调用官方 Workflow 引擎的 parallel 和 agent。官方框架负责子 Agent 生命周期、并行执行、等待与结果汇合；本组必须完成全部三个分支，不动态删减或增加 Agent。',
  query:'这个子 Agent 根据问题生成自己分片的检索词，并调用一次 bench_search。BM25 只搜索该分片的原始文档；返回后同一子 Session 再调用模型整理证据。',
  bm25:'这是实际执行的本地 BM25 工具：按子 Agent 生成的检索词在它负责的文档分片里排序，返回前三篇完整原文。工具不调用模型、不读取答案标签，本组没有人为注入等待。',
  evidence:'同一个子 Agent 阅读刚返回的来源，给出包含事实、原文引句和缺失信息的证据报告，然后结束。父工作流要等三个分支都结束才能返回；本组的全局请求许可只控制提交时机，不按这个阶段优先排序。',
  synthesis:'三个子报告已通过原生工作流工具返回，父 Agent 进行第二次模型调用，关联证据并给出最终 JSON 答案。下方标签与 F1 是完成后离线评分的结果，没有进入 Agent、prompt 或派发控制器。'
 };
 function model(session,stage,row,col,title){const req=requests.find(r=>r.node_id===session&&r.stage===stage);const response=responses.find(r=>r.call_id===req.call_id);return node(`dsh-${stage}-${nodeData.size}`,row,col,title,stage,'model',{request:req,response,role:dshRoles[stage]},'控制位置 · 模型请求提交');}
 function edge(a,b){edges.push([a,b]);}
 const start=node('dsh-task-root',1,'1 / -1','用户任务提交','root','root',{raw:{task:sample.task,scoring:sample.scoring},role:dshRoles.root});
 const plan=model(sample.root_id,'plan',2,'1 / -1','父 Agent · 发起研究工作流');edge(start,plan);
 const workflow=node('dsh-workflow',3,'1 / -1','原生 Workflow · 并行三个研究子 Agent','workflow','workflow',{raw:sample.workflow,role:dshRoles.workflow},'本组固定三分支 · 不是新设计机制');edge(plan,workflow);
 const ends=[];
 sample.child_sessions.forEach((session,index)=>{const col=index+1,q=model(session,'query',4,col,`子 Agent ${col} · 生成检索词`);edge(workflow,q);const raw=tools.find(t=>t.node_id===session);const search=node(`dsh-search-${col}`,5,col,'BM25 · 检索原始文档','bm25','tool',{raw,role:dshRoles.bm25});edge(q,search);const evidence=model(session,'evidence',6,col,`同一子 Agent ${col} · 证据报告`);edge(search,evidence);ends.push(evidence);});
 const final=model(sample.root_id,'synthesis',7,'1 / -1','父 Agent · 等三份报告齐全后汇总');ends.forEach(end=>edge(end,final));
 $('graph-caption').textContent='这道题的真实执行：4 个原生 Agent、8 次模型调用、3 次 BM25。箭头表示依赖顺序；橙色标记是本组派发基线的控制位置，不表示已经实现新的工作流机制。';
 requestAnimationFrame(drawEdges);
}
async function selectDshTask(identifier){
 const state=currentSamples;if(!state)return;const ticket=++loadVersion,task=state.entry.tasks.find(t=>t.task_id===identifier);$('task').value=identifier;
 try{const sample=await json(dshBase+task.path);if(ticket!==loadVersion||currentSamples!==state)return;
  $('question').textContent=sample.task.question;$('task-result').textContent=`本题完整耗时 ${fmt(sample.scoring.duration_seconds)} 秒 · 答案 F1 ${fmt(sample.scoring.f1,3)}\n模型答案：${sample.scoring.answer}\n离线标准答案：${sample.scoring.gold}`;
  $('task-data').href=dshBase+task.path;dshGraph(sample);$('status').textContent=`已载入官方 DSH 三轮真实数据。当前 ${state.entry.run_id} · 第 ${state.entry.tasks.indexOf(task)+1}/8 题。`;
 }catch(error){if(ticket===loadVersion)$('status').textContent='该题原始调用未能加载，请重试或下载本轮完整证据。';console.error(error);}
}
async function selectDshRun(entry,ticket){
 const s=entry.summary;currentSamples={entry};$('detail').hidden=false;$('run-label').textContent=entry.run_id;$('run-title').textContent='官方 DSH · 八题最小对照组';
 $('purpose').textContent='八道 HotpotQA 多跳问答同时提交。父 Agent 调用研究工作流，官方 DSH 并行创建三个子 Agent；每个孩子真实生成检索词、调用 BM25、整理证据，再由父 Agent 汇总。每题固定三个孩子、八次模型调用，三轮只比较就绪模型请求何时提交。';
 const policy=entry.run_id.endsWith('native')?'直接派发':entry.run_id.endsWith('fixed12')?'固定在途上限 12':'真实压力反馈，上限 12';
 $('validation-note').textContent=`当前设置：${policy}。8/8 题、32 个原生 Agent、64 次模型调用、24 次 BM25 通过审计，无工具错误或长度截断。每种设置只有一轮，生成内容与答案不同。`;
 $('cache-note').textContent=`真实后端观测：运行峰值 ${s.max_engine_running}，排队峰值 ${s.max_engine_waiting}，KV 峰值 ${fmt(s.max_kv_usage*100,2)}%，抢占 ${s.preemptions}；每次调用平均前端等待 ${fmt(s.frontend_wait_seconds.mean)} 秒。${s.policy==='pressure'?`压力收缩触发 ${s.feedback_reduced_admissions} 次，本轮实际一直保持 12。`:'节点卡片内保留各次派发时读取的引擎指标。'}`;
 $('stats').innerHTML=[['平均每题完整耗时',fmt(s.task_duration_seconds.mean)+' s'],['较慢任务 · P95',fmt(s.task_duration_seconds.p95)+' s'],['答案 F1',fmt(s.quality.f1,3)],['真实模型调用',s.agent_model_calls]].map(([a,b])=>`<div class="stat"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
 $('links').innerHTML=Object.entries({'config.json':'本轮实际参数','scored.json':'八题答案与离线评分','native-audit.json':'原生 Agent 审计','raw-archive':'全部 Prompt、响应和日志'}).map(([p,label])=>`<a href="${esc(dshBase+entry.paths[p])}" target="_blank" rel="noopener">${label} ↗</a>`).join('');
 $('task-controls').hidden=false;$('task-result').hidden=false;$('dsh-callouts').hidden=false;$('legacy-callouts').hidden=true;
 $('task').innerHTML=entry.tasks.map((t,i)=>`<option value="${esc(t.task_id)}">${i+1}. ${esc(t.question)}</option>`).join('');
 if(ticket!==loadVersion)return;
 await selectDshTask(entry.tasks.find(t=>t.task_id==='5a78f59755429970f5fffdf7')?.task_id||entry.tasks[0].task_id);
}
async function selectRun(id){
 current=id;$('run').value=id;table();closeDrawer();const ticket=++loadVersion,entry=rounds.find(r=>r.run_id===id);if(!entry)return;
 $('status').textContent=`正在加载 ${id} 的完整案例…`;
 if(entry.official_dsh){await selectDshRun(entry,ticket);if(current===id)history.replaceState(null,'','#'+encodeURIComponent(id));return;}
 currentSamples=null;$('task-controls').hidden=true;$('task-result').hidden=true;$('dsh-callouts').hidden=true;$('legacy-callouts').hidden=false;
 try{const [config,sample]=await Promise.all([json(base+entry.paths['config.json']),json(base+entry.paths['raw-example.json'])]);if(ticket!==loadVersion)return;
  const s=entry.summary,mixed=datasetKind(entry)==='mixed',shared=datasetKind(entry)==='shared';$('detail').hidden=false;$('run-label').textContent=id;$('run-title').textContent=shared?'共享真实引擎 · 独立控制器的任务竞争':mixed?'长短上下文混合 · 历史规模与派发':isLong(entry)?'真实全文研究 · 多来源证据汇合':'多跳问答 · 分片调查与事实汇合';
  const verify=s.source_verification,cache=s.cache_by_stage?.evidence;
  $('validation-note').textContent=verify?`本轮实际运行 ${verify.tool_calls} 次来源检查，草稿解析失败 ${verify.draft_parse_errors} 次；${verify.quote_checks} 条引用中 ${verify.valid_quotes} 条通过原文核验。来源有效与答案正确分别评价。${verify.draft_parse_errors?'此轮包含工具解析失败，不能当作全部核验正常完成的性能证据。':''}`:'本轮不包含引用核验工具；答案通过数据集隐藏标签独立评分。';
  $('cache-note').textContent=cache?.cached_fraction!=null?`工具之后的 evidence 调用：实际命中 ${cache.cached_prompt_tokens.toLocaleString()} / ${cache.accounted_prompt_tokens.toLocaleString()} 个输入 token（${fmt(cache.cached_fraction*100,1)}%）。这是实际测量；对比不同任务时需核对原文长度、缓存块对齐和引擎容量。`:'此轮没有逐请求缓存明细，缺失值不按零命中解释。';
  $('purpose').textContent=mixed?'固定的 LongBench-v2 原始长文题与 HotpotQA 短文多跳题交替提交，执行相同的三子 Session、十次必做调用流程。它们占用相同的逻辑 Session 数，但历史上下文规模不同。分别报告长文选项准确率和短文答案 F1；下方展示其中一个真实任务。':isLong(entry)?'任务来自 LongBench-v2 原始多文档研究题，涵盖论文、政府报告、法律资料和新闻。模型需要从完整来源中找到支持关系，给出四选一答案。原文按连续片段分给研究子 Session，未用占位文本扩充上下文。':'任务来自 HotpotQA 的真实问题与文档。研究子 Session 分别调查文档分片，把部分事实交给父 Agent 关联。集中阅读轮次直接提供全部文档，用来审核任务质量。';
  $('stats').innerHTML=[['任务平均耗时',fmt(s.root_latency_seconds.mean)+' s'],[mixed?'长文准确率 · 短文 F1':isLong(entry)?'选项准确率':'答案 F1',qualityText(entry)],['整批模型调用',s.model_calls],['抢占次数',fmt(s.preemptions_delta,0)]].map(([a,b])=>`<div class="stat"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
  if(mixed){const groups=s.quality_by_dataset;$('cache-note').textContent+=` 分组平均任务耗时：长文 ${fmt(groups['longbench-v2']?.root_latency_seconds.mean)} 秒，短文 ${fmt(groups.hotpot?.root_latency_seconds.mean)} 秒。混合均值改善不能代替两组都改善。`;}
  if(shared){
   const target=s.quality_by_tenant.target,background=s.quality_by_tenant.background;
   $('purpose').textContent=`这是同一轮实验中的两个独立Harness控制器，共享真实双卡推理引擎。目标控制器处理16道长短混合研究任务${background?'，背景控制器另外完成4道不重合的长文研究任务':'；本轮关闭背景作为参照'}。每题都保留完整的三子Session、检索、引用核验和父汇合。目标控制器只能看到自己的图和全局引擎指标，不能读取背景任务图或未来到达计划。背景取已有校准题作为有用负载，不当作新的隐藏测试集。`;
   $('stats').innerHTML=[['目标任务平均耗时',fmt(target.root_latency_seconds.mean)+' s'],['目标任务 P95',fmt(target.root_latency_seconds.p95)+' s'],['背景任务平均耗时',background?fmt(background.root_latency_seconds.mean)+' s':'未启用'],['整批真实模型调用',s.model_calls]].map(([a,b])=>`<div class="stat"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
   $('cache-note').textContent+=` 分组答题质量：${qualityText(entry)}。${background?`背景任务P95为${fmt(background.root_latency_seconds.p95)}秒。`:''} 引擎抢占和队列是共享的全局计数，不归给某一个控制器；上表平均耗时覆盖全部任务，这里另列目标与背景。`;
  }
  $('links').innerHTML=Object.entries({'raw-example.json':'完整案例 · Prompt 与调用','config.json':'完整实验参数','scored.jsonl':'全部任务评分','research_record.md':'本轮约 300 字记录','audit.json':'因果顺序审计','history_audit.json':'历史回流间隔审计','token_audit.json':'实际 token 前缀审计'}).filter(([p])=>entry.paths[p]).map(([p,label])=>`<a href="${esc(base+entry.paths[p])}" target="_blank" rel="noopener">${label} ↗</a>`).join('');
  $('question').textContent=sample.task.question;graph(config,sample);$('status').textContent=`已载入 ${rounds.length} 个已归档轮次。当前：${id}；上方是整批统计，下方是单个实际任务。`;history.replaceState(null,'','#'+encodeURIComponent(id));
 }catch(error){if(ticket===loadVersion)$('status').textContent='案例暂未加载。可通过下方的逐轮实验记录查看完整证据。';console.error(error);}
}
$('close').onclick=closeDrawer;$('backdrop').onclick=closeDrawer;$('run').onchange=()=>selectRun($('run').value);$('dataset').onchange=selectOptions;
$('task').onchange=()=>{closeDrawer();selectDshTask($('task').value);};
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer();if(e.key==='Tab'&&$('drawer').classList.contains('open')){const nodes=[...$('drawer').querySelectorAll('button,a[href],summary')];if(e.shiftKey&&document.activeElement===nodes[0]){e.preventDefault();nodes.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===nodes.at(-1)){e.preventDefault();nodes[0].focus();}}});
new ResizeObserver(()=>requestAnimationFrame(drawEdges)).observe($('flow'));
Promise.allSettled([json(base+'index.json'),json(dshBase+'index.json')]).then(results=>{
 const [legacy,dsh]=results;rounds=[...(dsh.status==='fulfilled'?dsh.value:[]),...(legacy.status==='fulfilled'?legacy.value:[])];
 if(!rounds.length)throw Error('No experiment index loaded');
 const hash=decodeURIComponent(location.hash.slice(1)),requested=rounds.find(r=>r.run_id===hash);
 current=requested?.run_id||rounds.find(r=>r.official_dsh)?.run_id||rounds.at(-1).run_id;
 $('dataset').value=requested?(requested.official_dsh?'dsh':'all'):(dsh.status==='fulfilled'?'dsh':'all');selectOptions();
 if(dsh.status==='rejected')$('status').textContent='官方 DSH 数据未加载；当前仅显示旧实验，请刷新重试。';
}).catch(error=>{$('status').textContent='实验数据暂未加载，请查看下方的逐轮实验记录。';console.error(error);});
