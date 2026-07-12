class MotionController {
  constructor() {
    this.cleanups = [];
    this.pendingOverlay = null;
    this.media = window.matchMedia("(prefers-reduced-motion: reduce)");
    this.syncLevel();
    this.onMotionChange = () => this.syncLevel();
    window.addEventListener("novel2gal:motion-change", this.onMotionChange);
  }

  get reduced() {
    return this.media.matches || this.level === "reduced";
  }

  syncLevel() {
    this.level = this.media.matches ? "reduced" : (localStorage.getItem("novel2gal.motionLevel") || "balanced");
    document.documentElement.dataset.motion = this.level;
  }

  mount(root) {
    this.syncLevel();
    root.getAnimations().forEach((animation) => animation.cancel());
    root.style.removeProperty("opacity");
    root.classList.remove("route-enter");
    this.cancelPendingOverlay();
    if (this.reduced) return;

    root.querySelectorAll(".anime-button, .icon-button, .landing-button").forEach((button) => {
      const ripple = (event) => {
        const rect = button.getBoundingClientRect();
        const dot = document.createElement("i");
        dot.className = "button-ripple";
        dot.style.setProperty("--ripple-x", `${event.clientX - rect.left}px`);
        dot.style.setProperty("--ripple-y", `${event.clientY - rect.top}px`);
        button.append(dot);
        dot.addEventListener("animationend", () => dot.remove(), { once: true });
      };
      button.addEventListener("pointerdown", ripple);
      this.cleanups.push(() => button.removeEventListener("pointerdown", ripple));
    });
  }

  async leave(root, destination = "") {
    if (this.reduced || !root.firstElementChild) return;
    this.cancelPendingOverlay();
    const label = ({ "/create": "制作室", "/templates": "模板书架", "/projects": "作品存档", "/": "卷首" })[destination] || "下一幕";
    const overlay = document.createElement("div");
    overlay.className = "route-curtain";
    overlay.innerHTML = `<span>${label}</span><i></i>`;
    document.body.append(overlay);
    const cover = overlay.animate([{ clipPath: "inset(100% 0 0 0)" }, { clipPath: "inset(0 0 0 0)" }], { duration: 480, easing: "cubic-bezier(.16,1,.3,1)", fill: "forwards" });
    try { await cover.finished; } catch (_) { /* navigation superseded */ }
    this.pendingOverlay = overlay;
  }

  revealPendingOverlay() {
    const overlay = this.pendingOverlay;
    if (!overlay) return;
    this.pendingOverlay = null;
    requestAnimationFrame(() => {
      const reveal = overlay.animate(
        [{ clipPath: "inset(0 0 0 0)" }, { clipPath: "inset(0 0 100% 0)" }],
        { duration: 460, delay: 80, easing: "cubic-bezier(.16,1,.3,1)", fill: "forwards" },
      );
      reveal.finished.catch(() => {}).finally(() => overlay.remove());
    });
  }

  cancelPendingOverlay() {
    this.pendingOverlay?.remove();
    this.pendingOverlay = null;
    document.querySelectorAll(".route-curtain").forEach((overlay) => overlay.remove());
  }

  unmount() {
    this.cleanups.splice(0).forEach((cleanup) => cleanup());
  }
}

export const motionController = new MotionController();
