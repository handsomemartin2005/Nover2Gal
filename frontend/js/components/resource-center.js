import { openModal, escapeHtml } from "/static/js/components/modal.js";

export function openResourceCenter(project) {
  const scenes = project?.result?.adaptation_scenes || [];
  const backgrounds = unique(scenes.map((scene) => scene.background).filter(Boolean));
  const characters = unique(scenes.flatMap((scene) => (scene.stage?.characters || []).map((item) => item.name || item)).filter(Boolean));
  const bgm = unique(scenes.map((scene) => scene.bgm).filter(Boolean));
  const groups = [
    ["背景图", backgrounds], ["角色立绘", characters], ["CG", []], ["BGM", bgm], ["SFX", []],
  ];
  openModal({
    title: "资源中心",
    eyebrow: "素材 · 故事世界",
    className: "resource-modal",
    content: `<div class="resource-overview"><span>已识别 <strong>${backgrounds.length + characters.length + bgm.length}</strong> 项需求</span><span>生成与上传接口已预留</span></div><div class="resource-groups">${groups.map(([label, items]) => `<section><header><h3>${label}</h3><span>${items.length}</span></header>${items.length ? `<ul>${items.map((item) => `<li><span>${escapeHtml(item)}</span><small>待确认</small></li>`).join("")}</ul>` : '<p>当前剧本暂无此类资源</p>'}</section>`).join("")}</div>`,
    actions: '<button class="anime-button anime-button--ghost" type="button" data-generic-close>完成</button>',
  });
}

function unique(items) { return [...new Set(items.map(String))]; }
