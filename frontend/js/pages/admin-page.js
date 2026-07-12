import { api } from "/static/js/api-client.js?v=20260713-byok1";
import { loadCurrentUser } from "/static/js/auth-state.js?v=20260710-auth6";
import { confirmModal, escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

export async function initAdminPage(root) {
  const host = root.querySelector("#adminContent");
  if (!host) return () => {};
  const currentUser = await loadCurrentUser({ force: true });
  if (!currentUser) {
    host.innerHTML = accessState("需要登录", "登录管理员账号后才能访问管理平台。", "/account", "前往登录");
    return () => {};
  }
  if (currentUser.role !== "admin") {
    host.innerHTML = accessState("没有管理权限", "当前账号只能访问自己的项目和样例。", "/projects", "返回我的项目");
    return () => {};
  }

  let state;
  try {
    state = await loadAdminState();
  } catch (error) {
    host.innerHTML = accessState("管理数据读取失败", error.message || "请稍后再试。", "/account", "返回账号页");
    return () => {};
  }
  render(host, state, currentUser);

  const refresh = async () => {
    state = await loadAdminState();
    render(host, state, currentUser);
  };
  const onClick = async (event) => {
    const tab = event.target.closest("[data-admin-tab]");
    if (tab) {
      host.querySelectorAll("[data-admin-tab]").forEach((item) => item.classList.toggle("active", item === tab));
      host.querySelectorAll("[data-admin-panel]").forEach((panel) => { panel.hidden = panel.dataset.adminPanel !== tab.dataset.adminTab; });
      return;
    }
    const action = event.target.closest("[data-admin-action]");
    if (!action) return;
    action.disabled = true;
    try {
      const id = action.dataset.id;
      if (action.dataset.adminAction === "toggle-user") {
        const user = state.users.find((item) => item.user_id === id);
        await api.adminUpdateUser(id, { status: user.status === "active" ? "suspended" : "active" });
      }
      if (action.dataset.adminAction === "toggle-role") {
        const user = state.users.find((item) => item.user_id === id);
        await api.adminUpdateUser(id, { role: user.role === "admin" ? "user" : "admin" });
      }
      if (action.dataset.adminAction === "assign-project") {
        const ownerId = action.closest("tr").querySelector("[data-owner-select]").value;
        await api.adminAssignProject(id, ownerId);
      }
      if (action.dataset.adminAction === "delete-project") {
        const confirmed = await confirmModal({ title: "删除项目？", message: "项目原文、脚本和版本将永久删除。", confirmLabel: "确认删除", danger: true });
        if (!confirmed) { action.disabled = false; return; }
        await api.adminDeleteProject(id);
      }
      if (action.dataset.adminAction === "toggle-sample") {
        const sample = state.samples.find((item) => item.sample_id === id);
        await api.adminUpdateSample(id, { visibility: sample.visibility === "public" ? "private" : "public" });
      }
      if (action.dataset.adminAction === "assign-sample") {
        const ownerId = action.closest("tr").querySelector("[data-owner-select]").value;
        await api.adminAssignSample(id, ownerId);
      }
      if (action.dataset.adminAction === "delete-sample") {
        const confirmed = await confirmModal({ title: "删除样例？", message: "该样例将从模板库永久移除。", confirmLabel: "确认删除", danger: true });
        if (!confirmed) { action.disabled = false; return; }
        await api.adminDeleteSample(id);
      }
      showToast("管理操作已完成", "success");
      await refresh();
    } catch (error) {
      action.disabled = false;
      showToast(error.message, "error");
    }
  };
  host.addEventListener("click", onClick);
  return () => host.removeEventListener("click", onClick);
}

async function loadAdminState() {
  const [overview, users, projects, samples, usage] = await Promise.all([
    api.adminOverview(), api.adminUsers(), api.adminProjects(), api.adminSamples(), api.adminUsage(),
  ]);
  return { overview, users: users.users || [], projects: projects.projects || [], samples: samples.samples || [], usage };
}

function render(host, state, currentUser) {
  host.innerHTML = `
    <section class="admin-dashboard">
      <header class="admin-heading"><div><span>ADMIN CONSOLE</span><h1>站点管理平台</h1><p>${escapeHtml(currentUser.display_name)} · 用户、项目与公开内容治理</p></div><a class="anime-button anime-button--ghost" href="/account">账号设置</a></header>
      <section class="admin-stats">${stat("用户", state.overview.users)}${stat("项目", state.overview.projects)}${stat("API 调用 · 30天", state.usage.totals.calls)}${stat("总 Token · 30天", Number(state.usage.totals.tokens_input || 0) + Number(state.usage.totals.tokens_output || 0))}${stat("失败调用", state.usage.totals.failures)}</section>
      <nav class="admin-tabs"><button class="active" type="button" data-admin-tab="users">用户</button><button type="button" data-admin-tab="usage">API 用量</button><button type="button" data-admin-tab="projects">项目</button><button type="button" data-admin-tab="samples">样例与公开状态</button></nav>
      <section class="admin-panel" data-admin-panel="users">${usersTable(state.users, currentUser)}</section>
      <section class="admin-panel" data-admin-panel="usage" hidden>${usageTable(state.usage)}</section>
      <section class="admin-panel" data-admin-panel="projects" hidden>${projectsTable(state.projects, state.users)}</section>
      <section class="admin-panel" data-admin-panel="samples" hidden>${samplesTable(state.samples, state.users)}</section>
    </section>`;
}

function usersTable(users, currentUser) {
  const rows = users.map((user) => `<tr><td><strong>${escapeHtml(user.display_name)}</strong><small>@${escapeHtml(user.username)}</small></td><td><span class="admin-badge">${user.role === "admin" ? "管理员" : "用户"}</span></td><td><span class="admin-badge admin-badge--${user.status}">${user.status === "active" ? "正常" : "已停用"}</span></td><td>${user.project_count} 项目 / ${user.sample_count} 样例</td><td>${user.user_id === currentUser.user_id ? "当前账号" : `<button type="button" data-admin-action="toggle-role" data-id="${user.user_id}">${user.role === "admin" ? "降为用户" : "设为管理员"}</button><button type="button" data-admin-action="toggle-user" data-id="${user.user_id}">${user.status === "active" ? "停用" : "启用"}</button>`}</td></tr>`).join("");
  return table("用户账号", "用户名、角色和账号状态", "<th>账号</th><th>角色</th><th>状态</th><th>内容</th><th>操作</th>", rows);
}

function projectsTable(projects, users) {
  const rows = projects.map((project) => `<tr><td><strong>${escapeHtml(project.title)}</strong><small>${escapeHtml(project.project_id)}</small></td><td>${escapeHtml(project.owner_display_name)}<small>@${escapeHtml(project.owner_username)}</small></td><td>${escapeHtml(project.status || "draft")} · ${project.scene_count || 0} 场景</td><td><select data-owner-select>${ownerOptions(users, project.owner_id)}</select><button type="button" data-admin-action="assign-project" data-id="${project.project_id}">转移</button><button class="danger-text" type="button" data-admin-action="delete-project" data-id="${project.project_id}">删除</button></td></tr>`).join("");
  return table("项目归属", "管理员只能查看元数据，不在列表中展示原文", "<th>项目</th><th>所有者</th><th>状态</th><th>操作</th>", rows);
}

function samplesTable(samples, users) {
  const rows = samples.map((sample) => `<tr><td><strong>${escapeHtml(sample.title)}</strong><small>${escapeHtml(sample.category || "其他")}</small></td><td>@${escapeHtml(sample.owner_username)}</td><td><span class="admin-badge admin-badge--${sample.visibility}">${sample.visibility === "public" ? "公开" : "私密"}</span></td><td><select data-owner-select>${ownerOptions(users, sample.owner_id)}</select><button type="button" data-admin-action="assign-sample" data-id="${sample.sample_id}">转移</button><button type="button" data-admin-action="toggle-sample" data-id="${sample.sample_id}">${sample.visibility === "public" ? "设为私密" : "设为公开"}</button><button class="danger-text" type="button" data-admin-action="delete-sample" data-id="${sample.sample_id}">删除</button></td></tr>`).join("");
  return table("样例可见性", "只有公开样例会出现在其他用户的模板库", "<th>样例</th><th>所有者</th><th>可见性</th><th>操作</th>", rows);
}

function usageTable(usage) {
  const rows = (usage.events || []).map((event) => `<tr><td><strong>${escapeHtml(event.display_name || event.username)}</strong><small>@${escapeHtml(event.username)}</small></td><td>${serviceLabel(event.service_type)}<small>${escapeHtml(event.provider)} · ${escapeHtml(event.model)}</small></td><td>${Number(event.tokens_input || 0).toLocaleString()} / ${Number(event.tokens_output || 0).toLocaleString()}<small>输入 / 输出 Token</small></td><td>${event.service_type === "tts" ? `${Number(event.characters || 0).toLocaleString()} 字符` : event.service_type === "image" ? `${Number(event.units || 0)} 张` : "—"}</td><td><span class="admin-badge admin-badge--${event.status === "success" ? "active" : "suspended"}">${event.status === "success" ? "成功" : "失败"}</span><small>${Number(event.duration_ms || 0).toLocaleString()} ms · ${formatTime(event.created_at)}</small></td></tr>`).join("");
  return table("API 用量详情", "最近 30 天的用户自带 API 调用账本，不保存请求正文和密钥", "<th>用户</th><th>服务 / 模型</th><th>Token</th><th>计量</th><th>状态 / 时间</th>", rows);
}

function table(title, note, heads, rows) {
  return `<header><div><h2>${title}</h2><p>${note}</p></div></header><div class="admin-table-wrap"><table><thead><tr>${heads}</tr></thead><tbody>${rows || '<tr><td colspan="5">暂无数据</td></tr>'}</tbody></table></div>`;
}
function stat(label, value) { return `<article><small>${label}</small><strong>${Number(value || 0)}</strong></article>`; }
function serviceLabel(value) { return ({ text: "文本处理", image: "生图", tts: "语音" })[value] || value; }
function formatTime(value) { return value ? new Date(Number(value) * 1000).toLocaleString("zh-CN") : "—"; }
function ownerOptions(users, selected) { return users.map((user) => `<option value="${user.user_id}" ${user.user_id === selected ? "selected" : ""}>${escapeHtml(user.display_name)} (@${escapeHtml(user.username)})</option>`).join(""); }
function accessState(title, copy, href, label) { return `<section class="admin-access-state"><span>403</span><h1>${title}</h1><p>${copy}</p><a class="anime-button anime-button--primary" href="${href}">${label}</a></section>`; }
