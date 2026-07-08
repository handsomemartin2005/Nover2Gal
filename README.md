# Novel2Gal

Novel2Gal is an MVP backend-first prototype for converting long-form novels into Galgame scripts from a selected core character's point of view.

The first increment focuses on deterministic parser/exporter foundations:

- chapter splitting
- coarse scene splitting
- RAG chunk preparation
- txt/md/epub document import
- Ren'Py scene export
- environment-based LLM configuration

Real API keys are not stored in this repository. Set `LLM_API_KEY` in your shell or local ignored `.env` file before calling any LLM provider.

## Run Tests

```powershell
cd backend
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

## Install Backend Dependencies

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Start The Workbench

```powershell
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open:

```text
http://127.0.0.1:8001/
```

## Run The CLI

```powershell
cd backend
.venv\Scripts\python.exe -m app.cli sample.txt --title 雨夜旧楼 --pov 林雨 --out exports/demo
```

EPUB input is supported:

```powershell
cd backend
.venv\Scripts\python.exe -m app.cli book.epub --pov 林雨 --out exports/book-demo
```

For EPUB files, `--title` is optional; the importer uses the EPUB metadata title when available.

## HTTP API

Text JSON input:

```http
POST /api/pipeline/run
```

EPUB/txt/md upload:

```http
POST /api/pipeline/upload
Content-Type: multipart/form-data

fields:
- file
- pov_character
- title optional
```

## DeepSeek Configuration

The default configuration is OpenAI-compatible and uses:

```text
LLM_PROVIDER=deepseek
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
EMBEDDING_MODEL=deepseek-v4-pro
```

Override values through environment variables when needed.
