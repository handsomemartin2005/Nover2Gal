import { api } from "/static/js/api-client.js";
import { openModal, escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

export function openPublishSample(project, { onPublished } = {}) {
  if (!project?.project_id) {
    showToast("请先保存项目，再发布样例", "warning");
    return;
  }
  openModal({
    title: "保存为样例",
    eyebrow: "发布 · 私人模板",
    className: "publish-sample-modal",
    content: `
      <form id="publishSampleForm" class="modal-form">
        <label>样例标题<input name="title" required maxlength="160" value="${escapeHtml(project.title || "未命名样例")}"></label>
        <label>简介<textarea name="description" maxlength="1000" rows="3" placeholder="概括这个样例的剧情结构与适用场景"></textarea></label>
        <div class="modal-form-grid">
          <label>分类<select name="category"><option>校园恋爱</option><option>悬疑推理</option><option>奇幻冒险</option><option>日常治愈</option><option>黑暗剧情</option><option>其他</option></select></label>
          <label>封面<select name="cover"><option value="/static/assets/landing/create-anime.png">创作舞台</option><option value="/static/assets/landing/templates-anime.png">故事书库</option><option value="/static/assets/landing/projects-anime.png">项目档案</option></select></label>
        </div>
        <div class="privacy-options">
          <label><input name="include_script" type="checkbox" checked><span>包含生成脚本<small>复制后可以继续编辑已生成场景</small></span></label>
          <label><input name="include_source" type="checkbox"><span>包含原文全文<small>默认关闭，公开样例禁止包含</small></span></label>
          <label><input name="allow_clone" type="checkbox" checked><span>允许复制<small>他人或本人可从此样例创建新项目</small></span></label>
        </div>
        <fieldset class="visibility-options"><legend>可见范围</legend><label><input type="radio" name="visibility" value="private" checked><span>私人样例</span></label><label><input type="radio" name="visibility" value="public"><span>公开样例</span></label></fieldset>
        <label class="public-confirm" hidden><input name="public_confirm" type="checkbox"><span>我确认不包含未经授权的原文，并理解公开后的版权与隐私影响</span></label>
        <p class="form-error" data-publish-error role="alert"></p>
      </form>`,
    actions: '<button class="anime-button anime-button--ghost" type="button" data-generic-close>取消</button><button class="anime-button anime-button--primary" type="submit" form="publishSampleForm" data-publish-submit>保存样例</button>',
    onMount(panel, close) {
      const form = panel.querySelector("#publishSampleForm");
      const visibility = [...form.elements.visibility];
      const publicConfirm = form.querySelector(".public-confirm");
      const includeSource = form.elements.include_source;
      visibility.forEach((radio) => radio.addEventListener("change", () => {
        const isPublic = form.elements.visibility.value === "public";
        delete form.dataset.publicConfirmed;
        form.querySelector("[data-publish-error]").textContent = "";
        panel.querySelector("[data-publish-submit]").textContent = "保存样例";
        publicConfirm.hidden = !isPublic;
        if (isPublic) includeSource.checked = false;
        includeSource.disabled = isPublic;
      }));
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const isPublic = form.elements.visibility.value === "public";
        if (isPublic && !form.elements.public_confirm.checked) {
          form.querySelector("[data-publish-error]").textContent = "公开样例前需要确认版权与隐私提示。";
          return;
        }
        if (isPublic && form.dataset.publicConfirmed !== "true") {
          form.dataset.publicConfirmed = "true";
          form.querySelector("[data-publish-error]").textContent = "请再次点击“确认公开”完成二次确认。原文全文不会公开。";
          panel.querySelector("[data-publish-submit]").textContent = "确认公开";
          return;
        }
        const submit = panel.querySelector("[data-publish-submit]");
        submit.disabled = true;
        submit.textContent = "正在收束故事线…";
        try {
          const sample = await api.publishSample(project.project_id, {
            title: form.elements.title.value.trim(),
            description: form.elements.description.value.trim(),
            category: form.elements.category.value,
            cover: form.elements.cover.value,
            include_source: includeSource.checked,
            include_script: form.elements.include_script.checked,
            visibility: form.elements.visibility.value,
            allow_clone: form.elements.allow_clone.checked,
          });
          close();
          showToast("样例已保存到模板库", "success");
          onPublished?.(sample);
        } catch (error) {
          submit.disabled = false;
          submit.textContent = "保存样例";
          form.querySelector("[data-publish-error]").textContent = error.message;
        }
      });
    },
  });
}
