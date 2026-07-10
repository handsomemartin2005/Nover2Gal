import { openModal, escapeHtml } from "/static/js/components/modal.js";

let procurementCatalogPromise = null;

export async function openResourceCenter(project) {
  const scenes = project?.result?.adaptation_scenes || [];
  const backgrounds = unique(scenes.map((scene) => scene.background).filter(Boolean));
  const characters = unique(scenes.flatMap((scene) => (scene.stage?.characters || []).map((item) => item.name || item)).filter(Boolean));
  const bgm = unique(scenes.map((scene) => scene.bgm).filter(Boolean));
  const catalog = await loadProcurementCatalog();
  const groups = [
    ["背景图", backgrounds], ["角色立绘", characters], ["CG", []], ["BGM", bgm], ["SFX", []],
  ];
  openModal({
    title: "资源中心",
    eyebrow: "素材 · 故事世界",
    className: "resource-modal",
    content: `<div class="resource-overview"><span>已识别 <strong>${backgrounds.length + characters.length + bgm.length}</strong> 项需求</span><span>候选素材 <strong>${catalogItemCount(catalog)}</strong> 项</span></div><div class="resource-groups">${groups.map(([label, items]) => `<section><header><h3>${label}</h3><span>${items.length}</span></header>${items.length ? `<ul>${items.map((item) => `<li><span>${escapeHtml(item)}</span><small>待确认</small></li>`).join("")}</ul>` : '<p>当前剧本暂无此类资源</p>'}</section>`).join("")}</div>${renderProcurementCatalog(catalog)}`,
    actions: '<button class="anime-button anime-button--ghost" type="button" data-generic-close>完成</button>',
  });
}

function unique(items) { return [...new Set(items.map(String))]; }

async function loadProcurementCatalog() {
  if (!procurementCatalogPromise) {
    procurementCatalogPromise = fetch("/static/assets/procurement_catalog.json?v=20260710-procurement1")
      .then((response) => response.ok ? response.json() : null)
      .catch(() => null);
  }
  return procurementCatalogPromise;
}

function catalogItemCount(catalog) {
  return (catalog?.platforms || []).reduce((platformTotal, platform) => platformTotal + (platform.groups || []).reduce((groupTotal, group) => groupTotal + (group.items || []).length, 0), 0);
}

function renderProcurementCatalog(catalog) {
  if (!catalog?.platforms?.length) return '<section class="procurement-empty"><h3>扩充素材库</h3><p>候选目录暂时不可用，请稍后重试。</p></section>';
  return `<section class="procurement-catalog"><header><div><span>CURATED SOURCES</span><h3>扩充素材库</h3><p>“可内置”采用 CC0 候选；“采购候选”需要在购买或下载前再次核对平台级授权。</p></div><strong>${catalogItemCount(catalog)} 项</strong></header><div class="procurement-platforms">${catalog.platforms.map((platform) => `<article><div class="procurement-platform-head"><div><h4>${escapeHtml(platform.name)}</h4><p>${escapeHtml(platform.default_license)}</p></div><span class="procurement-mode procurement-mode--${platform.default_mode === "bundled" ? "bundled" : "catalog"}">${platform.default_mode === "bundled" ? "可内置候选" : "采购候选"}</span></div>${(platform.groups || []).map((group) => `<details><summary><span>${escapeHtml(group.label)}</span><b>${(group.items || []).length}</b></summary><ul>${(group.items || []).map((item) => `<li><a href="${safeExternalUrl(item.url)}" target="_blank" rel="noopener noreferrer"><span>${escapeHtml(item.title)}</span><small>${escapeHtml(item.notes || "打开来源页并复核授权")}</small></a></li>`).join("")}</ul></details>`).join("")}</article>`).join("")}</div></section>`;
}

function safeExternalUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" ? escapeHtml(url.href) : "#";
  } catch {
    return "#";
  }
}
