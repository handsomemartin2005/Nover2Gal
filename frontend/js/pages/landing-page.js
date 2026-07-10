import { api } from "/static/js/api-client.js";

export async function initLandingPage(root) {
  const stage = root.querySelector(".home-character-stage");
  const dialogue = root.querySelector("[data-typewriter]");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches || document.documentElement.dataset.motion === "reduced";
  const cleanups = [];

  if (stage) {
    const onMove = (event) => {
      if (reduced || window.innerWidth < 768) return;
      const rect = stage.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width - 0.5) * 6;
      const y = ((event.clientY - rect.top) / rect.height - 0.5) * 4;
      stage.style.setProperty("--parallax-x", `${x.toFixed(2)}px`);
      stage.style.setProperty("--parallax-y", `${y.toFixed(2)}px`);
    };
    const onLeave = () => {
      stage.style.setProperty("--parallax-x", "0px");
      stage.style.setProperty("--parallax-y", "0px");
    };
    stage.addEventListener("pointermove", onMove);
    stage.addEventListener("pointerleave", onLeave);
    cleanups.push(() => stage.removeEventListener("pointermove", onMove), () => stage.removeEventListener("pointerleave", onLeave));
  }

  if (dialogue && !reduced) {
    const copy = dialogue.textContent.trim();
    dialogue.textContent = "";
    let index = 0;
    const timer = window.setInterval(() => {
      dialogue.textContent = copy.slice(0, ++index);
      if (index >= copy.length) window.clearInterval(timer);
    }, 34);
    cleanups.push(() => window.clearInterval(timer));
  }

  try {
    const response = await api.listProjects();
    const latest = [...(response.projects || [])].sort((a, b) => (b.updated_at || 0) - (a.updated_at || 0))[0];
    if (latest) fillRecentProject(root, latest);
  } catch (_) {
    /* The first-run card remains useful while the backend is unavailable. */
  }

  return () => cleanups.forEach((cleanup) => cleanup());
}

function fillRecentProject(root, project) {
  const title = root.querySelector("[data-home-recent-title]");
  const meta = root.querySelector("[data-home-recent-meta]");
  const progress = root.querySelector("[data-home-recent-progress]");
  const percent = root.querySelector("[data-home-recent-percent]");
  const link = root.querySelector("[data-home-recent-link]");
  const cover = root.querySelector("[data-home-recent-cover]");
  const value = Number(project.progress || (project.has_result ? 100 : 0));
  title.textContent = `《${project.title || "未命名企划"}》`;
  meta.textContent = `${project.pov_character || "自动视角"} · ${project.scene_count || 0} 个场景 · ${relativeTime(project.updated_at)}`;
  progress.style.width = `${Math.max(0, Math.min(100, value))}%`;
  percent.textContent = `${value}%`;
  link.textContent = "继续制作 →";
  link.href = `/create?project_id=${encodeURIComponent(project.project_id)}`;
  cover.classList.add("has-project");
  cover.innerHTML = `<span>${String(project.scene_count || 0).padStart(2, "0")}</span><small>场景存档</small>`;
}

function relativeTime(value) {
  if (!value) return "尚未保存";
  const seconds = Math.max(0, Date.now() / 1000 - value);
  if (seconds < 60) return "刚刚编辑";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`;
  return `${Math.floor(seconds / 86400)} 天前`;
}
