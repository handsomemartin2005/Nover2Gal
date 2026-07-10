import { api } from "/static/js/api-client.js?v=20260710-auth3";
import { openModal, escapeHtml, confirmModal } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

const BUILTIN_SAMPLES = [
  { id: "campus-confession", category: "校园恋爱", title: "天台告白练习", description: "以转学生视角组织误会、试探与告白分支。", pov: "转学生", scenes: 12, cover: "/static/assets/editorial/campus-rooftop.webp", characters: 4, branches: 6, cost: "约 ¥1.80", updated: "本周更新", resources: 9 },
  { id: "old-school-recorder", category: "悬疑推理", title: "旧教学楼的录音笔", description: "用有限视角推进线索、误导与真相回收。", pov: "调查者", scenes: 9, cover: "/static/assets/editorial/old-school-recorder.webp", characters: 5, branches: 8, cost: "约 ¥2.10", updated: "3 天前", resources: 11 },
  { id: "rain-convenience", category: "日常治愈", title: "雨后便利店", description: "慢节奏对话与关系推进，适合短篇日常。", pov: "夜班店员", scenes: 7, cover: "/static/assets/editorial/rain-convenience.webp", characters: 3, branches: 3, cost: "约 ¥0.90", updated: "昨天", resources: 7 },
  { id: "moonlit-forest", category: "奇幻冒险", title: "月光森林的誓约", description: "任务、同伴与世界观信息逐幕展开。", pov: "见习旅者", scenes: 14, cover: "/static/assets/editorial/moonlit-forest.webp", characters: 6, branches: 10, cost: "约 ¥2.80", updated: "上周更新", resources: 16 },
  { id: "black-rose", category: "黑暗剧情", title: "黑蔷薇审判", description: "高压冲突、秘密关系与多阶段抉择。", pov: "证言者", scenes: 11, cover: "/static/assets/editorial/black-rose-hearing.webp", characters: 5, branches: 7, cost: "约 ¥2.30", updated: "6 天前", resources: 13 },
];

export async function initTemplatesPage(root) {
  const grid = root.querySelector("#templateGrid");
  const search = root.querySelector("#templateSearch");
  const filters = [...root.querySelectorAll("[data-template-filter]")];
  let activeCategory = "全部";
  let customSamples = [];
  let destroyed = false;
  const render = () => {
    const query = search.value.trim().toLowerCase();
    const items = [
      ...BUILTIN_SAMPLES.map((item) => ({ ...item, builtin: true })),
      ...customSamples.map((item) => ({ ...item, id: item.sample_id, category: item.category || "其他", pov: item.pov_character || "自动视角", scenes: item.scene_count || 0, characters: "随项目", branches: "随项目", cost: "已生成", updated: item.visibility === "public" ? "公开样例" : "私人样例", resources: "—", builtin: false })),
    ].filter((item) => (activeCategory === "全部" || (activeCategory === "我的样例" ? item.can_manage : item.category === activeCategory)) && `${item.title} ${item.description} ${item.category}`.toLowerCase().includes(query));
    grid.innerHTML = items.map(templateCard).join("") || '<div class="library-empty"><span class="empty-book" aria-hidden="true"></span><h2>没有找到匹配的样例</h2><p>尝试其他关键词或分类。</p></div>';
  };
  const onFilter = (event) => {
    const button = event.currentTarget;
    activeCategory = button.dataset.templateFilter;
    filters.forEach((item) => item.classList.toggle("active", item === button));
    render();
  };
  const onGrid = (event) => {
    const button = event.target.closest("[data-template-action]");
    if (!button) return;
    const id = button.closest("[data-template-id]").dataset.templateId;
    const item = BUILTIN_SAMPLES.find((sample) => sample.id === id) || customSamples.find((sample) => sample.sample_id === id);
    if (button.dataset.templateAction === "preview") openTemplateDetail(item, Boolean(item.sample_id));
    if (button.dataset.templateAction === "use") useTemplate(item, Boolean(item.sample_id));
  };
  search.addEventListener("input", render);
  filters.forEach((button) => button.addEventListener("click", onFilter));
  grid.addEventListener("click", onGrid);
  render();
  try {
    const response = await api.listSamples();
    if (!destroyed) { customSamples = response.samples || []; render(); }
  } catch (error) { showToast(`私人样例暂时无法读取：${error.message}`, "warning"); }
  return () => {
    destroyed = true;
    search.removeEventListener("input", render);
    filters.forEach((button) => button.removeEventListener("click", onFilter));
    grid.removeEventListener("click", onGrid);
  };
}

function templateCard(item, index) {
  const featured = index === 0 ? " template-volume--featured" : "";
  const privateClass = !item.builtin && item.visibility !== "public" ? " template-volume--private" : "";
  const cover = escapeHtml(item.cover || "/static/assets/editorial/rain-convenience.webp");
  return `<article class="template-volume genre-${genreSlug(item.category)}${featured}${privateClass}" data-template-id="${escapeHtml(item.id)}" data-reveal-card>
    <button class="volume-cover" type="button" data-template-action="preview" style="--template-art:url('${cover}')" aria-label="预览${escapeHtml(item.title)}">
      <span class="volume-binding"></span><span class="volume-issue">${item.builtin ? `第 ${String(index + 1).padStart(2, "0")} 册` : item.visibility === "public" ? "公开样例" : "私人样例"}</span>
      <span class="volume-cover-title">${escapeHtml(item.title)}</span><span class="volume-cover-category">${escapeHtml(item.category)}</span>
    </button>
    <div class="volume-copy"><span class="paper-tab">${escapeHtml(item.category)}</span><h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.description)}</p><small>核心视角：${escapeHtml(item.pov || "自动视角")}</small>
      <dl class="volume-meta"><div><dt>角色</dt><dd>${escapeHtml(item.characters)}</dd></div><div><dt>场景</dt><dd>${escapeHtml(item.scenes)}</dd></div><div><dt>分支</dt><dd>${escapeHtml(item.branches)}</dd></div><div><dt>预计成本</dt><dd>${escapeHtml(item.cost)}</dd></div></dl>
      <footer><span>${escapeHtml(item.updated)}</span><button class="anime-button anime-button--primary" type="button" data-template-action="use">以此创作</button></footer>
    </div>
  </article>`;
}

function genreSlug(category = "") {
  return { "校园恋爱": "romance", "悬疑推理": "mystery", "奇幻冒险": "fantasy", "日常治愈": "healing", "黑暗剧情": "dark" }[category] || "private";
}

function openTemplateDetail(item, custom) {
  openModal({
    title: item.title,
    eyebrow: `${item.category} · 模板详情`,
    className: "template-detail-modal",
    content: `<div class="template-detail"><div class="template-detail-cover" style="background-image:linear-gradient(180deg,transparent,rgba(4,8,20,.72)),url('${escapeHtml(item.cover || "/static/assets/editorial/rain-convenience.webp")}')"></div><div class="template-detail-copy"><p>${escapeHtml(item.description || "创作样例")}</p><dl><div><dt>核心视角</dt><dd>${escapeHtml(item.pov || item.pov_character || "自动视角")}</dd></div><div><dt>场景</dt><dd>${item.scenes || item.scene_count || 0}</dd></div><div><dt>角色</dt><dd>${item.characters || "随项目"}</dd></div><div><dt>可见性</dt><dd>${custom ? item.visibility === "public" ? "公开" : "仅自己" : "内置"}</dd></div></dl><p class="privacy-note">${custom ? item.visibility === "public" ? "公开样例会展示给所有访问者，但不包含原文全文。" : "私人样例只对当前账号可见。" : "内置样例提供结构参考，复制后可自由编辑。"}</p></div></div>`,
    actions: `${custom && item.can_manage ? `<button class="anime-button anime-button--ghost" type="button" data-toggle-sample>${item.visibility === "public" ? "设为私密" : "设为公开"}</button><button class="anime-button anime-button--danger" type="button" data-delete-sample>删除样例</button>` : ""}<button class="anime-button anime-button--ghost" type="button" data-generic-close>返回</button><button class="anime-button anime-button--primary" type="button" data-use-detail>复制为新项目</button>`,
    onMount(panel) {
      panel.querySelector("[data-use-detail]").addEventListener("click", () => useTemplate(item, custom));
      panel.querySelector("[data-delete-sample]")?.addEventListener("click", async () => {
        const confirmed = await confirmModal({ title: "删除样例？", message: `“${item.title}”将从模板库移除，原项目不会删除。`, confirmLabel: "删除样例", danger: true });
        if (!confirmed) return;
        await api.deleteSample(item.sample_id);
        showToast("私人样例已删除", "success");
        window.location.reload();
      });
      panel.querySelector("[data-toggle-sample]")?.addEventListener("click", async () => {
        await api.updateSample(item.sample_id, { visibility: item.visibility === "public" ? "private" : "public" });
        showToast(item.visibility === "public" ? "样例已设为私密" : "样例已公开", "success");
        window.location.reload();
      });
    },
  });
}

async function useTemplate(item, custom) {
  try {
    let project = custom ? await api.cloneSample(item.sample_id) : await api.createProject({ title: `${item.title} · 改编`, pov_character: item.pov, max_scenes: item.scenes });
    if (!custom) project = await api.updateProject(project.project_id, { status: "done", result: builtinResult(item), version_note: "内置样例初始化" });
    showToast("样例已复制，正在进入工作台", "success");
    window.location.href = `/create?project_id=${encodeURIComponent(project.project_id)}`;
  } catch (error) {
    if (error.status === 401) window.location.assign(`/account?next=${encodeURIComponent("/templates")}`);
    else showToast(error.message, "error");
  }
}

function builtinResult(item) {
  const protagonist = item.pov || "主角";
  const friend = item.category === "悬疑推理" ? "线索提供者" : "故事中的她";
  const scenes = [
    {
      scene_id: "sample_001", title: `${item.title} · 序幕`, background: "bg_classroom", bgm: "bgm_daily", adapter: "sample",
      stage: { location: "classroom", props: ["window", "desk"], characters: [protagonist, friend] },
      blocks: [{ type: "narration", text: "风从半开的窗边掠过，故事在这一刻有了声音。" }, { type: "dialogue", speaker: friend, text: "你终于来了。" }],
    },
    {
      scene_id: "sample_002", title: `${item.title} · 选择`, background: "bg_old_school_night", bgm: "bgm_memory", adapter: "sample",
      stage: { location: "old_school", props: ["door", "corridor"], characters: [protagonist, friend] },
      blocks: [{ type: "dialogue", speaker: protagonist, text: "如果现在追问，某些关系也许会改变。" }, { type: "choice", choice_mode: "parallel", choices: [{ text: "问出真相", branch_text: "我向前一步，说出了那个藏了很久的问题。" }, { text: "先陪她离开", branch_text: "我没有追问，只是和她并肩走进夜色。" }] }],
    },
  ];
  return {
    title: item.title,
    pov_character: protagonist,
    analysis: { characters: [{ name: protagonist, role: "主角", personality: "由玩家选择塑造", speech_style: "克制", visual_notes: { style: "anime" } }, { name: friend, role: "关键角色", personality: "保留秘密", speech_style: "轻声", visual_notes: { style: "anime" } }] },
    adaptation_scenes: scenes,
    source_scenes: [], source_chunks: [], consistency_reports: [],
    stats: { chapters: 1, source_scenes: 2, source_chunks: 2, adaptation_scenes: scenes.length },
    exports: { markdown: scenes.map((scene) => `## ${scene.title}`).join("\n\n"), renpy: `label start:\n    \"${item.title}\"\n    return` },
  };
}
