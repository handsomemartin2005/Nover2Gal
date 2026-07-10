let activeModal = null;

export function openModal({ title, eyebrow = "NOVEL2GAL", content = "", actions = "", className = "", onMount } = {}) {
  closeModal(false);
  const overlayRoot = document.querySelector("#overlayRoot");
  const trigger = document.activeElement;
  overlayRoot.innerHTML = `
    <div class="modal-backdrop" data-generic-backdrop>
      <section class="modal-panel ${className}" role="dialog" aria-modal="true" aria-labelledby="genericModalTitle">
        <div class="modal-ornament" aria-hidden="true"></div>
        <header class="modal-head">
          <div><span class="chapter-label"><i></i>${eyebrow}</span><h2 id="genericModalTitle">${escapeHtml(title || "")}</h2></div>
          <button class="icon-button" type="button" data-generic-close aria-label="关闭弹窗">×</button>
        </header>
        <div class="modal-content">${content}</div>
        ${actions ? `<footer class="modal-actions">${actions}</footer>` : ""}
      </section>
    </div>`;
  const backdrop = overlayRoot.querySelector("[data-generic-backdrop]");
  const panel = overlayRoot.querySelector(".modal-panel");
  const onBackdrop = (event) => { if (event.target === backdrop) closeModal(); };
  const onKey = (event) => {
    if (event.key === "Escape") closeModal();
    if (event.key === "Tab") trapFocus(event, panel);
  };
  backdrop.addEventListener("mousedown", onBackdrop);
  document.addEventListener("keydown", onKey);
  overlayRoot.querySelectorAll("[data-generic-close]").forEach((button) => button.addEventListener("click", () => closeModal()));
  activeModal = {
    trigger,
    cleanup: () => {
      backdrop.removeEventListener("mousedown", onBackdrop);
      document.removeEventListener("keydown", onKey);
    },
  };
  document.body.classList.add("modal-open");
  requestAnimationFrame(() => backdrop.classList.add("is-visible"));
  onMount?.(panel, () => closeModal());
  panel.querySelector("button, input, textarea, select, a[href]")?.focus();
  return () => closeModal();
}

export function closeModal(restoreFocus = true) {
  if (!activeModal) return;
  const { cleanup, trigger } = activeModal;
  activeModal = null;
  cleanup?.();
  document.querySelector("#overlayRoot").innerHTML = "";
  document.body.classList.remove("modal-open");
  if (restoreFocus && trigger instanceof HTMLElement) trigger.focus();
}

export function confirmModal({ title, message, confirmLabel = "确认", danger = false }) {
  return new Promise((resolve) => {
    openModal({
      title,
      eyebrow: danger ? "危险操作 · 请确认" : "操作确认",
      content: `<p class="modal-copy">${escapeHtml(message)}</p>`,
      actions: `<button class="anime-button anime-button--ghost" type="button" data-confirm-cancel>取消</button><button class="anime-button ${danger ? "anime-button--danger" : "anime-button--primary"}" type="button" data-confirm-ok>${escapeHtml(confirmLabel)}</button>`,
      onMount(panel) {
        panel.querySelector("[data-confirm-cancel]").addEventListener("click", () => { closeModal(); resolve(false); });
        panel.querySelector("[data-confirm-ok]").addEventListener("click", () => { closeModal(); resolve(true); });
      },
    });
  });
}

function trapFocus(event, panel) {
  const nodes = [...panel.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])')];
  if (!nodes.length) return;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
