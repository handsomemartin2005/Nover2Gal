import { api } from "/static/js/api-client.js?v=20260710-auth6";
import { openModal, confirmModal, escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

export async function openVersionHistory(projectId, { onRollback } = {}) {
  if (!projectId) { showToast("项目尚未保存，没有版本记录", "warning"); return; }
  const { versions } = await api.listVersions(projectId);
  openModal({
    title: "版本历史",
    eyebrow: "场景 · 历史版本",
    content: versions.length ? `<div class="version-list">${versions.map((version) => `<article><span class="story-node"></span><div><h3>${escapeHtml(version.note || "自动快照")}</h3><time>${formatTime(version.created_at)}</time></div><button class="anime-button anime-button--ghost" type="button" data-rollback="${version.version_id}">回滚</button></article>`).join("")}</div>` : '<div class="modal-empty"><strong>还没有历史版本</strong><p>重新生成或覆盖已有脚本时，会自动保存旧版本。</p></div>',
    actions: '<button class="anime-button anime-button--ghost" type="button" data-generic-close>关闭</button>',
    onMount(panel, close) {
      panel.querySelectorAll("[data-rollback]").forEach((button) => button.addEventListener("click", async () => {
        const confirmed = await confirmModal({ title: "回滚到此版本？", message: "当前版本会先自动保存为快照，然后恢复所选内容。", confirmLabel: "确认回滚" });
        if (!confirmed) return;
        const project = await api.rollbackVersion(projectId, button.dataset.rollback);
        close();
        showToast("已恢复历史版本", "success");
        onRollback?.(project);
      }));
    },
  });
}

function formatTime(value) { return value ? new Date(value * 1000).toLocaleString("zh-CN", { hour12: false }) : "—"; }
