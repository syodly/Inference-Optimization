/* Native framework evidence viewer. Playback reads recorded files only. */
(()=>{'use strict';
const root='../experiments/dsh-engine/results/natural-dag-20261029/frameworks/';
const el=id=>document.getElementById(id), E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])), F=x=>Number(x).toFixed(2);
let index,run,cursor=0,timer=null,version=0,selected=null,returnFocus=null;
const backdrop=document.createElement('button');backdrop.className='backdrop fw-backdrop';backdrop.hidden=true;backdrop.setAttribute('aria-label','关闭原生轨迹详情');
const drawer=document.createElement('aside');drawer.className='drawer fw-drawer';drawer.hidden=true;drawer.setAttribute('role','dialog');drawer.setAttribute('aria-modal','true');drawer.setAttribute('aria-label','原生工作流节点详情');
document.body.append(backdrop,drawer);
function stop(){if(timer)clearInterval(timer);timer=null;if(el('fw-play'))el('fw-play').textContent='从头播放';}
function close(){drawer.hidden=true;backdrop.hidden=true;selected=null;returnFocus?.focus();}
backdrop.onclick=close;
document.addEventListener('keydown',e=>{if(drawer.hidden)return;if(e.key==='Escape')close();if(e.key==='Tab'){const a=[...drawer.querySelectorAll('button,a,summary')].filter(n=>n.getClientRects().length);if(e.shiftKey&&document.activeElement===a[0]){e.preventDefault();a.at(-1).focus();}else if(!e.shiftKey&&document.activeElement===a.at(-1)){e.preventDefault();a[0].focus();}}});
function raw(label,obj){return `<details><summary>${E(label)}</summary><pre>${E(JSON.stringify(obj,null,2))}</pre></details>`;}
function provenance(p,id,change){
 return `<div class="fw-provenance"><p class="eyebrow">任务与材料来源</p><dl class="kv"><dt>运行编号</dt><dd>${E(id)}</dd><dt>初始任务</dt><dd>${E(p.task_origin)}</dd><dt>数据集</dt><dd>${E(p.dataset||'无；这是自编诊断任务')}</dd><dt>输入材料</dt><dd>${E(p.input_origin)}</dd>${change?`<dt>本轮变化</dt><dd>${E(change)}</dd>`:''}</dl></div>`;
}
function sourceDetail(p){
 return (p.task_ids?`<details><summary>原始数据集题号、版本与哈希</summary><p>版本：${E(p.revision)}</p><p>tasks.jsonl SHA256：<code>${E(p.source_sha256)}</code></p><ol>${p.task_ids.map(id=>`<li><code>${E(id)}</code></li>`).join('')}</ol><a href="${E(p.source_url)}" target="_blank" rel="noopener">原始数据源 ↗</a><p>外层合并报告任务由本实验编写，不采用官方问答评分协议。</p></details>`:'')+
 (p.input_files?.length?`<details><summary>输入文件清单 · ${p.input_files.length} 项</summary><ul>${p.input_files.map(f=>`<li><code>${E(f)}</code></li>`).join('')}</ul></details>`:'');
}
function renderCatalogue(c){
 el('fw-coverage').innerHTML=`<p class="eyebrow">实验覆盖总览 · 次数不等于数据集数</p><h3>先确认做了什么、哪些还没有做</h3><p>ODR 的三个标签是同类诊断任务的变体与重跑，GPT 标签选取一次完整轨迹。两者的初始任务都由 Codex 编写，官方源码是检索语料；均未使用公开研究数据集原题。</p><div class="fw-coverage-grid">${c.framework_coverage.map(r=>`<article class="fw-coverage-card" data-coverage="${E(r.id)}"><h3>${E(r.framework)}</h3><p>${E(r.task_source)}</p><p><b>${E(r.attempts)}</b></p><p class="fw-dataset-count">${E(r.dataset_coverage)}</p><p>当前层次：${E(r.level)}</p><p class="fw-unfinished">未完成：${E(r.missing)}</p></article>`).join('')}</div>`;
 el('fw-coverage').insertAdjacentHTML('afterbegin',`<p class="notice">以下覆盖统计只针对此前机制诊断。本轮六道公开原题另用官方 DSH 执行，包含两道 LiveCodeBench；PopQA 两题不算 CRAG 算法复现。<a href="${E(c.latest_dsh_public_tasks.page_url)}">回到本轮原题结果 ↑</a></p>`);
 el('fw-audit').innerHTML=`<p>${E(index.audit_note)}</p><p>18 次是下面六类任务的策略对照与参数排查。每次只提交一个根任务，不是18个数据集。native 为原生策略；allow 放宽 workflow 条件；encourage 增加一般委派建议；autodelegate 增加拆分评估规则；Teams 切换工具面。推理强度以实际 API 流量为准。</p><div class="fw-group-list">${c.dsh_groups.map(g=>`<details class="fw-group" data-dsh-group="${E(g.id)}"><summary><span>${E(g.title)}</span><b>${g.count} 次尝试</b></summary><div class="inside"><p><b>排查问题：</b>${E(g.question)}</p><p><b>来源：</b>${E(g.source.label)}。${E(g.source.task_origin)}。</p><p class="muted">${E(g.source.input_origin)}。${E(g.source.unit)}。</p>${sourceDetail(g.source)}${c.dsh_runs.filter(r=>r.group===g.id).map(r=>{const s=r.summary;return `<details class="fw-run" data-dsh-run="${E(r.run_id)}"><summary><span>${E(s.label)}</span><small>${E(s.outcome)}</small></summary><div class="inside"><p class="fw-run-id">${E(r.run_id)}</p><p><b>本轮变量：</b>${E(r.experiment_change)}</p><p><b>实测：</b>${F(s.duration_seconds)} 秒 · ${s.model_requests} 次模型调用 · ${s.tool_calls} 次工具调用 · ${s.session_files} 个Session文件（含根）。</p><h4>提交给根 Agent 的初始任务全文</h4><div class="task fw-task">${E(r.initial_task)}</div>${sourceDetail({...r.provenance,task_ids:null})}${raw('配置与输入文件哈希（原spec）',r.spec)}<p class="muted">原包 ${E(r.raw_archive)} / <code>${E(r.raw_spec_member)}</code>。原始记录保留；目录编号与实际wire校正仅用于派生索引。</p></div></details>`;}).join('')}</div></details>`).join('')}</div><div class="links"><a href="${root}experiment-catalogue.json">统一实验索引 ↗</a><a href="../experiments/dsh-engine/evidence/autonomy-20261030-v002/index.json">18次原始证据索引 ↗</a></div>`;
 el('fw-attempts').innerHTML=`<p>7 次 ODR、5 次 GPT Researcher，包含初始化失败、截断、空报告及重跑。初始任务均由 Codex 编写，公开数据集均为零题；下列次数不表示独立样本数。运行完成也不保证报告事实全部正确。</p><div class="table-wrap"><table><thead><tr><th>运行 / 页面选例</th><th>材料来源与本轮变化</th><th>结果 / 模型请求</th></tr></thead><tbody>${c.upstream_runs.map(r=>`<tr data-upstream-run="${E(r.run_id)}"><td><code>${E(r.run_id)}</code>${r.display_id?`<p><button type="button" data-fw-example="${E(r.display_id)}">查看这次流程 ↗</button></p>`:''}</td><td><p>${E(r.provenance.input_origin)}</p><p>${E(r.experiment_change)}</p><details><summary>自编初始任务全文与配置</summary><div class="task fw-task">${E(r.initial_task)}</div>${raw('实际应用配置',r.config)}<p class="muted">${E(r.raw_archive)} / <code>${E(r.raw_spec_member)}</code></p></details></td><td>${E(r.outcome)}<p class="muted">${r.wire_requests} 次API请求</p></td></tr>`).join('')}</tbody></table></div>`;
 el('fw-attempts').querySelectorAll('[data-fw-example]').forEach(b=>b.onclick=()=>{choose(b.dataset.fwExample).then(()=>el('fw-tabs').scrollIntoView({behavior:'smooth',block:'start'}));});
 el('fw-archives').innerHTML=`<p>当前入口只有两个原始包。旧包是同批运行的较早快照；按 run_id 去重，不能加总为新实验。原始包、Prompt 和日志均保留。</p><div class="fw-archive-list">${c.archives.map(a=>`<div class="fw-archive"><span class="badge">${a.current?'当前入口':'旧快照'}</span><b>${E(a.id)}</b><p>${E(a.scope)}</p><div class="links"><a href="${E(a.index_url)}">包索引 ↗</a><a href="${E(a.url)}">原始包 ↗</a></div><details><summary>大小与SHA256</summary><p>${a.bytes} bytes</p><code>${E(a.sha256)}</code></details></div>`).join('')}</div><p class="muted">${E(c.legacy_evidence_note)}</p><h3>另列此前 E1，避免与自然委派排查混淆</h3><p>${E(c.historical_dataset_experiment.attempts)}；${E(c.historical_dataset_experiment.protocol)}。</p><div class="links"><a href="${E(c.historical_dataset_experiment.page_url)}">E1 原实验页面 ↗</a><a href="${E(c.historical_dataset_experiment.manifest_url)}">E1 数据集清单 ↗</a><a href="${root}experiment-catalogue.json">所有来源与逐次任务的统一索引 ↗</a></div>`;
}
function open(id){stop();el('close').click();returnFocus=document.activeElement;selected=id;drawer.hidden=false;backdrop.hidden=false;renderDrawer();drawer.querySelector('button').focus();}
function renderDrawer(){
 const n=run.nodes.find(n=>n.id===selected);if(!n||n.start>cursor){close();return;}
 const completed=n.end<=cursor;
 let html=`<button class="close" id="fw-close">关闭 ×</button><p class="eyebrow">${E(run.title)} · 原始执行</p><h2>${E(n.title)}</h2><p>${E(n.role)}</p><p class="fw-time-note">出现 +${F(n.start)} s · ${completed?'完成 +'+F(n.end)+' s':'观察时刻仍在途'} · ${E(new Date((run.started_wall_time+n.start)*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}))}</p>`;
 if(n.query)html+=`<h3>该节点收到的任务</h3><div class="readable">${E(n.query)}</div>`;
 html+=`<h3>前后关系</h3><p>${E(n.relation)}</p>`;
 const requests=run.requests.filter(r=>(n.request_ids||[]).includes(r.id)&&r.start<=cursor);
 html+=`<h3>此节点的实际模型调用 · ${requests.length} 次已开始</h3>`;
 if(!requests.length)html+='<p class="muted">这是任务创建或汇合边界；不把程序节点计为一次模型推理。</p>';
 for(const r of requests){
  const done=r.end<=cursor;
  html+=`<details class="fw-request"><summary>调用 ${E(r.ordinal)} · +${F(r.start)} s ${done?'→ +'+F(r.end)+' s':'· 在途'}</summary><p class="muted">${E(r.stage)} · HTTP ${done?E(r.http_status):'尚未知'} · ${done?E(r.finish_reason||'错误'):'响应未完成'}</p><h3>完整输入消息与 Prompt</h3>`;
  for(const m of r.request.messages||[])html+=`<div class="fw-detail-label">${E(m.role)}${m.name?' · '+E(m.name):''}</div><div class="fw-message">${E(typeof m.content==='string'?m.content:JSON.stringify(m.content,null,2))}</div>`+(m.tool_calls?raw('输入中携带的工具调用',m.tool_calls):'');
  if(done){
   html+='<h3>本次返回</h3><div class="readable">'+E(r.response.content||'无正文；请查看下方工具调用或错误。')+'</div>';
   for(const t of r.response.tool_calls||[])html+=`<div class="fw-tool"><b>${E(t.function?.name||t.name)}</b><div class="fw-message">${E(t.function?.arguments||JSON.stringify(t.args))}</div></div>`;
   if(r.response.reasoning)html+=`<details><summary>模型返回的 reasoning 字段</summary><div class="fw-message">${E(r.response.reasoning)}</div></details>`;
  }else html+='<p class="notice">响应尚未完整返回，不展示后续动作。</p>';
  html+=raw('全部请求参数与工具定义',r.request)+(done?raw('完整已解析响应与测量',{response:r.response,measurement:r.measurement}):'')+'</details>';
 }
 if(n.output&&completed)html+='<h3>节点结果</h3><div class="readable">'+E(n.output)+'</div>';
 html+=raw('本次运行的配置（含应用预算）',run.spec);
 drawer.innerHTML=html;el('fw-close').onclick=close;
}
function render(){
 if(!run)return;
 el('fw-clock').textContent='+'+F(cursor)+' s';
 const shown=run.nodes.filter(n=>n.start<=cursor),maxrow=Math.max(0,...run.nodes.map(n=>n.row));
 const narrow=el('fw-graph').clientWidth<650;
 const width=narrow?Math.max(260,el('fw-graph').clientWidth-24):780;
 const ordered=[...run.nodes].sort((a,b)=>a.row-b.row||(a.lane||0)-(b.lane||0));
 const height=narrow?ordered.length*154+20:(maxrow+1)*162+10;
 const pos=n=>({x:width/2+(narrow?0:(n.lane||0)*252)-109,y:narrow?ordered.findIndex(x=>x.id===n.id)*154+12:n.row*162+12});
 let svg=`<svg width="${width}" height="${height}" aria-hidden="true"><defs><marker id="fw-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#6c8d7a"/></marker></defs>`;
 for(const edge of run.edges){const a=shown.find(n=>n.id===edge.from),b=shown.find(n=>n.id===edge.to);if(!a||!b)continue;const p=pos(a),q=pos(b),x=p.x+109,y=p.y+116,xx=q.x+109,yy=q.y;let path=`M${x} ${y} C${x} ${y+22} ${xx} ${yy-22} ${xx} ${yy}`;if(narrow&&b.kind==='worker')path=`M${x} ${y} L${x} ${y+15} L10 ${y+15} L10 ${q.y+58} L${q.x} ${q.y+58}`;if(narrow&&a.kind==='worker')path=`M${p.x+218} ${p.y+58} L${width-10} ${p.y+58} L${width-10} ${yy-15} L${xx} ${yy-15} L${xx} ${yy}`;svg+=`<path d="${path}" fill="none" stroke="#6c8d7a" stroke-width="1.7" marker-end="url(#fw-arrow)"${edge.order?' stroke-dasharray="5 4"':''}/>`;}
 svg+='</svg>';
 const html=shown.map(n=>{const p=pos(n);return `<button class="fw-node ${E(n.kind||'')} ${n.end>cursor?'running':''}" data-fw-node="${E(n.id)}" style="left:${p.x}px;top:${p.y}px"><strong>${E(n.title)}</strong><small>+${F(n.start)} s ${n.end<=cursor?'→ +'+F(n.end)+' s':'· 进行中'}</small><small>${E(narrow&&n.kind==='worker'?'同批分支可并行 · 点击展开':n.caption||'点击查看任务、Prompt 与调用')}</small></button>`;}).join('');
 el('fw-graph').innerHTML=`<div class="fw-chart" style="width:${width}px;height:${height}px">${svg}${html||'<p class="fw-empty">推进时间轴，观察新工作何时产生。</p>'}</div>`;
 el('fw-graph').querySelectorAll('[data-fw-node]').forEach(b=>b.onclick=()=>open(b.dataset.fwNode));
 el('fw-progress').textContent=`当时已出现 ${shown.filter(n=>n.kind==='worker').length} 个子研究实例；${run.requests.filter(r=>r.start<=cursor).length} 次模型请求已开始。橙色边框表示仍在途；虚线箭头表示程序顺序约束。${narrow?'窄屏把同批卡片纵向列出，左右箭头仍表示分叉与汇合，不表示这些研究串行。':''}`;
 const end=run.duration_seconds;
 el('fw-gantt').innerHTML=`<div class="fw-axis"><span>0 s</span><span>${F(end/2)} s</span><span>${F(end)} s</span></div>`+run.nodes.filter(n=>n.kind==='worker'&&n.start<=cursor).map(n=>`<div class="fw-row"><span>${E(n.title)}</span><div class="fw-track"><button class="fw-bar" style="left:${n.start/end*100}%;width:${Math.max(.1,(Math.min(cursor,n.end)-n.start)/end*100)}%" data-fw-bar="${E(n.id)}" aria-label="${E(n.title)}的执行区间"></button><span style="left:${cursor/end*100}%"></span></div></div>`).join('');
 el('fw-gantt').querySelectorAll('[data-fw-bar]').forEach(b=>b.onclick=()=>open(b.dataset.fwBar));
 // Opening a drawer pauses playback. Resizing the graph must retain the
 // reader's expanded request cards and scroll position inside that drawer.
}
async function choose(id){
 stop();close();const v=++version;run=null;el('fw-body').dataset.loaded='';el('fw-body').innerHTML='<p class="muted">正在读取该轮真实记录…</p>';
 el('fw-tabs').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.fw===id));
 const meta=index.runs.find(r=>r.id===id);
 if(!meta){el('fw-body').innerHTML='<p>该证据尚未加入。</p>';return;}
 const data=await(await fetch(root+meta.path)).json();if(v!==version)return;run=data;cursor=run.duration_seconds;
 el('fw-body').innerHTML=`<h3>${E(run.title)}</h3><p><span class="badge">${E(run.status_label||run.report_finish_reason)}</span></p>${provenance(run.provenance,run.case_id||run.spec.run_id||index.catalogue.upstream_runs.find(r=>r.display_id===id).run_id,run.experiment_change)}<div class="fw-claim">${E(run.finding)}</div><p class="fw-scope">${E(run.scope)}</p><div class="stats">${run.stats.map(([a,b])=>`<div class="stat"><span>${E(a)}</span><b>${E(b)}</b></div>`).join('')}</div><details class="fold"><summary>自编初始任务原文与本次报告</summary><div class="inside"><div class="task">${E(run.query)}</div><p>${E(run.quality)}</p><div class="links">${run.links.map(([label,url])=>`<a href="${E(url)}" target="_blank" rel="noopener">${E(label)} ↗</a>`).join('')}</div></div></details><div class="controls"><button id="fw-play" type="button">从头播放</button><label>观察时刻<input id="fw-cursor" type="range" min="0" max="${run.duration_seconds}" step="0.001" value="${cursor}" aria-label="原生框架执行经过秒数"></label><output class="clock" id="fw-clock"></output></div><p class="muted" id="fw-progress"></p><div class="two"><div><h3>按实际执行展开的工作图</h3><div class="graph-wrap" id="fw-graph"></div></div><div><h3>子研究的真实执行区间</h3><p class="muted">每条横条是一个有独立状态的研究实例，里面可能有多次模型与工具调用。区间重叠不等于 GPU 内核同时运行。</p><div id="fw-gantt"></div><div class="focus-line">${E(run.design_implication)}</div><div class="links"><a href="${E(run.data_url)}" target="_blank" rel="noopener">完整结构化记录 ↗</a></div></div></div>`;
 el('fw-cursor').oninput=()=>{stop();cursor=Number(el('fw-cursor').value);render();};
 el('fw-play').onclick=()=>{if(timer){stop();return;}cursor=0;render();el('fw-play').textContent='暂停';timer=setInterval(()=>{cursor=Math.min(run.duration_seconds,cursor+run.duration_seconds/110);el('fw-cursor').value=cursor;render();if(cursor>=run.duration_seconds)stop();},250);};render();el('fw-body').dataset.loaded=id;
}
fetch(root+'index.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();}).then(async data=>{
 index=data;const response=await fetch(root+data.catalogue_path,{cache:'no-cache'});if(!response.ok)throw Error('catalogue HTTP '+response.status);index.catalogue=await response.json();renderCatalogue(index.catalogue);
 el('fw-tabs').innerHTML=data.runs.map(r=>`<button type="button" data-fw="${E(r.id)}" aria-pressed="false">${E(r.label)}</button>`).join('');el('fw-tabs').querySelectorAll('button').forEach(b=>b.onclick=()=>choose(b.dataset.fw));
 const wanted=new URLSearchParams(location.search).get('framework');return choose(data.runs.some(r=>r.id===wanted)?wanted:data.runs[0].id);
}).catch(error=>{el('fw-body').textContent='证据加载失败：'+error.message;console.error(error);});
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,80);});
})();
