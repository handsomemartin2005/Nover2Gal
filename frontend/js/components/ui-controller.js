class UiController {
  constructor() {
    this.cleanups = [];
    this.lastFocused = null;
  }

  mount(root) {
    const header = root.querySelector("[data-anime-header]");
    const navToggle = root.querySelector("[data-nav-toggle]");
    const nav = root.querySelector("[data-site-nav]");
    if (header) {
      const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 18);
      onScroll();
      window.addEventListener("scroll", onScroll, { passive: true });
      this.cleanups.push(() => window.removeEventListener("scroll", onScroll));
    }
    if (navToggle && nav) {
      const toggle = () => {
        const open = !nav.classList.contains("is-open");
        nav.classList.toggle("is-open", open);
        navToggle.setAttribute("aria-expanded", String(open));
      };
      navToggle.addEventListener("click", toggle);
      this.cleanups.push(() => navToggle.removeEventListener("click", toggle));
    }
    root.querySelectorAll("[data-open-settings]").forEach((button) => {
      const open = () => this.openSettings(button);
      button.addEventListener("click", open);
      this.cleanups.push(() => button.removeEventListener("click", open));
    });
  }

  unmount() {
    this.cleanups.splice(0).forEach((cleanup) => cleanup());
    this.closeModal(false);
  }

  openSettings(trigger) {
    this.lastFocused = trigger;
    const selected = localStorage.getItem("novel2gal.motionLevel") || "balanced";
    const overlay = document.querySelector("#overlayRoot");
    overlay.innerHTML = `
      <div class="modal-backdrop" data-modal-backdrop>
        <section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="motionSettingsTitle">
          <div class="modal-ornament" aria-hidden="true"></div>
          <div class="modal-head">
            <div><span class="chapter-label"><i></i>显示与演出</span><h2 id="motionSettingsTitle">舞台动效设置</h2></div>
            <button class="icon-button" type="button" data-close-modal aria-label="关闭设置">×</button>
          </div>
          <p class="modal-copy">选择适合设备与阅读习惯的动画强度。系统的“减少动态效果”设置始终优先。</p>
          <fieldset class="motion-options">
            ${[
              ["full", "完整动效", "完整的过场、视差与环境氛围"],
              ["balanced", "平衡动效", "保留叙事反馈，降低持续动画"],
              ["reduced", "减少动效", "关闭视差并缩短所有过场"],
            ].map(([value, label, copy]) => `<label><input type="radio" name="motionLevel" value="${value}" ${selected === value ? "checked" : ""}><span><strong>${label}</strong><small>${copy}</small></span></label>`).join("")}
          </fieldset>
          <div class="modal-actions"><button class="anime-button anime-button--ghost" type="button" data-close-modal>取消</button><button class="anime-button anime-button--primary" type="button" data-save-motion>保存设置</button></div>
        </section>
      </div>`;
    const backdrop = overlay.querySelector("[data-modal-backdrop]");
    const panel = overlay.querySelector(".modal-panel");
    const closeButtons = overlay.querySelectorAll("[data-close-modal]");
    const save = overlay.querySelector("[data-save-motion]");
    const close = () => this.closeModal();
    const onBackdrop = (event) => { if (event.target === backdrop) close(); };
    const onKey = (event) => {
      if (event.key === "Escape") close();
      if (event.key === "Tab") this.trapFocus(event, panel);
    };
    closeButtons.forEach((button) => button.addEventListener("click", close));
    backdrop.addEventListener("mousedown", onBackdrop);
    document.addEventListener("keydown", onKey);
    save.addEventListener("click", () => {
      const level = overlay.querySelector('input[name="motionLevel"]:checked')?.value || "balanced";
      localStorage.setItem("novel2gal.motionLevel", level);
      document.documentElement.dataset.motion = level;
      this.closeModal();
      this.toast("动效设置已保存", "success");
      window.dispatchEvent(new CustomEvent("novel2gal:motion-change", { detail: { level } }));
    });
    this.modalCleanup = () => {
      backdrop.removeEventListener("mousedown", onBackdrop);
      document.removeEventListener("keydown", onKey);
    };
    document.body.classList.add("modal-open");
    requestAnimationFrame(() => backdrop.classList.add("is-visible"));
    panel.querySelector("button")?.focus();
  }

  closeModal(restoreFocus = true) {
    const overlay = document.querySelector("#overlayRoot");
    this.modalCleanup?.();
    this.modalCleanup = null;
    if (overlay) overlay.innerHTML = "";
    document.body.classList.remove("modal-open");
    if (restoreFocus) this.lastFocused?.focus();
  }

  trapFocus(event, panel) {
    const nodes = [...panel.querySelectorAll('button, input, a[href], [tabindex]:not([tabindex="-1"])')];
    if (!nodes.length) return;
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }

  toast(message, tone = "info") {
    const region = document.querySelector("#toastRegion");
    if (!region) return;
    const toast = document.createElement("div");
    toast.className = `toast toast--${tone}`;
    toast.innerHTML = `<span aria-hidden="true"></span><p>${message}</p>`;
    region.append(toast);
    requestAnimationFrame(() => toast.classList.add("is-visible"));
    window.setTimeout(() => { toast.classList.remove("is-visible"); window.setTimeout(() => toast.remove(), 240); }, 2600);
  }
}

export const uiController = new UiController();
