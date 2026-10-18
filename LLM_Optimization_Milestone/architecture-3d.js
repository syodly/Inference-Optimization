const layerInfo = {
  workflow: {
    title:'06 · Agent 工作流与上下文',
    copy:'表达任务依赖、Agent 角色、工具与上下文操作，决定质量目标、模型选择和内容生命周期。Parrot、NALAR 等把应用结构交给执行系统；Akashic 管理语义记忆，MemTrace 管理环境证据，二者都不等同于 KV 数值复用。',
    representatives:[20,53,46]
  },
  orchestration: {
    title:'05 · 编排与调度',
    copy:'决定哪个程序、阶段和请求先推进，何时准入、暂停或恢复，以及工具等待期间如何保留状态。KVFlow、CacheWise、Continuum 等联合使用工作流信息与 KV 成本；具体缓存内容和有效性仍由数据面处理。',
    representatives:[23,45,28]
  },
  engine: {
    title:'04 · 推理引擎执行',
    copy:'将请求变成 Prefill、Decode、动态批次和 GPU 执行。Orca 改变批处理粒度，Sarathi-Serve 组织混合批次，PagedAttention 提供分页状态映射，TokenRouter 协调多个常驻模型的逐 token 执行。',
    representatives:[11,19,62]
  },
  kv: {
    title:'03 · KV Cache 数据面',
    copy:'管理历史状态的复用、修复、压缩、分层和淘汰。CacheBlend 处理独立文档 KV 的融合，Leyline 处理编辑指令，Strata 处理分层数据与 I/O。精确前缀、有损修复和语义记忆具有不同的复用条件。',
    representatives:[41,61,48]
  },
  compute: {
    title:'02 · 模型计算与算子',
    copy:'改变一次模型执行的计算和访存路径。FlashAttention 优化 Attention 的 IO，投机解码用候选与并行验证减少串行大模型步骤，Medusa 和多 token 预测进一步改变候选生成方式。',
    representatives:[2,4,6]
  },
  infra: {
    title:'01 · 集群与硬件资源',
    copy:'管理 GPU、显存、CPU、存储和网络所构成的资源底座。MuxServe 研究多模型共享资源，Cortex 研究阶段资源池，Nuska 研究 KV 通信调度；这里侧重软硬件资源协同，并不表示这些论文设计了新 GPU。',
    representatives:[21,31,58]
  },
  control: {
    title:'HEAR · 横向 Codesign 控制面',
    copy:'工作流侧提供意图与控制，引擎侧返回状态能力与真实结果，策略再据此改变调度、缓存或执行配置。HEAR 统一双方交互契约，贯穿多个层次；图中各层的协同方法可通过跨层关联查看。',
    representatives:[60]
  },
  overview: {
    title:'整体综述',
    copy:'提供推理优化技术谱系，作为六层结构的阅读入口。',
    representatives:[1]
  }
};
const paperRows = new Map(PAPERS.map(row => [Number(row[0]), row]));
const catalog = new Map(ARCHITECTURE_CATALOG.map(p => [p.id, p]));
const groupOrder = ['workflow','orchestration','engine','kv','compute','infra','control','overview'];
const zones = [...document.querySelectorAll('.system-figure [data-layer]')];
const ns = 'http://www.w3.org/2000/svg';
const floorBase = {workflow:205,orchestration:416,engine:627,kv:838,compute:1049,infra:1260};
const statusLabels = {done:'已整理',partial:'摘要 · 待精读',todo:'待整理'};
let selected = 'kv';

function members(key) { return ARCHITECTURE_CATALOG.filter(p => p.home === key); }
function shortLayer(key) { return layerInfo[key].title.replace(/^\d+ · /,'').replace('HEAR · 横向 Codesign 控制面','跨层控制面'); }
function makeLink(p, className='paper-link') {
  const a = document.createElement('a');
  a.className = className; a.href = p.href;
  a.target = '_blank'; a.rel = 'noopener';
  a.textContent = p.short + ' ↗';
  a.title = paperRows.get(p.id)[1]; a.dataset.paperId = String(p.id);
  return a;
}
function selectLayer(key) {
  const item = layerInfo[key];
  if (!item) return;
  selected = key;
  zones.forEach(zone => {
    const on = zone.dataset.layer === key;
    zone.classList.toggle('is-selected', on);
    zone.setAttribute('aria-pressed', String(on));
  });
  document.querySelectorAll('[data-select-layer]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.selectLayer === key)));
  document.querySelectorAll('[data-layer-papers]').forEach(node => node.classList.toggle('is-selected', node.dataset.layerPapers === key));
  document.getElementById('detail-title').textContent = item.title;
  document.getElementById('detail-copy').textContent = item.copy;
  document.getElementById('current-component').textContent = item.title;
  const links = document.getElementById('detail-links');
  links.replaceChildren(...members(key).map(p => makeLink(p, 'detail-link')));
  const jump = document.createElement('a');
  jump.href = '#library-' + key; jump.className = 'index-jump';
  jump.textContent = '查看该层 ' + members(key).length + ' 篇归档 ↓';
  links.append(jump);
}
function svgNode(tag,attrs={},text='') {
  const n = document.createElementNS(ns,tag);
  for (const [k,v] of Object.entries(attrs)) n.setAttribute(k,v);
  if (text) n.textContent = text;
  return n;
}
function buildFigureLinks() {
  document.querySelectorAll('[data-layer-papers]').forEach(group => {
    const key = group.dataset.layerPapers;
    const ids = layerInfo[key].representatives;
    const base = floorBase[key];
    ids.forEach((id,i) => {
      const p = catalog.get(id);
      const x = key === 'control' ? 1218 : 350 + i * 235;
      const y = key === 'control' ? 764 : base + 42;
      const a = svgNode('a',{href:p.href,target:'_blank',rel:'noopener','data-paper-id':id,class:'figure-paper','aria-label':paperRows.get(id)[1]+'，打开阅读'});
      a.append(svgNode('title',{},paperRows.get(id)[1]));
      a.append(svgNode('rect',{x:x-7,y:y-23,width:key==='control'?157:220,height:37,rx:5,class:'paper-link-hit'}));
      a.append(svgNode('text',{x,y,class:'figure-paper-name'},p.short+' ↗'));
      group.append(a);
    });
    if (base) {
      const a = svgNode('a',{href:'#library-'+key,class:'figure-all','aria-label':'查看'+shortLayer(key)+'全部论文'});
      a.append(svgNode('rect',{x:1060,y:base+16,width:104,height:40,rx:5,fill:'transparent'}));
      a.append(svgNode('text',{x:1064,y:base+42},members(key).length+' 篇 ↓'));
      group.append(a);
    }
  });
}
function buildNavigation() {
  const nav = document.getElementById('component-nav');
  groupOrder.filter(key=>key!=='overview').forEach(key => {
    const button = document.createElement('button');
    button.type = 'button'; button.dataset.selectLayer = key;
    button.textContent = key==='control'?'HEAR 跨层':layerInfo[key].title.replace(' · ',' ');
    button.addEventListener('click',()=>selectLayer(key)); nav.append(button);
  });
}
function buildLibrary() {
  const root = document.getElementById('library-groups');
  for (const key of groupOrder) {
    const section = document.createElement('section');
    section.className = 'library-group'; section.id = 'library-'+key;
    const header = document.createElement('div'); header.className='group-heading';
    const heading=document.createElement('h3'); heading.textContent=layerInfo[key].title;
    const count=document.createElement('span'); count.className='group-count';count.textContent=members(key).length+' 篇';
    header.append(heading,count);section.append(header);
    const grid=document.createElement('div');grid.className='paper-grid';
    for (const p of members(key)) {
      const row=paperRows.get(p.id);
      const entry=document.createElement('article');entry.className='paper-entry';entry.dataset.paperEntry=p.id;
      const number=document.createElement('span');number.className='paper-id';number.textContent=String(p.id).padStart(2,'0');
      const body=document.createElement('div');body.className='paper-body';
      const top=document.createElement('div');top.className='paper-heading';top.append(makeLink(p));
      const status=document.createElement('span');status.className='paper-status status-'+row[5];status.textContent=statusLabels[row[5]];top.append(status);
      const mechanism=document.createElement('p');mechanism.className='paper-mechanism';mechanism.textContent=p.mechanism;
      const cross=document.createElement('div');cross.className='cross-links';
      const crossLabel=document.createElement('span');crossLabel.textContent='关联 ';cross.append(crossLabel);
      p.cross.forEach((layer,i)=>{
        const a=document.createElement('a');a.href='#library-'+layer;a.textContent=shortLayer(layer);cross.append(a);
        if(i<p.cross.length-1)cross.append(document.createTextNode(' / '));
      });
      body.append(top,mechanism,cross);entry.append(number,body);grid.append(entry);
    }
    section.append(grid);root.append(section);
  }
}
function setupInteraction() {
  for (const zone of zones) {
    zone.addEventListener('click',()=>selectLayer(zone.dataset.layer));
    zone.addEventListener('keydown',event=>{
      if(event.key==='Enter'||event.key===' '){event.preventDefault();selectLayer(zone.dataset.layer);}
    });
  }
  document.getElementById('reset-view').addEventListener('click',()=>selectLayer('kv'));
  const panel=document.getElementById('cutaway');
  const expand=document.getElementById('expand-view');
  expand.addEventListener('click',async()=>{
    try {
      if(document.fullscreenElement)await document.exitFullscreen();
      else if(panel.requestFullscreen)await panel.requestFullscreen();
      else panel.classList.toggle('is-expanded');
    }catch{panel.classList.toggle('is-expanded');}
    if(!document.fullscreenElement)expand.textContent=panel.classList.contains('is-expanded')?'退出大图':'全屏查看';
  });
  document.addEventListener('fullscreenchange',()=>{expand.textContent=document.fullscreenElement?'退出全屏':'全屏查看';});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){panel.classList.remove('is-expanded');if(!document.fullscreenElement)expand.textContent='全屏查看';}});
}
buildFigureLinks();
buildNavigation();
buildLibrary();
setupInteraction();
selectLayer(location.hash.startsWith('#layer-')?location.hash.slice(7):selected);
