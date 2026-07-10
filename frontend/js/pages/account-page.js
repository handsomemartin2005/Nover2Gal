import { api } from "/static/js/api-client.js?v=20260710-auth6";
import { loadCurrentUser, setCurrentUser } from "/static/js/auth-state.js?v=20260710-auth6";
import { escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

export async function initAccountPage(root) {
  const host = root.querySelector("#accountContent");
  const user = await loadCurrentUser({ force: true });
  if (!host) return () => {};
  if (user) renderProfile(host, user);
  else renderAuthForms(host);

  const onSubmit = async (event) => {
    const form = event.target.closest("form[data-auth-form]");
    if (!form) return;
    event.preventDefault();
    const submit = form.querySelector('button[type="submit"]');
    const error = form.querySelector("[data-form-error]");
    submit.disabled = true;
    error.textContent = "";
    try {
      const fields = new FormData(form);
      if (form.dataset.authForm === "login") {
        const payload = await api.login({ username: fields.get("username"), password: fields.get("password") });
        setCurrentUser(payload.user);
        window.location.assign(safeNextPath());
      }
      if (form.dataset.authForm === "register") {
        if (fields.get("password") !== fields.get("password_confirm")) throw new Error("两次输入的密码不一致");
        const payload = await api.register({ username: fields.get("username"), display_name: fields.get("display_name"), password: fields.get("password") });
        setCurrentUser(payload.user);
        window.location.assign(safeNextPath());
      }
      if (form.dataset.authForm === "profile") {
        const payload = await api.updateProfile({ display_name: String(fields.get("display_name") || "").trim() });
        setCurrentUser(payload.user);
        showToast("个人资料已更新", "success");
        renderProfile(host, payload.user);
      }
      if (form.dataset.authForm === "password") {
        if (fields.get("new_password") !== fields.get("password_confirm")) throw new Error("两次输入的新密码不一致");
        await api.changePassword({ current_password: fields.get("current_password"), new_password: fields.get("new_password") });
        showToast("密码已更新，请重新登录", "success");
        setCurrentUser(null);
        window.location.assign("/account");
      }
    } catch (cause) {
      error.textContent = cause.message || "操作失败";
      submit.disabled = false;
    }
  };
  const onClick = async (event) => {
    const tab = event.target.closest("[data-account-tab]");
    if (tab) {
      host.querySelectorAll("[data-account-tab]").forEach((item) => item.classList.toggle("active", item === tab));
      host.querySelectorAll("[data-auth-panel]").forEach((panel) => { panel.hidden = panel.dataset.authPanel !== tab.dataset.accountTab; });
    }
    if (event.target.closest("[data-account-logout]")) {
      await api.logout();
      setCurrentUser(null);
      window.location.assign("/");
    }
  };
  host.addEventListener("submit", onSubmit);
  host.addEventListener("click", onClick);
  return () => {
    host.removeEventListener("submit", onSubmit);
    host.removeEventListener("click", onClick);
  };
}

function renderAuthForms(host) {
  host.innerHTML = `
    <section class="identity-card">
      <div class="identity-intro"><span>PRIVATE WORKSPACE</span><h1>登录你的创作空间</h1><p>项目、原文和私人样例只对账号本人可见。公开内容必须经过单独确认。</p><ul><li>项目与原文默认私密</li><li>HttpOnly 会话保护</li><li>公开样例不包含原文全文</li></ul></div>
      <div class="identity-forms">
        <nav class="identity-tabs"><button class="active" type="button" data-account-tab="login">登录</button><button type="button" data-account-tab="register">注册</button></nav>
        <form data-auth-form="login" data-auth-panel="login">
          <label>用户名<input name="username" required autocomplete="username" minlength="3" maxlength="32"></label>
          <label>密码<input name="password" type="password" required autocomplete="current-password" minlength="8" maxlength="128"></label>
          <p class="form-error" data-form-error role="alert"></p>
          <button class="anime-button anime-button--primary" type="submit">进入创作空间</button>
        </form>
        <form data-auth-form="register" data-auth-panel="register" hidden>
          <label>用户名<input name="username" required autocomplete="username" minlength="3" maxlength="32" pattern="[A-Za-z0-9_.-]+"><small>3–32 位字母、数字、点、横线或下划线</small></label>
          <label>显示名称<input name="display_name" autocomplete="name" maxlength="60" placeholder="用于页面显示"></label>
          <label>密码<input name="password" type="password" required autocomplete="new-password" minlength="8" maxlength="128"></label>
          <label>确认密码<input name="password_confirm" type="password" required autocomplete="new-password" minlength="8" maxlength="128"></label>
          <p class="form-error" data-form-error role="alert"></p>
          <button class="anime-button anime-button--primary" type="submit">建立账号</button>
        </form>
      </div>
    </section>`;
}

function renderProfile(host, user) {
  host.innerHTML = `
    <section class="account-dashboard">
      <header><div><span>ACCOUNT</span><h1>${escapeHtml(user.display_name || user.username)}</h1><p>@${escapeHtml(user.username)} · ${user.role === "admin" ? "管理员" : "创作者"}</p></div><div class="account-actions">${user.role === "admin" ? '<a class="anime-button anime-button--primary" href="/admin">进入管理平台</a>' : ""}<button class="anime-button anime-button--ghost" type="button" data-account-logout>退出登录</button></div></header>
      <div class="account-settings-grid">
        <form class="account-setting" data-auth-form="profile"><span>01</span><h2>个人资料</h2><label>显示名称<input name="display_name" required maxlength="60" value="${escapeHtml(user.display_name || user.username)}"></label><p class="form-error" data-form-error></p><button class="anime-button anime-button--primary" type="submit">保存资料</button></form>
        <form class="account-setting" data-auth-form="password"><span>02</span><h2>修改密码</h2><label>当前密码<input name="current_password" type="password" required autocomplete="current-password"></label><label>新密码<input name="new_password" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label><label>确认新密码<input name="password_confirm" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label><p class="form-error" data-form-error></p><button class="anime-button anime-button--primary" type="submit">更新密码</button></form>
      </div>
    </section>`;
}

function safeNextPath() {
  const next = new URLSearchParams(window.location.search).get("next") || "/projects";
  return next.startsWith("/") && !next.startsWith("//") ? next : "/projects";
}
