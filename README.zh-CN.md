# Novel2Gal

Novel2Gal 是一个“小说 → 指定/自动核心人物视角 → Galgame 剧本”的 AI 改编工具。

它的目标不是简单把小说改成对话，而是让 AI 先理解章节、场景、人物、视角可知信息、分支选择、布景素材和可点击文本，再生成更接近 Galgame 的体验。

English documentation: [README.md](README.md)

## 当前能力

- 支持 TXT / Markdown / EPUB 导入
- 清理 EPUB 里的目录、版权页、站点水印等非正文噪声
- 如果原书有章节标题，优先按原书分章；如果没有，长文本会按剧情转折自动分“自动章节”
- 按时间和地点切分场景，已补充教室、走廊、浴室、女厕/男厕/卫生间、宿舍、午休等常见信号
- 先分析人物，过滤“这个、任何、顶楼、心的”等非人物名词
- DeepSeek 辅助识别人物、性格、说话风格、真实性/二次元风格、性别提示
- RAG 辅助改编，支持 `deepseek-v4-pro` 和 `deepseek-v4-flash`
- POV 视角约束，避免视角人物提前知道未来信息
- Galgame 预览支持短句点击、居中选项、分支后回收、跳转页、自动播放、快进、音乐开关、全屏
- 素材清单支持按标签匹配二次元背景、人物立绘和 BGM
- 后端预留生图和 TTS 接口，后续可接 GLM、通义、火山、Minimax 等国产服务
- 支持 Ren'Py 和 JSON 导出

## 项目结构

```text
frontend/              网页工作台和 Galgame 预览
backend/app/importers  TXT/Markdown/EPUB 导入
backend/app/parser     章节、场景、RAG chunk 拆分
backend/app/analysis   规则 + DeepSeek 故事/人物分析
backend/app/rag        基于源文本 chunk 的轻量检索
backend/app/pov        视角人物可知信息状态
backend/app/adaptation 规则 + DeepSeek Galgame 改编
backend/app/media      生图/TTS provider 接口占位
backend/app/exporters  Ren'Py、Markdown、JSON 导出
```

## 本地运行

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

设置 DeepSeek key：

```powershell
$env:DEEPSEEK_API="your-key"
# 或
$env:LLM_API_KEY="your-key"
```

启动：

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

打开：

```text
http://127.0.0.1:8001/
```

## 模型选择

网页里可以选择：

- `deepseek-v4-pro`：适合正式长篇改编，人物一致性和复杂剧情理解更稳
- `deepseek-v4-flash`：适合快速预览和便宜试跑

每次运行会把模型作为 `llm_model` 传给后端。

## 素材系统

素材索引在：

```text
frontend/assets/asset_manifest.json
```

当前引用来源：

- 背景：みんちりえ，https://min-chi.material.jp/
- 人物预览：わたおきば，https://wataokiba.net/
- BGM：音楽の卵，https://ontama-m.com/

第三方原始素材没有提交进仓库，因为很多免费素材站允许在游戏作品中使用，但不允许把素材包本身二次分发。确认来源许可后，可以本地缓存：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\download_assets.ps1
```

下载文件会放到 `frontend/assets/vendor/`，该目录已被 git 忽略。

## 生图和语音接口

后端现在提供计划接口：

```http
GET  /api/media/providers
POST /api/media/image/plan
POST /api/media/tts/plan
```

环境变量：

```text
IMAGE_PROVIDER=glm
IMAGE_BASE_URL=https://open.bigmodel.cn/api/paas/v4/images/generations
IMAGE_API_KEY=
IMAGE_MODEL=cogview-4

TTS_PROVIDER=openai-compatible
TTS_BASE_URL=
TTS_API_KEY=
TTS_MODEL=
```

目前先返回请求计划，不会自动花费生图或语音 token。等确认 provider 和 key 后，再加入真实调用器。

## 测试

```powershell
cd backend
.venv\Scripts\python.exe -m unittest discover -s tests
```

前端语法检查：

```powershell
node --check frontend/app.js
```

## 未来计划

- 保存项目、上传文件、生成剧本和玩家分支记录
- 接入真实生图模型，为每个场景自动生成背景/角色概念图
- 接入中文 TTS，为旁白和角色对白生成语音
- 增加素材来源归因 UI
- 用 SSE/WebSocket 展示真实改编进度，避免用户长时间等待不知道发生了什么
- 增加人物表、关系、章节、场景切分的人工审核面板
- 打包完整 Ren'Py 项目，包含素材、音频和脚本
