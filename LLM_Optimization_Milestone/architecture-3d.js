const nodeData = {
  application: {title:'L1 · 应用 / 工作流层',copy:'表达请求依赖、工具执行、分支、重试、上下文编辑和质量目标。工作流提供优化所需的语义与约束。',links:[['Parrot','20'],['NALAR','53'],['Murakkab','47']]},
  schedule: {title:'L2 · 编排与调度层',copy:'决定哪个 workflow、哪个阶段、哪个请求先推进，以及显存压力下是否准入、暂停、抢占或恢复。',links:[['KVFlow','23'],['SAGA','55'],['TOPAS','56']]},
  engine: {title:'L3 · 推理引擎执行层',copy:'将请求组织成 Prefill、Decode、Batch 与 GPU 执行。Continuous Batching、Chunked Prefill 和 PagedAttention 在这里落地。',links:[['vLLM PagedAttention','19'],['Sarathi-Serve','15'],['Akashic','46']]},
  kv: {title:'L4 · KV Cache 数据面',copy:'管理历史状态的复用、修复、保留、淘汰、压缩与分层存储。它横跨引擎与存储，命中率需要结合构建、搬运和重算成本判断。',links:[['CacheBlend','41'],['CacheWise','45'],['Leyline','61'],['PBKV','https://arxiv.org/abs/2605.06472']]},
  compute: {title:'L5 · 模型计算与算子层',copy:'针对单次模型执行减少算力与访存开销，包括 Attention kernel、投机解码、多 token 预测和量化。',links:[['FlashAttention','https://arxiv.org/abs/2205.14135'],['Medusa','https://arxiv.org/abs/2401.10774'],['SpecInfer','https://arxiv.org/abs/2305.09781']]},
  system: {title:'L6 · 集群 / I/O / 硬件层',copy:'处理 GPU 与节点放置、网络、CPU/SSD I/O、通信重叠和资源隔离。缓存收益必须覆盖构建与搬运成本。',links:[['MuxServe','21'],['Cortex','57'],['FlowMesh','54']]},
  harness: {title:'Agent Harness · 工作流意图',copy:'Harness 了解会话、角色、工具和上下文生命周期，却看不到引擎实时驻留与压力。它提供跨层优化需要的应用语义。',links:[['Parrot','20'],['Helium','49']]},
  codesign: {title:'HEAR · Codesign 控制面',copy:'Harness 传递工作流意图与控制需求；引擎返回状态能力与真实结果。HEAR 规定交互契约，具体缓存和调度策略可以插拔。',links:[['HEAR 精读','60'],['研究进展','research-update-20261014.html']]}
};
const viewport = document.getElementById('viewport');
const world = document.getElementById('world');
const layers = [...document.querySelectorAll('[data-layer]')];
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
const views = {perspective: [-9, -24], front: [0, 0], side: [-12, -48]};
let rx = -9, ry = -24, zoom = 1, spread = 1, auto = false, selected = 'kv';
let drag = null, suppressClick = false, frame = 0, lastTime = 0;
const art = ['workflow', 'schedule', 'engine', 'kv', 'compute', 'system'];
layers.slice(0, 6).forEach((layer, i) => {
  layer.style.setProperty('--level', i);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'module-art');
  svg.setAttribute('viewBox', '0 0 160 110');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', 'architecture-3d-assets.svg#' + art[i]);
  svg.append(use); layer.append(svg);
  for (const name of ['top-face', 'right-face']) {
    const face = document.createElement('span');
    face.className = name; face.setAttribute('aria-hidden', 'true'); layer.prepend(face);
  }
});
function render() {
  const fit = Math.min(1.04, (viewport.clientWidth - 18) / 1120);
  world.style.transform = 'translate(-50%,-50%) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) scale(' + fit * zoom + ')';
  world.style.setProperty('--pitch', (90 + spread * 47) + 'px');
}
function selectNode(id) {
  const item = nodeData[id];
  if (!item) return;
  selected = id;
  layers.forEach(n => {n.classList.toggle('is-selected', n.dataset.layer === id); n.setAttribute('aria-pressed', String(n.dataset.layer === id));});
  document.querySelectorAll('[data-select]').forEach(n => n.setAttribute('aria-pressed', String(n.dataset.select === id)));
  document.getElementById('detail-title').textContent = item.title;
  document.getElementById('detail-copy').textContent = item.copy;
  document.getElementById('detail-links').replaceChildren(...item.links.map(([label, target]) => {
    const a = document.createElement('a');
    a.href = target === '19' ? 'https://arxiv.org/abs/2309.06180' : /^\d+$/.test(target) ? 'papers/paper-' + target + '.html' : target;
    a.target = '_blank'; a.rel = 'noopener'; a.textContent = label + ' ↗';
    return a;
  }));
}
function setAuto(value) {
  auto = value && !reduceMotion.matches;
  const button = document.getElementById('auto-orbit');
  button.setAttribute('aria-pressed', String(auto));
  button.textContent = auto ? '暂停巡览' : '自动巡览';
  cancelAnimationFrame(frame); lastTime = 0;
  if (auto) frame = requestAnimationFrame(orbit);
}
function orbit(time) {
  if (!auto || document.hidden) return;
  if (lastTime) ry = -24 + Math.sin(time / 7000) * 13;
  lastTime = time; render();
  frame = requestAnimationFrame(orbit);
}
viewport.addEventListener('pointerdown', e => {
  if (e.button !== 0 || e.target.closest('a,input')) return;
  setAuto(false); suppressClick = false;
  drag = {id: e.pointerId, x: e.clientX, y: e.clientY, rx, ry, moved: false};
});
viewport.addEventListener('pointermove', e => {
  if (!drag || drag.id !== e.pointerId) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < 6) return;
  drag.moved = true; viewport.setPointerCapture(e.pointerId);
  viewport.classList.add('is-dragging');
  ry = Math.max(-65, Math.min(65, drag.ry + dx * .2));
  rx = Math.max(-32, Math.min(25, drag.rx - dy * .15)); render();
});
function endDrag(e) {
  if (!drag || drag.id !== e.pointerId) return;
  suppressClick = drag.moved;
  if (viewport.hasPointerCapture(e.pointerId)) viewport.releasePointerCapture(e.pointerId);
  drag = null; viewport.classList.remove('is-dragging');
}
viewport.addEventListener('pointerup', endDrag);
viewport.addEventListener('pointercancel', endDrag);
layers.forEach(n => n.addEventListener('click', () => {if (!suppressClick) {setAuto(false); selectNode(n.dataset.layer);}}));
document.querySelectorAll('[data-select]').forEach(n => n.addEventListener('click', () => {setAuto(false); selectNode(n.dataset.select);}));
function setZoom(value) {zoom = Math.max(.7, Math.min(1.35, value)); render();}
viewport.addEventListener('wheel', e => {
  if (!e.ctrlKey && !e.metaKey) return;
  e.preventDefault(); setZoom(zoom - e.deltaY * .001);
}, {passive: false});
document.getElementById('zoom-in').addEventListener('click', () => setZoom(zoom + .1));
document.getElementById('zoom-out').addEventListener('click', () => setZoom(zoom - .1));
document.getElementById('spread').addEventListener('input', e => {
  spread = Number(e.target.value) / 100;
  document.getElementById('spread-value').textContent = e.target.value + '%'; render();
});
document.querySelectorAll('[data-view]').forEach(n => n.addEventListener('click', () => {
  setAuto(false); [rx, ry] = views[n.dataset.view];
  document.querySelectorAll('[data-view]').forEach(b => {b.classList.toggle('active', b === n); b.setAttribute('aria-pressed', String(b === n));}); render();
}));
document.getElementById('reset-camera').addEventListener('click', () => {
  setAuto(false); [rx, ry] = views.perspective; zoom = 1; spread = 1;
  document.getElementById('spread').value = '100'; document.getElementById('spread-value').textContent = '100%';
  document.querySelectorAll('[data-view]').forEach(b => {const active = b.dataset.view === 'perspective'; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active));}); render();
});
document.getElementById('auto-orbit').addEventListener('click', () => setAuto(!auto));
document.getElementById('fullscreen').addEventListener('click', async () => {
  const panel = document.querySelector('.workspace');
  if (document.fullscreenElement) await document.exitFullscreen();
  else if (panel.requestFullscreen) await panel.requestFullscreen();
});
document.addEventListener('fullscreenchange', () => {document.getElementById('fullscreen').textContent = document.fullscreenElement ? '退出全屏' : '全屏探索'; render();});
document.addEventListener('visibilitychange', () => {if (document.hidden) cancelAnimationFrame(frame); else if (auto) {lastTime = 0; frame = requestAnimationFrame(orbit);}});
reduceMotion.addEventListener('change', () => {if (reduceMotion.matches) setAuto(false);});
new ResizeObserver(render).observe(viewport);
selectNode(selected); render();
