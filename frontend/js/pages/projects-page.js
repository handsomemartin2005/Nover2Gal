import { api } from "/static/js/api-client.js?v=20260710-auth3";
import { confirmModal, openModal, escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";
import { openPublishSample } from "/static/js/components/publish-sample.js";
import { openExportCenter } from "/static/js/components/export-center.js";

export async function initProjectsPage(root) {
  const grid = root.querySelector("#projectGrid");
  const search = root.querySelector("#projectSearch");
  const sort = root.querySelector("#projectSort");
  const filters = [...root.querySelectorAll("[data-project-filter]")];
  const viewButtons = [...root.querySelectorAll("[data-project-view]")];
  const importButton = root.querySelector("#importProjectButton");
  const importInput = root.querySelector("#projectJsonInput");
  let projects = [];
  let activeFilter = "all";
  let destroyed = false;
  const render = () => {
    const query = search.value.toLowerCase().trim();
    const filtered = projects.filter((project) => matchesStatus(project.status, activeFilter) && `${project.title} ${project.filename || ""} ${project.pov_character || ""}`.toLowerCase().includes(query));
    const sorted = [...filtered].sort((a, b) => sort.value === "oldest" ? a.updated_at - b.updated_at : sort.value === "title" ? String(a.title).localeCompare(String(b.title), "zh-CN") : b.updated_at - a.updated_at);
    grid.innerHTML = sorted.length ? sorted.map(projectCard).join("") : emptyProjects(Boolean(projects.length));
    updateStats(root, projects);
  };
  const onFilter = (event) => {
    activeFilter = event.currentTarget.dataset.projectFilter;
    filters.forEach((button) => button.classList.toggle("active", button === event.currentTarget));
    render();
  };
  const onGrid = async (event) => {
    const button = event.target.closest("[data-project-action]");
    if (!button) return;
    const card = button.closest("[data-project-id]");
    const project = projects.find((item) => item.project_id === card.dataset.projectId);
    const action = button.dataset.projectAction;
    if (action === "edit") window.location.href = `/create?project_id=${encodeURIComponent(project.project_id)}`;
    if (action === "preview") previewProject(project);
    if (action === "sample") openPublishSample(await api.getProject(project.project_id));
    if (action === "export") openExportCenter(await api.getProject(project.project_id));
    if (action === "duplicate") {
      const copy = await api.duplicateProject(project.project_id);
      projects.unshift(toSummary(copy)); render(); showToast("项目副本已创建", "success");
    }
    if (action === "delete") {
      const confirmed = await confirmModal({ title: "删除这个项目？", message: `“${project.title}”的原文、脚本和版本记录都会被删除，此操作无法撤销。`, confirmLabel: "删除项目", danger: true });
      if (!confirmed) return;
      card.classList.add("is-removing");
      try { await api.deleteProject(project.project_id); projects = projects.filter((item) => item !== project); window.setTimeout(render, 220); showToast("项目已删除", "success"); }
      catch (error) { card.classList.remove("is-removing"); showToast(error.message, "error"); }
    }
  };
  search.addEventListener("input", render);
  sort.addEventListener("change", render);
  filters.forEach((button) => button.addEventListener("click", onFilter));
  const onView = (event) => {
    grid.dataset.view = event.currentTarget.dataset.projectView;
    viewButtons.forEach((button) => button.classList.toggle("active", button === event.currentTarget));
  };
  viewButtons.forEach((button) => button.addEventListener("click", onView));
  grid.addEventListener("click", onGrid);
  const onImport = () => importInput.click();
  const onImportFile = async () => {
    const file = importInput.files?.[0];
    if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      const project = await api.createProject({ title: payload.title || file.name.replace(/\.json$/i, ""), pov_character: payload.pov_character || "" });
      const saved = await api.updateProject(project.project_id, { result: payload.result || payload, status: "done", version_note: "导入 JSON" });
      projects.unshift(toSummary(saved)); render(); showToast("项目 JSON 已导入", "success");
    } catch (error) { showToast(`导入失败：${error.message}`, "error"); }
    importInput.value = "";
  };
  importButton.addEventListener("click", onImport);
  importInput.addEventListener("change", onImportFile);
  render();
  try {
    const response = await api.listProjects();
    if (!destroyed) { projects = response.projects || []; render(); }
  } catch (error) { grid.innerHTML = `<div class="library-empty"><h2>项目列表读取失败</h2><p>${escapeHtml(error.message)}</p></div>`; }
  return () => {
    destroyed = true;
    search.removeEventListener("input", render);
    sort.removeEventListener("change", render);
    filters.forEach((button) => button.removeEventListener("click", onFilter));
    viewButtons.forEach((button) => button.removeEventListener("click", onView));
    grid.removeEventListener("click", onGrid);
    importButton.removeEventListener("click", onImport);
    importInput.removeEventListener("change", onImportFile);
  };
}

function projectCard(project, index) {
  const status = statusMeta(project.status);
  const progress = Number(project.progress || (project.has_result ? 100 : 0));
  return `<article class="save-slot" data-project-id="${escapeHtml(project.project_id)}" data-reveal-card style="--project-index:${index || 0}">
    <div class="save-number"><span>存档</span><strong>${String((index || 0) + 1).padStart(2, "0")}</strong></div>
    <div class="save-cover save-cover--${escapeHtml(project.status || "draft")}"><span>${String(project.scene_count || 0).padStart(2, "0")}</span><small>场景</small><i></i></div>
    <div class="save-content">
      <header><div><span class="project-status project-status--${escapeHtml(project.status)}"><i></i>${status.label}</span><h2>${escapeHtml(project.title)}</h2><p>${escapeHtml(project.filename || "手动录入台本")} · ${escapeHtml(project.pov_character || "自动视角")}</p></div><span class="save-chapter">第 ${Math.max(1, Math.ceil((project.scene_count || 1) / 5))} 章</span></header>
      <dl class="save-meta"><div><dt>场景</dt><dd>${project.scene_count || 0} 个</dd></div><div><dt>生成进度</dt><dd>${progress}%</dd></div><div><dt>最后编辑</dt><dd>${relativeTime(project.updated_at)}</dd></div><div><dt>导出状态</dt><dd>${project.has_result ? "可以导出" : "尚未生成"}</dd></div></dl>
      <div class="project-progress"><span><i style="width:${Math.max(0, Math.min(100, progress))}%"></i></span><small>${progress}%</small></div>
    </div>
    <div class="save-actions"><button class="anime-button anime-button--primary" type="button" data-project-action="edit">继续制作</button><button class="anime-button anime-button--ghost" type="button" data-project-action="preview">预览</button><div class="project-more"><button type="button" data-project-action="sample">保存为模板</button><button type="button" data-project-action="export">导出作品</button><button type="button" data-project-action="duplicate">复制存档</button><button class="danger-text" type="button" data-project-action="delete">删除</button></div></div>
  </article>`;
}

function emptyProjects(hasProjects) {
  return `<div class="library-empty project-empty"><div class="empty-manuscript" aria-hidden="true"><span></span><i></i><b></b></div><h2>${hasProjects ? "没有符合条件的存档" : "台本还停在第一页"}</h2><p>${hasProjects ? "调整搜索词或状态书签，再找一次。" : "导入一篇小说，为它建立第一场演出。"}</p><a class="anime-button anime-button--primary" href="/create?new=1" data-route>建立第一部作品</a></div>`;
}

function previewProject(project) {
  openModal({ title: project.title, eyebrow: "作品 · 快速预览", content: `<div class="project-preview"><div class="project-preview-stage"><span>场景 ${String(project.scene_count || 0).padStart(2, "0")}</span><p>${project.has_result ? "已生成的视觉小说脚本可以继续播放与编辑。" : "这个企划还没有生成场景。"}</p></div><dl><div><dt>状态</dt><dd>${statusMeta(project.status).label}</dd></div><div><dt>进度</dt><dd>${project.progress || 0}%</dd></div><div><dt>版本</dt><dd>${project.version_count || 0}</dd></div></dl></div>`, actions: `<button class="anime-button anime-button--ghost" type="button" data-generic-close>关闭</button><a class="anime-button anime-button--primary" href="/create?project_id=${project.project_id}">进入工作台</a>` });
}

function updateStats(root, projects) {
  const values = { total: projects.length, done: projects.filter((item) => item.status === "done").length, running: projects.filter((item) => ["queued", "running"].includes(item.status)).length, review: projects.filter((item) => item.status === "failed").length };
  Object.entries(values).forEach(([key, value]) => { const target = root.querySelector(`[data-project-stat="${key}"]`); if (target) target.textContent = value; });
  const recent = root.querySelector('[data-project-stat="recent"]');
  if (recent) recent.textContent = projects[0] ? relativeTime(projects[0].updated_at) : "—";
}

function statusMeta(status) { return { draft: { label: "待检查" }, queued: { label: "排队中" }, running: { label: "生成中" }, done: { label: "已完成" }, failed: { label: "生成失败" }, cancelled: { label: "已取消" } }[status] || { label: "待检查" }; }
function matchesStatus(status, filter) { if (filter === "all") return true; if (filter === "running") return ["queued", "running"].includes(status); if (filter === "draft") return ["draft", "failed", "cancelled"].includes(status); return status === filter; }
function relativeTime(value) { if (!value) return "—"; const seconds = Math.max(0, Date.now() / 1000 - value); if (seconds < 60) return "刚刚"; if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`; if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`; return `${Math.floor(seconds / 86400)} 天前`; }
function toSummary(project) { return { ...project, scene_count: project.result?.stats?.adaptation_scenes || 0, progress: project.status === "done" ? 100 : 0, has_result: Boolean(project.result), version_count: project.versions?.length || 0 }; }
