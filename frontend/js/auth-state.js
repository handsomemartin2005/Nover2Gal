import { api } from "/static/js/api-client.js?v=20260710-auth2";

let currentUser = null;
let loaded = false;
let pending = null;

export async function loadCurrentUser({ force = false } = {}) {
  if (loaded && !force) return currentUser;
  if (pending && !force) return pending;
  pending = api.getMe()
    .then((payload) => {
      currentUser = payload.user || null;
      loaded = true;
      return currentUser;
    })
    .catch(() => {
      currentUser = null;
      loaded = true;
      return null;
    })
    .finally(() => { pending = null; });
  return pending;
}

export function getCurrentUser() {
  return currentUser;
}

export function setCurrentUser(user) {
  currentUser = user || null;
  loaded = true;
  window.dispatchEvent(new CustomEvent("novel2gal:auth-change", { detail: currentUser }));
}

export async function hydrateAuthShell(root = document) {
  const user = await loadCurrentUser();
  const slot = root.querySelector("[data-auth-slot]");
  if (!slot) return user;
  slot.innerHTML = user ? authenticatedMarkup(user) : '<a class="account-link" href="/account">登录 / 注册</a>';
  slot.querySelector("[data-auth-logout]")?.addEventListener("click", async () => {
    const button = slot.querySelector("[data-auth-logout]");
    button.disabled = true;
    try { await api.logout(); } catch (_) { /* The local session is cleared below. */ }
    setCurrentUser(null);
    window.location.assign("/");
  });
  return user;
}

function authenticatedMarkup(user) {
  const admin = user.role === "admin" ? '<a href="/admin">管理台</a>' : "";
  return `<div class="account-menu"><a class="account-link" href="/account"><span>${escapeHtml(user.display_name || user.username)}</span><small>@${escapeHtml(user.username)}</small></a>${admin}<button type="button" data-auth-logout>退出</button></div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
