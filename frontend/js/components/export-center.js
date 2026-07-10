import { openModal, escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

export function openExportCenter(project) {
  const result = project?.result || {};
  const scenes = result.adaptation_scenes || [];
  const exports = result.exports || {};
  const resourceStats = collectResources(scenes);
  openModal({
    title: "导出中心",
    eyebrow: "导出 · 作品包",
    className: "export-modal",
    content: `
      <div class="export-summary"><span><small>场景</small><strong>${scenes.length}</strong></span><span><small>角色</small><strong>${resourceStats.characters}</strong></span><span><small>背景</small><strong>${resourceStats.backgrounds}</strong></span></div>
      <div class="export-list">
        ${exportRow("markdown", "Markdown 剧本", "适合审阅、协作和文档归档", Boolean(exports.markdown))}
        ${exportRow("json", "JSON 数据", "完整结构化场景、角色、分支和资源需求", Boolean(result && Object.keys(result).length))}
        ${exportRow("renpy", "Ren'Py Script", "可继续整理为 script.rpy", Boolean(exports.renpy))}
        ${exportRow("renpy-project", "Ren'Py Project ZIP", "入口已预留，后端打包器将在后续接入", false)}
        ${exportRow("resources", "资源需求清单", "背景、立绘、BGM 与音效缺口", scenes.length > 0)}
      </div>`,
    actions: '<button class="anime-button anime-button--ghost" type="button" data-generic-close>完成</button>',
    onMount(panel) {
      panel.querySelectorAll("[data-export]").forEach((button) => button.addEventListener("click", () => {
        const type = button.dataset.export;
        if (type === "markdown") download(`${safeName(project.title)}.md`, exports.markdown || "", "text/markdown");
        if (type === "json") download(`${safeName(project.title)}.json`, JSON.stringify(result, null, 2), "application/json");
        if (type === "renpy") download(`${safeName(project.title)}.rpy`, exports.renpy || "", "text/plain");
        if (type === "resources") download(`${safeName(project.title)}-resources.md`, resourceChecklist(resourceStats), "text/markdown");
        showToast("导出文件已生成", "success");
      }));
    },
  });
}

function exportRow(type, title, copy, ready) {
  return `<article class="export-row"><span class="export-icon" aria-hidden="true">${type === "json" ? "{}" : "◇"}</span><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(copy)}</p></div><button class="anime-button anime-button--ghost" type="button" ${ready ? `data-export="${type}"` : "disabled"}>${ready ? "导出" : "尚未可用"}</button></article>`;
}

function collectResources(scenes) {
  const characters = new Set();
  const backgrounds = new Set();
  const bgm = new Set();
  scenes.forEach((scene) => {
    if (scene.background) backgrounds.add(scene.background);
    if (scene.bgm) bgm.add(scene.bgm);
    (scene.stage?.characters || []).forEach((character) => characters.add(character.name || character));
  });
  return { characters: characters.size, backgrounds: backgrounds.size, bgm: bgm.size, characterNames: [...characters], backgroundNames: [...backgrounds], bgmNames: [...bgm] };
}

function resourceChecklist(stats) {
  return `# 资源需求清单\n\n## 角色立绘（${stats.characters}）\n${stats.characterNames.map((item) => `- [ ] ${item}`).join("\n") || "- 暂无"}\n\n## 场景背景（${stats.backgrounds}）\n${stats.backgroundNames.map((item) => `- [ ] ${item}`).join("\n") || "- 暂无"}\n\n## BGM（${stats.bgm}）\n${stats.bgmNames.map((item) => `- [ ] ${item}`).join("\n") || "- 暂无"}\n`;
}

function download(filename, content, type) {
  const blob = new Blob([content], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function safeName(value) { return String(value || "novel2gal").replace(/[\\/:*?"<>|]/g, "-"); }
