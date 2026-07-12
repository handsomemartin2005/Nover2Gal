import { escapeHtml } from "/static/js/components/modal.js";

class CommandPalette {
  constructor() {
    this.commands = [];
    this.cleanups = [];
  }

  mount(commands = []) {
    this.unmount();
    this.commands = commands;
    const onKey = (event) => {
      const typing = /INPUT|TEXTAREA|SELECT/.test(event.target?.tagName) || event.target?.isContentEditable;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        this.open();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
        event.preventDefault();
        this.run("save");
      } else if (!typing && event.key === " " && this.has("toggle-stage")) {
        event.preventDefault();
        this.run("toggle-stage");
      } else if (!typing && event.key === "ArrowLeft" && this.has("previous-scene")) {
        event.preventDefault(); this.run("previous-scene");
      } else if (!typing && event.key === "ArrowRight" && this.has("next-scene")) {
        event.preventDefault(); this.run("next-scene");
      }
    };
    document.addEventListener("keydown", onKey);
    this.cleanups.push(() => document.removeEventListener("keydown", onKey));
  }

  open() {
    if (document.querySelector(".command-palette")) return;
    const root = document.querySelector("#overlayRoot");
    root.innerHTML = `<div class="command-backdrop"><section class="command-palette" role="dialog" aria-modal="true" aria-label="命令面板"><div class="command-search"><span>⌘</span><input type="search" placeholder="搜索命令、项目或场景…" aria-label="搜索命令"></div><div class="command-results" role="listbox"></div><footer><span>↑↓ 选择</span><span>Enter 执行</span><span>Esc 关闭</span></footer></section></div>`;
    const backdrop = root.querySelector(".command-backdrop");
    const input = root.querySelector("input");
    const results = root.querySelector(".command-results");
    let activeIndex = 0;
    let filtered = [...this.commands];
    const render = () => {
      results.innerHTML = filtered.map((command, index) => `<button type="button" role="option" class="${index === activeIndex ? "active" : ""}" data-command="${escapeHtml(command.id)}"><span>${escapeHtml(command.label)}</span><small>${escapeHtml(command.hint || "")}</small></button>`).join("") || '<p class="command-empty">没有匹配的命令</p>';
    };
    const close = () => { cleanup(); root.innerHTML = ""; };
    const execute = (id) => { close(); this.run(id); };
    const onInput = () => {
      const query = input.value.toLowerCase().trim();
      filtered = this.commands.filter((command) => `${command.label} ${command.hint || ""}`.toLowerCase().includes(query));
      activeIndex = 0;
      render();
    };
    const onClick = (event) => {
      const button = event.target.closest("[data-command]");
      if (button) execute(button.dataset.command);
      if (event.target === backdrop) close();
    };
    const onKey = (event) => {
      if (event.key === "Escape") close();
      if (event.key === "ArrowDown") { event.preventDefault(); activeIndex = Math.min(activeIndex + 1, filtered.length - 1); render(); }
      if (event.key === "ArrowUp") { event.preventDefault(); activeIndex = Math.max(activeIndex - 1, 0); render(); }
      if (event.key === "Enter" && filtered[activeIndex]) { event.preventDefault(); execute(filtered[activeIndex].id); }
    };
    const cleanup = () => {
      input.removeEventListener("input", onInput);
      backdrop.removeEventListener("click", onClick);
      document.removeEventListener("keydown", onKey, true);
    };
    input.addEventListener("input", onInput);
    backdrop.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey, true);
    render();
    requestAnimationFrame(() => backdrop.classList.add("is-visible"));
    input.focus();
  }

  run(id) { this.commands.find((command) => command.id === id)?.action?.(); }
  has(id) { return this.commands.some((command) => command.id === id); }
  unmount() { this.cleanups.splice(0).forEach((cleanup) => cleanup()); }
}

export const commandPalette = new CommandPalette();
