export function showToast(message, tone = "info", duration = 2800) {
  const region = document.querySelector("#toastRegion");
  if (!region) return;
  const toast = document.createElement("div");
  toast.className = `toast toast--${tone}`;
  toast.innerHTML = `<span aria-hidden="true"></span><p>${escapeHtml(message)}</p>`;
  region.append(toast);
  requestAnimationFrame(() => toast.classList.add("is-visible"));
  window.setTimeout(() => {
    toast.classList.remove("is-visible");
    window.setTimeout(() => toast.remove(), 240);
  }, duration);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

