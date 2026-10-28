/* Measured artifacts only. No simulated performance or invented prompts. */
const base='../experiments/harness-engine/results/';
const $=id=>document.getElementById(id), esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(x,n=2)=>x==null?'—':Number(x).toFixed(n);
let rounds=[],current=null,loadVersion=0,nodeData=new Map(),edges=[],lastFocus=null,closeTimer;
const isLong=r=>r.run_id.includes('long');
const roles={
 root:'这是用户的一次逻辑任务，由 Harness 按本轮固定规则创建研究子 Session。这里没有额外的规划模型调用；父模型在全部必做子任务汇合后回答。分支启动时机是 D1 的控制位置。',
 query:'这是研究子 Agent 的第一次 activation。它根据问题和自己负责的来源标题生成检索词，随后把控制权交给 BM25 工具。后面的证据整理继续使用同一 Session，不是新建一个 Agent。',
 bm25:'这是实际运行的本地 BM25 检索。工具在这个子 Agent 的文档分片中排序并返回来源，结果成为后续模型调用的输入。图中分别显示实际检索耗时与人为延迟处理；工具不调用模型，也不读取隐藏答案。',
 draft:'同一个研究子 Agent 阅读工具返回的来源，起草正面事实、原文引句和相关性说明。它随后等待引用检查工具；这个阶段已经形成了较长的 Session 历史，后续 activation 有可能复用前缀。',
 source_check:'实际工具逐条检查草稿中的引用是否出现在给定来源，忽略纯空白差异，并把成功或失败结果返回原 Session。它只检查引用来源，不证明推理或最终答案正确。等待中的下一次模型调用尚未进入引擎队列。',
 evidence:'研究子 Agent 整理自己分片的事实、实体关系和来源编号，交给父任务。带来源验证的流程会先消费检查结果，再继续这个 activation。父任务必须等待全部必做分支结束，才能开始汇总。这里是 D2 请求派发的控制位置。',
 synthesis:'父 Agent 等待全部必做子 Session，关联它们的部分事实，生成带来源的最终答案。集中阅读对照则直接给它全部原文。任务耗时从用户提交开始计算，包括 Harness 等待、工具与模型时间；答案在执行后独立评分。'
};
const stageNames={query:'生成检索词',draft:'起草事实与原文引用',evidence:'整理证据并返回',synthesis:'汇合并生成最终答案'};
async function json(path){const r=await fetch(path,{cache:'no-cache'});if(!r.ok)throw Error(`${r.status} ${path}`);return r.json();}
function visible(){return rounds.filter(r=>$('dataset').value==='all'||(isLong(r)?'long':'short')===$('dataset').value);}
function table(){
 const list=visible();$('rounds').innerHTML=list.map(r=>{const s=r.summary;return `<tr class="${r.run_id===current?'selected':''}"><td><button data-run="${esc(r.run_id)}">${esc(r.run_id)}</button></td><td>${s.completed_root_records}/${s.expected_roots}</td><td>${s.model_calls}</td><td>${fmt((isLong(r)?s.quality.em:s.quality.f1)*100,1)}%</td><td>${fmt(s.root_latency_seconds.mean)}</td><td>${fmt(s.root_latency_seconds.p95)}</td><td>${fmt(s.preemptions_delta,0)}</td></tr>`}).join('');
 $('rounds').querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>selectRun(b.dataset.run));
}
function selectOptions(){const list=visible();$('run').innerHTML=list.map(r=>`<option value="${esc(r.run_id)}">${esc(r.run_id)}</option>`).join('');table();if(list.length)selectRun(list.some(r=>r.run_id===current)?current:list[list.length-1].run_id);}
function cardDetails(title,data){return `<details><summary>${esc(title)}</summary><pre>${esc(typeof data==='string'?data:JSON.stringify(data,null,2))}</pre></details>`;}
function openNode(key){
 const n=nodeData.get(key);if(!n)return;clearTimeout(closeTimer);lastFocus=document.activeElement;
 let content=`<p class="eyebrow">${esc(n.kind==='root'?'逻辑任务':n.kind==='model'?'真实模型 activation':'真实工具执行')}</p><h2 id="drawer-title">${esc(n.title)}</h2><p class="role">${esc(roles[n.stage])}</p>`;
 if(n.kind==='model'){
  const response=n.response||{},payload=n.request.payload,params={...payload};delete params.messages;
  content+=`<p>API 耗时 ${fmt(response.duration)} 秒 · 首 token ${fmt(response.ttft)} 秒 · 输出 ${response.usage?.completion_tokens??'—'} token</p>`;
  const cached=response.usage?.prompt_tokens_details?.cached_tokens;
  if(cached!=null)content+=`<p>引擎实际命中 ${cached} / ${response.usage.prompt_tokens} 个输入 token。首 token 时间包含排队与准备；缓存命中不直接等于任务加速。</p>`;
  if(response.server_metrics?.queue_time_ms!=null)content+=`<p>引擎报告的队列等待 ${fmt(response.server_metrics.queue_time_ms/1000)} 秒。</p>`;
  content+=cardDetails('完整 Prompt · 实际 messages',payload.messages)+cardDetails('完整采样与 API 参数',params)+cardDetails('模型真实返回与测量',response);
 }else content+=cardDetails(n.kind==='root'?'原始任务与最终记录':'完整工具参数与结果',n.raw);
 $('drawer-content').innerHTML=content;$('drawer').hidden=false;$('drawer').setAttribute('aria-labelledby','drawer-title');
 requestAnimationFrame(()=>$('drawer').classList.add('open'));$('backdrop').classList.add('open');document.body.style.overflow='hidden';$('close').focus();
}
function closeDrawer(){ $('drawer').classList.remove('open');$('backdrop').classList.remove('open');document.body.style.overflow='';closeTimer=setTimeout(()=>$('drawer').hidden=true,200);if(lastFocus?.isConnected)lastFocus.focus(); }
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
 $('graph-caption').textContent=`这是此轮一个完整任务的实际调用：${requests.length} 次模型请求、${tools.length} 次工具执行。${direct?'集中阅读使用一个父 Session。':`${branches} 个子 Session 分别多次 activation，另有父 Session；Agent 数与模型请求数不同。`} 点击节点查看说明和原始数据。`;
 requestAnimationFrame(drawEdges);
}
async function selectRun(id){
 current=id;$('run').value=id;table();closeDrawer();const ticket=++loadVersion,entry=rounds.find(r=>r.run_id===id);if(!entry)return;
 $('status').textContent=`正在加载 ${id} 的完整案例…`;
 try{const [config,sample]=await Promise.all([json(base+entry.paths['config.json']),json(base+entry.paths['raw-example.json'])]);if(ticket!==loadVersion)return;
  const s=entry.summary;$('detail').hidden=false;$('run-label').textContent=id;$('run-title').textContent=isLong(entry)?'真实全文研究 · 多来源证据汇合':'多跳问答 · 分片调查与事实汇合';
  const verify=s.source_verification,cache=s.cache_by_stage?.evidence;
  $('validation-note').textContent=verify?`本轮实际运行 ${verify.tool_calls} 次来源检查，草稿解析失败 ${verify.draft_parse_errors} 次；${verify.quote_checks} 条引用中 ${verify.valid_quotes} 条通过原文核验。来源有效与答案正确分别评价。${verify.draft_parse_errors?'此轮包含工具解析失败，不能当作全部核验正常完成的性能证据。':''}`:'本轮不包含引用核验工具；答案通过数据集隐藏标签独立评分。';
  $('cache-note').textContent=cache?.cached_fraction!=null?`工具之后的 evidence 调用：实际命中 ${cache.cached_prompt_tokens.toLocaleString()} / ${cache.accounted_prompt_tokens.toLocaleString()} 个输入 token（${fmt(cache.cached_fraction*100,1)}%）。这是实际测量；对比不同任务时需核对原文长度、缓存块对齐和引擎容量。`:'此轮没有逐请求缓存明细，缺失值不按零命中解释。';
  $('purpose').textContent=isLong(entry)?'任务来自 LongBench-v2 原始多文档研究题，涵盖论文、政府报告、法律资料和新闻。模型需要从完整来源中找到支持关系，给出四选一答案。原文按连续片段分给研究子 Session，未用占位文本扩充上下文。':'任务来自 HotpotQA 的真实问题与文档。研究子 Session 分别调查文档分片，把部分事实交给父 Agent 关联。集中阅读轮次直接提供全部文档，用来审核任务质量。';
  $('stats').innerHTML=[['任务平均耗时',fmt(s.root_latency_seconds.mean)+' s'],[isLong(entry)?'选项准确率':'答案 F1',fmt((isLong(entry)?s.quality.em:s.quality.f1)*100,1)+'%'],['整批模型调用',s.model_calls],['抢占次数',fmt(s.preemptions_delta,0)]].map(([a,b])=>`<div class="stat"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
  $('links').innerHTML=Object.entries({'raw-example.json':'完整案例 · Prompt 与调用','config.json':'完整实验参数','scored.jsonl':'全部任务评分','research_record.md':'本轮约 300 字记录','audit.json':'因果顺序审计'}).filter(([p])=>entry.paths[p]).map(([p,label])=>`<a href="${esc(base+entry.paths[p])}" target="_blank" rel="noopener">${label} ↗</a>`).join('');
  $('question').textContent=sample.task.question;graph(config,sample);$('status').textContent=`已载入 ${rounds.length} 个完整轮次。当前：${id}；上方是整批统计，下方是单个实际任务。`;history.replaceState(null,'','#'+encodeURIComponent(id));
 }catch(error){if(ticket===loadVersion)$('status').textContent='案例暂未加载。可通过下方的逐轮实验记录查看完整证据。';console.error(error);}
}
$('close').onclick=closeDrawer;$('backdrop').onclick=closeDrawer;$('run').onchange=()=>selectRun($('run').value);$('dataset').onchange=selectOptions;
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDrawer();if(e.key==='Tab'&&$('drawer').classList.contains('open')){const nodes=[...$('drawer').querySelectorAll('button,a[href],summary')];if(e.shiftKey&&document.activeElement===nodes[0]){e.preventDefault();nodes.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===nodes.at(-1)){e.preventDefault();nodes[0].focus();}}});
new ResizeObserver(()=>requestAnimationFrame(drawEdges)).observe($('flow'));
json(base+'index.json').then(data=>{rounds=data;const hash=decodeURIComponent(location.hash.slice(1));current=rounds.some(r=>r.run_id===hash)?hash:(rounds.find(r=>r.run_id==='v010-long-native-a')?.run_id||rounds.at(-1)?.run_id);selectOptions();}).catch(error=>{$('status').textContent='实验数据暂未加载，请查看下方的逐轮实验记录。';console.error(error);});
