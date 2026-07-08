# Novel2Gal Backend Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend-first Novel2Gal MVP skeleton for text parsing, basic Galgame IR export, and DeepSeek V4 environment configuration.

**Architecture:** The first increment is a small Python package under `backend/app` with pure functions for parser and exporter behavior. API, database, RAG, and LangGraph modules are scaffolded but not implemented until the parser/exporter baseline is tested.

**Tech Stack:** Python 3.11, stdlib `unittest`, FastAPI-ready package layout, environment-variable configuration, Markdown/JSON/Ren'Py export primitives.

## Global Constraints

- Do not persist real API keys in repository files; use `LLM_API_KEY` from the environment.
- MVP input formats are `txt`, `md`, and pasted UTF-8 text.
- MVP route mode is `single_route` with light branching only.
- MVP exports are Markdown, JSON, and Ren'Py.
- GraphRAG is not implemented in this increment; leave only future module boundaries.
- Use TDD: write failing tests before each production module.

---

## File Structure

- `backend/app/core/config.py`: loads runtime settings from environment variables, including DeepSeek-compatible defaults.
- `backend/app/parser/chapter_splitter.py`: splits plain text into ordered chapter objects.
- `backend/app/parser/scene_splitter.py`: splits a chapter into coarse source scenes using blank lines and transition cues.
- `backend/app/parser/chunker.py`: chunks scene text for future RAG ingestion while preserving overlap.
- `backend/app/exporters/renpy_exporter.py`: converts a minimal Galgame scene IR into Ren'Py script text.
- `backend/tests/...`: stdlib unit tests for every implemented module.
- `docs/Novel2Gal_MVP_Tech_Design.md`: copied project design baseline.
- `.env.example`: placeholder-only runtime configuration.

### Task 1: Runtime Configuration

**Files:**
- Create: `backend/tests/core/test_config.py`
- Create: `backend/app/core/config.py`
- Create: `.env.example`

**Interfaces:**
- Produces: `Settings.from_env(env: Mapping[str, str] | None = None) -> Settings`
- Produces: `Settings.llm_base_url: str`, `Settings.llm_model: str`, `Settings.embedding_model: str`, `Settings.embedding_dim: int`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from app.core.config import Settings


class SettingsTest(unittest.TestCase):
    def test_uses_deepseek_v4_defaults_without_persisting_secret(self):
        settings = Settings.from_env({})

        self.assertEqual(settings.llm_provider, "deepseek")
        self.assertEqual(settings.llm_base_url, "https://api.deepseek.com")
        self.assertEqual(settings.llm_model, "deepseek-v4-pro")
        self.assertEqual(settings.embedding_model, "deepseek-v4-pro")
        self.assertEqual(settings.embedding_dim, 1536)
        self.assertEqual(settings.llm_api_key, "")

    def test_environment_overrides_model_and_key(self):
        settings = Settings.from_env({
            "LLM_API_KEY": "secret-value",
            "LLM_MODEL": "deepseek-v4-flash",
            "EMBEDDING_DIM": "1024",
        })

        self.assertEqual(settings.llm_api_key, "secret-value")
        self.assertEqual(settings.llm_model, "deepseek-v4-flash")
        self.assertEqual(settings.embedding_dim, 1024)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend/tests/core/test_config.py -v`

Expected: FAIL or ERROR because `app.core.config` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Implement a small dataclass and `.env.example` placeholders only.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend/tests/core/test_config.py -v`

Expected: PASS.

### Task 2: Chapter Splitter

**Files:**
- Create: `backend/tests/parser/test_chapter_splitter.py`
- Create: `backend/app/parser/chapter_splitter.py`

**Interfaces:**
- Produces: `Chapter(index: int, title: str, text: str, start_offset: int, end_offset: int)`
- Produces: `split_chapters(text: str) -> list[Chapter]`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from app.parser.chapter_splitter import split_chapters


class ChapterSplitterTest(unittest.TestCase):
    def test_splits_chinese_chapter_headings(self):
        text = "序言\n不进章节。\n\n第一章 雨夜\n林雨推开门。\n\n第二章 清晨\n苏晚没有出现。"

        chapters = split_chapters(text)

        self.assertEqual([chapter.title for chapter in chapters], ["第一章 雨夜", "第二章 清晨"])
        self.assertEqual(chapters[0].index, 1)
        self.assertIn("林雨推开门。", chapters[0].text)
        self.assertNotIn("第二章", chapters[0].text)

    def test_falls_back_to_single_chapter_when_no_heading_exists(self):
        chapters = split_chapters("林雨推开旧教学楼的门。")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "Chapter 1")
        self.assertEqual(chapters[0].text, "林雨推开旧教学楼的门。")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend/tests/parser/test_chapter_splitter.py -v`

Expected: FAIL or ERROR because `split_chapters` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Use heading regexes for Chinese and English chapter titles; fallback to one pseudo chapter.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend/tests/parser/test_chapter_splitter.py -v`

Expected: PASS.

### Task 3: Scene Splitter

**Files:**
- Create: `backend/tests/parser/test_scene_splitter.py`
- Create: `backend/app/parser/scene_splitter.py`

**Interfaces:**
- Produces: `SourceScene(index: int, title: str, text: str, start_offset: int, end_offset: int)`
- Produces: `split_scenes(chapter_text: str, min_scene_chars: int = 80) -> list[SourceScene]`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from app.parser.scene_splitter import split_scenes


class SceneSplitterTest(unittest.TestCase):
    def test_splits_on_blank_line_transition_cues(self):
        text = (
            "林雨推开旧教学楼的门，雨水落在身后。\n"
            "苏晚站在讲台旁。\n\n"
            "第二天清晨，教室里只剩下粉笔灰。\n"
            "林雨想起昨晚那张纸。"
        )

        scenes = split_scenes(text, min_scene_chars=10)

        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[0].index, 1)
        self.assertIn("旧教学楼", scenes[0].text)
        self.assertIn("第二天清晨", scenes[1].text)

    def test_keeps_short_fragments_with_previous_scene(self):
        text = "林雨推门。\n\n雨声。\n\n苏晚沉默了很久。"

        scenes = split_scenes(text, min_scene_chars=20)

        self.assertEqual(len(scenes), 1)
        self.assertIn("雨声。", scenes[0].text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend/tests/parser/test_scene_splitter.py -v`

Expected: FAIL or ERROR because `split_scenes` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Split on blank lines and merge fragments shorter than `min_scene_chars`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend/tests/parser/test_scene_splitter.py -v`

Expected: PASS.

### Task 4: RAG Chunker

**Files:**
- Create: `backend/tests/parser/test_chunker.py`
- Create: `backend/app/parser/chunker.py`

**Interfaces:**
- Produces: `TextChunk(index: int, text: str, start_offset: int, end_offset: int)`
- Produces: `chunk_text(text: str, max_chars: int = 1500, overlap_chars: int = 200) -> list[TextChunk]`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from app.parser.chunker import chunk_text


class ChunkerTest(unittest.TestCase):
    def test_chunks_text_with_overlap(self):
        text = "一二三四五六七八九十"

        chunks = chunk_text(text, max_chars=4, overlap_chars=1)

        self.assertEqual([chunk.text for chunk in chunks], ["一二三四", "四五六七", "七八九十"])
        self.assertEqual(chunks[1].start_offset, 3)

    def test_rejects_overlap_not_smaller_than_max_chars(self):
        with self.assertRaises(ValueError):
            chunk_text("abc", max_chars=3, overlap_chars=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend/tests/parser/test_chunker.py -v`

Expected: FAIL or ERROR because `chunk_text` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Create sliding-window chunks with deterministic offsets.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend/tests/parser/test_chunker.py -v`

Expected: PASS.

### Task 5: Ren'Py Exporter

**Files:**
- Create: `backend/tests/exporters/test_renpy_exporter.py`
- Create: `backend/app/exporters/renpy_exporter.py`

**Interfaces:**
- Produces: `export_scene_to_renpy(scene: dict) -> str`

- [ ] **Step 1: Write the failing test**

```python
import unittest

from app.exporters.renpy_exporter import export_scene_to_renpy


class RenpyExporterTest(unittest.TestCase):
    def test_exports_dialogue_and_choice_blocks(self):
        scene = {
            "scene_id": "common_001_001",
            "background": "bg_old_school_night_rain",
            "bgm": "bgm_suspense_low",
            "blocks": [
                {"type": "narration", "text": "雨声还没有停。"},
                {"type": "dialogue", "speaker_key": "lin", "text": "你为什么在这里？"},
                {
                    "type": "choice",
                    "choices": [
                        {
                            "text": "继续追问她",
                            "effects": {"affection_suwan": -1, "flag_questioned_suwan": True},
                            "next_label": "common_001_001_ask",
                        }
                    ],
                },
            ],
        }

        script = export_scene_to_renpy(scene)

        self.assertIn("label common_001_001:", script)
        self.assertIn("scene bg_old_school_night_rain", script)
        self.assertIn('play music "bgm_suspense_low.ogg"', script)
        self.assertIn('narrator "雨声还没有停。"', script)
        self.assertIn('lin "你为什么在这里？"', script)
        self.assertIn('"继续追问她":', script)
        self.assertIn("$ affection_suwan -= 1", script)
        self.assertIn("$ flag_questioned_suwan = True", script)
        self.assertIn("jump common_001_001_ask", script)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend/tests/exporters/test_renpy_exporter.py -v`

Expected: FAIL or ERROR because `export_scene_to_renpy` is not implemented.

- [ ] **Step 3: Write minimal implementation**

Render label, scene, music, narration, dialogue, and menu blocks.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest backend/tests/exporters/test_renpy_exporter.py -v`

Expected: PASS.

### Task 6: Baseline Verification and Sync

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`
- Copy project files to `D:\PyCharmPojects\Novel2Gal`

**Interfaces:**
- Produces: a project skeleton that can run `python -m unittest discover -s backend/tests -v`

- [ ] **Step 1: Run all tests**

Run: `python -m unittest discover -s backend/tests -v`

Expected: all tests pass.

- [ ] **Step 2: Sync to target directory**

Copy the generated project tree from the writable workspace into `D:\PyCharmPojects\Novel2Gal`.

- [ ] **Step 3: Verify target tree**

Run: `python -m unittest discover -s backend/tests -v` from `D:\PyCharmPojects\Novel2Gal`.

Expected: all tests pass.
