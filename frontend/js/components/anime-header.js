const navItems = [
  ["/", "首页"],
  ["/templates", "模板与案例"],
  ["/create", "开始制作"],
  ["/projects", "我的项目"],
  ["/account", "账号"],
];

export function brandMarkup(extraClass = "") {
  return `
    <a class="brand ${extraClass}" href="/" data-route aria-label="Novel2Gal 首页">
      <img class="brand-logo" src="/static/assets/brand/novel2gal-logo.svg" alt="" width="46" height="46" />
      <span class="brand-copy">
        <strong>Novel<span>2</span>Gal</strong>
        <small>小说视角改编工作台</small>
      </span>
    </a>
  `;
}

export function animeHeaderMarkup(activePath = "/", options = {}) {
  return `
    <header class="site-header anime-header" data-anime-header>
      ${brandMarkup()}
      <button class="nav-toggle" type="button" data-nav-toggle aria-label="展开导航" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
      <nav class="site-nav" aria-label="主导航" data-site-nav>
        ${navItems.map(([href, label], index) => `
          <a class="${activePath === href ? "active" : ""}" href="${href}" data-route style="--nav-index:${index}" ${activePath === href ? 'aria-current="page"' : ""}>${label}</a>
        `).join("")}
      </nav>
      <div class="header-tools">
        <div class="auth-slot" data-auth-slot><a class="account-link" href="/account">登录 / 注册</a></div>
        <button class="icon-button" type="button" data-open-settings aria-label="动效设置" title="动效设置">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 8.25A3.75 3.75 0 1 0 12 15.75 3.75 3.75 0 0 0 12 8.25Zm8.1 5.13-1.56.9a7.2 7.2 0 0 1-.74 1.78l.47 1.74-1.47 1.47-1.74-.47a7.2 7.2 0 0 1-1.78.74l-.9 1.56h-2.08l-.9-1.56a7.2 7.2 0 0 1-1.78-.74l-1.74.47-1.47-1.47.47-1.74a7.2 7.2 0 0 1-.74-1.78l-1.56-.9v-2.08l1.56-.9c.17-.63.42-1.22.74-1.78L4.61 6.9 6.08 5.43l1.74.47c.56-.32 1.15-.57 1.78-.74l.9-1.56h2.08l.9 1.56c.63.17 1.22.42 1.78.74L17 5.43l1.47 1.47L18 8.64c.32.56.57 1.15.74 1.78l1.56.9v2.08Z"/></svg>
        </button>
        ${options.workspace
          ? '<button id="runButton" class="anime-button anime-button--primary header-cta" type="button"><span>开始制作</span><i aria-hidden="true">→</i></button>'
          : '<a class="anime-button anime-button--primary header-cta" href="/create" data-route><span>进入工作台</span><i aria-hidden="true">→</i></a>'}
      </div>
    </header>
  `;
}
