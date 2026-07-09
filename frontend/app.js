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
const CHARACTER_PORTRAITS = [
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1527980965255-d3b416303d12?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1544725176-7c40e5a71c5e?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1531891437562-4301cf35b7e4?auto=format&fit=crop&w=420&q=80",
  "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=420&q=80",
];
const ASSET_CATALOG = {
  portraits: {
    child: [
      "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1542810634-71277d95dcbb?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&w=420&q=80",
    ],
    young_female: [
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1554151228-14d9def656e4?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=420&q=80",
    ],
    young_male: [
      "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1527980965255-d3b416303d12?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1552058544-f2b08422138a?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1564564321837-a57b7070ac4f?auto=format&fit=crop&w=420&q=80",
    ],
    adult_female: [
      "https://images.unsplash.com/photo-1544725176-7c40e5a71c5e?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=420&q=80",
    ],
    adult_male: [
      "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1568602471122-7832951cc4c5?auto=format&fit=crop&w=420&q=80",
    ],
    elder: [
      "https://images.unsplash.com/photo-1581579438747-104c53d7fbc4?auto=format&fit=crop&w=420&q=80",
      "https://images.unsplash.com/photo-1542327897-d73f4005b533?auto=format&fit=crop&w=420&q=80",
    ],
    anime_female: [
      "https://api.dicebear.com/9.x/adventurer/svg?seed=girl-a&backgroundColor=ffd5dc",
      "https://api.dicebear.com/9.x/lorelei/svg?seed=girl-b&backgroundColor=fecdd3",
      "https://api.dicebear.com/9.x/adventurer/svg?seed=heroine-c&backgroundColor=fbcfe8",
      "https://api.dicebear.com/9.x/lorelei/svg?seed=student-d&backgroundColor=e9d5ff",
    ],
    anime_male: [
      "https://api.dicebear.com/9.x/adventurer/svg?seed=boy-a&backgroundColor=bfdbfe",
      "https://api.dicebear.com/9.x/lorelei/svg?seed=boy-b&backgroundColor=c7d2fe",
      "https://api.dicebear.com/9.x/adventurer/svg?seed=hero-c&backgroundColor=bae6fd",
      "https://api.dicebear.com/9.x/lorelei/svg?seed=student-e&backgroundColor=ddd6fe",
    ],
    anime_child: [
      "https://api.dicebear.com/9.x/adventurer/svg?seed=child-a&backgroundColor=fef3c7",
      "https://api.dicebear.com/9.x/lorelei/svg?seed=child-b&backgroundColor=dcfce7",
    ],
    anime_elder: [
      "https://api.dicebear.com/9.x/adventurer/svg?seed=elder-a&backgroundColor=e5e7eb",
      "https://api.dicebear.com/9.x/lorelei/svg?seed=elder-b&backgroundColor=f3f4f6",
    ],
  },
  propImages: {
    book: "https://openmoji.org/data/color/svg/1F4D6.svg",
    paper: "https://openmoji.org/data/color/svg/1F4C4.svg",
    phone: "https://openmoji.org/data/color/svg/1F4F1.svg",
    bag: "https://openmoji.org/data/color/svg/1F392.svg",
    cup: "https://openmoji.org/data/color/svg/2615.svg",
    bowl: "https://openmoji.org/data/color/svg/1F963.svg",
    umbrella: "https://openmoji.org/data/color/svg/2602.svg",
    clothes: "https://openmoji.org/data/color/svg/1F455.svg",
    animal_dog: "https://openmoji.org/data/color/svg/1F415.svg",
    animal_cat: "https://openmoji.org/data/color/svg/1F408.svg",
    animal_chicken: "https://openmoji.org/data/color/svg/1F414.svg",
    animal_cow: "https://openmoji.org/data/color/svg/1F404.svg",
    animal_horse: "https://openmoji.org/data/color/svg/1F40E.svg",
    animal_sheep: "https://openmoji.org/data/color/svg/1F411.svg",
    weather_rain: "https://openmoji.org/data/color/svg/1F327.svg",
    weather_snow: "https://openmoji.org/data/color/svg/1F328.svg",
    weather_sun: "https://openmoji.org/data/color/svg/2600.svg",
    weather_wind: "https://openmoji.org/data/color/svg/1F32C.svg",
  },
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

function navigateTo(path) {
  if (window.location.pathname !== path) {
    window.history.pushState({}, "", path);
  }
  renderRoute(path);
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
  clearTimeout(autoplayTimer);
  autoplayEnabled = false;
  if (bgmAudio) bgmAudio.pause();
  resetWorkbenchDom();
  if (path === "/create" || path === "/studio") {
    appRoot.innerHTML = workbenchPageTemplate();
    initWorkbench();
    return;
  }
  if (path === "/templates") {
    appRoot.innerHTML = templatesPageTemplate();
    bindRouteLinks(appRoot);
    return;
  }
  if (path === "/projects") {
    appRoot.innerHTML = projectsPageTemplate();
    bindRouteLinks(appRoot);
    return;
  }
  appRoot.innerHTML = landingPageTemplate();
  bindRouteLinks(appRoot);
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
  bindRouteLinks(appRoot);
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
}

window.addEventListener("popstate", () => renderRoute(window.location.pathname));
renderRoute();

function brandMarkup(extraClass = "") {
  return `
    <a class="brand ${extraClass}" href="/" data-route aria-label="Novel2Gal 首页">
      <span class="brand-mark" aria-hidden="true">
        <span class="brand-page"></span>
        <span class="brand-spark"></span>
      </span>
      <span class="brand-copy">
        <strong>Novel2Gal</strong>
        <small>小说视角改编工作台</small>
      </span>
    </a>
  `;
}

function landingPageTemplate() {
  return `
    <section class="landing-page">
      <header class="landing-header">
        ${brandMarkup("brand-light")}
        <a class="landing-header-action" href="/create" data-route>进入工作台</a>
      </header>
      <main class="landing-main" aria-label="Novel2Gal 功能入口">
        <a class="landing-panel landing-panel-templates" href="/templates" data-route>
          <span class="panel-glow"></span>
          <div class="landing-panel-content">
            <span class="landing-kicker">Examples</span>
            <h1>模板与案例</h1>
            <p class="landing-subtitle">浏览不同类型小说的 Galgame 改编效果</p>
            <p class="landing-copy">校园恋爱、悬疑推理、奇幻冒险、日常治愈等模板。</p>
            <span class="landing-button">查看案例</span>
          </div>
        </a>
        <a class="landing-panel landing-panel-create featured" href="/create" data-route>
          <span class="panel-glow"></span>
          <div class="landing-panel-content">
            <span class="landing-kicker">Create</span>
            <h1>开始制作 Galgame</h1>
            <p class="landing-subtitle">上传小说，选择核心人物视角，生成视觉小说剧本</p>
            <p class="landing-copy">支持章节分析、角色关系、视角过滤、剧本生成与 Ren'Py 导出。</p>
            <span class="landing-button primary">立即开始</span>
          </div>
        </a>
        <a class="landing-panel landing-panel-projects" href="/projects" data-route>
          <span class="panel-glow"></span>
          <div class="landing-panel-content">
            <span class="landing-kicker">Projects</span>
            <h1>我的项目</h1>
            <p class="landing-subtitle">继续编辑历史作品，管理剧本、场景与导出记录</p>
            <p class="landing-copy">查看分析进度、修改生成结果、继续导出 Galgame 项目。</p>
            <span class="landing-button">打开项目</span>
          </div>
        </a>
      </main>
    </section>
  `;
}

function animeHeaderMarkup(activePath = "/") {
  return `
    <header class="site-header anime-header">
      ${brandMarkup()}
      <nav class="site-nav" aria-label="主导航">
        <a class="${activePath === "/" ? "active" : ""}" href="/" data-route>首页</a>
        <a class="${activePath === "/templates" ? "active" : ""}" href="/templates" data-route>模板与案例</a>
        <a class="${activePath === "/create" ? "active" : ""}" href="/create" data-route>开始制作</a>
        <a class="${activePath === "/projects" ? "active" : ""}" href="/projects" data-route>我的项目</a>
      </nav>
      <a class="header-button anime-button anime-button--primary" href="/create" data-route>进入工作台</a>
    </header>
  `;
}

function templatesPageTemplate() {
  const categories = ["全部", "校园恋爱", "悬疑推理", "奇幻冒险", "日常治愈", "我的样例"];
  const samples = [
    ["校园恋爱", "天台告白练习", "核心视角：转学生 · 12 Scenes", "轻小说校园分支演出模板"],
    ["悬疑推理", "旧教学楼的录音笔", "核心视角：调查者 · 9 Scenes", "线索、误导与回收结构样例"],
    ["日常治愈", "雨后便利店", "核心视角：店员 · 7 Scenes", "慢节奏对话与关系推进样例"],
  ];
  return `
    <section class="anime-app library-page templates-page">
      ${animeHeaderMarkup("/templates")}
      <main class="library-main">
        <section class="page-hero glass-panel">
          <span class="status-badge">Templates</span>
          <h1>模板与案例</h1>
          <p>浏览不同类型小说的 Galgame 改编效果。之后保存为样例的项目，也会沉淀到这里复用。</p>
          <div class="filter-row">
            ${categories.map((item, index) => `<button class="anime-button ${index === 0 ? "anime-button--primary" : "anime-button--ghost"}" type="button">${item}</button>`).join("")}
          </div>
        </section>
        <section class="card-grid sample-grid">
          ${samples.map(([tag, title, meta, copy], index) => `
            <article class="template-card glass-panel template-card-${index + 1}">
              <div class="template-cover"></div>
              <div class="template-body">
                <span class="status-badge">${tag}</span>
                <h2>${title}</h2>
                <p>${copy}</p>
                <small>${meta}</small>
                <div class="card-actions">
                  <button class="anime-button anime-button--ghost" type="button">预览</button>
                  <a class="anime-button anime-button--primary" href="/create" data-route>使用此样例</a>
                </div>
              </div>
            </article>
          `).join("")}
        </section>
      </main>
    </section>
  `;
}

function projectsPageTemplate() {
  return `
    <section class="anime-app library-page projects-page">
      ${animeHeaderMarkup("/projects")}
      <main class="library-main">
        <section class="page-hero glass-panel">
          <span class="status-badge">Projects</span>
          <h1>我的项目</h1>
          <p>继续编辑你的 Galgame 改编工程。项目持久化接入后，这里会显示历史作品、生成状态和导出记录。</p>
          <div class="hero-actions">
            <a class="anime-button anime-button--primary" href="/create" data-route>新建 Galgame</a>
            <button class="anime-button anime-button--ghost" type="button">导入项目 JSON</button>
            <a class="anime-button anime-button--ghost" href="/" data-route>返回首页</a>
          </div>
        </section>
        <section class="glass-panel empty-project-panel">
          <div class="empty-archive-visual" aria-hidden="true">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <span class="status-badge">Project Archive</span>
          <h2>还没有保存的项目</h2>
          <p>下一阶段会接入后端项目保存与恢复。现在可以先进入工作台上传小说，生成你的第一部 Galgame。</p>
          <a class="anime-button anime-button--primary" href="/create" data-route>开始制作</a>
        </section>
      </main>
    </section>
  `;
}

function workbenchPageTemplate() {
  return `
    <section class="workspace-page anime-app">
      <header class="site-header anime-header">
        ${brandMarkup()}
        <nav class="site-nav" aria-label="主导航">
          <a href="/" data-route>首页</a>
          <a href="/templates" data-route>模板与案例</a>
          <a class="active" href="/create" data-route>制作工作台</a>
          <a href="/projects" data-route>我的项目</a>
        </nav>
        <button id="runButton" type="button">开始制作</button>
      </header>

      <section id="workspace" class="workspace">
        <form id="pipelineForm" class="panel input-panel">
          <div class="studio-panel-title">
            <span class="status-badge">Project Setup</span>
            <h2>企划设定</h2>
          </div>
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
          <div id="sceneRecommend" class="recommend-hint">推荐场景数：输入或上传后估算</div>
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
          <label for="novelText">原作正文</label>
          <textarea id="novelText" name="novelText" placeholder="也可以不上传文件，直接把小说正文粘贴到这里。"></textarea>
        </form>

        <section class="panel summary-panel">
          <div class="panel-head">
            <h2>剧情记忆</h2>
            <span id="statusText">ready</span>
          </div>
          <div class="summary-grid">
            <div>
              <h3>角色</h3>
              <ul id="characters"></ul>
            </div>
            <div>
              <h3>场景</h3>
              <ul id="scenes"></ul>
            </div>
          </div>
        </section>

        <section id="gamePreview" class="panel preview-panel">
          <div class="panel-head">
            <h2>Galgame</h2>
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
            <button id="gameFullscreen" type="button" title="全屏播放">全屏</button>
            <button id="gamePrev" type="button" title="上一句">←</button>
            <button id="gameNext" type="button" title="下一句">→</button>
          </div>
        </section>

        <section id="thoughtPanel" class="panel thought-panel">
          <div class="panel-head">
            <h2>生成日志</h2>
            <span id="thoughtStatus">idle</span>
          </div>
          <div id="adapterStatus" class="adapter-status">改编来源：未运行</div>
          <ol class="thought-steps">
            <li data-step="import">读取原文</li>
            <li data-step="split">章节切分</li>
            <li data-step="analyze">角色分析</li>
            <li data-step="pov">视角过滤</li>
            <li data-step="adapt">剧本生成</li>
            <li data-step="check">一致性检查</li>
          </ol>
          <div id="thoughtLog" class="thought-log">等待运行</div>
        </section>

        <section class="panel output-panel">
          <div class="tabs" role="tablist">
            <button class="tab active" type="button" data-target="renpyOutput">Ren'Py</button>
            <button class="tab" type="button" data-target="jsonOutput">JSON</button>
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
  runButton.disabled = true;
  startThinkingProgress();

  try {
    const response = file && file.name.toLowerCase().endsWith(".epub")
      ? await runUploadedFileJob(formData, file)
      : await runTextInputJob(formData);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const payload = await response.json();
    const result = payload.result
      ? payload.result
      : await waitForPipelineJob(payload.job_id);
    await completeThinkingProgress(result);
    renderResult(result);
    statusText.textContent = "done";
  } catch (error) {
    failThinkingProgress(error);
    statusText.textContent = "failed";
    renpyOutput.textContent = String(error);
  } finally {
    runButton.disabled = false;
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

async function runTextInputJob(formData) {
  const payload = {
    title: formData.get("title") || "Untitled Novel",
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
  const maxScenes = parseMaxScenes(formData.get("maxScenes"));
  if (maxScenes) payload.append("max_scenes", String(maxScenes));
  const title = formData.get("title");
  if (title) payload.append("title", title);
  return fetch("/api/pipeline/upload/jobs", {
    method: "POST",
    body: payload,
  });
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
    updateThinkingStep("read", "active", `已提交任务 ${payload.job_id}，等待后端开始处理。`);
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
  activePovCharacter = String(result.pov_character || form.elements.pov?.value || "").trim();
  characterProfilesByName = Object.fromEntries(
    (result.analysis.characters || []).map((character) => [character.name, character]),
  );
  charactersList.replaceChildren(
    ...result.analysis.characters.map((character) => {
      const item = document.createElement("li");
      const personality = character.personality ? ` · ${character.personality}` : "";
      const speech = character.speech_style ? ` · ${character.speech_style}` : "";
      item.textContent = `${character.name} · ${character.role}${personality}${speech}`;
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
    const response = await fetch("/static/assets/asset_manifest.json?v=20260709-assets-expanded");
    if (!response.ok) return;
    const payload = await response.json();
    externalAssetCatalog = {
      backgrounds: Array.isArray(payload.backgrounds) ? payload.backgrounds : [],
      portraits: Array.isArray(payload.portraits) ? payload.portraits : [],
      bgm: Array.isArray(payload.bgm) ? payload.bgm : [],
    };
    if (gameScreen) renderActiveFrame();
  } catch {
    externalAssetCatalog = { backgrounds: [], portraits: [], bgm: [] };
  }
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
}

function failThinkingProgress(error) {
  clearInterval(thinkingTimer);
  const active = document.querySelector(".thought-steps li.active");
  if (active) active.className = "failed";
  thoughtStatus.textContent = "failed";
  thoughtLog.textContent = String(error);
  adapterStatus.textContent = "改编来源：失败";
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
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
  if (detail) thoughtLog.textContent = detail;
}

function renderGamePreview(result) {
  activeVisualStyle = inferResultVisualStyle(result);
  gameFrames = buildGameFrames(result);
  activeFrameIndex = 0;
  renderActiveFrame();
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
  const stageCharacters = (stage.characters || ["protagonist"]).slice(0, 4);
  const activeSpeaker = focusedSpeakerName(frame, stageCharacters);
  stageCharacters.forEach((name, index) => {
    const node = document.createElement("div");
    node.className = `stage-character character-slot-${index} ${characterFocusClass(name, activeSpeaker)}`;
    const portrait = document.createElement("img");
    portrait.src = characterPortrait(name, index, usedPortraits);
    portrait.alt = displayCharacterName(name);
    portrait.loading = "lazy";
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
  const bucket = portraitBucket(name);
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
  const fallback = CHARACTER_PORTRAITS[Math.abs(seed) % CHARACTER_PORTRAITS.length];
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
  return ASSET_CATALOG.propImages[prop] || "";
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
