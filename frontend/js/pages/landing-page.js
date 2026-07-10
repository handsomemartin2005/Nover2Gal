import { api } from "/static/js/api-client.js";

export function initLandingPage(root) {
  const deck = root.querySelector("#folioDeck");
  const cards = [...root.querySelectorAll("[data-folio]")];
  const cleanups = [];
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.motion === "reduced";
  let activeCard = null;

  const activate = (card) => {
    if (!deck || window.innerWidth < 760) return;
    if (!card || !deck.contains(card)) return;
    activeCard = card;
    deck.classList.add("is-exploded");
    deck.dataset.activeFolio = card.dataset.folio || "";
    cards.forEach((item) => item.classList.toggle("is-active", item === card));
  };

  const reset = () => {
    if (!deck) return;
    activeCard = null;
    deck.classList.remove("is-exploded");
    delete deck.dataset.activeFolio;
    cards.forEach((item) => {
      item.classList.remove("is-active");
      item.style.removeProperty("--tilt-x");
      item.style.removeProperty("--tilt-y");
    });
  };

  if (deck) {
    deck.dataset.folioReady = "true";
    const cardFromEvent = (event) => event.target instanceof Element ? event.target.closest("[data-folio]") : null;
    const onEnter = (event) => activate(cardFromEvent(event));
    const onFocus = (event) => activate(cardFromEvent(event));
    const onMove = (event) => {
      if (reduced || !activeCard) return;
      const rect = activeCard.getBoundingClientRect();
      const tiltY = ((event.clientX - rect.left) / rect.width - .5) * 4;
      const tiltX = ((event.clientY - rect.top) / rect.height - .5) * -3;
      activeCard.style.setProperty("--tilt-x", `${tiltX.toFixed(2)}deg`);
      activeCard.style.setProperty("--tilt-y", `${tiltY.toFixed(2)}deg`);
    };
    const onLeave = () => reset();
    const onFocusOut = () => window.setTimeout(() => {
      if (!deck.contains(document.activeElement)) reset();
    }, 0);
    deck.addEventListener("pointerover", onEnter);
    deck.addEventListener("mouseover", onEnter);
    deck.addEventListener("focusin", onFocus);
    deck.addEventListener("pointermove", onMove);
    deck.addEventListener("mousemove", onMove);
    deck.addEventListener("pointerleave", onLeave);
    deck.addEventListener("mouseleave", onLeave);
    deck.addEventListener("focusout", onFocusOut);
    cleanups.push(
      () => deck.removeEventListener("pointerover", onEnter),
      () => deck.removeEventListener("mouseover", onEnter),
      () => deck.removeEventListener("focusin", onFocus),
      () => deck.removeEventListener("pointermove", onMove),
      () => deck.removeEventListener("mousemove", onMove),
      () => deck.removeEventListener("pointerleave", onLeave),
      () => deck.removeEventListener("mouseleave", onLeave),
      () => deck.removeEventListener("focusout", onFocusOut),
      () => delete deck.dataset.folioReady,
    );
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
