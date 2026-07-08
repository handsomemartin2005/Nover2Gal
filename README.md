# Novel2Gal

Novel2Gal is an AI-assisted workbench that converts long-form fiction into a Galgame-style script from a selected point of view.

It is not a simple "novel to dialogue" converter. The pipeline tries to understand chapters, scenes, characters, point-of-view knowledge, branching choices, visual staging, and playable click-through text.

Chinese documentation: [README.zh-CN.md](README.zh-CN.md)

## Current Features

- TXT / Markdown / EPUB import
- Common non-body text cleanup for EPUB front matter, copyright pages, TOC fragments, and site watermarks
- Chapter splitting from source headings, with automatic fallback chapters for long unheaded text
- Scene splitting based on time and location transitions, including classroom, hallway, bathroom, toilet, dormitory, and daily-life transitions
- Character extraction with DeepSeek refinement, including real/anime style and gender hints
- RAG-assisted scene adaptation with DeepSeek `deepseek-v4-pro` or `deepseek-v4-flash`
- Conservative POV filtering so the chosen character does not know future facts too early
- Galgame preview with short click-through lines, centered choices, branch convergence, jump, autoplay, fast-forward, BGM toggle, and fullscreen
- External asset manifest for anime backgrounds, character portraits, and BGM
- Backend media-provider planning endpoints for future image generation and TTS adapters
- Ren'Py export and JSON export

## Architecture

```text
frontend/              Browser workbench and Galgame preview
backend/app/importers  TXT/Markdown/EPUB import
backend/app/parser     Chapter, scene, and chunk splitting
backend/app/analysis   Rule + DeepSeek story and character analysis
backend/app/rag        Lightweight retrieval over source chunks
backend/app/pov        POV knowledge state construction
backend/app/adaptation Rule + DeepSeek Galgame scene generation
backend/app/media      Image/TTS provider planning endpoints
backend/app/exporters  Ren'Py, Markdown, JSON exporters
```

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set a DeepSeek key through either variable:

```powershell
$env:DEEPSEEK_API="your-key"
# or
$env:LLM_API_KEY="your-key"
```

Run locally:

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open:

```text
http://127.0.0.1:8001/
```

## Model Selection

The frontend can choose:

- `deepseek-v4-pro`: better for final long-fiction adaptation and character consistency
- `deepseek-v4-flash`: better for fast previews and cheaper iteration

Both are passed to the backend as `llm_model` per run.

## Asset Catalog

Runtime assets are indexed in:

```text
frontend/assets/asset_manifest.json
```

Current sources include:

- Backgrounds: https://min-chi.material.jp/
- Character previews: https://wataokiba.net/
- BGM: https://ontama-m.com/

Raw third-party assets are not committed. To cache referenced assets locally after reviewing source licenses:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\download_assets.ps1
```

Downloaded files go under `frontend/assets/vendor/`, which is ignored by git.

## Media Provider Interfaces

These endpoints are planning interfaces for future adapters:

```http
GET  /api/media/providers
POST /api/media/image/plan
POST /api/media/tts/plan
```

Environment variables:

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

The app intentionally returns plans first instead of silently spending image or voice tokens.

## Tests

```powershell
cd backend
.venv\Scripts\python.exe -m unittest discover -s tests
```

Frontend syntax check:

```powershell
node --check frontend/app.js
```

## Deployment

Build a release tarball:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\build_release_tar.ps1
```

The existing deploy script installs the FastAPI app under `/opt/novel2gal` and configures Nginx as a reverse proxy.

## Roadmap

- Persist projects, uploaded books, generated scripts, and branch choices
- Add real provider adapters for image generation and Chinese TTS
- Add asset-license attribution UI
- Add better long-running progress events through SSE/WebSocket
- Add human review tools for characters, relationships, and scene boundaries
- Add Ren'Py project packaging with downloaded assets and audio
