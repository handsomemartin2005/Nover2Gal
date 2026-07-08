# Novel2Gal Backend MVP Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic backend MVP vertical slice that can transform a small txt/md novel sample into analysis data, POV knowledge, Galgame scene IR, consistency reports, and Markdown/JSON/Ren'Py exports.

**Architecture:** Keep the first complete flow dependency-light and pure-Python so it is testable before Postgres, LlamaIndex, LangGraph, and FastAPI integration. The modules use dataclasses and dictionaries that can later map directly to ORM models and API schemas.

**Tech Stack:** Python 3.11, stdlib `unittest`, dataclasses, JSON, optional OpenAI-compatible DeepSeek HTTP client via `urllib`.

## Global Constraints

- Do not persist real API keys in repository files; use `LLM_API_KEY` from the environment.
- MVP input formats are `txt`, `md`, and pasted UTF-8 text.
- MVP route mode is `single_route` with light branching only.
- MVP exports are Markdown, JSON, and Ren'Py.
- GraphRAG is not implemented in this increment; leave future module boundaries.
- Use TDD: write failing tests before each production module.

---

## Tasks

### Task 1: Story Schemas and Heuristic Analyzer

**Files:**
- Create: `backend/app/schemas/story.py`
- Create: `backend/app/analysis/simple_analyzer.py`
- Test: `backend/tests/analysis/test_simple_analyzer.py`

**Interfaces:**
- Produces: `analyze_story(title: str, chapters: list[Chapter], scenes_by_chapter: dict[int, list[SourceScene]]) -> StoryAnalysis`
- Produces dataclasses for characters, events, clues, story bible, and analysis bundle.

### Task 2: POV Engine and Consistency Checker

**Files:**
- Create: `backend/app/pov/pov_engine.py`
- Create: `backend/app/consistency/checker.py`
- Test: `backend/tests/pov/test_pov_engine.py`
- Test: `backend/tests/consistency/test_checker.py`

**Interfaces:**
- Produces: `build_pov_knowledge(project_id: str, pov_character: str, events: list[StoryEvent], clues: list[Clue]) -> list[POVKnowledgeState]`
- Produces: `check_scene(scene: dict, pov_state: POVKnowledgeState) -> ConsistencyReport`

### Task 3: Galgame Scene Generator and Project Pipeline

**Files:**
- Create: `backend/app/adaptation/script_generator.py`
- Create: `backend/app/services/novel_pipeline.py`
- Test: `backend/tests/services/test_novel_pipeline.py`

**Interfaces:**
- Produces: `generate_scene_ir(source_scene: SourceScene, analysis: StoryAnalysis, pov_state: POVKnowledgeState, chapter_index: int) -> dict`
- Produces: `run_pipeline(title: str, text: str, pov_character: str) -> PipelineResult`

### Task 4: Markdown/JSON Exporters

**Files:**
- Create: `backend/app/exporters/markdown_exporter.py`
- Create: `backend/app/exporters/json_exporter.py`
- Test: `backend/tests/exporters/test_project_exporters.py`

**Interfaces:**
- Produces: `export_project_to_markdown(result: PipelineResult) -> str`
- Produces: `export_project_to_json(result: PipelineResult) -> str`

### Task 5: DeepSeek Client and CLI

**Files:**
- Create: `backend/app/llm/deepseek_client.py`
- Create: `backend/app/cli.py`
- Test: `backend/tests/llm/test_deepseek_client.py`
- Test: `backend/tests/test_cli.py`

**Interfaces:**
- Produces: `DeepSeekClient.build_chat_payload(messages: list[dict[str, str]], json_output: bool = False) -> dict`
- Produces command: `python -m app.cli input.txt --pov 林雨 --title 示例 --out exports/demo`

### Task 6: Verification

Run:

```powershell
C:\Users\A\AppData\Local\Programs\Python\Python311\python.exe -B -m unittest discover -s tests -v
```

Expected: all tests pass and no `__pycache__` remains when using `-B`.
