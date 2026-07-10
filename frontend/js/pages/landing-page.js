import { api } from "/static/js/api-client.js";

export function initLandingPage(root) {
  const deck = root.querySelector("#folioDeck");
  const cards = [...root.querySelectorAll("[data-folio]")];
  const cleanups = [];
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.motion === "reduced";

  const activate = (card) => {
    if (!deck || window.innerWidth < 760) return;
    deck.classList.add("is-exploded");
    deck.dataset.activeFolio = card.dataset.folio || "";
    cards.forEach((item) => item.classList.toggle("is-active", item === card));
  };

  const reset = () => {
    if (!deck) return;
    deck.classList.remove("is-exploded");
    delete deck.dataset.activeFolio;
    cards.forEach((item) => {
      item.classList.remove("is-active");
      item.style.removeProperty("--tilt-x");
      item.style.removeProperty("--tilt-y");
    });
  };

  cards.forEach((card) => {
    const onEnter = () => activate(card);
    const onFocus = () => activate(card);
    const onMove = (event) => {
      if (reduced || !card.classList.contains("is-active")) return;
      const rect = card.getBoundingClientRect();
      const tiltY = ((event.clientX - rect.left) / rect.width - .5) * 4;
      const tiltX = ((event.clientY - rect.top) / rect.height - .5) * -3;
      card.style.setProperty("--tilt-x", `${tiltX.toFixed(2)}deg`);
      card.style.setProperty("--tilt-y", `${tiltY.toFixed(2)}deg`);
    };
    card.addEventListener("pointerenter", onEnter);
    card.addEventListener("focus", onFocus);
    card.addEventListener("pointermove", onMove);
    cleanups.push(
      () => card.removeEventListener("pointerenter", onEnter),
      () => card.removeEventListener("focus", onFocus),
      () => card.removeEventListener("pointermove", onMove),
    );
  });

  if (deck) {
    const onLeave = () => reset();
    const onFocusOut = () => window.setTimeout(() => {
      if (!deck.contains(document.activeElement)) reset();
    }, 0);
    deck.addEventListener("pointerleave", onLeave);
    deck.addEventListener("focusout", onFocusOut);
    cleanups.push(() => deck.removeEventListener("pointerleave", onLeave), () => deck.removeEventListener("focusout", onFocusOut));
  }

  hydrateRecentProject(root).catch(() => {
    /* The archive entry remains useful while the project API is unavailable. */
  });

  return () => cleanups.forEach((cleanup) => cleanup());
}

async function hydrateRecentProject(root) {
  const response = await api.listProjects();
  const latest = [...(response.projects || [])].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0))[0];
  if (!latest) return;
  const card = root.querySelector("[data-folio-recent]");
  const title = root.querySelector("[data-folio-recent-title]");
  const meta = root.querySelector("[data-folio-recent-meta]");
  const action = root.querySelector("[data-folio-recent-action]");
  if (!card || !title || !meta) return;
  card.href = `/create?project_id=${encodeURIComponent(latest.project_id)}`;
  title.textContent = `继续《${latest.title || "未命名企划"}》`;
  meta.textContent = `${latest.scene_count || 0} 个场景 · ${relativeTime(latest.updated_at)}`;
  if (action) action.innerHTML = "回到上次一幕 <i>→</i>";
}

function relativeTime(value) {
  if (!value) return "尚未保存";
  const seconds = Math.max(0, Date.now() / 1000 - value);
  if (seconds < 60) return "刚刚编辑";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`;
  return `${Math.floor(seconds / 86400)} 天前`;
}
