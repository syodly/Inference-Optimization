const CATEGORY_NAMES = {
  foundation: "基础推理 / 解码",
  serving: "Serving / 调度",
  workflow: "DAG / Agent workflow",
  kv: "Agentic KV Cache"
};

const STATUS_NAMES = {
  done: "已整理",
  partial: "已提及，待补全",
  todo: "待整理"
};

const $ = (id) => document.getElementById(id);
const dateValue = (value) => value.length === 4 ? `${value}-01-01` : value.length === 7 ? `${value}-01` : value;
const paperById = new Map(PAPERS.map((paper) => [paper[0], paper]));
const milestoneById = new Map(MILESTONES.map((milestone) => [milestone.id, milestone]));
const pdfPath = (path) => path;
const paperHref = (paper) => paper[5] !== "todo" ? `papers/paper-${paper[0]}.html` : pdfPath(paper[7]);

function phasePaper(paper) {
  const milestone = milestoneById.get(paper[0]);
  const detail = MILESTONE_DETAILS[paper[0]];
  const title = milestone ? milestone.title : paper[1];
  const details = detail
    ? `<div class="lane-paper-tags"><b>关键词</b>${detail.keywords.map((keyword) => `<span>${keyword}</span>`).join("")}</div><div class="lane-paper-byline"><b>作者</b> ${detail.authors}<span> · ${detail.affiliation}</span></div><div class="lane-paper-sections"><div><b>研究动机</b><p>${detail.motivation}</p></div><div><b>核心设计</b><p>${detail.design}</p></div><div><b>实验结果</b><p>${detail.result}</p></div><div><b>局限与启示</b><p>${detail.limitations}</p></div></div>`
    : `<div class="lane-paper-detail"><b>研究内容</b>：${PAPER_NOTES[paper[0]] || "该论文已归入本阶段，详细内容待补充到 Markdown 总结。"}</div>`;
  return `<article class="lane-paper${milestone ? " key" : ""}">
    <div class="lane-paper-title">${milestone ? '<span class="key-dot" title="Milestone 论文"></span>' : ""}<a href="${paperHref(paper)}" target="_blank" rel="noopener">${title}</a></div>
    <div class="lane-paper-meta">${paper[3]} · ${paper[4]} · ${STATUS_NAMES[paper[5]]}</div>
    <div class="lane-paper-note">${details}</div>
  </article>`;
}

function phaseCard(phase, visibleIds) {
  const visibleLanes = phase.lanes.map((lane) => ({
    ...lane,
    ids: lane.ids
      .filter((id) => visibleIds.has(id))
      .sort((a, b) => dateValue(paperById.get(a)[3]).localeCompare(dateValue(paperById.get(b)[3])) || a - b)
  })).filter((lane) => lane.ids.length);
  if (!visibleLanes.length) return "";
  return `<section class="phase">
    <div class="phase-head"><div class="phase-number">${phase.number}</div><div><h3>${phase.title}</h3><div class="phase-period">${phase.period}</div><p class="phase-thesis">${phase.thesis}</p></div></div>
    <div class="phase-lanes">${visibleLanes.map((lane) => `<div class="lane"><div class="lane-head"><h4>${lane.title}</h4><span class="lane-count">${lane.ids.length} 篇</span></div><div class="lane-papers">${lane.ids.map((id) => phasePaper(paperById.get(id))).join("")}</div></div>`).join("")}</div>
  </section>`;
}

function paperRows(items) {
  return items.sort((a, b) => dateValue(a[3]).localeCompare(dateValue(b[3])) || a[0] - b[0]).map((paper) => `
    <tr>
      <td>${paper[0]}</td>
      <td><div class="paper-title"><a href="${paperHref(paper)}" target="_blank" rel="noopener">${paper[1]}</a></div><div class="paper-meta">${paper[5] !== "todo" ? "打开 Markdown 精读页面" : "打开本地 PDF"}</div></td>
      <td><span class="tag ${paper[2]}">${CATEGORY_NAMES[paper[2]]}</span></td>
      <td>${paper[3]}</td>
      <td>${paper[4]}</td>
      <td><span class="status ${paper[5]}">${STATUS_NAMES[paper[5]]}</span></td>
      <td><span class="priority ${paper[6].toLowerCase()}">${paper[6]}</span></td>
    </tr>`).join("");
}

function render() {
  const query = $("search").value.trim().toLowerCase();
  const category = $("category").value;
  const status = $("status").value;
  const priority = $("priority").value;
  const filtered = PAPERS.filter((paper) => {
    const text = [paper[1], paper[2], CATEGORY_NAMES[paper[2]], paper[3], paper[4], PAPER_NOTES[paper[0]] || ""].join(" ").toLowerCase();
    return (!query || text.includes(query)) && (category === "all" || paper[2] === category) && (status === "all" || paper[5] === status) && (priority === "all" || paper[6] === priority);
  });
  const visibleIds = new Set(filtered.map((paper) => paper[0]));
  $("phase-board").innerHTML = PHASE_GROUPS.map((phase) => phaseCard(phase, visibleIds)).join("");
  $("empty").style.display = filtered.length ? "none" : "block";
  $("paper-rows").innerHTML = paperRows(filtered);
  const visiblePhases = PHASE_GROUPS.filter((phase) => phase.lanes.some((lane) => lane.ids.some((id) => visibleIds.has(id)))).length;
  $("result-count").textContent = `当前显示 ${filtered.length} / ${PAPERS.length} 篇，已归入 ${visiblePhases} 个 Research Phase`;
}

["search", "category", "status", "priority"].forEach((id) => $(id).addEventListener("input", render));
render();
