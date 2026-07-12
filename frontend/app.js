import { animeHeaderMarkup } from "/static/js/components/anime-header.js?v=20260710-auth6";
import { motionController } from "/static/js/motion/motion-controller.js?v=20260710-auth6";
import { uiController } from "/static/js/components/ui-controller.js";
import { commandPalette } from "/static/js/components/command-palette.js";
import { ProjectSession } from "/static/js/project-session.js?v=20260710-auth6";
import { initLandingPage } from "/static/js/pages/landing-page.js?v=20260710-auth6";
import { initTemplatesPage } from "/static/js/pages/templates-page.js?v=20260710-auth6";
import { initProjectsPage } from "/static/js/pages/projects-page.js";
import { initAccountPage } from "/static/js/pages/account-page.js?v=20260713-byok1";
import { initAdminPage } from "/static/js/pages/admin-page.js?v=20260713-byok1";
import { hydrateAuthShell, loadCurrentUser } from "/static/js/auth-state.js?v=20260713-byok1";
import { openPublishSample } from "/static/js/components/publish-sample.js";
import { openExportCenter } from "/static/js/components/export-center.js";
import { openVersionHistory } from "/static/js/components/version-history.js";
import { openResourceCenter } from "/static/js/components/resource-center.js?v=20260710-procurement1";
import { openModal } from "/static/js/components/modal.js";
import { showToast } from "/static/js/components/toast.js";
import { api } from "/static/js/api-client.js?v=20260713-byok1";

window.__novel2galBuild = "20260710-auth6";
window.__novel2galBootstrap = "started";
window.addEventListener("error", (event) => {
  window.__novel2galError = `${event.message} @ ${event.filename}:${event.lineno}:${event.colno}`;
});

const appRoot = document.querySelector("#appRoot");
let form;
let runButton;
let bookFile;
let llmModelInput;
let modelOptions = [];
let modelHint;
let statusText;
let charactersList;
let scenesList;
let renpyOutput;
let jsonOutput;
let thoughtStatus;
let thoughtLog;
let adapterStatus;
let gameScreen;
let sceneArt;
let gameCounter;
let gameSceneId;
let gameBgm;
let gameSpeaker;
let gameDialogue;
let choiceList;
let characterStandee;
let gamePrev;
let gameNext;
let gameAuto;
let gameFast;
let gameJump;
let gameJumpButton;
let gameBgmToggle;
let gameFullscreen;
let sceneRecommend;

const THINKING_STEPS = [
  ["import", "正在读取原文和电子书结构"],
  ["split", "正在拆分章节与场景"],
  ["analyze", "正在提取人物、事件和线索"],
  ["pov", "正在过滤核心人物可知信息"],
  ["adapt", "正在改写为视觉小说场景"],
  ["check", "正在检查剧透和一致性"],
];
const MODEL_DETAILS = {
  "deepseek-v4-pro": {
    label: "V4 Pro",
    hint: "当前：V4 Pro，质量优先，适合长篇人物关系、伏笔梳理和复杂分支。",
  },
  "deepseek-v4-flash": {
    label: "V4 Flash",
    hint: "当前：V4 Flash，速度优先，适合快速预览、小段文本和多次试跑。",
  },
};
const MIN_THINKING_MS = 1800;
const LOCAL_FEMALE_PORTRAITS = [
  "/static/assets/runtime/wata_female_18_stand_a.png",
  "/static/assets/runtime/wata_female_19_stand_a.png",
  "/static/assets/runtime/wata_female_20_stand_a.png",
];
const LOCAL_MALE_PORTRAITS = [
  "/static/assets/runtime/wata_male_15_stand_a.png",
  "/static/assets/runtime/wata_male_16_stand_a.png",
];
const CHARACTER_PORTRAITS = [...LOCAL_FEMALE_PORTRAITS, ...LOCAL_MALE_PORTRAITS];
const ASSET_CATALOG = {
  portraits: {
    child: CHARACTER_PORTRAITS,
    young_female: LOCAL_FEMALE_PORTRAITS,
    young_male: LOCAL_MALE_PORTRAITS,
    adult_female: LOCAL_FEMALE_PORTRAITS,
    adult_male: LOCAL_MALE_PORTRAITS,
    elder: CHARACTER_PORTRAITS,
    anime_female: LOCAL_FEMALE_PORTRAITS,
    anime_male: LOCAL_MALE_PORTRAITS,
    anime_child: CHARACTER_PORTRAITS,
    anime_elder: CHARACTER_PORTRAITS,
  },
  propImages: {},
};

let characterProfilesByName = {};
let externalAssetCatalog = { backgrounds: [], portraits: [], bgm: [] };
let activeVisualStyle = "real";
let activePovCharacter = "";
let autoplayTimer = null;
let autoplayEnabled = false;
let bgmEnabled = false;
const bgmAudio = new Audio();
bgmAudio.loop = true;

let gameFrames = [];
let activeFrameIndex = 0;
let thinkingTimer = null;
let thinkingStartedAt = 0;
let projectSession = null;
let currentProject = null;
let routeCleanups = [];
let routeVersion = 0;
let latestResult = null;
let restoringProject = false;

let navigationLocked = false;

async function navigateTo(path) {
  let destination = new URL(path, window.location.origin);
  if (navigationLocked || `${window.location.pathname}${window.location.search}` === `${destination.pathname}${destination.search}`) return;
  navigationLocked = true;
  try {
    if (["/create", "/studio", "/projects", "/admin"].includes(destination.pathname) && !await loadCurrentUser()) {
      destination = new URL(`/account?next=${encodeURIComponent(`${destination.pathname}${destination.search}`)}`, window.location.origin);
    }
    if (projectSession && ["dirty", "saving", "failed", "offline"].includes(projectSession.state)) {
      const saved = await saveCurrentProject();
      if (!saved && !window.confirm("当前项目尚未同步到服务器，确定离开并保留本地快照吗？")) return;
    }
    await motionController.leave(appRoot, destination.pathname);
    if (`${window.location.pathname}${window.location.search}` !== `${destination.pathname}${destination.search}`) {
      window.history.pushState({}, "", `${destination.pathname}${destination.search}`);
    }
    renderRoute(destination.pathname);
  } catch (error) {
    motionController.cancelPendingOverlay();
    console.error("Route navigation failed", error);
    window.location.assign(destination.href);
  } finally {
    navigationLocked = false;
  }
}

function bindRouteLinks(root = document) {
  root.querySelectorAll("[data-route]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigateTo(link.getAttribute("href") || link.dataset.route || "/");
    });
  });
}

function renderRoute(path = window.location.pathname) {
  const routePath = new URL(path, window.location.origin).pathname;
  const currentRouteVersion = ++routeVersion;
  routeCleanups.splice(0).forEach((cleanup) => {
    if (typeof cleanup === "function") cleanup();
  });
  projectSession?.destroy();
  projectSession = null;
  currentProject = null;
  commandPalette.unmount();
  motionController.unmount();
  uiController.unmount();
  clearTimeout(autoplayTimer);
  autoplayEnabled = false;
  if (bgmAudio) bgmAudio.pause();
  resetWorkbenchDom();
  if (routePath === "/create" || routePath === "/studio") {
    appRoot.innerHTML = workbenchPageTemplate();
    initWorkbench();
  } else if (routePath === "/templates") {
    appRoot.innerHTML = templatesPageTemplate();
  } else if (routePath === "/projects") {
    appRoot.innerHTML = projectsPageTemplate();
  } else if (routePath === "/account") {
    appRoot.innerHTML = accountPageTemplate();
  } else if (routePath === "/admin") {
    appRoot.innerHTML = adminPageTemplate();
  } else {
    appRoot.innerHTML = landingPageTemplate();
  }
  bindRouteLinks(appRoot);
  uiController.mount(appRoot);
  motionController.mount(appRoot);
  hydrateAuthShell(appRoot);
  initializeRouteFeatures(routePath, currentRouteVersion);
  window.scrollTo({ top: 0, behavior: motionController.reduced ? "auto" : "smooth" });
}

function initializeRouteFeatures(path, currentRouteVersion) {
  if (path === "/") routeCleanups.push(initLandingPage(appRoot));
  if (path === "/templates") registerAsyncRouteCleanup(initTemplatesPage(appRoot), currentRouteVersion);
  if (path === "/projects") registerAsyncRouteCleanup(initProjectsPage(appRoot), currentRouteVersion);
  if (path === "/account") registerAsyncRouteCleanup(initAccountPage(appRoot), currentRouteVersion);
  if (path === "/admin") registerAsyncRouteCleanup(initAdminPage(appRoot), currentRouteVersion);
  if (path === "/create" || path === "/studio") initProjectSession();
  setupCommandPalette(path);
}

function registerAsyncRouteCleanup(initializer, currentRouteVersion) {
  Promise.resolve(initializer).then((cleanup) => {
    if (typeof cleanup !== "function") return;
    if (currentRouteVersion === routeVersion) routeCleanups.push(cleanup);
    else cleanup();
  });
}

function resetWorkbenchDom() {
  form = null;
  runButton = null;
  bookFile = null;
  llmModelInput = null;
  modelOptions = [];
  modelHint = null;
  statusText = null;
  charactersList = null;
  scenesList = null;
  renpyOutput = null;
  jsonOutput = null;
  thoughtStatus = null;
  thoughtLog = null;
  adapterStatus = null;
  gameScreen = null;
  sceneArt = null;
  gameCounter = null;
  gameSceneId = null;
  gameBgm = null;
  gameSpeaker = null;
  gameDialogue = null;
  choiceList = null;
  characterStandee = null;
  gamePrev = null;
  gameNext = null;
  gameAuto = null;
  gameFast = null;
  gameJump = null;
  gameJumpButton = null;
  gameBgmToggle = null;
  gameFullscreen = null;
  sceneRecommend = null;
}

function queryWorkbenchDom() {
  form = document.querySelector("#pipelineForm");
  runButton = document.querySelector("#runButton");
  bookFile = document.querySelector("#bookFile");
  llmModelInput = document.querySelector("#llmModel");
  modelOptions = document.querySelectorAll(".model-option");
  modelHint = document.querySelector("#modelHint");
  statusText = document.querySelector("#statusText");
  charactersList = document.querySelector("#characters");
  scenesList = document.querySelector("#scenes");
  renpyOutput = document.querySelector("#renpyOutput");
  jsonOutput = document.querySelector("#jsonOutput");
  thoughtStatus = document.querySelector("#thoughtStatus");
  thoughtLog = document.querySelector("#thoughtLog");
  adapterStatus = document.querySelector("#adapterStatus");
  gameScreen = document.querySelector("#gameScreen");
  sceneArt = document.querySelector(".scene-art");
  gameCounter = document.querySelector("#gameCounter");
  gameSceneId = document.querySelector("#gameSceneId");
  gameBgm = document.querySelector("#gameBgm");
  gameSpeaker = document.querySelector("#gameSpeaker");
  gameDialogue = document.querySelector("#gameDialogue");
  choiceList = document.querySelector("#choiceList");
  characterStandee = document.querySelector("#characterStandee");
  gamePrev = document.querySelector("#gamePrev");
  gameNext = document.querySelector("#gameNext");
  gameAuto = document.querySelector("#gameAuto");
  gameFast = document.querySelector("#gameFast");
  gameJump = document.querySelector("#gameJump");
  gameJumpButton = document.querySelector("#gameJumpButton");
  gameBgmToggle = document.querySelector("#gameBgmToggle");
  gameFullscreen = document.querySelector("#gameFullscreen");
  sceneRecommend = document.querySelector("#sceneRecommend");
}

function initWorkbench() {
  queryWorkbenchDom();
  gameFrames = [];
  activeFrameIndex = 0;
  characterProfilesByName = {};
  activeVisualStyle = "real";
  activePovCharacter = "";
  updateModelHint();
  loadExternalAssets();

  runButton.addEventListener("click", () => {
    runPipeline();
  });

  gamePrev.addEventListener("click", () => {
    if (activeFrameIndex > 0) {
      activeFrameIndex -= 1;
      renderActiveFrame();
    }
  });

  gameNext.addEventListener("click", () => {
    if (activeFrameIndex < gameFrames.length - 1) {
      activeFrameIndex += 1;
      renderActiveFrame();
    }
  });

  gameAuto?.addEventListener("click", () => {
    autoplayEnabled = !autoplayEnabled;
    gameAuto.classList.toggle("active", autoplayEnabled);
    if (autoplayEnabled) {
      scheduleAutoplay();
    } else {
      clearTimeout(autoplayTimer);
    }
  });

  gameFast?.addEventListener("click", () => {
    if (!gameFrames.length) return;
    activeFrameIndex = Math.min(activeFrameIndex + 5, gameFrames.length - 1);
    renderActiveFrame();
  });

  gameJumpButton?.addEventListener("click", () => {
    jumpToFrame(Number.parseInt(gameJump?.value || "1", 10) - 1);
  });

  gameJump?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      jumpToFrame(Number.parseInt(gameJump.value || "1", 10) - 1);
    }
  });

  gameBgmToggle?.addEventListener("click", () => {
    bgmEnabled = !bgmEnabled;
    gameBgmToggle.classList.toggle("active", bgmEnabled);
    updateBgm(gameFrames[activeFrameIndex] || emptyFrame(), true);
  });

  gameFullscreen?.addEventListener("click", () => {
    const target = document.querySelector("#gamePreview") || gameScreen;
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
    } else {
      target.requestFullscreen?.();
    }
  });

  document.querySelector("#regenerateSceneButton")?.addEventListener("click", regenerateCurrentScene);

  bookFile.addEventListener("change", async () => {
    const file = bookFile.files?.[0];
    if (!file) return;
    if (isTextFile(file.name)) {
      const text = await file.text();
      document.querySelector("#novelText").value = text;
      if (!document.querySelector("#title").value.trim()) {
        document.querySelector("#title").value = titleFromFilename(file.name);
      }
      updateRecommendedScenes(text);
    } else {
      updateRecommendedScenes("");
    }
  });

  document.querySelector("#novelText")?.addEventListener("input", (event) => {
    updateRecommendedScenes(event.target.value || "");
  });

  modelOptions.forEach((button) => {
    button.addEventListener("click", () => {
      setSelectedModel(button.dataset.model || "deepseek-v4-pro");
    });
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.dataset.target;
      renpyOutput.hidden = target !== "renpyOutput";
      jsonOutput.hidden = target !== "jsonOutput";
    });
  });

  document.querySelectorAll("[data-memory-tab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("[data-memory-tab]").forEach((item) => item.classList.toggle("active", item === tab));
      document.querySelectorAll("[data-memory-pane]").forEach((pane) => pane.classList.toggle("active", pane.dataset.memoryPane === tab.dataset.memoryTab));
    });
  });

  const scriptEditToggle = document.querySelector("#scriptEditToggle");
  scriptEditToggle?.addEventListener("click", () => {
    const editing = renpyOutput.contentEditable !== "true";
    renpyOutput.contentEditable = String(editing);
    renpyOutput.classList.toggle("is-editing", editing);
    scriptEditToggle.textContent = editing ? "完成编辑" : "编辑脚本";
    if (editing) renpyOutput.focus();
    if (!editing && latestResult) {
      latestResult = { ...latestResult, exports: { ...latestResult.exports, renpy: renpyOutput.textContent } };
      projectSession?.markDirty({ result: latestResult, status: "done", version_note: "手动编辑脚本" });
    }
  });
}

window.addEventListener("popstate", () => bootstrapRoute());
bootstrapRoute();

async function bootstrapRoute() {
  const user = await loadCurrentUser();
  const route = window.location.pathname;
  if (["/create", "/studio", "/projects", "/admin"].includes(route) && !user) {
    const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
    window.history.replaceState({}, "", `/account?next=${next}`);
  }
  renderRoute(window.location.pathname);
}

function landingPageTemplate() {
  return `
    <section class="landing-page artistic-cover">
      ${animeHeaderMarkup("/")}
      <main id="mainContent" class="cover-page" aria-label="Novel2Gal 扉页">
        <div class="cover-watermark" aria-hidden="true">N<span>2</span>G</div>
        <section class="cover-intro" data-reveal>
          <span class="cover-volume">Novel2Gal · 第一卷</span>
          <p class="cover-overline">轻小说改编与视觉小说排演室</p>
          <h1 aria-label="让文字成为可以登场的故事">
            <span class="cover-title-line">让文字成为</span>
            <span class="cover-title-line"><em>可以登场</em>的故事</span>
          </h1>
          <p class="cover-note">一段文字，一束追光，一次重新被听见的机会。</p>
          <div class="cover-prompt"><i></i><span>把光标移向右侧信纸，翻开你的下一幕</span></div>
        </section>

        <section class="folio-stage" aria-label="主要功能信纸">
          <div class="folio-orbit folio-orbit--one" aria-hidden="true"></div>
          <div class="folio-orbit folio-orbit--two" aria-hidden="true"></div>
          <div id="folioDeck" class="folio-deck">
            <a class="folio-letter folio-letter--create" href="/create?new=1" data-route data-folio="create" style="--stack-left:20px;--stack-top:54px;--stack-r:-11deg;--stack-z:1;--scatter-x:-760px;--scatter-y:-120px;--scatter-r:-26deg">
              <span class="folio-number">01</span><span class="folio-tab">新作</span>
              <div class="folio-art" style="--folio-art:url('/static/assets/editorial/campus-rooftop.webp')"></div>
              <div class="folio-copy"><small>从空白台本开始</small><h2>写下第一幕</h2><p>导入小说，选择目光所及的人。</p><b>开始新作品 <i>→</i></b></div>
            </a>
            <a class="folio-letter folio-letter--recent" href="/projects" data-route data-folio="recent" data-folio-recent style="--stack-left:76px;--stack-top:32px;--stack-r:-4deg;--stack-z:2;--scatter-x:680px;--scatter-y:-320px;--scatter-r:24deg">
              <span class="folio-number">02</span><span class="folio-tab">续写</span>
              <div class="folio-art" style="--folio-art:url('/static/assets/editorial/rain-convenience.webp')"></div>
              <div class="folio-copy"><small data-folio-recent-meta>作品存档与历史版本</small><h2 data-folio-recent-title>继续上次排演</h2><p>从保存的那一句对白继续。</p><b data-folio-recent-action>打开作品存档 <i>→</i></b></div>
            </a>
            <a class="folio-letter folio-letter--templates" href="/templates" data-route data-folio="templates" style="--stack-left:132px;--stack-top:38px;--stack-r:5deg;--stack-z:3;--scatter-x:-690px;--scatter-y:470px;--scatter-r:31deg">
              <span class="folio-number">03</span><span class="folio-tab">范本</span>
              <div class="folio-art" style="--folio-art:url('/static/assets/editorial/moonlit-forest.webp')"></div>
              <div class="folio-copy"><small>完整场景与分支范式</small><h2>翻阅模板书架</h2><p>借一部作品的骨架，写自己的故事。</p><b>进入模板图书馆 <i>→</i></b></div>
            </a>
            <a class="folio-letter folio-letter--studio" href="/create" data-route data-folio="studio" style="--stack-left:188px;--stack-top:62px;--stack-r:12deg;--stack-z:4;--scatter-x:780px;--scatter-y:430px;--scatter-r:-28deg">
              <span class="folio-number">04</span><span class="folio-tab">制作</span>
              <div class="folio-art" style="--folio-art:url('/static/assets/editorial/old-school-recorder.webp')"></div>
              <div class="folio-copy"><small>场景、角色与演出轨道</small><h2>进入制作室</h2><p>让对白、立绘与音乐在舞台汇合。</p><b>打开工作台 <i>→</i></b></div>
            </a>
          </div>
          <nav class="folio-switcher" aria-label="切换功能信纸">
            <button type="button" data-folio-switch="create"><span>01</span>新作</button>
            <button type="button" data-folio-switch="recent"><span>02</span>续写</button>
            <button type="button" data-folio-switch="templates"><span>03</span>范本</button>
            <button type="button" data-folio-switch="studio"><span>04</span>制作</button>
          </nav>
          <p class="folio-instruction"><span>悬停展开</span><i></i><span>点击翻页</span></p>
        </section>

        <footer class="cover-footer"><span>轻小说编辑部 × Galgame 制作软件</span><span>卷一 · 故事获得声音之前</span></footer>
      </main>
    </section>
  `;
}

function templatesPageTemplate() {
  const categories = ["全部", "校园恋爱", "悬疑推理", "奇幻冒险", "日常治愈", "黑暗剧情", "我的样例"];
  return `
    <section class="anime-app library-page templates-page">
      ${animeHeaderMarkup("/templates")}
      <main id="mainContent" class="library-main">
        <section class="library-heading">
          <div class="library-heading-copy"><span class="chapter-ribbon">模板图书馆</span><h1>从完整范例开始创作</h1><p>替换人物与文本即可制作；每一本都包含场景、分支与演出配置。</p></div>
          <div class="library-toolbar library-toolbar--editorial">
            <label class="search-field"><span aria-hidden="true"></span><input id="templateSearch" type="search" placeholder="搜索标题、分类或剧情关键词" aria-label="搜索模板"></label>
          </div>
        </section>
        <nav class="bookmark-filters" aria-label="模板分类">
          ${categories.map((item, index) => `<button class="${index === 0 ? "active" : ""}" type="button" data-template-filter="${item}">${item}</button>`).join("")}
        </nav>
        <section class="bookshelf-label"><span>馆藏作品</span><small>点击封面可预览详情</small></section>
        <section id="templateGrid" class="template-bookshelf" aria-live="polite"><div class="library-loading"><span class="story-loader"></span><p>正在整理故事书架…</p></div></section>
      </main>
    </section>
  `;
}

function projectsPageTemplate() {
  return `
    <section class="anime-app library-page projects-page">
      ${animeHeaderMarkup("/projects")}
      <main id="mainContent" class="library-main">
        <section class="projects-hero projects-hero--editorial">
          <div><span class="chapter-ribbon">作品存档</span><h1>我的项目</h1><p>继续上一次排演，或从空白台本建立新的故事。</p></div>
          <div class="projects-hero-actions"><input id="projectJsonInput" type="file" accept="application/json,.json" hidden><button id="importProjectButton" class="anime-button anime-button--ghost" type="button">导入项目 JSON</button><a class="anime-button anime-button--primary" href="/create?new=1" data-route>新建 Galgame <i>→</i></a></div>
        </section>
        <section class="project-stats" aria-label="项目统计">
          <article><small>全部存档</small><strong data-project-stat="total">0</strong><span>部作品</span></article>
          <article><small>已完成</small><strong data-project-stat="done">0</strong><span>可继续导出</span></article>
          <article><small>生成中</small><strong data-project-stat="running">0</strong><span>后台任务</span></article>
          <article><small>待检查</small><strong data-project-stat="review">0</strong><span>需要处理</span></article>
          <article><small>最近编辑</small><strong class="stat-time" data-project-stat="recent">—</strong><span>本地时间</span></article>
        </section>
        <section class="project-toolbar">
          <label class="search-field"><span aria-hidden="true"></span><input id="projectSearch" type="search" placeholder="搜索项目、原文件或核心人物" aria-label="搜索项目"></label>
          <div class="segmented-filter" aria-label="项目状态"><button class="active" type="button" data-project-filter="all">全部</button><button type="button" data-project-filter="done">已完成</button><button type="button" data-project-filter="running">生成中</button><button type="button" data-project-filter="draft">待检查</button></div>
          <label class="sort-field">排序<select id="projectSort"><option value="recent">最近编辑</option><option value="oldest">最早编辑</option><option value="title">标题</option></select></label>
          <div class="project-view-toggle" aria-label="项目视图"><button class="active" type="button" data-project-view="list" aria-label="列表视图">☷</button><button type="button" data-project-view="grid" aria-label="网格视图">▦</button></div>
        </section>
        <section id="projectGrid" class="project-grid" data-view="list" aria-live="polite">
          <div class="library-loading"><span class="story-loader"></span><p>正在读取项目档案…</p></div>
        </section>
      </main>
    </section>
  `;
}

function accountPageTemplate() {
  return `
    <section class="anime-app identity-page">
      ${animeHeaderMarkup("/account")}
      <main id="mainContent" class="identity-main"><div id="accountContent" class="identity-loading"><span class="story-loader"></span><p>正在打开私人创作空间…</p></div></main>
    </section>`;
}

function adminPageTemplate() {
  return `
    <section class="anime-app admin-page">
      ${animeHeaderMarkup("/admin")}
      <main id="mainContent" class="admin-main"><div id="adminContent" class="identity-loading"><span class="story-loader"></span><p>正在核对管理员权限…</p></div></main>
    </section>`;
}

function workbenchPageTemplate() {
  return `
    <section class="workspace-page anime-app">
      ${animeHeaderMarkup("/create", { workspace: true })}

      <section class="project-status-bar" aria-label="项目状态">
        <div class="project-status-title"><span class="story-node"></span><div><small>当前作品</small><strong id="projectTitleStatus">未命名企划</strong></div><span id="projectLifecycle" class="status-badge">草稿</span></div>
        <div class="status-cluster">
          <span class="status-item"><small>保存</small><strong id="saveState" data-state="idle">尚未保存</strong></span>
          <span class="status-item"><small>生成任务</small><strong id="aiTaskState">空闲</strong></span>
          <span class="status-item"><small>预计成本</small><strong id="estimatedCost">¥0.00</strong></span>
          <span class="status-item"><small>处理策略</small><strong id="currentModelStatus">V4 Pro</strong></span>
          <span class="status-item"><small>最后保存</small><strong id="lastSaved">—</strong></span>
        </div>
        <div class="status-actions">
          <button id="versionHistoryButton" class="anime-button anime-button--ghost" type="button">版本</button>
          <button id="resourceCenterButton" class="anime-button anime-button--ghost" type="button">素材</button>
          <button id="manualSaveButton" class="anime-button anime-button--ghost" type="button">保存</button>
          <button id="previewProjectButton" class="anime-button anime-button--ghost" type="button">预览</button>
          <button id="publishSampleButton" class="anime-button anime-button--ghost" type="button">存为模板</button>
          <button id="exportProjectButton" class="anime-button anime-button--primary" type="button">导出</button>
        </div>
      </section>

      <nav class="workspace-mobile-tabs" aria-label="工作台区域">
        <button class="active" type="button" data-workspace-tab="setup">场景</button><button type="button" data-workspace-tab="stage">舞台</button><button type="button" data-workspace-tab="script">演出</button><button type="button" data-workspace-tab="memory">资料</button><button id="mobileResourceCenterButton" type="button">素材</button>
      </nav>

      <section id="mainContent" class="workspace">
        <aside class="panel scene-navigator mobile-tab-active" data-workspace-panel="setup">
          <div class="panel-head"><div><small>台本目录</small><h2>章节与场景</h2></div><button id="openProjectSettings" class="scene-tool-button" type="button">项目设置</button></div>
          <div class="scene-nav-summary"><span>当前台本</span><strong id="sceneNavigatorCount">0 个场景</strong></div>
          <div id="sceneNavigatorList" class="scene-navigator-list"><div class="scene-nav-empty"><span>01</span><p>生成后，章节、场景和分支会排列在这里。</p></div></div>
          <button id="addSceneButton" class="scene-add-button" type="button">＋ 新建场景草稿</button>
        </aside>

        <button id="settingsDrawerBackdrop" class="settings-drawer-backdrop" type="button" aria-label="关闭项目设置" tabindex="-1"></button>
        <form id="pipelineForm" class="panel input-panel project-settings-drawer" aria-label="项目设置">
          <div class="studio-panel-title drawer-title">
            <div><span class="chapter-ribbon">项目设置</span><h2>原作与生成策略</h2></div>
            <button id="closeProjectSettings" class="drawer-close" type="button" aria-label="关闭项目设置">×</button>
          </div>
          <details class="studio-setting-group" open>
            <summary><span>01</span>基础设定<i></i></summary>
            <div class="setting-group-body">
          <div class="field-row">
            <label for="title">企划名称</label>
            <input id="title" name="title" placeholder="可留空，上传 EPUB 时自动读取" />
          </div>
          <div class="field-row">
            <label for="pov">核心视角</label>
            <input id="pov" name="pov" placeholder="可留空，自动选择主要人物" />
          </div>
          <div class="field-row">
            <label for="bookFile">原作导入</label>
            <input id="bookFile" name="bookFile" type="file" accept=".txt,.md,.markdown,.epub" />
          </div>
          <div class="field-row">
            <label for="maxScenes">场景数</label>
            <input id="maxScenes" name="maxScenes" type="number" min="1" step="1" value="5" />
          </div>
          <label class="full-book-toggle">
            <input id="fullBookMode" name="fullBookMode" type="checkbox" checked />
            EPUB 全书分章生成
          </label>
          <div id="sceneRecommend" class="recommend-hint">推荐场景数：输入或上传后估算</div>
            </div>
          </details>
          <details class="studio-setting-group" open>
            <summary><span>02</span>模型策略<i></i></summary>
            <div class="setting-group-body">
          <div class="field-row">
            <label>模型</label>
            <div class="model-toggle" role="group" aria-label="DeepSeek 模型选择">
              <input id="llmModel" name="llmModel" type="hidden" value="deepseek-v4-pro" />
              <button class="model-option active" type="button" data-model="deepseek-v4-pro">
                <strong>V4 Pro</strong>
                <span>质量优先</span>
              </button>
              <button class="model-option" type="button" data-model="deepseek-v4-flash">
                <strong>V4 Flash</strong>
                <span>速度优先</span>
              </button>
            </div>
          </div>
          <div id="modelHint" class="model-hint">当前：V4 Pro，质量优先，适合长篇人物关系和复杂分支。</div>
            </div>
          </details>
          <details class="studio-setting-group" open>
            <summary><span>03</span>原作正文<i></i></summary>
            <div class="setting-group-body">
          <label for="novelText">原作正文</label>
          <textarea id="novelText" name="novelText" placeholder="也可以不上传文件，直接把小说正文粘贴到这里。"></textarea>
            </div>
          </details>
        </form>

        <aside class="panel inspector-panel" data-workspace-panel="memory">
          <div class="panel-head"><div><small>演出资料</small><h2>角色与场景</h2></div><span id="statusText">ready</span></div>
          <div class="memory-tabs inspector-tabs" role="tablist" aria-label="演出资料分类"><button class="active" type="button" data-memory-tab="roles">角色</button><button type="button" data-memory-tab="world">场景</button><button type="button" data-memory-tab="memory">剧情记忆</button><button type="button" data-memory-tab="tasks">生成任务</button></div>
          <div class="memory-pane active" data-memory-pane="roles"><div class="inspector-pane-head"><h3>出场角色</h3><small>立绘与状态</small></div><ul id="characters" class="inspector-character-list"></ul><div class="quick-expression"><span>快速表情</span><div><button type="button" data-expression="normal">普通</button><button type="button" data-expression="smile">微笑</button><button type="button" data-expression="sad">低落</button><button type="button" data-expression="surprise">惊讶</button></div></div></div>
          <div class="memory-pane" data-memory-pane="world"><div class="inspector-pane-head"><h3>当前场景</h3><small>素材快速替换</small></div><label class="quick-resource">背景<select id="backgroundQuickSelect"><option value="bg_default">默认舞台</option><option value="bg_classroom">午后教室</option><option value="bg_old_school_night">夜间旧校舍</option><option value="bg_street_evening">黄昏街道</option></select></label><label class="quick-resource">音乐<select id="bgmQuickSelect"><option value="-">无音乐</option><option value="bgm_daily">日常</option><option value="bgm_memory">回忆</option><option value="bgm_tension">紧张</option></select></label><h3 class="world-facts-title">世界事实</h3><ul id="scenes"></ul></div>
          <div class="memory-pane" data-memory-pane="memory"><div class="memory-ledger"><article><span>伏笔</span><p>生成后会记录尚未回收的线索。</p></article><article><span>视角约束</span><p>核心人物可知信息会在这里核对。</p></article><article><span>时间线</span><p>章节与事件顺序会随场景同步。</p></article></div></div>
          <div class="memory-pane" data-memory-pane="tasks">
            <section id="thoughtPanel" class="thought-panel inspector-task-panel">
              <div class="panel-head"><h3>生成任务</h3><span id="thoughtStatus">idle</span></div>
              <div id="adapterStatus" class="adapter-status">改编来源：未运行</div>
              <span id="cacheState" class="cache-state">缓存：未命中</span>
              <dl class="ai-task-metrics"><div><dt>当前步骤</dt><dd id="aiCurrentStep">等待开始</dd></div><div><dt>使用策略</dt><dd id="aiModelMetric">V4 Pro</dd></div><div><dt>缓存</dt><dd id="aiCacheMetric">未命中</dd></div><div><dt>调用耗时</dt><dd id="aiElapsedMetric">0.0s</dd></div><div><dt>剩余步骤</dt><dd id="aiRemainingMetric">6</dd></div></dl>
              <ol class="thought-steps"><li data-step="import">读取原文</li><li data-step="split">章节切分</li><li data-step="analyze">角色分析</li><li data-step="pov">视角过滤</li><li data-step="adapt">剧本生成</li><li data-step="check">一致性检查</li></ol>
              <div id="thoughtLog" class="thought-log">等待运行</div>
            </section>
          </div>
        </aside>

        <section id="gamePreview" class="panel preview-panel" data-workspace-panel="stage">
          <div class="panel-head">
            <div><small>16:9 演出画面</small><h2>舞台预览</h2></div>
            <span id="gameCounter">0 / 0</span>
          </div>
          <div id="gameScreen" class="game-screen" data-bg="default">
            <div class="scene-art" aria-hidden="true">
              <div class="school-building">
                <span></span><span></span><span></span><span></span>
              </div>
              <div id="characterStandee" class="character-standee">林</div>
            </div>
            <div class="game-meta">
              <span id="gameSceneId">未生成</span>
              <span id="gameBgm">bgm: -</span>
            </div>
            <div class="dialogue-box">
              <div id="gameSpeaker" class="speaker-name">旁白</div>
              <p id="gameDialogue">运行后会在这里播放改编出的场景。</p>
              <div id="choiceList" class="choice-list"></div>
            </div>
          </div>
          <div class="game-controls">
            <button id="gameAuto" type="button" title="自动播放">自动</button>
            <button id="gameFast" type="button" title="快进 5 页">快进</button>
            <label class="jump-control" for="gameJump">跳转</label>
            <input id="gameJump" type="number" min="1" value="1" />
            <button id="gameJumpButton" type="button" title="跳转到指定页">Go</button>
            <button id="gameBgmToggle" type="button" title="播放/暂停 BGM">音乐</button>
            <button id="gameHistory" type="button" title="查看台本历史">历史</button>
            <button id="gameSave" type="button" title="保存当前项目">保存</button>
            <button id="gameLoad" type="button" title="读取历史版本">读取</button>
            <button id="gameFullscreen" type="button" title="全屏播放">全屏</button>
            <button id="regenerateSceneButton" type="button" title="保留版本并重新生成当前场景">重生成当前场</button>
            <button id="gamePrev" type="button" title="上一句">←</button>
            <button id="gameNext" type="button" title="下一句">→</button>
          </div>
          <details class="scene-timeline" open>
            <summary><span>场景胶片</span><small>点击切换当前演出</small></summary>
            <div id="sceneTimelineTrack" class="scene-timeline-track"></div>
          </details>
        </section>

        <section class="panel output-panel" data-workspace-panel="script">
          <div class="performance-timeline">
            <div class="performance-head"><div><small>演出时间轴</small><h2>场景轨道</h2></div><span>拖动场景缩略图可调整顺序</span></div>
            <div id="performanceTracks" class="performance-tracks"><div class="track-empty">生成场景后显示对白、角色、表情、背景、音乐、音效与转场轨道。</div></div>
          </div>
          <div class="tabs" role="tablist">
            <button class="tab active" type="button" data-target="renpyOutput">Ren'Py 台本</button>
            <button class="tab" type="button" data-target="jsonOutput">项目数据</button>
            <button id="scriptEditToggle" class="script-edit-toggle" type="button">编辑脚本</button>
          </div>
          <pre id="renpyOutput"></pre>
          <pre id="jsonOutput" hidden></pre>
        </section>
      </section>
    </section>
  `;
}

async function runPipeline() {
  const formData = new FormData(form);
  const file = bookFile.files?.[0];

  statusText.textContent = "running";
  const aiTaskState = document.querySelector("#aiTaskState");
  if (aiTaskState) aiTaskState.textContent = "运行中";
  runButton.disabled = true;
  startThinkingProgress();

  try {
    const response = file && file.name.toLowerCase().endsWith(".epub")
      ? await runUploadedProject(formData, file)
      : await runTextInputJob(formData);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (payload.project_id && projectSession) {
      projectSession.projectId = payload.project_id;
      localStorage.setItem("novel2gal.last_project_id", payload.project_id);
      const url = new URL(window.location.href);
      url.searchParams.set("project_id", payload.project_id);
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
    }
    const result = payload.project_id
      ? await waitForProject(payload.project_id)
      : payload.result
        ? payload.result
        : await waitForPipelineJob(payload.job_id);
    await completeThinkingProgress(result);
    renderResult(result);
    statusText.textContent = "done";
    if (payload.project_id) {
      try {
        currentProject = await api.getProject(payload.project_id);
        projectSession.project = currentProject;
        projectSession.remember(currentProject);
        projectSession.setState("saved");
      } catch (_) { /* result is still available in the current session */ }
    } else if (projectSession) {
      await saveCurrentProject();
    }
  } catch (error) {
    failThinkingProgress(error);
    statusText.textContent = "failed";
    renpyOutput.textContent = String(error);
    if (aiTaskState) aiTaskState.textContent = "失败";
  } finally {
    runButton.disabled = false;
    if (aiTaskState && statusText.textContent === "done") aiTaskState.textContent = "已完成";
  }
}

async function regenerateCurrentScene() {
  const text = document.querySelector("#novelText")?.value.trim();
  if (!text || !latestResult?.adaptation_scenes?.length) {
    showToast("请先生成至少一个场景", "warning");
    return;
  }
  const button = document.querySelector("#regenerateSceneButton");
  const activeSceneId = gameFrames[activeFrameIndex]?.sceneId;
  button.disabled = true;
  button.textContent = "重生成中…";
  startThinkingProgress();
  try {
    const response = await fetch("/api/pipeline/run/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: document.querySelector("#title")?.value || "未命名企划",
        text,
        pov_character: document.querySelector("#pov")?.value || "",
        max_scenes: 1,
        llm_model: selectedModel(),
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const job = await response.json();
    const regenerated = await waitForPipelineJob(job.job_id);
    const replacement = regenerated.adaptation_scenes?.[0];
    if (!replacement) throw new Error("本次没有生成可替换场景");
    replacement.scene_id = activeSceneId || replacement.scene_id;
    const scenes = latestResult.adaptation_scenes.map((scene) => scene.scene_id === activeSceneId ? replacement : scene);
    const merged = { ...latestResult, adaptation_scenes: scenes, stats: { ...latestResult.stats, adaptation_scenes: scenes.length }, exports: regenerated.exports || latestResult.exports };
    renderResult(merged);
    await projectSession?.save({ ...projectFormPayload(), result: merged, status: "done", version_note: `重新生成场景 ${activeSceneId || "current"}` });
    await completeThinkingProgress(regenerated);
    showToast("当前场景已重新生成，旧版本已保留", "success");
  } catch (error) {
    failThinkingProgress(error);
    showToast(error.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "重生成当前场";
  }
}

async function runTextInput(formData) {
  const payload = {
    title: formData.get("title") || "未命名小说",
    pov_character: formData.get("pov"),
    text: formData.get("novelText"),
    llm_model: selectedModel(),
  };
  const maxScenes = parseMaxScenes(formData.get("maxScenes"));
  if (maxScenes) payload.max_scenes = maxScenes;
  return fetch("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function initProjectSession() {
  projectSession = new ProjectSession();
  const formInput = () => {
    if (restoringProject) return;
    updateWorkbenchHeadline();
    projectSession.markDirty(projectFormPayload());
  };
  const onSaveState = (event) => updateSaveState(event.detail);
  const onBeforeUnload = (event) => {
    if (projectSession?.state !== "dirty" && projectSession?.state !== "saving") return;
    event.preventDefault();
    event.returnValue = "";
  };
  form.addEventListener("input", formInput);
  form.addEventListener("change", formInput);
  projectSession.addEventListener("statechange", onSaveState);
  window.addEventListener("beforeunload", onBeforeUnload);
  routeCleanups.push(() => form.removeEventListener("input", formInput), () => form.removeEventListener("change", formInput), () => projectSession?.removeEventListener("statechange", onSaveState), () => window.removeEventListener("beforeunload", onBeforeUnload));

  bindWorkspaceActions();
  const restored = await projectSession.restore();
  if (!projectSession) return;
  if (restored?.project) {
    hydrateProject(restored.project);
    showToast(restored.source === "snapshot" ? "服务器读取失败，已载入离线快照" : "已恢复上次编辑进度", restored.source === "snapshot" ? "warning" : "success");
  } else {
    updateWorkbenchHeadline();
    showFirstRunGuide();
  }
}

function bindWorkspaceActions() {
  const manualSave = document.querySelector("#manualSaveButton");
  const publish = document.querySelector("#publishSampleButton");
  const exportButton = document.querySelector("#exportProjectButton");
  const historyButton = document.querySelector("#versionHistoryButton");
  const resourceButton = document.querySelector("#resourceCenterButton");
  const mobileResourceButton = document.querySelector("#mobileResourceCenterButton");
  const previewButton = document.querySelector("#previewProjectButton");
  const workspacePage = document.querySelector(".workspace-page");
  const openSettings = document.querySelector("#openProjectSettings");
  const closeSettings = document.querySelector("#closeProjectSettings");
  const settingsBackdrop = document.querySelector("#settingsDrawerBackdrop");
  const toggleSettings = (open) => workspacePage?.classList.toggle("settings-open", open);
  manualSave?.addEventListener("click", () => saveCurrentProject(true));
  publish?.addEventListener("click", async () => {
    const project = await saveCurrentProject(true);
    if (project) openPublishSample(project);
  });
  exportButton?.addEventListener("click", async () => {
    const project = await saveCurrentProject(true);
    if (project) openExportCenter(project);
  });
  historyButton?.addEventListener("click", () => openVersionHistory(projectSession?.projectId, { onRollback: hydrateProject }));
  const showResources = async () => openResourceCenter(currentProject || await saveCurrentProject());
  resourceButton?.addEventListener("click", showResources);
  mobileResourceButton?.addEventListener("click", showResources);
  previewButton?.addEventListener("click", () => document.querySelector("#gamePreview")?.requestFullscreen?.());
  openSettings?.addEventListener("click", () => toggleSettings(true));
  closeSettings?.addEventListener("click", () => toggleSettings(false));
  settingsBackdrop?.addEventListener("click", () => toggleSettings(false));
  document.querySelector("#gameHistory")?.addEventListener("click", () => openVersionHistory(projectSession?.projectId, { onRollback: hydrateProject }));
  document.querySelector("#gameSave")?.addEventListener("click", () => saveCurrentProject(true));
  document.querySelector("#gameLoad")?.addEventListener("click", () => openVersionHistory(projectSession?.projectId, { onRollback: hydrateProject }));
  document.querySelector("#addSceneButton")?.addEventListener("click", addDraftScene);

  document.querySelector("#backgroundQuickSelect")?.addEventListener("change", (event) => updateActiveSceneResource("background", event.target.value));
  document.querySelector("#bgmQuickSelect")?.addEventListener("change", (event) => updateActiveSceneResource("bgm", event.target.value));
  document.querySelectorAll("[data-expression]").forEach((button) => button.addEventListener("click", () => {
    if (!gameFrames.length) return;
    gameScreen.dataset.expression = button.dataset.expression;
    document.querySelectorAll("[data-expression]").forEach((item) => item.classList.toggle("active", item === button));
    const frame = gameFrames[activeFrameIndex];
    frame.expression = button.dataset.expression;
    projectSession?.markDirty({ ...projectFormPayload(), result: latestResult, status: latestResult ? "done" : "draft", version_note: "调整角色表情" });
  }));

  const mobileTabs = [...document.querySelectorAll("[data-workspace-tab]")];
  mobileTabs.forEach((button) => button.addEventListener("click", () => {
    mobileTabs.forEach((item) => item.classList.toggle("active", item === button));
    document.querySelectorAll("[data-workspace-panel]").forEach((panel) => panel.classList.toggle("mobile-tab-active", panel.dataset.workspacePanel === button.dataset.workspaceTab));
  }));
}

function addDraftScene() {
  if (!latestResult) {
    showToast("请先在项目设置中导入原作并生成台本", "warning");
    document.querySelector(".workspace-page")?.classList.add("settings-open");
    return;
  }
  const number = (latestResult.adaptation_scenes?.length || 0) + 1;
  const scene = {
    scene_id: `draft_${Date.now()}`,
    title: `场景 ${String(number).padStart(2, "0")} · 未命名`,
    background: "bg_default",
    bgm: "-",
    adapter: "manual",
    stage: defaultStage("bg_default"),
    blocks: [{ type: "narration", text: "在这里写下这一场的第一句台本。" }],
  };
  latestResult = { ...latestResult, adaptation_scenes: [...(latestResult.adaptation_scenes || []), scene] };
  renderGamePreview(latestResult);
  jumpToFrame(gameFrames.findIndex((frame) => frame.sceneId === scene.scene_id));
  projectSession?.markDirty({ ...projectFormPayload(), result: latestResult, status: "done", version_note: "新建场景草稿" });
  showToast("已添加场景草稿", "success");
}

function updateActiveSceneResource(key, value) {
  const sceneId = gameFrames[activeFrameIndex]?.sceneId;
  const scenes = latestResult?.adaptation_scenes;
  if (!sceneId || !scenes) return;
  const scene = scenes.find((item) => item.scene_id === sceneId);
  if (!scene) return;
  scene[key] = value;
  renderGamePreview(latestResult);
  jumpToFrame(gameFrames.findIndex((frame) => frame.sceneId === sceneId));
  projectSession?.markDirty({ ...projectFormPayload(), result: latestResult, status: "done", version_note: key === "bgm" ? "替换场景音乐" : "替换场景背景" });
  showToast(key === "bgm" ? "场景音乐已替换" : "场景背景已替换", "success");
}

async function saveCurrentProject(notify = false) {
  if (!projectSession) return null;
  try {
    const project = await projectSession.save({ ...projectFormPayload(), result: latestResult, status: latestResult ? "done" : "draft" });
    currentProject = project;
    updateWorkbenchHeadline();
    if (notify) showToast("项目已保存", "success");
    return project;
  } catch (error) {
    showToast(`保存失败：${error.message}`, "error");
    return null;
  }
}

function projectFormPayload() {
  return {
    title: document.querySelector("#title")?.value.trim() || "未命名企划",
    source_text: document.querySelector("#novelText")?.value || "",
    filename: document.querySelector("#bookFile")?.files?.[0]?.name || currentProject?.filename || "",
    pov_character: document.querySelector("#pov")?.value.trim() || "",
    max_scenes: parseMaxScenes(document.querySelector("#maxScenes")?.value),
    llm_model: selectedModel(),
    current_scene_id: gameFrames[activeFrameIndex]?.sceneId || "",
    ui_state: { active_frame: activeFrameIndex, full_book: Boolean(document.querySelector("#fullBookMode")?.checked) },
  };
}

function hydrateProject(project) {
  if (!project) return;
  restoringProject = true;
  currentProject = project;
  projectSession.projectId = project.project_id;
  projectSession.project = project;
  const assign = (selector, value) => { const target = document.querySelector(selector); if (target && value !== undefined && value !== null) target.value = value; };
  assign("#title", project.title || "");
  assign("#pov", project.pov_character || "");
  assign("#maxScenes", project.max_scenes || 5);
  assign("#novelText", project.source_text || "");
  if (project.llm_model) setSelectedModel(project.llm_model);
  latestResult = project.result || null;
  if (latestResult) renderResult(latestResult);
  updateRecommendedScenes(project.source_text || "");
  updateWorkbenchHeadline();
  restoringProject = false;
}

function updateSaveState({ state, project, error } = {}) {
  if (project) currentProject = project;
  const target = document.querySelector("#saveState");
  if (!target) return;
  const labels = { idle: "尚未保存", dirty: "有未保存更改", saving: "保存中…", saved: "已保存", offline: "离线快照", failed: "保存失败", conflict: "需要处理冲突" };
  target.textContent = labels[state] || state;
  target.dataset.state = state;
  const lastSaved = document.querySelector("#lastSaved");
  if (lastSaved && project?.last_saved_at) lastSaved.textContent = new Date(project.last_saved_at * 1000).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  if (state === "offline") showToast("网络已断开，编辑内容保存在本地快照中", "warning");
  if (state === "failed" && error) showToast(`同步失败：${error.message}`, "error");
  updateWorkbenchHeadline();
}

function updateWorkbenchHeadline() {
  const title = document.querySelector("#title")?.value.trim() || currentProject?.title || "未命名企划";
  const titleTarget = document.querySelector("#projectTitleStatus");
  if (titleTarget) titleTarget.textContent = title;
  const lifecycle = document.querySelector("#projectLifecycle");
  if (lifecycle) lifecycle.textContent = latestResult ? "已生成" : currentProject?.status === "running" ? "生成中" : "草稿";
  const model = document.querySelector("#currentModelStatus");
  if (model) model.textContent = selectedModelLabel();
}

function showFirstRunGuide() {
  if (localStorage.getItem("novel2gal.onboarding.complete")) return;
  const steps = [
    ["导入你的小说", "上传 TXT、Markdown、EPUB，或直接粘贴正文。"],
    ["确定核心视角", "指定故事的观察者，控制角色能够知道的信息。"],
    ["选择处理策略", "用质量优先完成正式改编，或用速度优先快速试跑。"],
    ["开始剧情编排", "系统会依次完成切分、分析、视角过滤与剧本生成。"],
    ["预览并保存", "在舞台检查场景、分支和资源，然后保存或导出。"],
  ];
  let index = 0;
  openModal({
    title: "欢迎来到 Novel2Gal 制作室",
    eyebrow: "第一册 · 新手台本",
    className: "onboarding-modal",
    content: `<div class="onboarding-visual"><span class="open-book-mark"><i></i><b></b></span></div><div class="onboarding-step"><small>第 <b data-guide-index>1</b> / ${steps.length} 步</small><h3 data-guide-title>${steps[0][0]}</h3><p data-guide-copy>${steps[0][1]}</p></div>`,
    actions: '<button class="anime-button anime-button--ghost" type="button" data-guide-skip>跳过引导</button><button class="anime-button anime-button--primary" type="button" data-guide-next>下一步</button>',
    onMount(panel, close) {
      const finish = () => { localStorage.setItem("novel2gal.onboarding.complete", "1"); close(); };
      panel.querySelector("[data-guide-skip]").addEventListener("click", finish);
      panel.querySelector("[data-guide-next]").addEventListener("click", () => {
        index += 1;
        if (index >= steps.length) { finish(); return; }
        panel.querySelector("[data-guide-index]").textContent = index + 1;
        panel.querySelector("[data-guide-title]").textContent = steps[index][0];
        panel.querySelector("[data-guide-copy]").textContent = steps[index][1];
        if (index === steps.length - 1) panel.querySelector("[data-guide-next]").textContent = "开始创作";
      });
    },
  });
}

function setupCommandPalette(path) {
  const commands = [
    { id: "new", label: "新建项目", hint: "新作品", action: () => navigateTo("/create?new=1") },
    { id: "projects", label: "打开项目列表", hint: "作品存档", action: () => navigateTo("/projects") },
    { id: "templates", label: "浏览模板与案例", hint: "模板书架", action: () => navigateTo("/templates") },
    { id: "settings", label: "打开动效设置", hint: "显示设置", action: () => document.querySelector("[data-open-settings]")?.click() },
  ];
  if (path === "/create" || path === "/studio") commands.unshift(
    { id: "save", label: "保存当前项目", hint: "Ctrl / Cmd + S", action: () => saveCurrentProject(true) },
    { id: "export", label: "打开导出中心", hint: "导出作品", action: async () => { const project = await saveCurrentProject(); if (project) openExportCenter(project); } },
    { id: "toggle-stage", label: "播放 / 暂停舞台", hint: "Space", action: () => document.querySelector("#gameAuto")?.click() },
    { id: "previous-scene", label: "上一场景", hint: "←", action: () => document.querySelector("#gamePrev")?.click() },
    { id: "next-scene", label: "下一场景", hint: "→", action: () => document.querySelector("#gameNext")?.click() },
    { id: "versions", label: "查看版本历史", hint: "历史版本", action: () => document.querySelector("#versionHistoryButton")?.click() },
    { id: "resources", label: "打开素材中心", hint: "演出素材", action: () => document.querySelector("#resourceCenterButton")?.click() },
  );
  commandPalette.mount(commands);
}

async function runTextInputJob(formData) {
  const payload = {
    title: formData.get("title") || "未命名小说",
    pov_character: formData.get("pov"),
    text: formData.get("novelText"),
    llm_model: selectedModel(),
  };
  const maxScenes = parseMaxScenes(formData.get("maxScenes"));
  if (maxScenes) payload.max_scenes = maxScenes;
  return fetch("/api/pipeline/run/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

async function runUploadedFile(formData, file) {
  const payload = new FormData();
  payload.append("file", file);
  payload.append("pov_character", formData.get("pov"));
  payload.append("llm_model", selectedModel());
  const maxScenes = parseMaxScenes(formData.get("maxScenes"));
  if (maxScenes) payload.append("max_scenes", String(maxScenes));
  const title = formData.get("title");
  if (title) payload.append("title", title);
  return fetch("/api/pipeline/upload", {
    method: "POST",
    body: payload,
  });
}

async function runUploadedFileJob(formData, file) {
  const payload = new FormData();
  payload.append("file", file);
  payload.append("pov_character", formData.get("pov"));
  payload.append("llm_model", selectedModel());
  const fullBookMode = Boolean(document.querySelector("#fullBookMode")?.checked);
  const maxScenes = fullBookMode ? null : parseMaxScenes(formData.get("maxScenes"));
  if (maxScenes) payload.append("max_scenes", String(maxScenes));
  const title = formData.get("title");
  if (title) payload.append("title", title);
  return fetch("/api/pipeline/upload/jobs", {
    method: "POST",
    body: payload,
  });
}

async function runUploadedProject(formData, file) {
  const payload = new FormData();
  payload.append("file", file);
  payload.append("pov_character", formData.get("pov"));
  payload.append("llm_model", selectedModel());
  const fullBookMode = Boolean(document.querySelector("#fullBookMode")?.checked);
  const maxScenes = fullBookMode ? null : parseMaxScenes(formData.get("maxScenes"));
  if (maxScenes) payload.append("max_scenes", String(maxScenes));
  const title = formData.get("title");
  if (title) payload.append("title", title);
  return fetch("/api/projects/upload", {
    method: "POST",
    body: payload,
  });
}

async function waitForProject(projectId) {
  if (!projectId) {
    throw new Error("Missing project id");
  }
  let lastProgress = "";
  for (;;) {
    const response = await fetch(`/api/projects/${encodeURIComponent(projectId)}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    const progress = `${payload.status}:${payload.completed_chapters}/${payload.total_chapters}:${payload.current_chapter}`;
    if (progress !== lastProgress) {
      lastProgress = progress;
      updateProjectThinkingProgress(payload);
    }
    if (payload.status === "done" && payload.result) {
      return payload.result;
    }
    if (payload.status === "failed") {
      throw new Error(payload.error || "Project generation failed");
    }
    await delay(2500);
  }
}

function updateProjectThinkingProgress(payload) {
  if (!thoughtLog) return;
  const done = payload.completed_chapters || 0;
  const total = payload.total_chapters || 0;
  if (payload.status === "queued") {
    updateThinkingStep("import", "active", `已创建项目 ${payload.project_id}，等待分章任务开始。`);
    return;
  }
  if (payload.status === "running") {
    const chapter = payload.current_chapter ? `，当前：${payload.current_chapter}` : "";
    updateThinkingStep("adapt", "active", `分章生成中：${done}/${total}${chapter}`);
    return;
  }
  if (payload.status === "done") {
    updateThinkingStep("check", "done", `项目已完成：${done}/${total} 章。`);
  }
}

async function waitForPipelineJob(jobId) {
  if (!jobId) {
    throw new Error("Missing pipeline job id");
  }
  let lastStatus = "";
  for (;;) {
    const response = await fetch(`/api/pipeline/jobs/${encodeURIComponent(jobId)}`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    if (payload.status !== lastStatus) {
      lastStatus = payload.status;
      updateJobThinkingProgress(payload);
    }
    if (payload.status === "done" && payload.result) {
      return payload.result;
    }
    if (payload.status === "failed") {
      throw new Error(payload.error || "Pipeline job failed");
    }
    await delay(2000);
  }
}

function updateJobThinkingProgress(payload) {
  if (!thoughtLog) return;
  if (payload.status === "queued") {
    updateThinkingStep("import", "active", `已提交任务 ${payload.job_id}，等待后端开始处理。`);
    return;
  }
  if (payload.status === "running") {
    updateThinkingStep("adapt", "active", `任务 ${payload.job_id} 正在后台生成，长篇小说可能需要几分钟。`);
    return;
  }
  if (payload.status === "done") {
    updateThinkingStep("check", "done", `任务 ${payload.job_id} 已完成。`);
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function renderResult(result) {
  latestResult = result;
  activePovCharacter = String(result.pov_character || form.elements.pov?.value || "").trim();
  characterProfilesByName = Object.fromEntries(
    (result.analysis.characters || []).map((character) => [character.name, character]),
  );
  charactersList.replaceChildren(
    ...result.analysis.characters.map((character) => {
      const item = document.createElement("li");
      const personality = character.personality ? ` · ${character.personality}` : "";
      const speech = character.speech_style ? ` · ${character.speech_style}` : "";
      const copy = document.createElement("span");
      copy.textContent = `${character.name} · ${character.role}${personality}${speech}`;
      const generate = document.createElement("button");
      generate.type = "button";
      generate.className = "character-generate-button";
      generate.textContent = character.visual_notes?.generated_portrait ? "重新生成立绘" : "AI 生成立绘";
      generate.addEventListener("click", () => generateCharacterPortrait(character, generate));
      item.append(copy, generate);
      return item;
    }),
  );

  scenesList.replaceChildren(
    ...result.adaptation_scenes.map((scene) => {
      const item = document.createElement("li");
      item.textContent = `${scene.scene_id} · ${scene.title}`;
      return item;
    }),
  );

  renpyOutput.textContent = result.exports.renpy || "";
  jsonOutput.textContent = JSON.stringify(result, null, 2);
  if (sceneRecommend && result.stats?.source_scenes) {
    const light = Math.max(3, Math.ceil(result.stats.source_scenes * 0.35));
    const standard = Math.max(light, Math.ceil(result.stats.source_scenes * 0.6));
    sceneRecommend.textContent = `推荐场景数：${light}-${standard} 幕（本次源场景 ${result.stats.source_scenes} 个）`;
  }
  renderAdapterStatus(result);
  renderGamePreview(result);
  if (!restoringProject && projectSession) {
    projectSession.markDirty({ ...projectFormPayload(), result, status: "done", version_note: "生成完成自动保存" });
  }
}

async function generateCharacterPortrait(character, button) {
  button.disabled = true;
  button.textContent = "生成中…";
  try {
    const project = currentProject?.project_id ? currentProject : await saveCurrentProject();
    if (!project?.project_id) throw new Error("请先保存项目后再生成角色立绘");
    const result = await api.generateCharacterImage(project.project_id, character.character_id || character.name, {
      style: activeVisualStyle === "real" ? "real" : "anime",
      size: "1024x1536",
    });
    const image = result.images?.[0] || {};
    const url = image.url || (image.b64_json ? `data:image/png;base64,${image.b64_json}` : "");
    if (!url) throw new Error("生图 API 未返回图片");
    character.visual_notes = { ...(character.visual_notes || {}), generated_portrait: url };
    characterProfilesByName[character.name] = character;
    currentProject = await api.updateProject(project.project_id, { result: latestResult, version_note: `生成角色立绘：${character.name}` });
    renderGamePreview(latestResult);
    button.textContent = "重新生成立绘";
    showToast(`${character.name} 的立绘已生成`, "success");
  } catch (error) {
    button.disabled = false;
    button.textContent = "AI 生成立绘";
    showToast(error.message || "立绘生成失败", "error");
  }
}

window.runPipeline = runPipeline;
window.renderGamePreview = renderGamePreview;
window.renderAdapterStatus = renderAdapterStatus;
window.renderStage = renderStage;
window.applyChoiceBranch = applyChoiceBranch;
window.updateThinkingStep = updateThinkingStep;

function isTextFile(filename) {
  return [".txt", ".md", ".markdown"].some((suffix) => filename.toLowerCase().endsWith(suffix));
}

function titleFromFilename(filename) {
  return filename.replace(/\.[^.]+$/, "");
}

function parseMaxScenes(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

async function loadExternalAssets() {
  try {
    const response = await fetch("/static/assets/asset_manifest.json?v=20260710-runtime");
    if (!response.ok) return;
    const payload = await response.json();
    externalAssetCatalog = {
      backgrounds: localizeAssets(payload.backgrounds),
      portraits: localizeAssets(payload.portraits),
      bgm: localizeAssets(payload.bgm),
    };
    if (gameScreen) renderActiveFrame();
  } catch {
    externalAssetCatalog = { backgrounds: [], portraits: [], bgm: [] };
  }
}

function localizeAssets(items) {
  if (!Array.isArray(items)) return [];
  return items.filter((asset) => asset?.id && asset?.url).map((asset) => {
    const pathname = new URL(asset.url, window.location.origin).pathname;
    const extension = pathname.includes(".") ? pathname.slice(pathname.lastIndexOf(".")) : ".bin";
    return { ...asset, url: `/static/assets/runtime/${asset.id}${extension}` };
  });
}

function updateRecommendedScenes(text) {
  if (!sceneRecommend) return;
  const count = estimateSceneCount(text);
  if (!count) {
    sceneRecommend.textContent = "推荐场景数：输入文本后估算，EPUB 会在运行时按章节拆分";
    return;
  }
  const light = Math.max(3, Math.ceil(count * 0.35));
  const standard = Math.max(light, Math.ceil(count * 0.6));
  sceneRecommend.textContent = `推荐场景数：${light}-${standard} 幕（预计源场景约 ${count} 个）`;
}

function estimateSceneCount(text) {
  const compact = String(text || "").trim();
  if (!compact) return 0;
  const transitionMatches = compact.match(/第二天|第三天|清晨|早晨|上午|中午|午休|下午|傍晚|晚上|夜里|后来|回到|来到|离开|教室|走廊|浴室|厕所|女厕|卫生间|洗手间/g) || [];
  const paragraphCount = compact.split(/\n\s*\n+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(compact.length / 900), transitionMatches.length + 1, Math.ceil(paragraphCount / 2));
}

function jumpToFrame(index) {
  if (!gameFrames.length || !Number.isFinite(index)) return;
  activeFrameIndex = Math.min(Math.max(index, 0), gameFrames.length - 1);
  renderActiveFrame();
}

function scheduleAutoplay() {
  clearTimeout(autoplayTimer);
  if (!autoplayEnabled || activeFrameIndex >= gameFrames.length - 1) {
    autoplayEnabled = false;
    gameAuto?.classList.remove("active");
    return;
  }
  const current = gameFrames[activeFrameIndex] || emptyFrame();
  if ((current.choices || []).length) return;
  autoplayTimer = setTimeout(() => {
    activeFrameIndex += 1;
    renderActiveFrame();
  }, 1450);
}

function selectedModel() {
  return llmModelInput?.value || "deepseek-v4-pro";
}

function selectedModelLabel() {
  return MODEL_DETAILS[selectedModel()]?.label || "V4 Pro";
}

function setSelectedModel(model) {
  const normalized = model === "deepseek-v4-flash" ? "deepseek-v4-flash" : "deepseek-v4-pro";
  if (llmModelInput) {
    llmModelInput.value = normalized;
  }
  modelOptions.forEach((button) => {
    button.classList.toggle("active", button.dataset.model === normalized);
    button.setAttribute("aria-pressed", String(button.dataset.model === normalized));
  });
  updateModelHint();
}

function updateModelHint() {
  if (!modelHint) return;
  const detail = MODEL_DETAILS[selectedModel()] || MODEL_DETAILS["deepseek-v4-pro"];
  modelHint.textContent = `${detail.hint} 两个模式都按 1M 上下文链路传参。`;
}

function startThinkingProgress() {
  clearInterval(thinkingTimer);
  resetThinkingSteps();
  thinkingStartedAt = Date.now();
  thoughtLog.textContent = `使用 ${selectedModelLabel()} 处理。`;
  document.querySelector("#aiModelMetric").textContent = selectedModelLabel();
  document.querySelector("#aiCacheMetric").textContent = "检查中";
  document.querySelector("#aiElapsedMetric").textContent = "0.0s";
  let stepIndex = 0;
  updateThinkingStep(THINKING_STEPS[stepIndex][0], "active", THINKING_STEPS[stepIndex][1]);
  thinkingTimer = setInterval(() => {
    updateThinkingStep(THINKING_STEPS[stepIndex][0], "done", THINKING_STEPS[stepIndex][1]);
    stepIndex = Math.min(stepIndex + 1, THINKING_STEPS.length - 1);
    updateThinkingStep(THINKING_STEPS[stepIndex][0], "active", THINKING_STEPS[stepIndex][1]);
  }, 480);
}

async function completeThinkingProgress(result) {
  const elapsed = Date.now() - thinkingStartedAt;
  const remaining = Math.max(0, MIN_THINKING_MS - elapsed);
  if (remaining) await delay(remaining);
  clearInterval(thinkingTimer);
  THINKING_STEPS.forEach(([step, detail]) => updateThinkingStep(step, "done", detail));
  thoughtStatus.textContent = "done";
  thoughtLog.textContent = `完成：${result.adaptation_scenes.length} 个场景，${result.analysis.characters.length} 个角色。`;
  const cacheHit = Boolean(result.cache_hit || result.cached);
  const cacheMetric = document.querySelector("#aiCacheMetric");
  const cacheStateTarget = document.querySelector("#cacheState");
  if (cacheMetric) cacheMetric.textContent = cacheHit ? "已复用" : "未命中";
  if (cacheStateTarget) cacheStateTarget.textContent = cacheHit ? "已命中" : "未命中";
  const elapsedMetric = document.querySelector("#aiElapsedMetric");
  if (elapsedMetric) elapsedMetric.textContent = `${((Date.now() - thinkingStartedAt) / 1000).toFixed(1)}s`;
  const remainingMetric = document.querySelector("#aiRemainingMetric");
  if (remainingMetric) remainingMetric.textContent = "0";
}

function failThinkingProgress(error) {
  clearInterval(thinkingTimer);
  const active = document.querySelector(".thought-steps li.active");
  if (active) active.className = "failed";
  thoughtStatus.textContent = "failed";
  thoughtLog.textContent = String(error);
  adapterStatus.textContent = "改编来源：失败";
}

function resetThinkingSteps() {
  document.querySelectorAll(".thought-steps li").forEach((item) => {
    item.className = "queued";
  });
  thoughtStatus.textContent = "running";
  thoughtLog.textContent = "开始处理";
}

function updateThinkingStep(step, status, detail = "") {
  const item = document.querySelector(`.thought-steps li[data-step="${step}"]`);
  if (!item) return;
  item.className = status;
  if (status === "active") thoughtStatus.textContent = "thinking";
  if (status === "active") {
    const index = Math.max(0, THINKING_STEPS.findIndex(([key]) => key === step));
    const current = document.querySelector("#aiCurrentStep");
    const remaining = document.querySelector("#aiRemainingMetric");
    if (current) current.textContent = THINKING_STEPS[index]?.[1]?.replace(/^正在/, "") || step;
    if (remaining) remaining.textContent = String(Math.max(0, THINKING_STEPS.length - index - 1));
  }
  const elapsed = document.querySelector("#aiElapsedMetric");
  if (elapsed && thinkingStartedAt) elapsed.textContent = `${((Date.now() - thinkingStartedAt) / 1000).toFixed(1)}s`;
  if (detail) thoughtLog.textContent = detail;
}

function renderGamePreview(result) {
  activeVisualStyle = inferResultVisualStyle(result);
  gameFrames = buildGameFrames(result);
  activeFrameIndex = 0;
  renderSceneTimeline();
  renderSceneNavigator(result);
  renderPerformanceTracks(result);
  const estimatedCost = document.querySelector("#estimatedCost");
  if (estimatedCost) estimatedCost.textContent = `¥${((result.adaptation_scenes?.length || 0) * .18).toFixed(2)}`;
  renderActiveFrame();
}

function renderSceneTimeline() {
  const track = document.querySelector("#sceneTimelineTrack");
  if (!track) return;
  const scenes = [];
  gameFrames.forEach((frame, index) => {
    if (scenes.some((item) => item.id === frame.sceneId)) return;
    scenes.push({ id: frame.sceneId, title: frame.title || frame.sceneId, index });
  });
  track.innerHTML = scenes.map((scene, index) => `<button type="button" data-frame-index="${scene.index}"><span>${String(index + 1).padStart(2, "0")}</span><strong>${scene.title}</strong></button>`).join("");
  track.querySelectorAll("[data-frame-index]").forEach((button) => button.addEventListener("click", () => jumpToFrame(Number(button.dataset.frameIndex))));
}

function renderSceneNavigator(result) {
  const list = document.querySelector("#sceneNavigatorList");
  const count = document.querySelector("#sceneNavigatorCount");
  if (!list) return;
  const scenes = result?.adaptation_scenes || [];
  if (count) count.textContent = `${scenes.length} 个场景`;
  if (!scenes.length) {
    list.innerHTML = '<div class="scene-nav-empty"><span>01</span><p>生成后，章节、场景和分支会排列在这里。</p></div>';
    return;
  }
  list.innerHTML = scenes.map((scene, index) => `${index % 5 === 0 ? `<div class="scene-chapter-label">第 ${Math.floor(index / 5) + 1} 章</div>` : ""}<button class="scene-nav-item" type="button" draggable="true" data-scene-id="${escapeMarkup(scene.scene_id)}"><span class="scene-nav-thumb scene-nav-thumb--${sceneTone(scene.background)}"><b>${String(index + 1).padStart(2, "0")}</b></span><span class="scene-nav-copy"><strong>${escapeMarkup(scene.title || scene.scene_id)}</strong><small>${escapeMarkup(scene.background || "默认背景")} · ${(scene.blocks || []).length} 行</small></span><i title="拖动排序">⠿</i></button>`).join("");
  list.querySelectorAll("[data-scene-id]").forEach((button) => {
    button.addEventListener("click", () => jumpToFrame(Math.max(0, gameFrames.findIndex((frame) => frame.sceneId === button.dataset.sceneId))));
    button.addEventListener("dragstart", (event) => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", button.dataset.sceneId);
      button.classList.add("is-dragging");
    });
    button.addEventListener("dragend", () => button.classList.remove("is-dragging"));
    button.addEventListener("dragover", (event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; });
    button.addEventListener("drop", (event) => {
      event.preventDefault();
      reorderScene(event.dataTransfer.getData("text/plain"), button.dataset.sceneId);
    });
  });
}

function reorderScene(sourceId, targetId) {
  if (!sourceId || !targetId || sourceId === targetId || !latestResult?.adaptation_scenes) return;
  const scenes = [...latestResult.adaptation_scenes];
  const sourceIndex = scenes.findIndex((scene) => scene.scene_id === sourceId);
  const targetIndex = scenes.findIndex((scene) => scene.scene_id === targetId);
  if (sourceIndex < 0 || targetIndex < 0) return;
  const [scene] = scenes.splice(sourceIndex, 1);
  scenes.splice(targetIndex, 0, scene);
  latestResult = { ...latestResult, adaptation_scenes: scenes, stats: { ...latestResult.stats, adaptation_scenes: scenes.length } };
  renderGamePreview(latestResult);
  jumpToFrame(Math.max(0, gameFrames.findIndex((frame) => frame.sceneId === sourceId)));
  projectSession?.markDirty({ ...projectFormPayload(), result: latestResult, status: "done", version_note: "调整场景顺序" });
  showToast("场景顺序已调整", "success");
}

function renderPerformanceTracks(result) {
  const container = document.querySelector("#performanceTracks");
  if (!container) return;
  const scenes = result?.adaptation_scenes || [];
  if (!scenes.length) {
    container.innerHTML = '<div class="track-empty">生成场景后显示对白、角色、表情、背景、音乐、音效与转场轨道。</div>';
    return;
  }
  const tracks = [
    ["对白", (scene) => `${(scene.blocks || []).filter((block) => ["dialogue", "narration"].includes(block.type)).length} 行`],
    ["角色", (scene) => `${(scene.stage?.characters || []).length || "—"}`],
    ["表情", () => "普通"],
    ["背景", (scene) => scene.background || "默认"],
    ["BGM", (scene) => scene.bgm || "—"],
    ["音效", (scene) => scene.sfx || "—"],
    ["转场", (scene) => scene.transition || "淡入"],
  ];
  container.innerHTML = tracks.map(([label, value]) => `<div class="performance-track"><strong>${label}</strong><div>${scenes.map((scene, index) => `<button type="button" data-track-scene="${escapeMarkup(scene.scene_id)}" title="${escapeMarkup(scene.title || scene.scene_id)}"><span>${String(index + 1).padStart(2, "0")}</span>${escapeMarkup(value(scene))}</button>`).join("")}</div></div>`).join("");
  container.querySelectorAll("[data-track-scene]").forEach((button) => button.addEventListener("click", () => jumpToFrame(Math.max(0, gameFrames.findIndex((frame) => frame.sceneId === button.dataset.trackScene)))));
}

function sceneTone(background = "") {
  if (/night|old|dark/i.test(background)) return "night";
  if (/class|school/i.test(background)) return "school";
  if (/street|evening/i.test(background)) return "evening";
  return "default";
}

function escapeMarkup(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function renderAdapterStatus(result) {
  const counts = result.adaptation_scenes.reduce((total, scene) => {
    const key = scene.adapter || "rules";
    total[key] = (total[key] || 0) + 1;
    return total;
  }, {});
  if (counts.deepseek) {
    adapterStatus.textContent = `改编来源：DeepSeek+RAG · ${selectedModelLabel()} · ${counts.deepseek} 场`;
    adapterStatus.className = "adapter-status ai";
    return;
  }
  if (counts.rules_fallback) {
    adapterStatus.textContent = `改编来源：规则回退 ${counts.rules_fallback} 场`;
    adapterStatus.className = "adapter-status fallback";
    return;
  }
  adapterStatus.textContent = `改编来源：本地规则 ${counts.rules || result.adaptation_scenes.length} 场`;
  adapterStatus.className = "adapter-status rules";
}

function inferResultVisualStyle(result) {
  const notes = (result.analysis?.characters || []).map((character) => character.visual_notes || {});
  const animeCount = notes.filter((note) => String(note.style || "").toLowerCase() === "anime").length;
  const realCount = notes.filter((note) => String(note.style || "").toLowerCase() === "real").length;
  return animeCount > realCount ? "anime" : "real";
}

function buildGameFrames(result) {
  const frames = [];
  result.adaptation_scenes.forEach((scene) => {
    scene.blocks.forEach((block) => {
      if (block.type === "narration") {
        frames.push(frameFromBlock(scene, block, "旁白", block.text));
      }
      if (block.type === "dialogue") {
        frames.push(frameFromBlock(scene, block, block.speaker || "角色", block.text));
      }
      if (block.type === "choice") {
        frames.push({
          sceneId: scene.scene_id,
          title: scene.title,
          background: scene.background,
          stage: scene.stage || defaultStage(scene.background),
          bgm: scene.bgm,
          speaker: "选择",
          text: "我接下来怎么做？",
          choiceMode: block.choice_mode || "parallel",
          choices: (block.choices || []).map((choice) => ({
            ...choice,
            choice_mode: block.choice_mode || "parallel",
          })),
        });
      }
    });
  });
  return frames.length ? frames : [emptyFrame()];
}

function frameFromBlock(scene, block, speaker, text) {
  return {
    sceneId: scene.scene_id,
    title: scene.title,
    background: scene.background,
    stage: scene.stage || defaultStage(scene.background),
    bgm: scene.bgm,
    speaker,
    speakerKey: block.speaker_key || "",
    text,
    choices: block.choices || [],
    generatedBranch: false,
  };
}

function emptyFrame() {
  return {
    sceneId: "empty",
    title: "未生成",
    background: "bg_default",
    stage: defaultStage("bg_default"),
    bgm: "-",
    speaker: "旁白",
    text: "没有可播放的场景。",
    choices: [],
  };
}

function renderActiveFrame() {
  if (!gameScreen) return;
  const frame = gameFrames[activeFrameIndex] || emptyFrame();
  if (!motionController.reduced) {
    gameScreen.animate(
      [{ opacity: .58, filter: "brightness(1.25)", clipPath: "inset(0 50% 0 50%)" }, { opacity: 1, filter: "brightness(1)", clipPath: "inset(0 0 0 0)" }],
      { duration: 360, easing: "cubic-bezier(.16,1,.3,1)" },
    );
  }
  const hasChoices = (frame.choices || []).length > 0;
  gameScreen.dataset.bg = frame.background || "bg_default";
  gameScreen.dataset.visualStyle = activeVisualStyle;
  gameScreen.classList.toggle("choice-active", hasChoices);
  renderStage(frame);
  applySceneBackground(frame);
  updateBgm(frame);
  gameCounter.textContent = `${gameFrames.length ? activeFrameIndex + 1 : 0} / ${gameFrames.length}`;
  if (gameJump) {
    gameJump.max = String(Math.max(gameFrames.length, 1));
    gameJump.value = String(gameFrames.length ? activeFrameIndex + 1 : 1);
  }
  gameSceneId.textContent = sceneDisplayLabel(frame);
  gameBgm.textContent = `bgm: ${frame.bgm || "-"}`;
  document.querySelectorAll("#sceneTimelineTrack [data-frame-index]").forEach((button) => {
    const index = Number(button.dataset.frameIndex);
    const nextIndex = button.nextElementSibling ? Number(button.nextElementSibling.dataset.frameIndex) : Number.POSITIVE_INFINITY;
    button.classList.toggle("active", activeFrameIndex >= index && activeFrameIndex < nextIndex);
  });
  document.querySelectorAll("#sceneNavigatorList [data-scene-id]").forEach((button) => button.classList.toggle("active", button.dataset.sceneId === frame.sceneId));
  document.querySelectorAll("#performanceTracks [data-track-scene]").forEach((button) => button.classList.toggle("active", button.dataset.trackScene === frame.sceneId));
  const backgroundSelect = document.querySelector("#backgroundQuickSelect");
  const bgmSelect = document.querySelector("#bgmQuickSelect");
  if (backgroundSelect && [...backgroundSelect.options].some((option) => option.value === frame.background)) backgroundSelect.value = frame.background;
  if (bgmSelect && [...bgmSelect.options].some((option) => option.value === frame.bgm)) bgmSelect.value = frame.bgm || "-";
  gameSpeaker.textContent = frame.speaker;
  gameDialogue.textContent = frame.text;
  characterStandee.hidden = true;
  gamePrev.disabled = activeFrameIndex <= 0;
  gameNext.disabled = activeFrameIndex >= gameFrames.length - 1;
  renderChoices(frame.choices || []);
  scheduleAutoplay();
}

function renderChoices(choices) {
  choiceList.replaceChildren(
    ...choices.map((choice) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = choice.text || "选择";
      button.title = choice.text || "选择";
      button.addEventListener("click", () => {
        applyChoiceBranch(choice);
      });
      return button;
    }),
  );
}

function sceneDisplayLabel(frame) {
  const title = String(frame.title || "").trim();
  const id = String(frame.sceneId || "").trim();
  if (!title || title === "Scene 1" || title === "未生成") return id || title || "未生成";
  if (title.includes(id)) return title;
  return `${title} · ${id}`;
}

function applySceneBackground(frame) {
  const asset = selectBackgroundAsset(frame);
  if (!asset?.url) {
    sceneArt.classList.remove("asset-backed");
    sceneArt.style.backgroundImage = "";
    sceneArt.dataset.assetSource = "";
    return;
  }
  sceneArt.classList.add("asset-backed");
  sceneArt.style.backgroundImage = `linear-gradient(180deg, rgba(10, 18, 28, 0.18), rgba(10, 18, 28, 0.58)), url("${asset.url}")`;
  sceneArt.dataset.assetSource = asset.source || "";
}

function selectBackgroundAsset(frame) {
  const location = frame.stage?.location || backgroundToLocation(frame.background);
  const keys = new Set([location, frame.background, ...(frame.stage?.props || [])].filter(Boolean));
  const candidates = (externalAssetCatalog.backgrounds || []).filter((asset) => {
    const tags = new Set([asset.location, asset.style, ...(asset.tags || [])].filter(Boolean));
    return tags.has(activeVisualStyle) && [...keys].some((key) => tags.has(key));
  });
  if (!candidates.length) return null;
  return candidates[Math.abs(stableHash(`${frame.sceneId}:${location}`)) % candidates.length];
}

function backgroundToLocation(background) {
  return String(background || "").replace(/^bg_/, "") || "generic";
}

function updateBgm(frame, force = false) {
  const asset = selectBgmAsset(frame.bgm);
  if (!asset?.url) return;
  if (bgmAudio.src !== asset.url) {
    bgmAudio.src = asset.url;
  }
  if (!bgmEnabled && !force) return;
  if (bgmEnabled) {
    bgmAudio.play().catch(() => {
      bgmEnabled = false;
      gameBgmToggle?.classList.remove("active");
    });
  } else {
    bgmAudio.pause();
  }
}

function selectBgmAsset(key) {
  const normalized = String(key || "bgm_daily");
  const mood = bgmMood(normalized);
  return (externalAssetCatalog.bgm || []).find((asset) => asset.id === normalized)
    || (externalAssetCatalog.bgm || []).find((asset) => asset.id === mood)
    || (externalAssetCatalog.bgm || []).find((asset) => normalized.includes(asset.mood) || mood === asset.mood)
    || (externalAssetCatalog.bgm || []).find((asset) => (asset.tags || []).includes(mood))
    || (externalAssetCatalog.bgm || [])[0];
}

function bgmMood(value) {
  const normalized = String(value || "").toLowerCase();
  if (/romance|love|heart|confession/.test(normalized)) return "romance";
  if (/tension|tense|suspense|dark|uneasy|danger|high/.test(normalized)) return "tension";
  if (/rain/.test(normalized)) return "rain";
  if (/memory|sad|heartache|recall/.test(normalized)) return "memory";
  if (/cafe|restaurant|food|tea/.test(normalized)) return "restaurant";
  if (/street|walk|station/.test(normalized)) return "street";
  if (/peace|calm|ordinary|daily|cheerful|casual|bright/.test(normalized)) return "daily";
  return "daily";
}

function applyChoiceBranch(choice) {
  const current = gameFrames[activeFrameIndex] || emptyFrame();
  const nextFrames = gameFrames.slice(activeFrameIndex + 1).filter((frame) => !frame.generatedBranch);
  const branchFrames = [
    {
      sceneId: choice.next_label || `${current.sceneId}_choice`,
      title: current.title,
      background: current.background,
      stage: current.stage,
      bgm: current.bgm,
      speaker: generatedSpeaker(choice.branch_text),
      text: choice.branch_text || `你选择了：${choice.text}。`,
      choices: [],
      generatedBranch: true,
    },
    {
      sceneId: `${choice.next_label || current.sceneId}_converge`,
      title: current.title,
      background: current.background,
      stage: current.stage,
      bgm: current.bgm,
      speaker: "旁白",
      text: choice.converge_text || "对方停了一下，刚才的话还留在你们之间。",
      choices: [],
      generatedBranch: true,
    },
  ];
  gameFrames = [...gameFrames.slice(0, activeFrameIndex + 1), ...branchFrames, ...nextFrames];
  activeFrameIndex += 1;
  thoughtLog.textContent = `已选择：${choice.text}`;
  renderActiveFrame();
}

function choiceModeLabel(mode) {
  return mode === "opposed" ? "反向" : "并行";
}

function choiceRouteLabel(route) {
  return route === "mainline" ? "主线" : "偏离后回收";
}

function renderStage(frame) {
  const stage = frame.stage || defaultStage(frame.background);
  gameScreen.dataset.location = stage.location || "generic";
  sceneArt.querySelectorAll(".stage-prop, .stage-character").forEach((node) => node.remove());
  (stage.props || []).forEach((prop) => {
    const node = document.createElement("div");
    node.className = `stage-prop prop-${prop}`;
    const image = propImage(prop);
    if (image) {
      node.classList.add("prop-image");
      node.style.backgroundImage = `url("${image}")`;
    }
    node.setAttribute("aria-label", prop);
    sceneArt.appendChild(node);
  });
  const usedPortraits = new Set();
  const stageCharacters = (stage.characters || ["protagonist"]).slice(0, 4).map((character) => typeof character === "object" ? (character.name || character.id || "protagonist") : character);
  const activeSpeaker = focusedSpeakerName(frame, stageCharacters);
  stageCharacters.forEach((name, index) => {
    const node = document.createElement("div");
    node.className = `stage-character character-slot-${index} ${characterFocusClass(name, activeSpeaker)}`;
    const portrait = document.createElement("img");
    portrait.src = characterPortrait(name, index, usedPortraits);
    portrait.alt = displayCharacterName(name);
    portrait.loading = "lazy";
    portrait.addEventListener("error", () => {
      portrait.hidden = true;
      node.classList.add("portrait-missing");
    }, { once: true });
    const label = document.createElement("span");
    label.textContent = displayCharacterName(name);
    node.append(portrait, label);
    sceneArt.appendChild(node);
  });
}

function focusedSpeakerName(frame, stageCharacters) {
  const speaker = String(frame.speaker || "").trim();
  if (!speaker || speaker === "旁白" || speaker === "选择") return "";
  if (speaker === "我" || frame.speakerKey === "pov") {
    if (activePovCharacter && stageCharacters.some((name) => sameCharacterName(name, activePovCharacter))) {
      return activePovCharacter;
    }
    return stageCharacters.includes("protagonist") ? "protagonist" : "";
  }
  const normalizedSpeaker = normalizeCharacterToken(speaker);
  return stageCharacters.find((name) => {
    const normalizedName = normalizeCharacterToken(name);
    const displayName = normalizeCharacterToken(displayCharacterName(name));
    return normalizedName === normalizedSpeaker || displayName === normalizedSpeaker;
  }) || "";
}

function characterFocusClass(name, activeSpeaker) {
  if (!activeSpeaker) return "sprite--neutral";
  if (sameCharacterName(name, activeSpeaker)) return "sprite--active";
  if (name === "protagonist" && activeSpeaker === "protagonist") return "sprite--active";
  return "sprite--inactive";
}

function defaultStage(background) {
  if (background === "bg_home_living") {
    return { location: "home_living", props: ["sofa", "table", "chair", "cup"], characters: ["protagonist"] };
  }
  if (background === "bg_restaurant") {
    return { location: "restaurant", props: ["table", "chair", "bowl"], characters: ["protagonist"] };
  }
  if (background === "bg_bedroom") {
    return { location: "bedroom", props: ["bed", "wardrobe", "lamp"], characters: ["protagonist"] };
  }
  if (background === "bg_kitchen") {
    return { location: "kitchen", props: ["counter", "stove", "bowl"], characters: ["protagonist"] };
  }
  if (background === "bg_office") {
    return { location: "office", props: ["desk", "bookshelf", "lamp"], characters: ["protagonist"] };
  }
  if (background === "bg_village") {
    return { location: "village", props: ["tree", "fence", "road"], characters: ["protagonist"] };
  }
  if (background === "bg_field") {
    return { location: "field", props: ["field", "tree", "road"], characters: ["protagonist"] };
  }
  if (background === "bg_yard") {
    return { location: "yard", props: ["tree", "fence", "bench"], characters: ["protagonist"] };
  }
  if (background === "bg_cave_dwelling") {
    return { location: "cave_dwelling", props: ["kang", "table", "stove"], characters: ["protagonist"] };
  }
  if (background === "bg_station") {
    return { location: "station", props: ["bench", "sign", "road"], characters: ["protagonist"] };
  }
  if (background === "bg_hospital") {
    return { location: "hospital", props: ["bed", "curtain", "chair"], characters: ["protagonist"] };
  }
  if (background === "bg_shop") {
    return { location: "shop", props: ["counter", "shelf", "sign"], characters: ["protagonist"] };
  }
  if (background === "bg_bathroom") {
    return { location: "bathroom", props: ["bath", "mirror", "towel"], characters: ["protagonist"] };
  }
  if (background === "bg_toilet") {
    return { location: "toilet", props: ["sink", "mirror", "door"], characters: ["protagonist"] };
  }
  if (background === "bg_dormitory") {
    return { location: "dormitory", props: ["bed", "desk", "wardrobe"], characters: ["protagonist"] };
  }
  if (background === "bg_school_hallway") {
    return { location: "school_hallway", props: ["corridor", "window", "door"], characters: ["protagonist"] };
  }
  if (background === "bg_rooftop") {
    return { location: "rooftop", props: ["fence", "sky", "door"], characters: ["protagonist"] };
  }
  if (background === "bg_street") {
    return { location: "street", props: ["road", "streetlight", "sign"], characters: ["protagonist"] };
  }
  if (background === "bg_classroom") {
    return { location: "classroom", props: ["blackboard", "desk", "chair"], characters: ["protagonist"] };
  }
  if (background === "bg_old_school_night") {
    return { location: "old_school", props: ["windows", "door", "corridor"], characters: ["protagonist"] };
  }
  return { location: "generic", props: ["floor"], characters: ["protagonist"] };
}

function characterPortrait(name, index, usedPortraits = new Set()) {
  const generated = characterProfilesByName[name]?.visual_notes?.generated_portrait;
  if (generated) return generated;
  const bucket = portraitBucket(name).filter(isLocalAssetUrl);
  if (bucket.length) {
    const start = Math.abs(stableHash(String(name || "protagonist")) + index) % bucket.length;
    for (let offset = 0; offset < bucket.length; offset += 1) {
      const url = bucket[(start + offset) % bucket.length];
      if (!usedPortraits.has(url)) {
        usedPortraits.add(url);
        return url;
      }
    }
    return bucket[start];
  }
  const seed = [...String(name || "protagonist")].reduce((sum, char) => sum + char.charCodeAt(0), index);
  const localFallbacks = CHARACTER_PORTRAITS.filter(isLocalAssetUrl);
  const fallback = localFallbacks[Math.abs(seed) % localFallbacks.length] || "";
  if (!fallback) return "";
  usedPortraits.add(fallback);
  return fallback;
}

function portraitBucket(name) {
  const notes = characterProfilesByName[name]?.visual_notes || {};
  const text = `${name || ""} ${characterProfilesByName[name]?.role || ""} ${notes.age || ""} ${notes.gender || ""} ${notes.style || ""} ${notes.appearance || ""}`;
  const isAnime = activeVisualStyle === "anime" || /二次元|anime|动漫|动画|插画/.test(text);
  const external = externalPortraitBucket(notes, isAnime);
  if (external.length) return external;
  if (isAnime && /奶奶|爷爷|外婆|外公|老人|老汉|老头|老太|父亲|母亲|爸爸|妈妈|elder/.test(text)) return ASSET_CATALOG.portraits.anime_elder;
  if (isAnime && /小孩|孩子|少年|少女|学生|child/.test(text)) return ASSET_CATALOG.portraits.anime_child;
  if (isAnime) {
    return /男|父|哥|弟|少平|少安|male/.test(text) ? ASSET_CATALOG.portraits.anime_male : ASSET_CATALOG.portraits.anime_female;
  }
  if (/奶奶|爷爷|外婆|外公|老人|老汉|老头|老太|父亲|母亲|爸爸|妈妈|elder/.test(text)) return ASSET_CATALOG.portraits.elder;
  if (/小孩|孩子|少年|少女|学生|child/.test(text)) return ASSET_CATALOG.portraits.child;
  if (/女|她|母|姐|妹|玲|兰|霞|月|晚/.test(text)) return ASSET_CATALOG.portraits.young_female;
  if (/男|他|父|哥|弟|少平|少安|雨|默/.test(text)) return ASSET_CATALOG.portraits.young_male;
  return ASSET_CATALOG.portraits.adult_male.concat(ASSET_CATALOG.portraits.adult_female);
}

function externalPortraitBucket(notes, isAnime) {
  const wantedStyle = isAnime ? "anime" : "real";
  const gender = String(notes.gender || "unknown").toLowerCase();
  const age = String(notes.age || "").toLowerCase();
  const candidates = (externalAssetCatalog.portraits || []).filter((asset) => {
    if (asset.style !== wantedStyle) return false;
    if (isAnime && !isPlayableAnimePortrait(asset)) return false;
    if (gender !== "unknown" && asset.gender && asset.gender !== gender) return false;
    if (age && asset.age && asset.age !== age && !(age === "young" && asset.age === "adult")) return false;
    return true;
  });
  return candidates.map((asset) => asset.url);
}

function isPlayableAnimePortrait(asset) {
  const tags = asset.tags || [];
  const url = String(asset.url || "").toLowerCase();
  const id = String(asset.id || "").toLowerCase();
  if (tags.includes("standing")) return true;
  if (id.includes("_stand")) return true;
  return url.endsWith(".png") && !url.includes("syoukai");
}

function propImage(prop) {
  const candidate = ASSET_CATALOG.propImages[prop] || "";
  return isLocalAssetUrl(candidate) ? candidate : "";
}

function isLocalAssetUrl(value) {
  return String(value || "").startsWith("/static/");
}

function stableHash(value) {
  return [...value].reduce((sum, char) => ((sum * 31) + char.charCodeAt(0)) | 0, 7);
}

function displayCharacterName(name) {
  if (!name || name === "protagonist") return "主角";
  return String(name).slice(0, 4);
}

function sameCharacterName(a, b) {
  const left = normalizeCharacterToken(a);
  const right = normalizeCharacterToken(b);
  if (!left || !right) return false;
  if (left === right) return true;
  if (a === "protagonist" && activePovCharacter) return right === normalizeCharacterToken(activePovCharacter);
  if (b === "protagonist" && activePovCharacter) return left === normalizeCharacterToken(activePovCharacter);
  return false;
}

function normalizeCharacterToken(value) {
  return String(value || "")
    .replace(/^【|】$/g, "")
    .replace(/[“”"「」『』：:，,。.\s]/g, "")
    .trim();
}

function generatedSpeaker(text) {
  const value = String(text || "").trim();
  if (value.startsWith("我") || value.startsWith("（")) return "我";
  return "旁白";
}

function speakerInitial(speaker) {
  if (!speaker || speaker === "旁白" || speaker === "选择") return "景";
  return speaker.trim().slice(0, 1);
}

window.__novel2galBootstrap = "ready";
