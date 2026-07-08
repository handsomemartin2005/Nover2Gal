from __future__ import annotations

import json
import re
from typing import Any, Protocol

from app.adaptation.choice_fallback import build_concrete_choice_block
from app.adaptation.stage_builder import background_key_for_location, canonical_location, infer_background_key, infer_stage
from app.adaptation.text_polisher import polish_choice_text, polish_game_text
from app.parser.scene_splitter import SourceScene
from app.rag.retriever import RetrievedSnippet
from app.schemas.story import POVKnowledgeState, StoryAnalysis


class ChatClient(Protocol):
    def chat(self, messages: list[dict[str, str]], json_output: bool = False) -> str:
        ...


KNOWN_BACKGROUND_KEYS = {
    "bg_default",
    "bg_home_living",
    "bg_restaurant",
    "bg_bedroom",
    "bg_kitchen",
    "bg_office",
    "bg_village",
    "bg_field",
    "bg_yard",
    "bg_cave_dwelling",
    "bg_station",
    "bg_hospital",
    "bg_shop",
    "bg_bathroom",
    "bg_toilet",
    "bg_dormitory",
    "bg_school_hallway",
    "bg_rooftop",
    "bg_street",
    "bg_classroom",
    "bg_old_school_night",
}
GENERIC_OR_BROAD_LOCATIONS = {"generic", "home_living", "village"}


def adapt_scene_with_deepseek(
    source_scene: SourceScene,
    analysis: StoryAnalysis,
    pov_state: POVKnowledgeState,
    chapter_index: int,
    rag_context: list[RetrievedSnippet],
    client: ChatClient,
    pov_character: str = "",
) -> dict[str, Any]:
    scene_id = f"common_{chapter_index:03d}_{source_scene.index:03d}"
    messages = _build_messages(source_scene, analysis, pov_state, rag_context, scene_id, pov_character)
    raw = client.chat(messages, json_output=True)
    payload = json.loads(raw)
    return _normalize_scene_ir(payload, source_scene, scene_id, analysis, pov_state, rag_context, pov_character)


def _build_messages(
    source_scene: SourceScene,
    analysis: StoryAnalysis,
    pov_state: POVKnowledgeState,
    rag_context: list[RetrievedSnippet],
    scene_id: str,
    pov_character: str,
) -> list[dict[str, str]]:
    characters = [
        {
            "name": character.name,
            "role": character.role,
            "personality": character.personality,
            "speech_style": character.speech_style,
        }
        for character in analysis.characters
    ]
    user_payload = {
        "scene_id": scene_id,
        "project_title": analysis.title,
        "source_scene_title": source_scene.title,
        "source_scene_text": source_scene.text,
        "pov_character": pov_character,
        "story_bible": {
            "main_plot": analysis.story_bible.main_plot,
            "core_conflict": analysis.story_bible.core_conflict,
            "themes": analysis.story_bible.themes,
            "style_notes": analysis.story_bible.style_notes,
            "forbidden_changes": analysis.story_bible.forbidden_changes,
        },
        "characters": characters,
        "pov_knowledge": {
            "known_facts": pov_state.known_facts,
            "unknown_facts": pov_state.unknown_facts,
            "suspected_facts": pov_state.suspected_facts,
            "false_beliefs": pov_state.false_beliefs,
            "forbidden_reveals": pov_state.forbidden_reveals,
        },
        "rag_context": [
            {"chunk_index": snippet.chunk_index, "score": snippet.score, "text": snippet.text}
            for snippet in rag_context
        ],
        "choice_design": {
            "choice_mode": "Use parallel for two different actions. Use opposed sometimes for action/opposite pairs such as go/do not go, ask/stay silent, accept/refuse.",
            "branching": "Every choice block still needs one mainline route and one divergent route. Divergent routes must converge back before the next major source event.",
            "game_text_rule": "Do not write meta planning terms into text, branch_text, or converge_text. Forbidden terms include original book, mainline, core fact, key action, converge, route. Write concrete character actions from the current scene instead.",
            "player_choice_rule": (
                "Choice text must be a short daily action or decision the player can click directly. "
                "Good examples: 吃披萨 / 改吃汉堡, 同意她 / 先拒绝, 承认喜欢A / 选择D, 留下来 / 先回家. "
                "Bad examples: 继续问清楚, 先观察, 贴合主线, 偏离后回收, 并行, 主线."
            ),
        },
        "line_style": {
            "max_chars_per_block": 42,
            "max_blocks_for_long_speech": 5,
            "instruction": (
                "Do not paste a long novel paragraph into one block. "
                "Condense long speeches into short playable Chinese lines with natural dialogue. "
                "If one character talks a lot, split it into 3-5 short click-through lines instead of one paragraph."
            ),
        },
        "pov_writing_rule": {
            "narration": "旁白只写外部可见事实、环境和动作结果，不写第一人称心理。",
            "first_person": "核心视角人物的动作、犹豫和内心选择写成 speaker=我 的 dialogue/action line。",
            "question_choice": "如果有人向视角人物提问，优先把选择放在回答这个问题的位置。",
            "action_parentheses": "选择后的分支文本可以使用（动作/内心）补足互动感，例如 我伸出手（心里还是犹豫了一下），把话说出口。",
        },
        "required_json_schema": {
            "background": "stable background key like bg_library_night",
            "bgm": "stable bgm key like bgm_suspense_low",
            "stage": {
                "location": "home_living, classroom, school_hallway, bathroom, toilet, dormitory, restaurant, old_school, or generic",
                "props": ["table", "chair", "door", "window", "cup", "mirror", "sink", "towel"],
                "characters": ["visible character names or protagonist"],
            },
            "blocks": [
                {"type": "narration", "text": "short narration from POV"},
                {"type": "dialogue", "speaker": "character name or 我", "text": "line"},
                {
                    "type": "choice",
                    "choice_mode": "parallel or opposed",
                    "choices": [
                        {
                            "text": "short player-facing action, no route or mode labels",
                            "route": "mainline or divergent",
                            "branch_text": "what happens immediately after this choice",
                            "converge_text": "how this branch returns to the next main event",
                            "effects": {"flag_name": True},
                            "next_label": "label_name",
                        }
                    ],
                },
            ],
            "required_assets": [{"type": "background", "key": "asset key", "description": "visual note"}],
        },
    }
    return [
        {
            "role": "system",
            "content": (
                "你是小说改编为 Galgame 的结构化编剧。"
                "只输出合法 JSON，不输出解释、推理过程或 Markdown。"
                "改编必须遵守指定核心人物视角：未知事实不能提前揭露。"
                "旁白和第一视角要分清：旁白只写外部可见事实；视角人物的动作和心理用 speaker=我。"
                "对白要短，每个可点击文本块不要超过 42 个汉字；长对白要拆成四五次点击。"
                "不要把分析、路线、回收、主线、偏离等内部词写进游戏文本。"
                "选择项必须是玩家能直接点的日常动作或明确态度；如果原文有人提问，选择优先设计成回答。"
                "选择后的分支文本要有人物动作，可以使用中文括号写动作或内心。"
                "Every choice must include at least one route=mainline option that follows the source event, "
                "and one route=divergent option that briefly varies the action but returns before the next source event. "
                "Do not copy route labels or planning terms into player-visible text. "
                "Player choice text should read like everyday decisions, for example 吃披萨, 改吃汉堡, 同意她, 先拒绝, 选择D, 留下来."
            ),
        },
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _normalize_scene_ir(
    payload: dict[str, Any],
    source_scene: SourceScene,
    scene_id: str,
    analysis: StoryAnalysis,
    pov_state: POVKnowledgeState,
    rag_context: list[RetrievedSnippet],
    pov_character: str,
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    for raw_block in payload.get("blocks", []):
        if not isinstance(raw_block, dict):
            continue
        normalized = _normalize_block(raw_block, scene_id, pov_character)
        if isinstance(normalized, list):
            blocks.extend(normalized)
        elif normalized:
            blocks.append(normalized)
    if not blocks:
        blocks = [
            _normalize_pov_line({"type": "narration", "text": line}, pov_character)
            for line in _playable_lines(polish_game_text(source_scene.text.strip()))
        ]
    if not any(block.get("type") == "choice" for block in blocks):
        blocks = _insert_fallback_choice(blocks, scene_id, source_scene.text)
    blocks = _repair_choice_blocks(blocks, source_scene.text, scene_id)
    stage = _normalize_stage(payload.get("stage"), source_scene, analysis, rag_context)
    stage = _align_stage_to_visible_blocks(stage, blocks)

    return {
        "scene_id": scene_id,
        "title": source_scene.title,
        "background": _normalize_background(payload.get("background"), source_scene, rag_context, stage),
        "bgm": _string_or_default(payload.get("bgm"), "bgm_daily"),
        "blocks": blocks,
        "required_assets": _normalize_assets(payload.get("required_assets")),
        "stage": stage,
        "pov_after_event_order": pov_state.after_event_order,
        "adapter": "deepseek",
        "rag_chunk_indexes": [snippet.chunk_index for snippet in rag_context],
    }


def _normalize_block(block: dict[str, Any], scene_id: str, pov_character: str = "") -> dict[str, Any] | list[dict[str, Any]] | None:
    block_type = block.get("type")
    if block_type in {"narration", "dialogue"}:
        text = _string_or_default(block.get("text"), "").strip()
        if not text:
            return None
        text = polish_game_text(text)
        lines = _playable_lines(text)
        normalized_blocks: list[dict[str, Any]] = [{"type": block_type, "text": line} for line in lines]
        speaker = _string_or_default(block.get("speaker"), "").strip()
        if block_type == "narration":
            normalized_blocks = [_normalize_pov_line(line_block, pov_character) for line_block in normalized_blocks]
        if block_type == "dialogue" and speaker:
            for normalized in normalized_blocks:
                normalized["speaker"] = speaker
                normalized["speaker_key"] = _speaker_key(speaker)
        return normalized_blocks
    if block_type == "choice":
        choices = [_normalize_choice(choice, scene_id, pov_character) for choice in block.get("choices", []) if isinstance(choice, dict)]
        choices = [choice for choice in choices if choice]
        if not choices:
            return None
        return {"type": "choice", "choice_mode": _normalize_choice_mode(block.get("choice_mode")), "choices": choices}
    return None


def _normalize_choice(choice: dict[str, Any], scene_id: str, pov_character: str = "") -> dict[str, Any] | None:
    text = _clean_choice_visible_text(_string_or_default(choice.get("text"), "").strip())
    if not text:
        return None
    next_label = _string_or_default(choice.get("next_label"), f"{scene_id}_choice")
    route = _normalize_route(choice.get("route"))
    branch_text = _clean_branch_text(_string_or_default(choice.get("branch_text"), f"我选择了：{text}。"), pov_character, add_aside=True)
    converge_text = _string_or_default(
        choice.get("converge_text"),
        "对方停了一下，刚才的话还留在你们之间。",
    )
    converge_text = _clean_branch_text(converge_text, pov_character, add_aside=False)
    effects = choice.get("effects")
    if not isinstance(effects, dict):
        effects = {}
    return {
        "text": text,
        "route": route,
        "branch_text": branch_text,
        "converge_text": converge_text,
        "effects": effects,
        "next_label": next_label,
    }


def _fallback_choice_block(scene_id: str, source_text: str) -> dict[str, Any]:
    return build_concrete_choice_block(scene_id, source_text)


def _insert_fallback_choice(blocks: list[dict[str, Any]], scene_id: str, source_text: str) -> list[dict[str, Any]]:
    choice = _fallback_choice_block(scene_id, source_text)
    if not _source_has_question(source_text):
        return [*blocks, choice]
    for index, block in enumerate(blocks):
        text = str(block.get("text", ""))
        if _source_has_question(text):
            return [*blocks[: index + 1], choice, *blocks[index + 1 :]]
    insert_at = 1 if blocks else 0
    return [*blocks[:insert_at], choice, *blocks[insert_at:]]


def _repair_choice_blocks(blocks: list[dict[str, Any]], source_text: str, scene_id: str) -> list[dict[str, Any]]:
    repaired: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "choice":
            repaired.append(block)
            continue
        if _choice_block_needs_source_rebuild(block):
            repaired.append(_fallback_choice_block(scene_id, source_text))
            continue
        repaired.append(block)
    return repaired


def _source_has_question(text: str) -> bool:
    return any(term in text for term in ["？", "?", "为什么", "怎么", "什么", "谁", "哪", "要不要", "能不能", "可不可以", "行不行", "问"])


def _choice_block_needs_source_rebuild(block: dict[str, Any]) -> bool:
    choices = block.get("choices", [])
    if not isinstance(choices, list) or len(choices) < 2:
        return True
    routes = {choice.get("route") for choice in choices if isinstance(choice, dict)}
    if not {"mainline", "divergent"}.issubset(routes):
        return True
    return any(_choice_text_is_abstract(str(choice.get("text", ""))) for choice in choices if isinstance(choice, dict))


def _choice_text_is_abstract(text: str) -> bool:
    normalized = re.sub(r"\s+", "", text)
    if not normalized:
        return True
    forbidden_terms = [
        "主线",
        "支线",
        "分支",
        "路线",
        "并行",
        "反向",
        "偏离",
        "回收",
        "收束",
        "核心事实",
        "关键行动",
        "原书",
        "原文",
        "贴合",
        "继续问清楚",
        "继续确认",
        "暂时观察",
        "先观察",
        "绕到侧面",
    ]
    if any(term in normalized for term in forbidden_terms):
        return True
    return len(normalized) > 12


def _normalize_assets(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    assets: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        key = _string_or_default(item.get("key"), "").strip()
        if not key:
            continue
        assets.append(
            {
                "type": _string_or_default(item.get("type"), "background"),
                "key": key,
                "description": _string_or_default(item.get("description"), ""),
            }
        )
    return assets


def _normalize_background(
    value: Any,
    source_scene: SourceScene,
    rag_context: list[RetrievedSnippet],
    stage: dict[str, Any],
) -> str:
    background = _string_or_default(value, "bg_default")
    if background.startswith("bg_ai_"):
        return background
    stage_background = background_key_for_location(str(stage.get("location", "")))
    if stage_background != "bg_default" and background != stage_background:
        return stage_background
    inferred = infer_background_key(_source_and_rag_text(source_scene, rag_context))
    unknown_runtime_key = background not in KNOWN_BACKGROUND_KEYS and not background.startswith("bg_ai_")
    if inferred != "bg_default" and (background == "bg_default" or unknown_runtime_key):
        return inferred
    return background


def _normalize_stage(
    value: Any,
    source_scene: SourceScene,
    analysis: StoryAnalysis,
    rag_context: list[RetrievedSnippet],
) -> dict[str, Any]:
    inferred = _infer_stage_from_source(source_scene, analysis, rag_context)
    if isinstance(value, dict):
        location = _string_or_default(value.get("location"), "")
        location = canonical_location(location)
        props = value.get("props")
        characters = value.get("characters")
        if location and isinstance(props, list) and isinstance(characters, list):
            normalized_props = [str(item) for item in props if item]
            normalized_characters = [str(item) for item in characters if item]
            should_prefer_inferred = (
                inferred["location"] != "generic"
                and (location in GENERIC_OR_BROAD_LOCATIONS or len(normalized_props) < 2)
            )
            if should_prefer_inferred:
                return {
                    "location": inferred["location"],
                    "props": sorted(set(normalized_props) | set(inferred["props"])),
                    "characters": sorted(set(normalized_characters) | set(inferred["characters"])),
                }
            return {
                "location": location,
                "props": normalized_props,
                "characters": normalized_characters,
            }
    return inferred


def _align_stage_to_visible_blocks(stage: dict[str, Any], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    visible_text = "\n".join(
        str(block.get("text", ""))
        for block in blocks[:8]
        if block.get("type") in {"narration", "dialogue"}
    )
    inferred = infer_stage(visible_text, [str(name) for name in stage.get("characters", [])])
    inferred_location = inferred.get("location")
    current_location = canonical_location(str(stage.get("location", "")))
    if inferred_location and inferred_location != "generic" and inferred_location != current_location:
        return {
            "location": inferred_location,
            "props": sorted(set(stage.get("props", [])) | set(inferred.get("props", []))),
            "characters": sorted(set(stage.get("characters", [])) | set(inferred.get("characters", []))),
        }
    return {**stage, "location": current_location}


def _infer_stage_from_source(
    source_scene: SourceScene,
    analysis: StoryAnalysis,
    rag_context: list[RetrievedSnippet],
) -> dict[str, Any]:
    character_names = [character.name for character in analysis.characters]
    return infer_stage(_source_and_rag_text(source_scene, rag_context), character_names)


def _source_and_rag_text(source_scene: SourceScene, rag_context: list[RetrievedSnippet]) -> str:
    context = "\n".join(snippet.text for snippet in rag_context[:2])
    return f"{source_scene.text}\n{context}".strip()


def _playable_lines(text: str, max_chars: int = 42, max_lines: int = 5) -> list[str]:
    parts = [part.strip() for part in re.findall(r"[^。！？!?]+[。！？!?]?", text) if part.strip()]
    lines: list[str] = []
    for part in parts or [text]:
        while len(part) > max_chars:
            lines.append(part[:max_chars].rstrip("，,、 "))
            part = part[max_chars:].lstrip("，,、 ")
        if part:
            lines.append(part)
    if len(lines) <= max_lines:
        return lines
    return lines[: max_lines - 1] + [_trim_tail_line(lines[-1], max_chars)]


def _trim_tail_line(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else f"{text[: max_chars - 1].rstrip()}…"


def _normalize_pov_line(block: dict[str, Any], pov_character: str) -> dict[str, Any]:
    text = str(block.get("text", "")).strip()
    if not text:
        return block
    rewritten = _rewrite_pov_text(text, pov_character)
    if rewritten.startswith("我") or rewritten.startswith("（"):
        return {"type": "dialogue", "speaker": "我", "speaker_key": "pov", "text": rewritten}
    block["text"] = rewritten
    return block


def _rewrite_pov_text(text: str, pov_character: str) -> str:
    rewritten = text.replace("你们", "我们").replace("你", "我")
    if pov_character:
        rewritten = re.sub(rf"^{re.escape(pov_character)}", "我", rewritten)
        rewritten = rewritten.replace(f"{pov_character}心里", "我心里")
        rewritten = _rewrite_third_person_reference_to_pov(rewritten)
    return rewritten


def _rewrite_third_person_reference_to_pov(text: str) -> str:
    replacements = {
        "问他": "问我",
        "问她": "问我",
        "看着他": "看着我",
        "看着她": "看着我",
        "望着他": "望着我",
        "望着她": "望着我",
        "对他说": "对我说",
        "对她说": "对我说",
        "向他说": "向我说",
        "向她说": "向我说",
        "递给他": "递给我",
        "递给她": "递给我",
        "拉住他": "拉住我",
        "拉住她": "拉住我",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _normalize_route(value: Any) -> str:
    return value if value in {"mainline", "divergent"} else "divergent"


def _normalize_choice_mode(value: Any) -> str:
    return value if value in {"parallel", "opposed"} else "parallel"


def _string_or_default(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _speaker_key(name: str) -> str:
    return f"char_{abs(hash(name)) % 10000}"


def _clean_choice_visible_text(text: str) -> str:
    return polish_choice_text(text)


def _clean_branch_text(text: str, pov_character: str = "", add_aside: bool = False) -> str:
    replacements = {
        "这一步": "这下",
        "原书": "之前",
        "主线": "正事",
        "核心事实": "这件事",
        "关键行动": "下一步",
        "原来的节奏": "刚才的话题",
        "重新面对": "又回到",
        "收束": "停住",
        "回收": "带回",
        "偏离": "换个做法",
        "并行": "同时",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = _rewrite_pov_text(text, pov_character)
    text = polish_game_text(text)
    if add_aside:
        text = _with_action_aside(text)
    return text


def _with_action_aside(text: str) -> str:
    if "（" in text:
        return text
    asides = [
        "（心里斟酌了一下）",
        "（动作放轻了些）",
        "（还是决定试一试）",
        "（不想再拖下去）",
    ]
    aside = asides[abs(hash(text)) % len(asides)]
    if text.startswith("我"):
        return f"我{aside}{text[1:]}"
    return f"{aside}{text}"
