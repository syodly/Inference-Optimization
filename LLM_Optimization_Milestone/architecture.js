const nodes = {
  harness: {title:'Agent 工作流 / Harness', copy:'应用层掌握任务依赖、Agent 角色、工具调用、上下文生命周期和未来复用意图。它决定任务如何展开，底层驻留与资源压力需要引擎反馈。', links:[['Parrot','20'],['NALAR','53'],['Murakkab','47'],['Helium','49']]},
  scheduler: {title:'工作流调度', copy:'把动态程序、阶段状态和关键路径转化为准入、优先级、并发与恢复决策。这里关注整个 workflow 的完成时间，以及工具等待期间如何安排缓存和计算。', links:[['KVFlow','23'],['Astraea','52'],['SAGA','55'],['TOPAS','56'],['CONCUR','28'],['Pythia','38']]},
  application: {title:'L1 · 应用 / 工作流层', copy:'表达请求依赖、工具执行、分支、重试、上下文编辑和质量目标。这里的前端指 Agent Harness 与工作流编程接口。工作流提供优化所需的语义与约束。', links:[['Parrot','20'],['NALAR','53'],['Murakkab','47'],['Helium','49'],['Akashic','46'],['Agentic Context Engineering','32']]},
  schedule: {title:'L2 · 编排与调度层', copy:'决定哪个 workflow、哪个阶段、哪个请求先推进，以及显存压力下是否准入、暂停、抢占或恢复。这些决策可以发生在编排侧，也可以由引擎执行；二者需要明确边界。', links:[['Orca','11'],['KVFlow','23'],['Astraea','52'],['SAGA','55'],['TOPAS','56']]},
  engine: {title:'L3 · 推理引擎执行层', copy:'将请求组织成 Prefill、Decode、Batch 与 GPU 执行。Continuous Batching、Chunked Prefill、PagedAttention 和 Prefill/Decode 分离在这里落地，与 KV 管理和集群放置共同决定性能。', links:[['Orca','11'],['vLLM PagedAttention','19'],['Sarathi-Serve','15'],['DistServe','18'],['TokenRouter','62']]},
  kv: {title:'L4 · KV Cache 数据面', copy:'管理历史状态的复用、修复、保留、淘汰、压缩与分层存储。精确前缀和独立块的复用条件不同；版本标识不能代替有效性判断。KV 是横跨引擎与存储的数据面，图中的层次按主要优化对象组织。', links:[['CacheBlend','41'],['ContextPilot','43'],['CacheWise','45'],['PBKV','https://arxiv.org/abs/2605.06472'],['Strata','48'],['Leyline','61'],['PatchKV','https://arxiv.org/abs/2609.26219']]},
  compute: {title:'L5 · 模型计算与算子层', copy:'针对单次模型执行减少算力与访存开销，包括 Attention kernel、投机解码、多 token 预测和量化。它直接改变计算路径，与 KV 复用属于不同的优化维度。', links:[['FlashAttention','https://arxiv.org/abs/2205.14135'],['Speculative Decoding','https://arxiv.org/abs/2211.17192'],['Medusa','https://arxiv.org/abs/2401.10774'],['SpecInfer','https://arxiv.org/abs/2305.09781']]},
  system: {title:'L6 · 集群 / I/O / 硬件层', copy:'处理 GPU 与节点放置、网络、CPU/SSD I/O、通信重叠和资源隔离。缓存带来的计算节省必须覆盖构建与搬运成本，因此需要把缓存决策与资源执行共同评估。', links:[['MuxServe','21'],['Cortex','57'],['Nuska','58'],['Strata','48']]},
  hear: {title:'HEAR · Codesign 控制面', copy:'Harness 向引擎传递工作流意图与执行控制；引擎返回状态能力与执行结果。策略结合两侧信息调整调度、缓存或执行配置。HEAR 定义交互契约，具体优化策略另行实现。', links:[['HEAR 精读','60'],['研究进展','research-update-20261014.html']]},
  context: {title:'上下文状态与版本', copy:'追加、替换、删除、摘要压缩和分支回退会改变 KV 的有效范围。跨层接口需要传递编辑语义、版本和生命周期；引擎仍需判断哪些状态可以精确继承，哪些需要修复或重算。', links:[['Leyline','61'],['PatchKV','https://arxiv.org/abs/2609.26219'],['Retire','https://arxiv.org/abs/2610.01160']]}
};
const allNodes = [...document.querySelectorAll('[data-node]')];
const filters = [...document.querySelectorAll('.filter')];
const stage = document.getElementById('map-stage');
const connections = [
  ['harness','application','workflow'], ['scheduler','schedule','workflow'],
  ['hear','schedule','codesign'], ['hear','engine','codesign'],
  ['context','kv','codesign']
];
const targetMap = {
  '18': 'https://arxiv.org/abs/2401.09651',
  '19': 'https://arxiv.org/abs/2309.06180'
};
let activeFilter = 'all';
let selected = 'hear';
function selectNode(id) {
  const item = nodes[id];
  if (!item) return;
  selected = id;
  allNodes.forEach(node => {
    const match = node.dataset.node === id;
    node.classList.toggle('is-selected', match);
    node.setAttribute('aria-pressed', String(match));
  });
  document.getElementById('detail-title').textContent = item.title;
  document.getElementById('detail-copy').textContent = item.copy;
  const links = document.getElementById('detail-links');
  links.replaceChildren(...item.links.map(([label, target]) => {
    const link = document.createElement('a');
    link.href = /^\d+$/.test(target) ? (targetMap[target] || 'papers/paper-' + target + '.html') : target;
    link.textContent = label + ' ↗';
    link.target = '_blank'; link.rel = 'noopener';
    return link;
  }));
  document.getElementById('selection-summary').textContent = item.title;
  document.getElementById('dock-title').textContent = item.title;
  document.querySelectorAll('[data-edge]').forEach(path =>
    path.classList.toggle('edge-selected', path.dataset.edge.split(':').includes(id)));
}
function applyFilter(filter) {
  activeFilter = filter;
  filters.forEach(button => {
    const match = button.dataset.filter === filter;
    button.classList.toggle('is-active', match);
    button.setAttribute('aria-pressed', String(match));
  });
  allNodes.forEach(node => node.classList.toggle('is-dim',
    filter !== 'all' && !node.dataset.groups.split(',').includes(filter)));
  document.querySelectorAll('[data-edge]').forEach(path => {
    const endpoints = path.dataset.edge.split(':');
    path.classList.toggle('edge-dim', filter !== 'all' && !endpoints.every(id =>
      document.querySelector('[data-node="' + id + '"]').dataset.groups.split(',').includes(filter)));
  });
}
function drawConnections() {
  const svg = document.querySelector('.map-lines');
  const group = document.getElementById('connection-paths');
  if (!stage.clientWidth || getComputedStyle(svg).display === 'none') return;
  const box = stage.getBoundingClientRect();
  svg.setAttribute('viewBox', '0 0 ' + box.width + ' ' + box.height);
  group.replaceChildren(...connections.map(([from, to, kind]) => {
    const a = document.querySelector('[data-node="' + from + '"]').getBoundingClientRect();
    const b = document.querySelector('[data-node="' + to + '"]').getBoundingClientRect();
    const left = a.left < b.left;
    const x1 = (left ? a.right : a.left) - box.left;
    const x2 = (left ? b.left : b.right) - box.left;
    const y1 = a.top + a.height / 2 - box.top;
    const y2 = b.top + b.height / 2 - box.top;
    const mid = (x1 + x2) / 2;
    const path = document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d', 'M' + x1 + ',' + y1 + ' C' + mid + ',' + y1 + ' ' + mid + ',' + y2 + ' ' + x2 + ',' + y2);
    path.setAttribute('class','flow-line edge-' + kind);
    path.dataset.edge = from + ':' + to;
    return path;
  }));
  applyFilter(activeFilter);
  selectNode(selected);
}
allNodes.forEach(node => node.addEventListener('click', () => selectNode(node.dataset.node)));
filters.forEach(button => button.addEventListener('click', () => applyFilter(button.dataset.filter)));
document.getElementById('reset-view').addEventListener('click', () => {applyFilter('all'); selectNode('hear');});
document.getElementById('expand-view').addEventListener('click', async () => {
  const panel = document.querySelector('.map-wrap');
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await panel.requestFullscreen();
  } catch { panel.classList.toggle('is-expanded'); }
});
document.addEventListener('fullscreenchange', () => {
  document.getElementById('expand-view').textContent = document.fullscreenElement ? '退出全屏' : '全屏探索';
  drawConnections();
});
new ResizeObserver(drawConnections).observe(stage);
document.fonts.ready.then(drawConnections);
selectNode('hear'); applyFilter('all');
