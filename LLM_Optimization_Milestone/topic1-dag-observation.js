/* Read-only views over recorded DSH events; no inference or synthetic agents. */
const base='../experiments/dsh-engine/results/natural-dag-20261029/';
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(x,n=3)=>Number(x).toFixed(n);
const labels={simple:'简单问答',research:'多文档调查',coding:'代码修复',analysis:'CSV 数据分析',incident:'故障诊断'};
const purposes={simple:'计算一张账单的折后价格，观察无需工具时的最短执行路径。',research:'核对六个事实问题，从六十份给定来源中找证据，写成带文件引用的报告。',coding:'修复一个结账服务：读实现和测试，定位失败原因，修改后复测。',analysis:'核对订单、退款和产品数据，解释月度净收入变化，并交付可重复运行的分析。',incident:'联合查看日志、指标和部署配置，定位服务故障并提出验证方案。'};
const toolLabels={read:'读取文件',bash:'执行命令',edit:'修改文件',write:'写入文件',todo_write:'更新计划',web_search:'联网搜索',web_fetch:'读取网页',subagent:'派发子Agent',subagent_fork:'派发继承上下文的子Agent',workflow:'启动工作流'};
const roles={system:'系统规则',user:'用户任务',assistant:'模型历史',tool:'工具返回'};
let index,current,graph,timeline,cursor=0,version=0,timer=null,lastFocus=null,selectedStep=null,zoomTools=true;
let selectedSource='legacy',sourceSets={};
let stepModels=[],stepTools=new Map(),modelByStep=new Map(),connections=[],selectedNode=null,drawerTab='action';
const json=async p=>{const r=await fetch(p,{cache:'no-cache'});if(!r.ok)throw Error(`${r.status} ${p}`);return r.json();};
const detail=(title,html,open=false)=>`<details${open?' open':''}><summary>${esc(title)}</summary>${html}</details>`;
const raw=(title,value)=>detail(title,`<pre>${esc(typeof value==='string'?value:JSON.stringify(value,null,2))}</pre>`);
const readable=value=>`<div class="readable">${esc(value||'（没有文本内容）')}</div>`;
const key=n=>`${n.session_id}:${n.turn}:${n.step}`;
const absolute=()=>current.started_wall_time+cursor;
const parent=n=>modelByStep.get(key(n));
const knownAt=n=>n.kind==='tool'?(parent(n)?.ended_at??n.revealed_at):n.revealed_at;
const rel=t=>t-current.started_wall_time;
const done=n=>n.ended_at!=null&&n.ended_at<=absolute();
const safe=n=>current.execution.pinned_parallel_safe_tools.includes(n.label);
function textOf(value){
 if(value==null)return '';
 if(typeof value==='string')return value;
 if(Array.isArray(value))return value.map(b=>b.text??(b.type==='image'?'[图片内容]':JSON.stringify(b))).join('\n');
 if(value.content)return textOf(value.content);
 if(value.text)return value.text;
 return JSON.stringify(value,null,2);
}
function stop(){clearInterval(timer);timer=null;$('play').textContent='从头播放';}
function close(){ $('drawer').hidden=true;$('backdrop').hidden=true;document.body.style.overflow='';selectedNode=null;if(lastFocus?.isConnected)lastFocus.focus(); }
function params(value){
 return `<dl class="kv">${Object.entries(value||{}).map(([k,v])=>`<dt>${esc(({file_path:'文件',command:'命令',description:'用途',old_string:'匹配的原内容',new_string:'替换成',content:'写入内容',timeout:'超时参数',offset:'起始行',limit:'读取上限'})[k]||k)}</dt><dd>${typeof v==='object'?`<pre>${esc(JSON.stringify(v,null,2))}</pre>`:esc(v)}</dd>`).join('')}</dl>`;
}
function actionTitle(n){
 const ts=stepTools.get(n.id)||[];
 if(!done(n))return '根据当前信息推理';
 if(n.finish==='length')return '推理达到输出上限';
 if(!ts.length)return '汇总并回答任务';
 if(ts.every(t=>t.label==='web_search'))return '检索研究资料';
 if(ts.every(t=>t.label==='web_fetch'))return `读取 ${ts.length} 个网页`;
 if(ts.some(t=>['web_search','web_fetch'].includes(t.label)))return '检索并读取网页资料';
 if(ts.every(t=>t.label==='read'))return `读取 ${ts.length} 份文件`;
 if(ts.every(t=>t.label==='edit'))return `修改 ${ts.length} 个实现文件`;
 if(ts.some(t=>t.label==='write'))return ts.some(t=>(t.arguments.file_path||'').includes('report'))?'整理并写入报告':'写入分析文件';
 if(ts.some(t=>t.label==='todo_write'))return '整理计划与推进状态';
 if(ts.some(t=>t.label==='bash'&&/test|regression|unittest/i.test(t.arguments.command||t.arguments.description||'')))return '执行测试与验证';
 if(ts.some(t=>t.label==='read'))return '读取资料并检查环境';
 return '执行命令检查';
}
function toolResult(n){
 const value=n.result?.value;
 if(n.label==='read'&&Array.isArray(value?.lines))return `<div class="file-preview"><div class="file-title">${esc(value.path?.split('/').at(-1)||'文件内容')} · 保留原行号</div>${value.lines.map(line=>`<div class="file-line"><span>${line.number}</span><code>${esc(line.text)||' '}</code></div>`).join('')}</div>`;
 if(n.label==='bash'&&value?.kind==='foreground')return params({命令退出码:value.exitCode})+readable(value.stdout?.text)+(value.stderr?.text?detail('标准错误输出',readable(value.stderr.text),true):'');
 if(n.label==='edit'&&typeof value?.after==='string')return '<p class="badge">文件修改成功 · 以下为修改后的实际内容</p>'+readable(value.after)+detail('修改前的文件',readable(value.before));
 return readable(textOf(n.committed_result||n.result));
}
function modelAction(n){
 const proposed=(stepTools.get(n.id)||[]);
 let h='<p>这一轮模型消费已有上下文，再决定回答或调用工具。后续工作由它本轮的实际返回决定。</p>';
 if(!done(n))return h+'<p class="notice">观察时刻响应尚未完整提交，未来返回与工具参数暂不显示。</p>';
 h+=n.response.content?'<h3>模型实际返回</h3>'+readable(n.response.content):'<p class="muted">本轮以工具调用继续任务，没有独立的正文回答。</p>';
 if(proposed.length)h+='<h3 style="margin-top:20px">本轮完整提出的动作</h3>'+proposed.map(t=>`<div class="call-card"><b>${esc(toolLabels[t.label]||t.label)}</b><span class="badge">${safe(t)?'可并行工具':'Harness 互斥执行'}</span>${params(t.arguments)}</div>`).join('');
 if(n.response.reasoning)h+=detail('展开实际 reasoning 内容',readable(n.response.reasoning));
 return h;
}
function context(n){
 const messages=n.request.messages;
 return `<p class="context-count">请求实际携带 ${messages.length} 条消息。按角色展开原文；系统规则与过往工具输出默认折叠。</p>`+messages.map((m,i)=>detail(`${i+1} · ${m.role==='user'&&m.content!==current.initial_task?'运行环境 / 补充输入':roles[m.role]||m.role}${m.tool_call_id?' · '+m.tool_call_id:''}`,readable(textOf(m.content))+(m.tool_calls?raw('这条历史消息的工具调用',m.tool_calls):''),m.role==='user'&&i===messages.findIndex(x=>x.role==='user'))).join('');
}
function config(n){
 const p={...n.request};delete p.messages;delete p.tools;
 return '<h3>实际请求参数</h3>'+params(p)+params({输入token:done(n)?n.usage?.prompt_tokens:'响应完成后显示',生成token:done(n)?n.usage?.completion_tokens:'响应完成后显示',结束原因:done(n)?n.finish:'观察时刻尚未知'})+detail(`本轮可见的 ${n.request.tools?.length||0} 个工具`,(n.request.tools||[]).map(t=>detail(t.function.name,readable(t.function.description)+raw('参数定义',t.function.parameters))).join(''));
}
function renderDrawer(){
 const n=selectedNode;if(!n)return;
 const title=n.kind==='model'?`第 ${n.step} 轮 · 模型决定下一步`:`${toolLabels[n.label]||n.label} · ${n.arguments.file_path?.split('/').at(-1)||n.label}`;
 let h=`<p class="eyebrow">${n.kind==='model'?'QWEN · 模型步骤':'TOOL · 实际工具'}</p><h2>${esc(title)}</h2><p class="muted">${n.kind==='tool'?'完整提出':'请求就绪'} +${fmt(rel(knownAt(n)))} 秒${done(n)?` · 执行完成 +${fmt(rel(n.ended_at))} 秒`:n.ended_at?' · 观察时刻尚未完成':''}</p>`;
 const tabs=n.kind==='model'?[['action','本步内容'],['context','输入上下文'],['config','配置'],['raw','完整原始记录']]:[['action','参数与结果'],['raw','完整原始记录']];
 h+=`<div class="drawer-tabs" role="tablist">${tabs.map(([id,name])=>`<button role="tab" data-tab="${id}" aria-selected="${drawerTab===id}">${name}</button>`).join('')}</div><div role="tabpanel">`;
 if(n.kind==='model'){
  if(drawerTab==='action')h+=modelAction(n);
  if(drawerTab==='context')h+=context(n);
  if(drawerTab==='config')h+=config(n);
  if(drawerTab==='raw')h+=raw('实际请求 · 完整 Prompt 与工具定义',n.request)+(done(n)?raw('实际响应',n.response)+raw('接口测量',n.metadata):'<p class="notice">响应尚未完整提交，未来内容不可见。</p>');
 }else{
  const times={'模型完整提出':`+${fmt(rel(knownAt(n)))} 秒`,'Harness登记':n.revealed_at<=absolute()?`+${fmt(rel(n.revealed_at))} 秒`:'此刻尚未登记','执行开始':n.tool_started_at!=null&&n.tool_started_at<=absolute()?`+${fmt(rel(n.tool_started_at))} 秒`:'此刻尚未开始','执行完成':done(n)?`+${fmt(rel(n.ended_at))} 秒`:'此刻尚未完成'};
  if(drawerTab==='action'){
   h+=`<p>${safe(n)?'这是可并行工具；是否实际重叠由下方时间区间确认。':'DSH把此工具作为互斥动作，与同轮其他工具形成顺序屏障。'}结果交回当前Session后，模型再决定后续工作。</p><h3>模型实际生成的参数</h3>`+params(n.arguments)+'<h3>工具实际结果</h3>'+(done(n)?toolResult(n):'<p class="notice">此刻结果尚未返回。</p>')+params(times);
  }else h+=raw('工具调用原始事件与参数',{native_call:n.revealed_at<=absolute()?n.native_call:null,arguments:n.arguments})+(done(n)?raw('完整工具结果',n.committed_result||n.result):'<p>此刻结果尚未知。</p>')+params(times);
 }
 $('drawer-content').innerHTML=h+'</div>';
 $('drawer-content').querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{drawerTab=b.dataset.tab;renderDrawer();$('drawer-content').querySelector(`[data-tab="${drawerTab}"]`).focus();});
}
function open(id){
 const n=graph.nodes.find(n=>n.id===id);if(!n||knownAt(n)>absolute())return;
 lastFocus=document.activeElement;selectedNode=n;drawerTab='action';renderDrawer();$('drawer').hidden=false;$('backdrop').hidden=false;document.body.style.overflow='hidden';$('close').focus();
}
function peak(tools,at=Infinity){
 const edges=[];
 for(const t of tools)if(t.tool_started_at!=null&&t.tool_started_at<=at&&t.ended_at!=null){const end=Math.min(t.ended_at,at);if(end>t.tool_started_at)edges.push([t.tool_started_at,1],[end,-1]);}
 let live=0,p=0;for(const [,d] of edges.sort((a,b)=>a[0]-b[0]||a[1]-b[1])){live+=d;p=Math.max(p,live);}return p;
}
function node(n){
 const tool=n.kind==='tool',started=tool?n.tool_started_at:n.revealed_at;
 const failed=tool&&(n.result?.isError||n.committed_result?.isError||n.result?.error);
 const state=done(n)?failed?'执行失败':!tool&&n.finish==='length'?'输出截断':'已完成':started!=null&&started<=absolute()?'执行中':'等待执行';
 const file=n.arguments?.file_path?.split('/').at(-1);
 const title=tool?(file||n.arguments.description||toolLabels[n.label]||n.label):`第 ${n.step} 轮 · ${actionTitle(n)}`;
 return `<button class="${tool?'tool':'model'} ${state==='执行中'?'active':''}" data-node="${esc(n.id)}"><small>${tool?toolLabels[n.label]||n.label:'QWEN · 模型请求'} · ${state}</small><strong>${esc(title)}</strong><small>${tool?`完整提出 +${fmt(rel(knownAt(n)))} s`:`就绪 +${fmt(rel(n.revealed_at))} s`}${done(n)?` → 完成 +${fmt(rel(n.ended_at))} s`:''}</small></button>`;
}
function groups(tools){
 const result=[];
 for(const t of tools){const last=result.at(-1);if(safe(t)&&last?.parallel)last.tools.push(t);else result.push({parallel:safe(t),tools:[t]});}
 return result;
}
function drawWires(){
 const layer=$('graph').querySelector('.flow-layer'),svg=$('graph').querySelector('.wire-svg');if(!layer||!svg)return;
 const box=layer.getBoundingClientRect();svg.setAttribute('width',box.width);svg.setAttribute('height',box.height);
 const find=id=>[...layer.querySelectorAll('[data-anchor]')].find(e=>e.dataset.anchor===id);
 let paths='';
 for(const c of connections){const a=find(c.a),b=find(c.b);if(!a||!b)continue;const r=a.getBoundingClientRect(),s=b.getBoundingClientRect(),x=r.left+r.width/2-box.left,y=r.bottom-box.top,x2=s.left+s.width/2-box.left,y2=s.top-box.top,mid=(y+y2)/2;paths+=`<path d="M ${x} ${y+1} C ${x} ${mid},${x2} ${mid},${x2} ${y2-6}" fill="none" stroke="${c.order?'#a46932':'#639681'}" stroke-width="1.6" ${c.order?'stroke-dasharray="5 4"':''} marker-end="url(#${c.order?'order-arrow':'dep-arrow'})"/>`;}
 svg.innerHTML='<defs><marker id="dep-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#639681"/></marker><marker id="order-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#a46932"/></marker></defs>'+paths;
 layer.querySelectorAll('.branch-content').forEach(branch=>{
  const area=branch.getBoundingClientRect(),wire=branch.querySelector('.branch-svg'),top=branch.querySelector('.branch-start').getBoundingClientRect(),bottom=branch.querySelector('.branch-end').getBoundingClientRect();
  if(!area.height)return;
  wire.setAttribute('width',area.width);wire.setAttribute('height',area.height);
  const x1=top.left+top.width/2-area.left,y1=top.bottom-area.top,x2=bottom.left+bottom.width/2-area.left,y2=bottom.top-area.top;
  wire.innerHTML=[...branch.querySelectorAll('[data-node]')].map(button=>{const r=button.getBoundingClientRect(),x=r.left+r.width/2-area.left,y=r.top-area.top,end=r.bottom-area.top;return `<path d="M ${x1} ${y1} L ${x} ${y-5}" fill="none" stroke="#639681" stroke-width="1.3" marker-end="url(#dep-arrow)"/><path d="M ${x} ${end} L ${x2} ${y2-5}" fill="none" stroke="#639681" stroke-width="1.3" marker-end="url(#dep-arrow)"/>`;}).join('');
 });
}
function renderGraph(models){
 connections=[];let previous='task',serial=0;
 let html='<div class="flow-layer"><svg class="wire-svg" aria-label="模型工具依赖与Harness顺序箭头"></svg><div class="task-node" data-anchor="task"><small>用户提交初始任务</small><b>初始目标与已有输入</b></div>';
 if(!models.length)html+='<div class="empty">尚未发起第一次模型请求</div>';
 for(const m of models){
  const mid='model-'+m.step;connections.push({a:previous,b:mid});
  html+=`<div class="flow-group" data-anchor="${mid}">${node(m)}</div>`;previous=mid;
  const called=(stepTools.get(m.id)||[]).filter(t=>knownAt(t)<=absolute());
  const batches=groups(called);
  for(let i=0;i<batches.length;i++){
   const g=batches[i],id='group-'+serial++;connections.push({a:previous,b:id,order:i>0});
   html+=`<div class="flow-group ${i>0?'ordering':''}" data-anchor="${id}"><p class="group-label">${i>0?'Harness 顺序屏障 · 上一组结束后才能执行':'同一模型响应完整提出'}</p>`;
   if(g.parallel&&g.tools.length>1){
    html+=`<div class="parallel-block"><div class="parallel-title"><strong>${g.tools.length} 个工具分支 → 结果汇合</strong><span class="badge">截至此刻实测重叠峰值 ${peak(g.tools,absolute())}</span></div><p class="muted">Qwen在同一响应中提出动作；DSH按原生规则执行，结果交回后进入下一轮推理。</p><details><summary>展开 ${g.tools.length} 个实际调用与各自结果</summary><div class="branch-scroll"><div class="branch-content" style="min-width:${g.tools.length*165}px"><svg class="branch-svg" aria-label="工具分叉与汇合箭头"></svg><div class="branch-start">本轮模型提出的完整调用</div><div class="tool-branches" style="grid-template-columns:repeat(${g.tools.length},minmax(0,1fr))">${g.tools.map(node).join('')}</div><div class="branch-end">全部工具结果 → 下一轮模型</div></div></div></details></div>`;
   }else html+=`<div class="tools">${g.tools.map(node).join('')}</div>`;
   html+='</div>';previous=id;
  }
 }
 $('graph').innerHTML=html+'</div>';$('graph').querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>open(b.dataset.node));
 $('graph').querySelectorAll('details').forEach(d=>d.addEventListener('toggle',drawWires));requestAnimationFrame(drawWires);
}
function renderEvents(models){
 const at=absolute(),items=[];
 for(const m of models){
  items.push({at:m.revealed_at,text:`第 ${m.step} 轮模型请求就绪`});
  if(m.ended_at<=at){const tools=stepTools.get(m.id)||[];items.push({at:m.ended_at,text:tools.length?`完整提出 ${tools.length} 个工具动作`:'模型响应完成'});}
  const tools=stepTools.get(m.id)||[];
  if(tools.length){const known=tools.filter(t=>t.tool_started_at!=null&&t.tool_started_at<=at);if(known.length)items.push({at:Math.min(...known.map(t=>t.tool_started_at)),text:`本轮工具开始执行 · ${known.length}/${tools.length} 已启动`});if(tools.every(t=>t.ended_at!=null&&t.ended_at<=at))items.push({at:Math.max(...tools.map(t=>t.ended_at)),text:`本轮工具全部完成 · 重叠峰值 ${peak(tools)}`});}
 }
 $('events').innerHTML=items.sort((a,b)=>b.at-a.at).map(e=>`<li><time>+${fmt(rel(e.at))}s</time><span>${esc(e.text)}<small>${esc(new Date(e.at*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}))} · UTC+8</small></span></li>`).join('')||'<li>此刻尚无模型或工具事件。</li>';
}
function renderGantt(){
 const model=stepModels.find(m=>m.id===selectedStep&&m.revealed_at<=absolute());
 if(!model){$('gantt').innerHTML='<p class="empty">此刻没有可查看的模型步骤。</p>';$('gantt-caption').textContent='沿时间轴推进后再查看。';return;}
 const tools=(stepTools.get(model.id)||[]).filter(t=>knownAt(t)<=absolute()),knownEnd=Math.min(model.ended_at,absolute());
 const starts=tools.filter(t=>t.tool_started_at!=null&&t.tool_started_at<=absolute());
 const ends=starts.map(t=>Math.min(t.ended_at??absolute(),absolute()));
 let lo=zoomTools&&tools.length?Math.min(...tools.map(knownAt)):model.revealed_at;
 let hi=Math.max(knownEnd,...ends,lo+0.001);
 const pad=(hi-lo)*0.045;lo-=pad;hi+=pad;const span=hi-lo;
 const pos=t=>Math.max(0,Math.min(100,100*(t-lo)/span));
 function bar(n,start,end,cls){if(start==null||start>absolute()||end<=start)return '';return `<button class="gantt-bar ${cls}" data-node="${esc(n.id)}" style="left:${pos(start)}%;width:${Math.max(0.15,pos(end)-pos(start))}%" aria-label="${esc(n.label)} +${fmt(rel(start))} 至 +${fmt(rel(end))} 秒"></button>`;}
 let html='<div class="gantt-axis">'+[0,.25,.5,.75,1].map(f=>`<span style="left:${f*100}%">+${fmt(rel(lo+span*f),span<1?3:2)} s</span>`).join('')+'</div>';
 if(!zoomTools||!tools.length)html+=`<div class="gantt-row"><span class="gantt-name">第 ${model.step} 轮模型请求</span><div class="gantt-track">${bar(model,model.revealed_at,knownEnd,'model-bar')}</div></div>`;
 for(const t of tools){
  const start=t.tool_started_at!=null&&t.tool_started_at<=absolute()?t.tool_started_at:null,end=start!=null?Math.min(t.ended_at??absolute(),absolute()):null;
  html+=`<div class="gantt-row"><span class="gantt-name" title="${esc(t.arguments.file_path||t.label)}">${esc(t.arguments.file_path?.split('/').at(-1)||toolLabels[t.label]||t.label)}</span><div class="gantt-track">${bar(t,knownAt(t),start??absolute(),'wait-bar')}${start!=null?bar(t,start,end,''):''}</div></div>`;
 }
 $('gantt').innerHTML=html;$('gantt').querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>open(b.dataset.node));
 $('gantt-caption').textContent=`第 ${model.step} 轮 · ${tools.length} 个已提出工具 · 截至观察时刻重叠峰值 ${peak(tools,absolute())}。${zoomTools&&tools.length?'已按本轮真实工具区间放大，以横轴刻度为准。':'横轴包含本轮模型请求，工具时间可能非常短。'} 每行是一个调用，蓝色区间重叠才是实测在途重叠。`;
}
function render(){
 const at=absolute(),models=stepModels.filter(m=>m.revealed_at<=at),tools=graph.nodes.filter(n=>n.kind==='tool'&&knownAt(n)<=at);
 $('clock').textContent=`+${fmt(cursor,2)} s`;
 $('cursor-stats').textContent=`当时已知：${graph.nodes.filter(n=>n.kind==='agent'&&n.revealed_at<=at).length} 个 Agent · ${models.length} 次模型步骤 · ${tools.length} 个工具动作；已观察工具重叠峰值 ${peak(tools,at)}。`;
 renderGraph(models);renderEvents(models);
 const previous=selectedStep;if(!models.some(m=>m.id===selectedStep))selectedStep=models.at(-1)?.id??null;
 $('step-select').innerHTML=models.map(m=>`<option value="${esc(m.id)}">第 ${m.step} 轮${m.ended_at<=at?' · '+(stepTools.get(m.id)||[]).length+' 个工具':' · 模型仍在执行'}</option>`).join('');
 $('step-select').disabled=!models.length;if(selectedStep)$('step-select').value=selectedStep;
 $('zoom-tools').setAttribute('aria-pressed',String(zoomTools));renderGantt();
 if(selectedNode)renderDrawer();
}
async function select(id,updateHash=true){
 stop();close();const ticket=++version,s=index.cases.find(c=>c.case_id===id);
 try{
  const [g,t]=await Promise.all([json(base+s.paths.graph),json(base+s.paths.timeline)]);if(ticket!==version)return;
  current=s;graph=g;timeline=t;cursor=s.duration_seconds;stepModels=g.nodes.filter(n=>n.kind==='model').sort((a,b)=>a.revealed_at-b.revealed_at);modelByStep=new Map(stepModels.map(n=>[key(n),n]));stepTools=new Map(stepModels.map(m=>[m.id,g.nodes.filter(t=>t.kind==='tool'&&key(t)===key(m)).sort((a,b)=>a.revealed_at-b.revealed_at)]));
  selectedStep=[...stepModels].sort((a,b)=>peak(stepTools.get(b.id)||[])-peak(stepTools.get(a.id)||[])||(stepTools.get(b.id)||[]).length-(stepTools.get(a.id)||[]).length)[0].id;zoomTools=true;
  $('case-detail').hidden=false;$('timeline-panel').hidden=false;$('case-id').textContent=s.run_id+' · '+s.case_id;$('case-title').textContent=labels[id];$('case-purpose').textContent=purposes[id];$('initial-task').textContent=s.initial_task;$('provenance').textContent=s.provenance_cn;
  $('case-stats').innerHTML=[['实际 Agent 总数',s.agent_sessions],['模型调用 / 工具调用',`${s.model_calls} / ${s.tool_calls}`],['工具实际在途峰值',s.execution.peak_tool_dispatches],['本次观察耗时',fmt(s.duration_seconds,2)+' s']].map(([a,b])=>`<div class="stat"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
  $('agent-map').innerHTML=`<span>初始任务</span><b>→</b><span>根 Agent${s.child_sessions?'及'+s.child_sessions+'个子Agent':''} · ${s.model_calls} 次模型推理</span><span>${s.child_sessions?'子Agent创建见实际调用与时间戳':'实际没有创建子Agent'}</span>`;
  $('quality').textContent=s.result_cn;
  $('parallel-explanation').textContent=`本场景模型请求在途峰值 ${s.peak_outstanding_model_steps}；工具在途峰值 ${s.execution.peak_tool_dispatches}。${s.child_sessions?'存在子Agent，分别核对委派动作与孩子创建时间。':s.execution.peak_tool_dispatches>1?'并行发生在工具执行层；这些工具本身没有调用本地模型。':'本场景没有观察到工具重叠。'}这两种峰值不能混算为并行 Agent 数量。`;
  $('evidence-links').innerHTML=Object.entries(s.paths).map(([k,path])=>`<a href="${esc(base+path)}" target="_blank" rel="noopener">${esc({timeline:'原始完整时间戳',summary:'原始统计',raw:'完整证据包',input:'初始任务文件',graph:'原始模型与工具记录',answer:'最终输出',sources:'原题来源文件与哈希'}[k]||k)} ↗</a>`).join('');
  $('cursor').max=s.duration_seconds;$('cursor').value=cursor;
  $('cases').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.case===id));if(updateHash)history.replaceState(null,'','#'+id);render();
 }catch(error){$('overview').textContent='当前场景未加载，请刷新重试。';console.error(error);}
}
$('cursor').oninput=()=>{stop();cursor=Number($('cursor').value);render();};
$('play').onclick=()=>{if(timer){stop();return;}cursor=0;$('play').textContent='暂停';render();timer=setInterval(()=>{cursor=Math.min(current.duration_seconds,cursor+current.duration_seconds/90);$('cursor').value=cursor;render();if(cursor>=current.duration_seconds)stop();},300);};
$('step-select').onchange=e=>{selectedStep=e.target.value;renderGantt();};
$('zoom-tools').onclick=()=>{zoomTools=!zoomTools;$('zoom-tools').setAttribute('aria-pressed',String(zoomTools));renderGantt();};
$('close').onclick=close;$('backdrop').onclick=close;
document.addEventListener('keydown',e=>{if(e.key==='Escape')close();if(e.key==='Tab'&&!$('drawer').hidden){const nodes=[...$('drawer').querySelectorAll('button,summary')].filter(n=>n.getClientRects().length);if(e.shiftKey&&document.activeElement===nodes[0]){e.preventDefault();nodes.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===nodes.at(-1)){e.preventDefault();nodes[0].focus();}}});
new ResizeObserver(()=>requestAnimationFrame(drawWires)).observe($('graph'));
function showSource(source,preferred){
 selectedSource=source;const data=sourceSets[source];
 $('overview').textContent=source==='public'?'本轮直接把公开原题交给官方DSH，经vLLM调用Qwen27B；ODR、GPT Researcher、CRAG是结构参考，没有作为这批执行入口。6例只作初步观察，不报告总体准确率。':'旧五类观察：仅research含HotpotQA原题，其余为自编材料。与本轮公开原题分别保留。';
 $('summary').innerHTML=data.cases.map(s=>`<tr><td>${esc(labels[s.case_id])}</td><td>${s.agent_sessions}</td><td>${s.model_calls}</td><td>${s.tool_calls}</td><td>${s.execution.peak_tool_dispatches}</td><td>${fmt(s.duration_seconds,2)}</td><td>${esc(s.short_result_cn)}</td></tr>`).join('');
 $('cases').innerHTML=data.cases.map(s=>`<button type="button" data-case="${esc(s.case_id)}" aria-pressed="false">${esc(labels[s.case_id])}</button>`).join('');$('cases').querySelectorAll('button').forEach(b=>b.onclick=()=>select(b.dataset.case));
 $('observation-sources').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.source===source)));
 select(data.cases.some(s=>s.case_id===preferred)?preferred:source==='legacy'?'coding':data.cases[0].case_id,false);
}
Promise.all([json(base+'index.json'),json(base+'../public-tasks-20261030-v001/index.json')]).then(([data,publicData])=>{
 sourceSets={legacy:data,public:publicData};index={...data,cases:[...data.cases,...publicData.cases]};
 for(const s of publicData.cases){labels[s.case_id]=s.label;purposes[s.case_id]=s.purpose_cn;}
 $('failed-links').innerHTML=data.failed_attempts.map(s=>`<a href="${esc(base+s.summary)}" target="_blank" rel="noopener">${esc(labels[s.case_id])}首轮统计 ↗</a><a href="${esc(base+s.timeline)}" target="_blank" rel="noopener">首轮原始时间戳 ↗</a>`).join('');
 $('observation-sources').innerHTML='<button type="button" data-source="public">本轮 · 公开原题6例</button><button type="button" data-source="legacy">旧五类 · 来源分别标注</button>';
 $('observation-sources').querySelectorAll('button').forEach(b=>b.onclick=()=>showSource(b.dataset.source));
 const preferred=location.hash.slice(1),legacy=new URLSearchParams(location.search).get('source')==='legacy'||data.cases.some(s=>s.case_id===preferred);
 showSource(legacy?'legacy':'public',preferred);
}).catch(error=>{$('overview').textContent='观察数据未加载，请刷新重试。';console.error(error);});
