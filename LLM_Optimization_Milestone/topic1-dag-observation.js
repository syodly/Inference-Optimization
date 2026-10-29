/* Read-only visualization of newly executed native DSH event logs. */
const base='../experiments/dsh-engine/results/natural-dag-20261029/';
const $=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(x,n=2)=>Number(x).toFixed(n),labels={simple:'简单问答',research:'多文档调查',coding:'代码修复',analysis:'CSV 数据分析',incident:'故障诊断'};
let index,current,graph,timeline,cursor=0,version=0,timer=null,lastFocus=null;
const json=async p=>{const r=await fetch(p,{cache:'no-cache'});if(!r.ok)throw Error(`${r.status} ${p}`);return r.json();};
const details=(title,value)=>`<details><summary>${esc(title)}</summary><pre>${esc(typeof value==='string'?value:JSON.stringify(value,null,2))}</pre></details>`;
function stop(){clearInterval(timer);timer=null;$('play').textContent='从头播放';}
function close(){ $('drawer').hidden=true;$('backdrop').hidden=true;document.body.style.overflow='';if(lastFocus?.isConnected)lastFocus.focus(); }
function open(id){
 const n=graph.nodes.find(n=>n.id===id);if(!n)return;lastFocus=document.activeElement;
 const complete=n.ended_at&&n.ended_at<=cursor+current.started_wall_time;
 let html=`<p class="eyebrow">${esc(n.kind)} · 实测节点</p><h2>${esc(n.label)}</h2><p>进入图：+${fmt(n.revealed_at-current.started_wall_time,3)} 秒${complete?` · 完成：+${fmt(n.ended_at-current.started_wall_time,3)} 秒`:n.ended_at?' · 观察时刻仍未完成':''}</p>`;
 if(n.kind==='model'){
  const params={...n.request};delete params.messages;
  html+='<p>这是同一Session的一次真实模型请求。模型根据当前历史决定文字输出与工具调用；后续工具在完整调用提交后才成为可执行工作。</p>';
  html+=details('完整 Prompt · 实际 messages',n.request.messages)+details('采样参数与工具定义',params);
  html+=complete?details('模型实际返回',n.response)+details('接口测量与 token', {usage:n.usage,finish:n.finish,metadata:n.metadata}):'<p class="notice">此刻响应尚未完整提交；拖动到完成后可查看实际返回。</p>';
 }else if(n.kind==='tool'){
  html+='<p>工具由前一次模型响应提出，DSH在校验后执行。结果返回同一Session后，模型才决定接下来做什么。图中没有预设这一步。</p>';
  html+=details('模型生成的完整工具参数',n.arguments)+(complete?details('工具实际结果',n.committed_result||n.result):'<p class="notice">此刻工具尚未完成，结果还不可见。</p>')+details('真实执行时间', {committed:n.revealed_at,started:n.tool_started_at<=cursor+current.started_wall_time?n.tool_started_at:null,ended:complete?n.ended_at:null});
 }else html+=details('原始记录',n);
 $('drawer-content').innerHTML=html;$('drawer').hidden=false;$('backdrop').hidden=false;document.body.style.overflow='hidden';$('close').focus();
}
function node(n){
 const active=n.ended_at&&n.ended_at>cursor+current.started_wall_time;
 const tool=n.kind==='tool';
 const desc=tool?(n.arguments.file_path?.split('/').at(-1)||n.arguments.description||n.arguments.command?.slice(0,70)||'展开参数和结果'):`+${fmt(n.revealed_at-current.started_wall_time)}s → ${!active&&n.ended_at?fmt(n.ended_at-current.started_wall_time)+'s':'尚未完成'}`;
 return `<button class="${tool?'tool':'model'} ${active?'active':''}" data-node="${esc(n.id)}"><small>${tool?'TOOL · 工具':'QWEN · 模型调用'}${active?' · 正在执行':''}</small><strong>${esc(tool?n.label:`第 ${n.step} 步 · 模型决定下一步`)}</strong><small>${esc(desc)}</small></button>`;
}
function render(){
 const at=current.started_wall_time+cursor,visible=graph.nodes.filter(n=>n.revealed_at<=at),known=new Set(visible.map(n=>n.id));
 const models=visible.filter(n=>n.kind==='model').sort((a,b)=>a.revealed_at-b.revealed_at),tools=visible.filter(n=>n.kind==='tool');
 $('clock').textContent=`+${fmt(cursor)} s`;
 $('cursor-stats').textContent=`当时已生成：${visible.filter(n=>n.kind==='agent').length} 个Agent · ${models.length} 次模型步骤 · ${tools.length} 次工具调用 · ${graph.edges.filter(e=>e.revealed_at<=at&&known.has(e.source)&&known.has(e.target)).length} 条依赖。`;
 let html='<div class="model"><small>USER · 初始任务</small><strong>用户提交任务</strong><small>没有预置图或Agent数量</small></div>';
 if(!models.length)html+='<div class="empty">尚未发起第一次模型请求</div>';
 for(const m of models){
  html+='<div class="join" aria-label="依赖箭头">↓</div>'+node(m);
  const children=tools.filter(t=>t.session_id===m.session_id&&t.turn===m.turn&&t.step===m.step);
  if(children.length)html+=`<p class="tools-caption">↓ 本步已提出 ${children.length} 个工具调用 · 并排展示不表示同时执行 ↓</p><div class="tools">${children.map(node).join('')}</div>`;
 }
 $('graph').innerHTML=html;$('graph').querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>open(b.dataset.node));
 const names={tool_name_first_observed:'流中首次出现工具名',tool_execution_started:'Harness开始执行工具',child_published:'Harness创建子Agent','subagent/start':'子Agent开始','subagent/end':'子Agent结束'};
 const events=timeline.filter(e=>e.time<=at&&(['tool_name_first_observed','tool_execution_started','child_published','subagent/start','subagent/end'].includes(e.kind)||(['node_added','node_completed'].includes(e.kind)&&/^(model|tool):/.test(e.node_id))));
 $('events').innerHTML=events.slice().reverse().map(e=>`<li><time>+${fmt(e.relative_seconds,3)}s</time><span>${esc(e.kind==='node_added'?(e.node_id.startsWith('model:')?'模型请求就绪':'Harness接收完整工具调用'):e.kind==='node_completed'?(e.node_id.startsWith('model:')?'模型响应提交完成':'工具执行完成'):names[e.kind]||e.kind)}${e.tool||e.node_id?.startsWith('tool:')?` · ${esc(e.tool||e.label)}`:''}<small>${esc(e.timestamp_china)}</small></span></li>`).join('')||'<li>尚无模型或工具事件。</li>';
}
async function select(id){
 stop();close();const ticket=++version,s=index.cases.find(c=>c.case_id===id);
 try{
  const [g,t]=await Promise.all([json(base+s.paths.graph),json(base+s.paths.timeline)]);if(ticket!==version)return;
  current=s;graph=g;timeline=t;cursor=s.duration_seconds;
  $('case-detail').hidden=false;$('timeline-panel').hidden=false;$('case-id').textContent=s.run_id+' · '+s.case_id;$('case-title').textContent=labels[id];$('initial-task').textContent=s.initial_task;$('provenance').textContent=s.provenance_cn;
  $('case-stats').innerHTML=[['实际Agent总数',s.agent_sessions],['模型调用',s.model_calls],['工具调用',s.tool_calls],['完整任务耗时',fmt(s.duration_seconds)+' s']].map(([a,b])=>`<div class="stat"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join('');
  $('agent-map').innerHTML=`<span>用户任务</span><b>→</b><span>根 Agent · ${s.model_calls} 次模型调用</span>${s.child_sessions?`<b>→</b><span>${s.child_sessions} 个子Agent</span>`:'<span>实际没有创建子Agent</span>'}`;
  $('quality').textContent=s.result_cn;
  $('evidence-links').innerHTML=Object.entries(s.paths).filter(([k])=>k!=='graph').map(([key,path])=>`<a href="${esc(base+path)}" target="_blank" rel="noopener">${esc({timeline:'完整时间戳',summary:'实测统计与逐步记录',raw:'全部原始证据',input:'初始任务'}[key]||key)} ↗</a>`).join('');
  $('cursor').max=s.duration_seconds;$('cursor').value=cursor;
  $('cases').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.case===id));
  history.replaceState(null,'','#'+id);render();
 }catch(error){$('overview').textContent='当前场景未加载，请刷新重试。';console.error(error);}
}
$('cursor').oninput=()=>{stop();cursor=Number($('cursor').value);render();};
$('play').onclick=()=>{if(timer){stop();return;}cursor=0;$('play').textContent='暂停';render();timer=setInterval(()=>{cursor=Math.min(current.duration_seconds,cursor+current.duration_seconds/90);$('cursor').value=cursor;render();if(cursor>=current.duration_seconds)stop();},300);};
$('close').onclick=close;$('backdrop').onclick=close;document.addEventListener('keydown',e=>{if(e.key==='Escape')close();if(e.key==='Tab'&&!$('drawer').hidden){const nodes=[...$('drawer').querySelectorAll('button,summary')];if(e.shiftKey&&document.activeElement===nodes[0]){e.preventDefault();nodes.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===nodes.at(-1)){e.preventDefault();nodes[0].focus();}}});
json(base+'index.json').then(data=>{
 index=data;$('overview').textContent=data.conclusion;
 $('failed-links').innerHTML=data.failed_attempts.map(s=>`<a href="${esc(base+s.summary)}" target="_blank" rel="noopener">${esc(labels[s.case_id])}首轮 · 未完成统计 ↗</a><a href="${esc(base+s.timeline)}" target="_blank" rel="noopener">原始时间戳 ↗</a>`).join('');
 $('summary').innerHTML=data.cases.map(s=>`<tr><td>${esc(labels[s.case_id])}</td><td>${s.agent_sessions}</td><td>${s.model_calls}</td><td>${s.tool_calls}</td><td>${fmt(s.duration_seconds)}</td><td>${esc(s.short_result_cn)}</td></tr>`).join('');
 $('cases').innerHTML=data.cases.map(s=>`<button type="button" data-case="${esc(s.case_id)}" aria-pressed="false">${esc(labels[s.case_id])}</button>`).join('');
 $('cases').querySelectorAll('button').forEach(b=>b.onclick=()=>select(b.dataset.case));
 select(data.cases.some(s=>s.case_id===location.hash.slice(1))?location.hash.slice(1):'coding');
}).catch(error=>{$('overview').textContent='观察数据未加载，请刷新重试。';console.error(error);});
