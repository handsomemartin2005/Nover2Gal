import { api } from "/static/js/api-client.js?v=20260713-byok1";
import { loadCurrentUser, setCurrentUser } from "/static/js/auth-state.js?v=20260710-auth6";
import { escapeHtml } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";

export async function initAccountPage(root) {
  const host = root.querySelector("#accountContent");
  if (!host) return () => {};
  let user = await loadCurrentUser({ force: true });
  let apiState = null;

  const renderAccount = async () => {
    if (!user) { renderAuthForms(host); return; }
    const [settings, usage] = await Promise.all([
      api.getApiConfigs().catch(() => ({ configs: [], services: {} })),
      api.getUsage().catch(() => null),
    ]);
    apiState = settings;
    renderProfile(host, user, settings, usage);
  };
  await renderAccount();

  const onSubmit = async (event) => {
    const form = event.target.closest("form[data-auth-form]");
    if (!form) return;
    event.preventDefault();
    const submit = form.querySelector('button[type="submit"]');
    const error = form.querySelector("[data-form-error]");
    if (submit) submit.disabled = true;
    if (error) error.textContent = "";
    try {
      const fields = new FormData(form);
      if (form.dataset.authForm === "login") {
        const loginType = fields.get("login_type") || "user";
        const payload = await api.login({ username: fields.get("username"), password: fields.get("password"), login_type: loginType });
        setCurrentUser(payload.user);
        window.location.assign(loginType === "admin" ? "/admin" : safeNextPath());
      } else if (form.dataset.authForm === "register") {
        if (fields.get("password") !== fields.get("password_confirm")) throw new Error("两次输入的密码不一致");
        const payload = await api.register({ username: fields.get("username"), display_name: fields.get("display_name"), password: fields.get("password") });
        setCurrentUser(payload.user);
        window.location.assign(safeNextPath());
      } else if (form.dataset.authForm === "profile") {
        const payload = await api.updateProfile({ display_name: String(fields.get("display_name") || "").trim() });
        user = payload.user;
        setCurrentUser(user);
        showToast("个人资料已更新", "success");
        await renderAccount();
      } else if (form.dataset.authForm === "password") {
        if (fields.get("new_password") !== fields.get("password_confirm")) throw new Error("两次输入的新密码不一致");
        await api.changePassword({ current_password: fields.get("current_password"), new_password: fields.get("new_password") });
        showToast("密码已更新，请重新登录", "success");
        setCurrentUser(null);
        window.location.assign("/account");
      } else if (form.dataset.authForm === "api-config") {
        await api.saveApiConfig(fields.get("service_type"), {
          provider: fields.get("provider"), api_format: fields.get("api_format"),
          base_url: String(fields.get("base_url") || "").trim(), model: String(fields.get("model") || "").trim(),
          api_key: String(fields.get("api_key") || "").trim(), enabled: fields.get("enabled") === "on",
        });
        showToast("API 配置已安全保存", "success");
        await renderAccount();
      }
    } catch (cause) {
      if (error) error.textContent = cause.message || "操作失败";
      if (submit) submit.disabled = false;
    }
  };

  const onClick = async (event) => {
    const tab = event.target.closest("[data-account-tab]");
    if (tab) {
      host.querySelectorAll("[data-account-tab]").forEach((item) => item.classList.toggle("active", item === tab));
      host.querySelectorAll("[data-auth-panel]").forEach((panel) => { panel.hidden = panel.dataset.authPanel !== tab.dataset.accountTab; });
    }
    const removeApi = event.target.closest("[data-api-remove]");
    if (removeApi) {
      removeApi.disabled = true;
      try {
        await api.deleteApiConfig(removeApi.dataset.apiRemove);
        showToast("API 配置已移除", "success");
        await renderAccount();
      } catch (error) { showToast(error.message, "error"); removeApi.disabled = false; }
    }
    if (event.target.closest("[data-account-logout]")) {
      await api.logout();
      setCurrentUser(null);
      window.location.assign("/");
    }
  };

  const onChange = (event) => {
    const select = event.target.closest("[data-api-preset]");
    if (!select || !apiState) return;
    const form = select.closest("form");
    const preset = (apiState.services?.[form.dataset.service] || []).find((item) => item.id === select.value);
    if (!preset) return;
    form.elements.provider.value = preset.id;
    form.elements.api_format.value = preset.api_format || "";
    form.elements.base_url.value = preset.base_url || "";
    form.elements.model.value = preset.model || "";
  };
  host.addEventListener("submit", onSubmit);
  host.addEventListener("click", onClick);
  host.addEventListener("change", onChange);
  return () => {
    host.removeEventListener("submit", onSubmit);
    host.removeEventListener("click", onClick);
    host.removeEventListener("change", onChange);
  };
}

function renderAuthForms(host) {
  host.innerHTML = `<section class="identity-card">
    <div class="identity-intro"><span>PRIVATE WORKSPACE</span><h1>登录你的创作空间</h1><p>项目、原文和私人样例只对账号本人可见。管理员请选择专用入口。</p><ul><li>项目与原文默认私密</li><li>HttpOnly 会话保护</li><li>用户 API 密钥按账号隔离</li></ul></div>
    <div class="identity-forms"><nav class="identity-tabs"><button class="active" type="button" data-account-tab="login">登录</button><button type="button" data-account-tab="register">注册</button></nav>
      <form data-auth-form="login" data-auth-panel="login">
        <label>登录入口<select name="login_type"><option value="user">用户登录</option><option value="admin">管理员登录</option></select></label>
        <label>用户名<input name="username" required autocomplete="username" minlength="3" maxlength="32"></label>
        <label>密码<input name="password" type="password" required autocomplete="current-password" minlength="8" maxlength="128"></label>
        <p class="form-error" data-form-error role="alert"></p><button class="anime-button anime-button--primary" type="submit">登录</button>
      </form>
      <form data-auth-form="register" data-auth-panel="register" hidden>
        <label>用户名<input name="username" required autocomplete="username" minlength="3" maxlength="32" pattern="[A-Za-z0-9_.-]+"><small>3–32 位字母、数字、点、横线或下划线</small></label>
        <label>显示名称<input name="display_name" autocomplete="name" maxlength="60" placeholder="用于页面显示"></label>
        <label>密码<input name="password" type="password" required autocomplete="new-password" minlength="8" maxlength="128"></label>
        <label>确认密码<input name="password_confirm" type="password" required autocomplete="new-password" minlength="8" maxlength="128"></label>
        <p class="form-error" data-form-error role="alert"></p><button class="anime-button anime-button--primary" type="submit">建立账号</button>
      </form>
    </div></section>`;
}

function renderProfile(host, user, apiState, usage) {
  host.innerHTML = `<section class="account-dashboard">
    <header><div><span>ACCOUNT</span><h1>${escapeHtml(user.display_name || user.username)}</h1><p>@${escapeHtml(user.username)} · ${user.role === "admin" ? "管理员" : "创作者"}</p></div><div class="account-actions">${user.role === "admin" ? '<a class="anime-button anime-button--primary" href="/admin">进入管理平台</a>' : ""}<button class="anime-button anime-button--ghost" type="button" data-account-logout>退出登录</button></div></header>
    <div class="account-settings-grid">
      <form class="account-setting" data-auth-form="profile"><span>01</span><h2>个人资料</h2><label>显示名称<input name="display_name" required maxlength="60" value="${escapeHtml(user.display_name || user.username)}"></label><p class="form-error" data-form-error></p><button class="anime-button anime-button--primary" type="submit">保存资料</button></form>
      <form class="account-setting" data-auth-form="password"><span>02</span><h2>修改密码</h2><label>当前密码<input name="current_password" type="password" required autocomplete="current-password"></label><label>新密码<input name="new_password" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label><label>确认新密码<input name="password_confirm" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label><p class="form-error" data-form-error></p><button class="anime-button anime-button--primary" type="submit">更新密码</button></form>
    </div>
    <section class="api-settings-section"><header><div><span>BRING YOUR OWN API</span><h2>模型 API 配置</h2><p>文本负责小说理解与改编，生图负责角色和场景，语音负责对白合成。</p></div></header><div class="api-settings-grid">${["text", "image", "tts"].map((service) => apiConfigCard(service, apiState)).join("")}</div></section>
    ${usageCard(usage)}
  </section>`;
}

function apiConfigCard(service, state) {
  const labels = { text: ["文本处理 API", "03"], image: ["角色 / 场景生图 API", "04"], tts: ["语音合成 API", "05"] };
  const config = (state.configs || []).find((item) => item.service_type === service) || {};
  const presets = state.services?.[service] || [];
  const currentProvider = config.provider || presets[0]?.id || "custom";
  const selectedPreset = presets.find((item) => item.id === currentProvider) || {};
  const options = presets.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === currentProvider ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("");
  return `<form class="account-setting api-setting" data-auth-form="api-config" data-service="${service}"><span>${labels[service][1]}</span><h2>${labels[service][0]}</h2>
    <input type="hidden" name="service_type" value="${service}"><input type="hidden" name="provider" value="${escapeHtml(currentProvider)}"><input type="hidden" name="api_format" value="${escapeHtml(config.api_format || selectedPreset.api_format || "")}">
    <label>供应商预设<select data-api-preset>${options}</select></label>
    <label>Base URL<input name="base_url" type="url" required value="${escapeHtml(config.base_url || selectedPreset.base_url || "")}" placeholder="https://api.example.com/v1"></label>
    <label>模型名称<input name="model" required value="${escapeHtml(config.model || selectedPreset.model || "")}" placeholder="模型 ID"></label>
    <label>API Key<input name="api_key" type="password" autocomplete="off" placeholder="${escapeHtml(config.api_key_masked || "保存后不会再次明文显示")}"></label>
    <label class="api-enabled"><input name="enabled" type="checkbox" ${config.enabled !== false ? "checked" : ""}> 启用此 API</label>
    <p class="form-error" data-form-error></p><div class="api-form-actions"><button class="anime-button anime-button--primary" type="submit">保存配置</button>${config.has_api_key ? `<button class="anime-button anime-button--ghost" type="button" data-api-remove="${service}">移除</button>` : ""}</div>
  </form>`;
}

function usageCard(usage) {
  if (!usage) return "";
  const total = usage.totals || {};
  return `<section class="account-usage"><header><span>USAGE · ${Number(usage.period_days || 30)} DAYS</span><h2>我的 API 用量</h2></header><div class="usage-stats">${usageStat("调用", total.calls)}${usageStat("输入 Token", total.tokens_input)}${usageStat("输出 Token", total.tokens_output)}${usageStat("语音字符", total.characters)}${usageStat("生成图片", total.units)}${usageStat("失败", total.failures)}</div></section>`;
}

function usageStat(label, value) { return `<article><small>${label}</small><strong>${Number(value || 0).toLocaleString()}</strong></article>`; }
function safeNextPath() { const next = new URLSearchParams(window.location.search).get("next") || "/projects"; return next.startsWith("/") && !next.startsWith("//") ? next : "/projects"; }
