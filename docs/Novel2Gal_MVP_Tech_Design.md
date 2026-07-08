# Novel2Gal MVP 技术设计文档

版本：v0.1  
日期：2026-07-08  
定位：长篇小说指定核心人物视角 Galgame 改编工具

---

## 1. 技术决策结论

Novel2Gal 的核心能力不是普通文本生成，也不是普通 RAG 问答，而是：

> 将长篇小说解析成剧情结构，在用户指定核心人物后，维护该人物在不同剧情时刻的已知、未知、怀疑信息，并逐场景生成 Galgame 剧本、选项、资源需求和可导出脚本。

因此第一版采用 **核心项目自研**，不直接改造现成仓库作为底座。

### 1.1 第一版技术栈

```text
后端框架：FastAPI
前端框架：React 或 Vue
数据库：PostgreSQL
向量扩展：pgvector
RAG 框架：LlamaIndex
AI 流程编排：LangGraph
导出目标：Markdown / JSON / Ren'Py
GraphRAG：MVP 暂不接入完整实现，只预留 story graph 数据结构
```

### 1.2 参考项目定位

```text
NovelClaw：参考长篇写作记忆、storyboard、memory bank、人物/世界观视图
show-me-the-story：参考大纲、伏笔、fact-check、全书优化流程
ai-galgame：参考 Galgame 前端交互、LLM 输出协议、好感度/选项设计
LightRAG：后期参考人物-事件-伏笔图谱
pgvector：MVP 向量存储
Ren'Py：MVP 游戏脚本导出目标
```

### 1.3 核心原则

```text
1. 先分析小说，再生成 Galgame 剧本。
2. 不把整本小说一次性塞进模型。
3. RAG 只负责取原文证据，不负责全部剧情理解。
4. 剧情理解要结构化保存：章节、场景、人物、事件、伏笔、视角知识。
5. 生成时必须绑定核心人物视角，禁止提前暴露该人物不知道的信息。
6. 每个 Galgame 场景生成后必须做一致性检查。
7. MVP 优先单线剧情，少量选项，多结局和复杂路线后置。
```

---

## 2. 产品范围

### 2.1 产品目标

Novel2Gal MVP 要实现：

```text
上传 txt/md 小说
→ 自动分章
→ 自动场景切分
→ 提取人物表
→ 提取事件时间线
→ 生成章节摘要和 story bible
→ 用户选择核心视角人物
→ 生成该人物视角知识状态表
→ 逐场景生成 Galgame 剧本
→ 执行一致性检查
→ 导出 Markdown / JSON / Ren'Py
```

### 2.2 MVP 必做功能

| 编号 | 功能 | 说明 |
|---|---|---|
| F01 | 小说上传 | 支持 txt/md，UTF-8 文本优先 |
| F02 | 分章 | 识别“第 N 章”“Chapter N”等章节标题 |
| F03 | 场景切分 | 根据地点、时间、人物变化切分章节 |
| F04 | 章节摘要 | 为每章生成短摘要、长摘要、关键事件 |
| F05 | 人物抽取 | 生成人物表、别名、性格、关系、语气 |
| F06 | 事件时间线 | 提取事件、参与者、地点、因果、可见角色 |
| F07 | 核心人物选择 | 用户指定 Galgame 玩家绑定视角 |
| F08 | 视角知识表 | 维护该人物在每个时间点的已知、未知、怀疑信息 |
| F09 | 剧本生成 | 逐场景生成 Galgame 风格剧本 |
| F10 | 选项生成 | 支持少量剧情选项、好感度变化、flag |
| F11 | 一致性检查 | 检查提前剧透、OOC、时间线错误、伏笔遗漏 |
| F12 | 导出 | Markdown、JSON、Ren'Py `.rpy` |

### 2.3 MVP 暂不做

```text
1. 不做完整 Galgame 游戏引擎。
2. 不做自动生成角色立绘、CG、BGM、语音。
3. 不做复杂多路线、多结局闭环系统。
4. 不做百万字小说一次性完整改编。
5. 不做版权授权判断。
6. 不做多人协作编辑。
7. 不接入完整 GraphRAG，只预留数据结构。
8. 不支持 PDF/DOCX/EPUB，后续再接 MarkItDown/Docling/Marker。
```

### 2.4 推荐 MVP 输入规模

```text
短篇：1 万字以内，可完整处理。
中篇：1–10 万字，MVP 主要目标。
长篇：10–50 万字，需要分卷/分批处理。
超长篇：50 万字以上，第一版不作为主要目标。
```

---

## 3. 总体架构

### 3.1 架构图

```text
┌──────────────────────────────────────────────────────────┐
│                        Frontend                           │
│  上传页 / 分析结果页 / 视角选择页 / 剧本编辑器 / 导出页       │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTP / SSE / WebSocket
┌────────────────────────────▼─────────────────────────────┐
│                       FastAPI Backend                      │
│  Auth / Novel API / Analysis API / Adaptation API / Export │
└────────────────────────────┬─────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐   ┌───────▼────────┐   ┌───────▼────────┐
│  Novel Parser   │   │ LangGraph Flow │   │ Ren'Py Exporter│
│  分章/场景/清洗  │   │ 多阶段 AI 编排  │   │ 脚本导出        │
└───────┬────────┘   └───────┬────────┘   └────────────────┘
        │                    │
┌───────▼────────────────────▼─────────────────────────────┐
│                     RAG / Memory Layer                     │
│  LlamaIndex / Prompt Builder / Retrieval Bundle Builder    │
└───────┬────────────────────┬─────────────────────────────┘
        │                    │
┌───────▼────────┐   ┌───────▼────────┐
│ PostgreSQL      │   │ pgvector        │
│ 结构化剧情数据   │   │ chunk embedding │
└────────────────┘   └────────────────┘
        │
┌───────▼──────────────────────────────────────────────────┐
│                         LLM Provider                       │
│  OpenAI-compatible API / local model / embedding model      │
└──────────────────────────────────────────────────────────┘
```

### 3.2 核心模块

| 模块 | 职责 |
|---|---|
| Novel Parser | 文本清洗、章节识别、场景切分、段落切分 |
| Analysis Pipeline | 摘要、人物、事件、伏笔、story bible 提取 |
| RAG Indexer | chunk embedding、metadata 写入、检索索引构建 |
| POV Engine | 生成和维护核心人物视角知识状态 |
| Adaptation Planner | 将原小说场景规划为 Galgame 场景 |
| Script Generator | 生成 Galgame 剧本、选项、演出提示 |
| Consistency Checker | 检查视角泄露、时间线冲突、人物 OOC、伏笔遗漏 |
| Exporter | 导出 Markdown、JSON、Ren'Py |
| Frontend Editor | 展示分析结果，支持人工修改和确认 |

---

## 4. 推荐目录结构

```text
Novel2Gal/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ novels.py
│  │  │  ├─ analysis.py
│  │  │  ├─ adaptations.py
│  │  │  ├─ exports.py
│  │  │  └─ tasks.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  ├─ logging.py
│  │  │  └─ errors.py
│  │  ├─ db/
│  │  │  ├─ session.py
│  │  │  ├─ models.py
│  │  │  └─ migrations/
│  │  ├─ schemas/
│  │  │  ├─ novel.py
│  │  │  ├─ story.py
│  │  │  ├─ pov.py
│  │  │  ├─ adaptation.py
│  │  │  └─ export.py
│  │  ├─ services/
│  │  │  ├─ novel_service.py
│  │  │  ├─ analysis_service.py
│  │  │  ├─ adaptation_service.py
│  │  │  └─ export_service.py
│  │  ├─ parser/
│  │  │  ├─ text_cleaner.py
│  │  │  ├─ chapter_splitter.py
│  │  │  ├─ scene_splitter.py
│  │  │  └─ chunker.py
│  │  ├─ rag/
│  │  │  ├─ indexer.py
│  │  │  ├─ retriever.py
│  │  │  ├─ context_builder.py
│  │  │  └─ reranker.py
│  │  ├─ pipelines/
│  │  │  ├─ ingest_graph.py
│  │  │  ├─ analysis_graph.py
│  │  │  ├─ pov_graph.py
│  │  │  └─ adaptation_graph.py
│  │  ├─ prompts/
│  │  │  ├─ extract_characters.md
│  │  │  ├─ extract_events.md
│  │  │  ├─ build_pov_knowledge.md
│  │  │  ├─ generate_vn_scene.md
│  │  │  └─ check_consistency.md
│  │  ├─ exporters/
│  │  │  ├─ markdown_exporter.py
│  │  │  ├─ json_exporter.py
│  │  │  └─ renpy_exporter.py
│  │  └─ tests/
│  ├─ pyproject.toml
│  └─ README.md
├─ frontend/
│  ├─ src/
│  │  ├─ pages/
│  │  ├─ components/
│  │  ├─ api/
│  │  ├─ stores/
│  │  └─ types/
│  └─ package.json
├─ docs/
│  ├─ Novel2Gal_MVP_Tech_Design.md
│  ├─ API.md
│  ├─ Database.md
│  └─ Prompt_Spec.md
├─ scripts/
│  ├─ init_db.sql
│  └─ dev_start.sh
└─ README.md
```

---

## 5. 数据库设计

### 5.1 核心实体关系

```text
novels
  └─ chapters
       └─ source_scenes
            └─ source_chunks

novels
  ├─ characters
  ├─ story_events
  ├─ clues
  ├─ story_bibles
  └─ adaptation_projects
          └─ adaptation_scenes
                 ├─ choices
                 ├─ required_assets
                 └─ consistency_reports

adaptation_projects
  └─ pov_knowledge_states
```

### 5.2 novels

保存小说原始信息。

```sql
CREATE TABLE novels (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    source_type TEXT NOT NULL DEFAULT 'txt',
    raw_text TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'zh-CN',
    status TEXT NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

状态建议：

```text
uploaded
parsed
analyzed
adaptation_ready
failed
```

### 5.3 chapters

```sql
CREATE TABLE chapters (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_index INT NOT NULL,
    title TEXT,
    raw_text TEXT NOT NULL,
    start_offset INT,
    end_offset INT,
    summary_short TEXT,
    summary_long TEXT,
    key_events JSONB DEFAULT '[]',
    characters JSONB DEFAULT '[]',
    locations JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(novel_id, chapter_index)
);
```

### 5.4 source_scenes

原小说场景。一个章节可以被切成多个场景。

```sql
CREATE TABLE source_scenes (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    scene_index INT NOT NULL,
    title TEXT,
    raw_text TEXT NOT NULL,
    summary TEXT,
    time_label TEXT,
    location TEXT,
    characters JSONB DEFAULT '[]',
    emotional_tone TEXT,
    narrative_pov TEXT,
    start_offset INT,
    end_offset INT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(chapter_id, scene_index)
);
```

### 5.5 source_chunks

用于 RAG 的最小文本检索单位。

```sql
CREATE TABLE source_chunks (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
    scene_id UUID REFERENCES source_scenes(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    token_count INT,
    characters JSONB DEFAULT '[]',
    locations JSONB DEFAULT '[]',
    time_label TEXT,
    metadata JSONB DEFAULT '{}',
    embedding VECTOR(1536),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_source_chunks_novel ON source_chunks(novel_id);
CREATE INDEX idx_source_chunks_chapter ON source_chunks(chapter_id);
CREATE INDEX idx_source_chunks_scene ON source_chunks(scene_id);
CREATE INDEX idx_source_chunks_embedding ON source_chunks USING ivfflat (embedding vector_cosine_ops);
```

`VECTOR(1536)` 需要根据实际 embedding 模型维度调整。

### 5.6 characters

```sql
CREATE TABLE characters (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    aliases JSONB DEFAULT '[]',
    role TEXT,
    first_appearance_scene_id UUID,
    personality TEXT,
    speech_style TEXT,
    relationship_map JSONB DEFAULT '{}',
    secrets JSONB DEFAULT '[]',
    visual_notes JSONB DEFAULT '{}',
    do_not_do JSONB DEFAULT '[]',
    source_evidence JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(novel_id, name)
);
```

### 5.7 story_events

```sql
CREATE TABLE story_events (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    chapter_id UUID REFERENCES chapters(id) ON DELETE SET NULL,
    scene_id UUID REFERENCES source_scenes(id) ON DELETE SET NULL,
    time_order INT NOT NULL,
    event_text TEXT NOT NULL,
    participants JSONB DEFAULT '[]',
    location TEXT,
    cause TEXT,
    effect TEXT,
    visible_to JSONB DEFAULT '[]',
    hidden_from JSONB DEFAULT '[]',
    related_clues JSONB DEFAULT '[]',
    importance INT NOT NULL DEFAULT 3,
    source_evidence JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(novel_id, time_order)
);
```

`importance` 取值建议：

```text
1：背景补充
2：普通事件
3：重要剧情事件
4：关键转折
5：主线核心事件
```

### 5.8 clues

伏笔、线索、道具、秘密。

```sql
CREATE TABLE clues (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    clue_name TEXT NOT NULL,
    clue_type TEXT NOT NULL,
    first_appears_scene_id UUID,
    reveal_scene_id UUID,
    hidden_meaning TEXT,
    surface_form TEXT,
    related_characters JSONB DEFAULT '[]',
    related_events JSONB DEFAULT '[]',
    must_keep BOOLEAN NOT NULL DEFAULT FALSE,
    reveal_policy TEXT NOT NULL DEFAULT 'do_not_reveal_before_reveal_scene',
    source_evidence JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

`clue_type` 示例：

```text
item
secret
relationship
past_event
location
symbol
line_of_dialogue
```

### 5.9 story_bibles

整部小说的结构化总设定。

```sql
CREATE TABLE story_bibles (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    world_setting TEXT,
    main_plot TEXT,
    core_conflict TEXT,
    themes JSONB DEFAULT '[]',
    major_characters JSONB DEFAULT '[]',
    timeline_summary TEXT,
    ending_summary TEXT,
    style_notes TEXT,
    forbidden_changes JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.10 adaptation_projects

一次改编任务。一个小说可以创建多个改编项目，例如不同核心人物视角。

```sql
CREATE TABLE adaptation_projects (
    id UUID PRIMARY KEY,
    novel_id UUID NOT NULL REFERENCES novels(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    pov_character_id UUID NOT NULL REFERENCES characters(id),
    adaptation_level TEXT NOT NULL DEFAULT 'faithful',
    route_mode TEXT NOT NULL DEFAULT 'single_route',
    output_target TEXT NOT NULL DEFAULT 'renpy',
    status TEXT NOT NULL DEFAULT 'created',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

`adaptation_level`：

```text
strict：极度忠实，尽量不新增内容
faithful：保留原作主线，允许补充演出和对话
expanded：允许增加少量支线和选项
rewrite：允许重构路线，MVP 暂不启用
```

### 5.11 pov_knowledge_states

核心人物在某个剧情时间点的知识状态。

```sql
CREATE TABLE pov_knowledge_states (
    id UUID PRIMARY KEY,
    adaptation_project_id UUID NOT NULL REFERENCES adaptation_projects(id) ON DELETE CASCADE,
    after_event_order INT NOT NULL,
    known_facts JSONB DEFAULT '[]',
    unknown_facts JSONB DEFAULT '[]',
    suspected_facts JSONB DEFAULT '[]',
    false_beliefs JSONB DEFAULT '[]',
    forbidden_reveals JSONB DEFAULT '[]',
    source_evidence JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(adaptation_project_id, after_event_order)
);
```

### 5.12 adaptation_scenes

Galgame 改编后的场景。

```sql
CREATE TABLE adaptation_scenes (
    id UUID PRIMARY KEY,
    adaptation_project_id UUID NOT NULL REFERENCES adaptation_projects(id) ON DELETE CASCADE,
    scene_index INT NOT NULL,
    route_id TEXT NOT NULL DEFAULT 'common',
    source_scene_ids JSONB DEFAULT '[]',
    title TEXT,
    location TEXT,
    time_label TEXT,
    bg_asset_key TEXT,
    bgm_asset_key TEXT,
    script_text TEXT,
    script_ir JSONB DEFAULT '{}',
    summary TEXT,
    state_before JSONB DEFAULT '{}',
    state_after JSONB DEFAULT '{}',
    required_assets JSONB DEFAULT '[]',
    generation_status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(adaptation_project_id, scene_index)
);
```

### 5.13 choices

```sql
CREATE TABLE choices (
    id UUID PRIMARY KEY,
    adaptation_scene_id UUID NOT NULL REFERENCES adaptation_scenes(id) ON DELETE CASCADE,
    choice_index INT NOT NULL,
    choice_text TEXT NOT NULL,
    effect JSONB DEFAULT '{}',
    next_scene_id UUID,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### 5.14 consistency_reports

```sql
CREATE TABLE consistency_reports (
    id UUID PRIMARY KEY,
    adaptation_scene_id UUID NOT NULL REFERENCES adaptation_scenes(id) ON DELETE CASCADE,
    pass BOOLEAN NOT NULL,
    score NUMERIC(4, 2),
    issues JSONB DEFAULT '[]',
    checked_by TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

---

## 6. 核心数据结构

### 6.1 SourceScene

```json
{
  "scene_id": "ch012_sc003",
  "chapter_index": 12,
  "scene_index": 3,
  "title": "雨夜的旧教学楼",
  "time_label": "深夜",
  "location": "旧教学楼三楼",
  "characters": ["林雨", "苏晚"],
  "raw_text": "...",
  "summary": "林雨在旧教学楼遇见苏晚，并发现她似乎在寻找旧案资料。",
  "emotional_tone": "紧张、怀疑",
  "narrative_pov": "第三人称限视角"
}
```

### 6.2 CharacterCard

```json
{
  "character_id": "suwan",
  "name": "苏晚",
  "aliases": ["晚晚"],
  "role": "主要角色",
  "personality": "外冷内热，防备心强，不轻易表达信任。",
  "speech_style": "短句偏多，常回避直接情绪表达。",
  "relationship_to_pov": {
    "early": "疏远、互相试探",
    "middle": "逐渐信任",
    "late": "情感依赖"
  },
  "secrets": [
    "知道七年前旧案与姐姐有关"
  ],
  "do_not_do": [
    "前期不能主动透露姐姐的秘密",
    "不能突然表现得过度热情"
  ],
  "visual_notes": {
    "expressions": ["normal", "cold", "smile", "angry", "sad", "cry"]
  }
}
```

### 6.3 StoryEvent

```json
{
  "event_id": "E034",
  "time_order": 34,
  "chapter_index": 12,
  "scene_id": "ch012_sc003",
  "event_text": "林雨在旧教学楼发现苏晚正在寻找旧案资料。",
  "participants": ["林雨", "苏晚"],
  "location": "旧教学楼",
  "cause": "林雨怀疑苏晚隐瞒真相。",
  "effect": "林雨开始调查七年前旧案。",
  "visible_to": ["林雨", "苏晚"],
  "hidden_from": ["陈默"],
  "related_clues": ["C018"],
  "importance": 4
}
```

### 6.4 POVKnowledgeState

```json
{
  "pov_character": "林雨",
  "after_event_order": 34,
  "known_facts": [
    "苏晚深夜出现在旧教学楼。",
    "苏晚似乎正在寻找某份资料。"
  ],
  "unknown_facts": [
    "苏晚的姐姐和七年前旧案有关。",
    "陈默手里有关键录音。"
  ],
  "suspected_facts": [
    "苏晚可能知道旧案真相。"
  ],
  "false_beliefs": [],
  "forbidden_reveals": [
    "不得直接写出苏晚姐姐与旧案的关系。",
    "不得让林雨知道录音笔内容。"
  ]
}
```

### 6.5 AdaptationScene IR

内部中间表示，先不要直接生成 Ren'Py。先生成结构化 IR，再导出不同格式。

```json
{
  "scene_id": "vg_common_012_003",
  "route_id": "common",
  "source_scene_ids": ["ch012_sc003"],
  "title": "雨夜的旧教学楼",
  "background": "bg_old_school_night_rain",
  "bgm": "bgm_suspense_low",
  "sfx": ["sfx_rain_loop"],
  "characters": [
    {
      "name": "苏晚",
      "sprite": "suwan_cold"
    }
  ],
  "blocks": [
    {
      "type": "narration",
      "speaker": "林雨",
      "text": "雨声从破损的窗缝里挤进来，旧教学楼像被整个夜晚吞没。"
    },
    {
      "type": "dialogue",
      "speaker": "林雨",
      "text": "你为什么会在这里？"
    },
    {
      "type": "dialogue",
      "speaker": "苏晚",
      "expression": "cold",
      "text": "这句话应该我问你。"
    },
    {
      "type": "choice",
      "choices": [
        {
          "text": "继续追问她",
          "effects": {
            "suwan_affection": -1,
            "clue_old_school": true
          },
          "next_label": "common_012_003_ask"
        },
        {
          "text": "暂时相信她",
          "effects": {
            "suwan_affection": 1
          },
          "next_label": "common_012_003_trust"
        }
      ]
    }
  ],
  "required_assets": [
    {
      "type": "background",
      "key": "bg_old_school_night_rain",
      "description": "雨夜旧教学楼三楼走廊或教室背景"
    },
    {
      "type": "sprite",
      "key": "suwan_cold",
      "description": "苏晚冷淡表情立绘"
    }
  ]
}
```

---

## 7. AI 流程设计

### 7.1 总流程

```text
用户上传小说
  ↓
parse_novel
  ↓
split_chapters
  ↓
split_scenes
  ↓
build_chunks
  ↓
index_chunks
  ↓
analyze_chapters
  ↓
extract_characters
  ↓
extract_events
  ↓
extract_clues
  ↓
build_story_bible
  ↓
用户选择核心人物
  ↓
build_pov_knowledge
  ↓
plan_adaptation_scenes
  ↓
逐场景 generate_vn_scene
  ↓
check_consistency
  ↓
必要时 revise_scene
  ↓
export_markdown / export_json / export_renpy
```

### 7.2 LangGraph 状态设计

```python
from typing import TypedDict, List, Dict, Any, Optional

class NovelPipelineState(TypedDict):
    novel_id: str
    raw_text: str
    chapters: List[Dict[str, Any]]
    source_scenes: List[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    characters: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    clues: List[Dict[str, Any]]
    story_bible: Optional[Dict[str, Any]]
    errors: List[str]

class AdaptationPipelineState(TypedDict):
    novel_id: str
    adaptation_project_id: str
    pov_character_id: str
    story_bible: Dict[str, Any]
    pov_knowledge_states: List[Dict[str, Any]]
    source_scene_plan: List[Dict[str, Any]]
    generated_scenes: List[Dict[str, Any]]
    consistency_reports: List[Dict[str, Any]]
    export_paths: Dict[str, str]
    errors: List[str]
```

### 7.3 分析流程节点

```text
Node: parse_text
输入：raw_text
输出：clean_text

Node: split_chapters
输入：clean_text
输出：chapters

Node: split_scenes
输入：chapters
输出：source_scenes

Node: chunk_scenes
输入：source_scenes
输出：source_chunks

Node: embed_chunks
输入：source_chunks
输出：embedding 写入 pgvector

Node: summarize_chapters
输入：chapters + source_scenes
输出：chapter summaries

Node: extract_characters
输入：source_scenes + chapter summaries
输出：characters

Node: extract_events
输入：source_scenes + chapter summaries
输出：story_events

Node: extract_clues
输入：source_scenes + events + characters
输出：clues

Node: build_story_bible
输入：chapter summaries + characters + events + clues
输出：story_bible
```

### 7.4 改编流程节点

```text
Node: build_pov_knowledge
输入：pov_character + events + clues + story_bible
输出：pov_knowledge_states

Node: plan_adaptation_scenes
输入：source_scenes + events + story_bible + pov_character
输出：adaptation_scene_plan

Node: build_generation_context
输入：当前 source_scene + RAG 检索 + POV state + character cards
输出：generation_context

Node: generate_vn_scene
输入：generation_context
输出：AdaptationScene IR

Node: check_consistency
输入：AdaptationScene IR + source evidence + POV state
输出：ConsistencyReport

Node: revise_scene
输入：ConsistencyReport + previous AdaptationScene IR
输出：修订后的 AdaptationScene IR

Node: export
输入：全部 AdaptationScene IR
输出：Markdown / JSON / Ren'Py
```

---

## 8. RAG 设计

### 8.1 RAG 的职责边界

RAG 在 Novel2Gal 中只承担三件事：

```text
1. 找到与当前生成任务相关的原文证据。
2. 找到相关人物、事件、伏笔、前后场景。
3. 为生成和一致性检查提供可追溯上下文。
```

RAG 不负责：

```text
1. 直接决定剧情改编结构。
2. 单独维护人物视角知识。
3. 单独判断分支逻辑是否闭合。
4. 单独生成完整 Galgame。
```

这些必须由结构化剧情库和流程编排共同完成。

### 8.2 chunk 策略

MVP 建议：

```text
chunk 单位：场景内段落组
chunk 大小：800–1500 中文字
overlap：100–200 中文字
边界：优先按段落切，不在句中硬切
metadata：novel_id / chapter_id / scene_id / characters / location / time_label
```

### 8.3 检索类型

MVP：

```text
1. metadata 精确过滤
2. pgvector 向量检索
3. 简单全文搜索，可用 PostgreSQL tsvector 或 ILIKE 兜底
```

后续增强：

```text
1. BM25
2. reranker
3. LightRAG / story graph
4. Neo4j
```

### 8.4 生成单个 Galgame 场景的上下文包

生成一个场景时，不直接用用户 query 检索，而是由系统根据任务构造 context bundle。

```json
{
  "task": {
    "type": "generate_vn_scene",
    "source_scene_id": "ch012_sc003",
    "route_id": "common",
    "pov_character": "林雨"
  },
  "global_story_bible": "...",
  "current_chapter_summary": "...",
  "current_source_scene": "...",
  "neighbor_scene_summaries": ["...", "..."],
  "retrieved_source_chunks": ["...", "..."],
  "character_cards": ["...", "..."],
  "nearby_events": ["...", "..."],
  "related_clues": ["..."],
  "pov_knowledge_state": {
    "known_facts": [],
    "unknown_facts": [],
    "suspected_facts": [],
    "forbidden_reveals": []
  },
  "previous_adapted_summary": "...",
  "output_format_spec": "AdaptationScene IR JSON"
}
```

### 8.5 上下文预算建议

```text
固定规则：10%
Story Bible 精简版：10–15%
当前章节摘要：5–10%
当前原文场景：25–30%
前后相邻场景摘要：5–10%
检索到的相关原文片段：10–15%
人物卡：10%
视角知识状态：10%
输出格式约束：5%
```

优先级最高的是：

```text
当前原文场景
当前 POV 已知/未知/禁止信息
出场人物卡
前文 Galgame 摘要
```

---

## 9. Prompt 规格

### 9.1 人物提取 Prompt 输出格式

输入：若干场景原文 + 章节摘要  
输出：结构化人物候选列表。

```json
{
  "characters": [
    {
      "name": "林雨",
      "aliases": [],
      "role": "主角候选",
      "personality": "...",
      "speech_style": "...",
      "relationships": [
        {
          "target": "苏晚",
          "relation": "同学 / 怀疑对象",
          "stage": "early"
        }
      ],
      "evidence": [
        {
          "scene_id": "ch001_sc001",
          "quote_or_summary": "..."
        }
      ]
    }
  ]
}
```

### 9.2 事件提取 Prompt 输出格式

```json
{
  "events": [
    {
      "event_text": "林雨在旧教学楼遇见苏晚。",
      "participants": ["林雨", "苏晚"],
      "location": "旧教学楼",
      "cause": "...",
      "effect": "...",
      "visible_to": ["林雨", "苏晚"],
      "hidden_from": [],
      "importance": 4,
      "source_scene_id": "ch012_sc003"
    }
  ]
}
```

### 9.3 视角知识 Prompt 约束

关键规则：

```text
1. 只记录核心人物在该时间点已经知道的信息。
2. 对核心人物不知道但原文读者知道的信息，必须写入 unknown_facts 或 forbidden_reveals。
3. 如果核心人物只能推测，写入 suspected_facts，不得写入 known_facts。
4. 如果核心人物产生误解，写入 false_beliefs。
5. 每个状态必须对应 after_event_order。
```

输出：

```json
{
  "after_event_order": 34,
  "known_facts": [],
  "unknown_facts": [],
  "suspected_facts": [],
  "false_beliefs": [],
  "forbidden_reveals": []
}
```

### 9.4 Galgame 场景生成 Prompt 约束

```text
你要将原小说场景改编为 Galgame 剧本。

硬性规则：
1. 玩家视角绑定为指定核心人物。
2. 玩家只能知道该人物亲历、听到、看到、阅读到或合理推测的信息。
3. 不得直接写出 forbidden_reveals 中的信息。
4. 其他角色的心理活动必须转成外部表现，如表情、动作、语气、停顿。
5. 不要改变主线关键事件，除非 adaptation_level 允许。
6. 输出必须是合法 JSON，符合 AdaptationScene IR。
7. 对每个选项写清楚 effects。
8. 资源需求只写描述和 key，不生成图片或音频。
```

### 9.5 一致性检查 Prompt 输出格式

```json
{
  "pass": false,
  "score": 72.5,
  "issues": [
    {
      "type": "premature_reveal",
      "severity": "high",
      "location": "block[7]",
      "problem": "林雨直接说出了苏晚姐姐与旧案有关，但该信息在当前时间点属于 forbidden_reveals。",
      "suggestion": "改成林雨只注意到苏晚对旧案表现出异常紧张。"
    }
  ],
  "revision_required": true
}
```

问题类型：

```text
premature_reveal：提前剧透
pov_violation：视角违规
time_order_error：时间线错误
ooc：人物 OOC
clue_missing：伏笔遗漏
clue_overexposed：伏笔暴露过度
branch_conflict：选项/flag 冲突
format_error：输出格式错误
asset_missing：资源需求缺失
```

---

## 10. Galgame 改编状态设计

### 10.1 状态变量类型

MVP 支持以下变量：

```text
affection：好感度
flag：剧情布尔标记
clue：线索是否获得
route：当前路线
trust：信任度，可选
```

### 10.2 变量命名规范

```text
角色好感度：affection_{character_key}
角色信任度：trust_{character_key}
线索：clue_{clue_key}
剧情 flag：flag_{short_event_key}
路线：route_id
```

示例：

```text
affection_suwan
trust_suwan
clue_black_recorder
flag_entered_old_school
route_common
```

### 10.3 选项效果格式

```json
{
  "choice_text": "继续追问苏晚",
  "effects": {
    "affection_suwan": -1,
    "clue_old_school": true,
    "flag_questioned_suwan": true
  },
  "next_label": "common_012_003_ask"
}
```

### 10.4 MVP 分支策略

第一版不做复杂树状分支，采用“轻分支”策略：

```text
1. 选项可以改变好感度或 flag。
2. 大多数选项短暂分歧后回到主线。
3. 关键选项只影响后续对白、线索获得或结局条件。
4. 暂不自动生成大量独立路线。
```

这样可以避免分支爆炸。

---

## 11. 一致性检查设计

### 11.1 检查输入

```text
1. 当前 AdaptationScene IR
2. 当前 source scene 原文
3. 当前章节摘要
4. 当前 POV knowledge state
5. 出场人物卡
6. 相关事件时间线
7. 相关伏笔/线索
8. 前文 Galgame 摘要
```

### 11.2 检查规则

| 类型 | 检查内容 |
|---|---|
| 视角 | 主角是否知道了不该知道的信息 |
| 剧透 | 是否提前揭露 forbidden_reveals |
| 时间线 | 是否引用未来才发生的事件 |
| 人物 | 说话风格、行为是否 OOC |
| 伏笔 | 必须保留的伏笔是否遗漏或解释过度 |
| 分支 | 选项 effects 是否冲突、变量名是否规范 |
| 格式 | IR JSON 是否合法，字段是否完整 |
| 资源 | 是否输出必要背景、立绘、BGM、音效需求 |

### 11.3 修订策略

MVP 可以采用单轮修订：

```text
生成场景
→ 一致性检查
→ 如果 high severity issue 存在，执行一次 revise
→ 再检查一次
→ 如果仍失败，标记为 need_human_review
```

不建议无限自动修订，容易成本失控。

---

## 12. Ren'Py 导出设计

### 12.1 IR 到 Ren'Py 的映射

| IR 字段 | Ren'Py 输出 |
|---|---|
| scene_id | label |
| background | scene bg_xxx |
| bgm | play music "xxx.ogg" |
| sfx | play sound "xxx.ogg" |
| character sprite | show character expression |
| narration | narrator text |
| dialogue | character "text" |
| choice | menu |
| effects | Python 变量赋值 |
| next_label | jump label |

### 12.2 角色定义

导出时生成 `characters.rpy`：

```renpy
define narrator = Character(None)
define lin = Character("林雨")
define suwan = Character("苏晚")
define chenmo = Character("陈默")
```

### 12.3 变量定义

生成 `variables.rpy`：

```renpy
default affection_suwan = 0
default trust_suwan = 0
default clue_old_school = False
default flag_questioned_suwan = False
```

### 12.4 场景脚本示例

```renpy
label common_012_003:

    scene bg_old_school_night_rain
    play music "bgm_suspense_low.ogg" fadein 1.0
    play sound "sfx_rain_loop.ogg"

    show suwan cold at center

    narrator "雨声从破损的窗缝里挤进来，旧教学楼像被整个夜晚吞没。"

    lin "你为什么会在这里？"

    suwan "这句话应该我问你。"

    narrator "她的声音很平静，可手指却紧紧攥着书包带。"

    menu:
        "继续追问她":
            $ affection_suwan -= 1
            $ clue_old_school = True
            $ flag_questioned_suwan = True
            jump common_012_003_ask

        "暂时相信她":
            $ affection_suwan += 1
            jump common_012_003_trust
```

### 12.5 文件输出结构

```text
renpy_export/
├─ game/
│  ├─ script.rpy
│  ├─ characters.rpy
│  ├─ variables.rpy
│  ├─ assets_manifest.json
│  ├─ images/
│  │  └─ placeholder.txt
│  ├─ audio/
│  │  └─ placeholder.txt
│  └─ README_export.md
```

### 12.6 资源清单

生成 `assets_manifest.json`：

```json
{
  "backgrounds": [
    {
      "key": "bg_old_school_night_rain",
      "description": "雨夜旧教学楼三楼教室或走廊背景",
      "used_in": ["common_012_003"]
    }
  ],
  "sprites": [
    {
      "key": "suwan_cold",
      "character": "苏晚",
      "expression": "cold",
      "description": "苏晚冷淡或警惕表情立绘"
    }
  ],
  "bgm": [
    {
      "key": "bgm_suspense_low",
      "description": "低沉悬疑氛围音乐"
    }
  ],
  "sfx": [
    {
      "key": "sfx_rain_loop",
      "description": "持续雨声"
    }
  ]
}
```

---

## 13. API 设计

### 13.1 小说上传

```http
POST /api/novels/upload
Content-Type: multipart/form-data
```

响应：

```json
{
  "novel_id": "uuid",
  "title": "示例小说",
  "status": "uploaded"
}
```

### 13.2 启动解析

```http
POST /api/novels/{novel_id}/parse
```

响应：

```json
{
  "task_id": "uuid",
  "status": "queued"
}
```

### 13.3 获取章节列表

```http
GET /api/novels/{novel_id}/chapters
```

响应：

```json
{
  "chapters": [
    {
      "chapter_id": "uuid",
      "chapter_index": 1,
      "title": "第一章 雨夜",
      "summary_short": "...",
      "scene_count": 5
    }
  ]
}
```

### 13.4 启动小说分析

```http
POST /api/novels/{novel_id}/analysis/run
```

响应：

```json
{
  "task_id": "uuid",
  "stages": [
    "summarize_chapters",
    "extract_characters",
    "extract_events",
    "extract_clues",
    "build_story_bible"
  ]
}
```

### 13.5 获取人物表

```http
GET /api/novels/{novel_id}/characters
```

响应：

```json
{
  "characters": [
    {
      "character_id": "uuid",
      "name": "林雨",
      "role": "主角候选",
      "personality": "..."
    }
  ]
}
```

### 13.6 创建改编项目

```http
POST /api/adaptations
Content-Type: application/json
```

请求：

```json
{
  "novel_id": "uuid",
  "name": "林雨视角改编",
  "pov_character_id": "uuid",
  "adaptation_level": "faithful",
  "route_mode": "single_route",
  "output_target": "renpy"
}
```

响应：

```json
{
  "adaptation_project_id": "uuid",
  "status": "created"
}
```

### 13.7 生成视角知识表

```http
POST /api/adaptations/{project_id}/pov-knowledge/build
```

响应：

```json
{
  "task_id": "uuid",
  "status": "queued"
}
```

### 13.8 生成单个 Galgame 场景

```http
POST /api/adaptations/{project_id}/scenes/generate
Content-Type: application/json
```

请求：

```json
{
  "source_scene_id": "uuid",
  "route_id": "common",
  "with_consistency_check": true
}
```

响应：

```json
{
  "adaptation_scene_id": "uuid",
  "generation_status": "draft",
  "consistency_pass": true
}
```

### 13.9 导出

```http
POST /api/adaptations/{project_id}/export
Content-Type: application/json
```

请求：

```json
{
  "formats": ["markdown", "json", "renpy"]
}
```

响应：

```json
{
  "exports": [
    {
      "format": "renpy",
      "download_url": "/api/exports/uuid/download"
    }
  ]
}
```

---

## 14. 前端设计

### 14.1 页面列表

```text
1. NovelUploadPage：上传小说
2. NovelAnalysisPage：查看分章、场景、摘要、人物、事件
3. POVSelectionPage：选择核心人物和改编策略
4. AdaptationPlannerPage：查看原场景到 Galgame 场景的映射
5. ScriptEditorPage：编辑生成剧本、选项、资源需求
6. ConsistencyPanel：查看一致性检查结果
7. ExportPage：导出 Markdown / JSON / Ren'Py
```

### 14.2 剧本编辑器布局

```text
┌──────────────────────────────────────────────────────────┐
│ 顶部：项目名 / POV 人物 / 当前章节 / 导出按钮              │
├───────────────┬────────────────────────┬─────────────────┤
│ 左侧场景列表   │ 中间 Galgame 剧本编辑器 │ 右侧上下文面板    │
│               │                        │                 │
│ 原章节         │ 旁白/对白/选项          │ 人物卡           │
│ 原场景         │ 资源需求               │ POV 已知/未知     │
│ 生成状态       │ 一致性问题高亮          │ 原文证据          │
└───────────────┴────────────────────────┴─────────────────┘
```

### 14.3 人工确认点

MVP 至少需要以下人工确认：

```text
1. 章节切分结果确认。
2. 人物表确认和合并别名。
3. 核心人物选择。
4. Galgame 场景规划确认。
5. high severity 一致性问题人工处理。
```

---

## 15. 关键算法和规则

### 15.1 分章规则

正则候选：

```regex
^第[一二三四五六七八九十百千万0-9]+[章节卷回].*$
^Chapter\s+\d+.*$
^CHAPTER\s+\d+.*$
^\d+[\.、]\s*.+$
```

策略：

```text
1. 优先识别中文“第 N 章”。
2. 如果章节过少或过多，回退到标题行启发式。
3. 如果完全无法识别，按字数粗切为伪章节。
```

### 15.2 场景切分启发式

场景边界信号：

```text
1. 时间变化：第二天、当天晚上、三年前、与此同时。
2. 地点变化：回到教室、来到医院、走进旧楼。
3. 人物组合变化：某角色离场/登场。
4. 叙事视角变化。
5. 空行、分隔符、章节内小标题。
```

MVP 可以先用规则粗切，再用 LLM 做校正。

### 15.3 角色别名合并

规则：

```text
1. 同名直接合并。
2. 全名和称呼根据上下文合并，例如“苏晚”“晚晚”。
3. 身份称呼不直接合并，例如“老师”“医生”，需要证据。
4. 低置信度别名进入人工确认。
```

### 15.4 事件排序

事件排序优先级：

```text
1. 原文出现顺序。
2. 明确时间标记。
3. 回忆/倒叙标记。
4. LLM 推断时间顺序。
```

事件需要区分：

```text
narrative_order：叙述顺序
chronological_order：故事真实时间顺序
```

MVP 生成 Galgame 时优先使用叙述顺序，防止改编结构过度复杂。

---

## 16. 错误处理和质量控制

### 16.1 常见错误

| 错误 | 原因 | 处理 |
|---|---|---|
| 人物重复 | 别名识别失败 | 人工合并 + merge 规则 |
| 场景过碎 | 切分规则过敏感 | 设置最小场景长度 |
| 场景过长 | 没识别转场 | LLM 二次切分 |
| 事件缺失 | 摘要阶段遗漏 | 用场景级事件抽取补充 |
| 视角泄露 | 生成 prompt 约束不足 | POV checker 必检 |
| 角色 OOC | 人物卡信息不足 | 增加 speech_style 检索 |
| Ren'Py 语法错误 | 导出模板问题 | 添加语法转义和测试 |

### 16.2 质量分数

每个生成场景可以给出质量分数：

```text
source_fidelity：原作忠实度
pov_safety：视角安全性
character_consistency：人物一致性
script_quality：Galgame 剧本质量
branch_validity：选项/变量有效性
format_validity：格式合法性
```

示例：

```json
{
  "source_fidelity": 0.86,
  "pov_safety": 0.94,
  "character_consistency": 0.82,
  "script_quality": 0.78,
  "branch_validity": 0.91,
  "format_validity": 1.0
}
```

---

## 17. 配置设计

### 17.1 后端环境变量

```env
APP_ENV=dev
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/novel2gal

LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:8000/v1
LLM_API_KEY=replace_me
LLM_MODEL=replace_me

EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_MODEL=replace_me
EMBEDDING_DIM=1536

MAX_CHUNK_CHARS=1500
CHUNK_OVERLAP_CHARS=200
MAX_RETRIEVED_CHUNKS=8

ENABLE_LIGHTRAG=false
ENABLE_AUTO_REVISION=true
MAX_AUTO_REVISION_ROUNDS=1
```

### 17.2 Prompt 版本管理

每个 prompt 文件需要记录版本：

```yaml
prompt_name: generate_vn_scene
version: 0.1.0
updated_at: 2026-07-08
input_schema: AdaptationContext
output_schema: AdaptationSceneIR
```

生成记录中保存：

```text
prompt_name
prompt_version
model_name
temperature
context_hash
output_hash
```

用于复现和 debug。

---

## 18. 测试策略

### 18.1 单元测试

```text
chapter_splitter_test.py
scene_splitter_test.py
chunker_test.py
renpy_exporter_test.py
pov_rule_test.py
json_schema_validation_test.py
```

### 18.2 集成测试

准备 3 类样本文本：

```text
1. 3000 字短篇：用于快速端到端测试。
2. 2 万字中篇：用于 RAG 和章节测试。
3. 带倒叙/多人物/伏笔样例：用于 POV 和一致性检查。
```

### 18.3 Ren'Py 导出测试

检查：

```text
1. label 命名合法。
2. 变量初始化完整。
3. menu 缩进正确。
4. 中文引号和特殊字符转义正确。
5. jump label 存在。
```

### 18.4 一致性测试样例

构造测试场景：

```text
原作第 10 章才揭示“苏晚姐姐参与旧案”。
第 3 章生成剧本时 forbidden_reveals 包含该信息。
测试 checker 是否能发现提前剧透。
```

---

## 19. 里程碑规划

### M0：仓库初始化

```text
初始化 FastAPI 项目
初始化 React/Vue 项目
配置 PostgreSQL + pgvector
建立基础目录结构
编写 README 和开发启动脚本
```

### M1：小说导入和切分

```text
支持 txt/md 上传
保存 novels
分章写入 chapters
场景切分写入 source_scenes
chunk 写入 source_chunks
```

### M2：基础 RAG

```text
接入 embedding
写入 pgvector
实现按 novel/chapter/scene metadata 检索
实现 context_builder
```

### M3：剧情分析

```text
章节摘要
人物提取
事件时间线
伏笔提取初版
story bible 初版
```

### M4：核心人物视角

```text
选择 POV 人物
生成 pov_knowledge_states
支持 known/unknown/suspected/forbidden_reveals
前端展示和编辑
```

### M5：Galgame 场景生成

```text
AdaptationScene IR
逐场景生成
选项和变量 effects
资源需求清单
```

### M6：一致性检查

```text
POV 检查
提前剧透检查
人物 OOC 检查
格式检查
单轮自动修订
```

### M7：导出

```text
Markdown 导出
JSON 导出
Ren'Py 导出
assets_manifest.json
```

### M8：前端可用化

```text
上传页
分析结果页
POV 选择页
剧本编辑页
一致性报告页
导出页
```

---

## 20. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| 长文本处理成本高 | 解析慢、费用高 | 分章/分场景处理，缓存结果 |
| AI 抽取不稳定 | 人物、事件表质量波动 | JSON Schema 校验 + 人工确认 |
| 视角泄露 | Galgame 体验崩坏 | POV knowledge + checker 双重限制 |
| 伏笔丢失 | 改编质量下降 | clues 表 + must_keep 标记 |
| 分支爆炸 | 剧情无法闭合 | MVP 采用轻分支，短分歧回主线 |
| Ren'Py 语法错误 | 导出不可运行 | 模板化导出 + 单元测试 |
| 角色 OOC | 用户不满意 | 人物卡 + 原文台词 RAG |
| GraphRAG 过早引入 | 工程复杂度高 | MVP 只预留 story graph，后续接 LightRAG |

---

## 21. 后续扩展方向

### 21.1 Story Graph

MVP 后可以引入：

```text
character nodes
location nodes
event nodes
clue nodes
secret nodes
relationship edges
causal edges
reveal edges
```

示例：

```text
林雨 --怀疑--> 苏晚
苏晚 --隐瞒--> 七年前旧案
陈默 --持有--> 黑色录音笔
黑色录音笔 --证明--> 事故真相
旧教学楼 --发生过--> 七年前事故
```

### 21.2 多路线和多结局

后续支持：

```text
共通线
角色线
普通结局
坏结局
真结局
好感度门槛
线索收集门槛
```

### 21.3 资源生成

后续可接入：

```text
角色立绘生成
CG 生成
背景图生成
BGM 推荐
语音合成
```

但这不属于 MVP 核心。

### 21.4 多格式导入

后续接：

```text
PDF
DOCX
EPUB
HTML
```

推荐优先：

```text
MarkItDown 或 Docling
```

---

## 22. MVP 验收标准

MVP 完成时，至少应满足：

```text
1. 可以上传一篇 txt/md 小说。
2. 可以自动识别章节和场景。
3. 可以生成人物表、章节摘要、事件时间线。
4. 可以选择一个核心人物作为 Galgame 玩家视角。
5. 可以生成该人物的已知/未知/怀疑/禁止揭露信息表。
6. 可以逐场景生成 Galgame 剧本 IR。
7. 可以检测明显提前剧透和视角违规。
8. 可以导出 Markdown、JSON、Ren'Py。
9. Ren'Py 脚本基本可读，变量、label、menu 结构正确。
10. 前端能完成上传、查看分析结果、选择 POV、查看/编辑剧本、导出。
```

---

## 23. 当前实现优先级

优先写后端核心，不要一开始陷入复杂 UI。

推荐顺序：

```text
1. backend/app/parser：txt/md 导入、分章、切场景、chunk。
2. backend/app/db：PostgreSQL 表结构和 ORM。
3. backend/app/rag：embedding 写入、检索、context_builder。
4. backend/app/prompts：人物、事件、POV、场景生成、检查 prompt。
5. backend/app/pipelines：LangGraph 流程。
6. backend/app/exporters：Markdown/JSON/Ren'Py。
7. frontend：上传、分析结果、剧本编辑、导出。
```

第一轮开发只需要保证从命令行或 API 跑通：

```text
sample.md
→ parse
→ analyze
→ create adaptation project
→ build pov knowledge
→ generate first 3 Galgame scenes
→ check consistency
→ export renpy
```

---

## 24. 最小端到端样例

### 24.1 输入

```text
第一章 雨夜

林雨推开旧教学楼的门时，雨声正从身后涌来。
三楼的教室亮着一盏灯。
苏晚站在讲台旁，手里攥着一张泛黄的纸。

“你为什么在这里？”林雨问。

苏晚把纸藏到身后。
“这句话应该我问你。”
```

### 24.2 分析输出

```json
{
  "characters": ["林雨", "苏晚"],
  "events": [
    {
      "event_text": "林雨在雨夜进入旧教学楼。",
      "visible_to": ["林雨"]
    },
    {
      "event_text": "林雨发现苏晚在教室里拿着一张泛黄的纸。",
      "visible_to": ["林雨", "苏晚"],
      "hidden_meaning": "纸与旧案有关，但林雨当前不知道。"
    }
  ],
  "pov_knowledge": {
    "known_facts": ["苏晚深夜在旧教学楼", "苏晚藏起了一张纸"],
    "unknown_facts": ["纸的真实内容"],
    "suspected_facts": ["苏晚可能在隐瞒什么"],
    "forbidden_reveals": ["不得直接说明纸与旧案有关"]
  }
}
```

### 24.3 Galgame 输出 IR

```json
{
  "scene_id": "common_001_001",
  "title": "雨夜旧楼",
  "background": "bg_old_school_night_rain",
  "bgm": "bgm_suspense_low",
  "blocks": [
    {
      "type": "narration",
      "text": "旧教学楼的门轴发出低哑的响声。雨声从身后涌进来，像是把整栋楼都困在夜色里。"
    },
    {
      "type": "dialogue",
      "speaker": "林雨",
      "text": "你为什么在这里？"
    },
    {
      "type": "dialogue",
      "speaker": "苏晚",
      "expression": "cold",
      "text": "这句话应该我问你。"
    },
    {
      "type": "narration",
      "text": "她把手里的纸藏到了身后。动作很快，却没有快到让我忽略。"
    },
    {
      "type": "choice",
      "choices": [
        {
          "text": "追问那张纸",
          "effects": {
            "affection_suwan": -1,
            "flag_questioned_paper": true
          },
          "next_label": "common_001_001_question_paper"
        },
        {
          "text": "先不提纸的事",
          "effects": {
            "affection_suwan": 1
          },
          "next_label": "common_001_001_ignore_paper"
        }
      ]
    }
  ]
}
```

---

## 25. 结论

Novel2Gal 的 MVP 应该围绕四个核心对象构建：

```text
原文结构：chapter / source_scene / source_chunk
剧情结构：character / story_event / clue / story_bible
视角结构：pov_knowledge_state
改编结构：adaptation_scene / choice / asset / consistency_report
```

第一版不追求完整游戏引擎，也不追求自动美术音乐生成。技术重点是：

```text
长文本结构化
剧情型 RAG
核心人物视角约束
逐场景 Galgame 剧本生成
一致性检查
Ren'Py 导出
```

这条路线可以保证项目边界清楚、可实现、可演示，也能为后续 GraphRAG、多路线、多结局和资产生成留下扩展空间。
