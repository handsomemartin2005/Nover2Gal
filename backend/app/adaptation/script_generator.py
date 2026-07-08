from __future__ import annotations

import re
from typing import Any

from app.adaptation.choice_fallback import build_concrete_choice_block
from app.adaptation.stage_builder import infer_background_key, infer_stage
from app.adaptation.text_polisher import polish_game_text
from app.parser.scene_splitter import SourceScene
from app.schemas.story import POVKnowledgeState, StoryAnalysis


QUOTE_RE = re.compile(r"[“\"]([^”\"]+)[”\"]([^。！？\n]*)")
KNOWN_KEYS = {"林雨": "lin", "苏晚": "suwan", "陈默": "chenmo"}
RAIN_TERMS = ["雨声", "雨夜", "雨水", "下雨", "暴雨", "小雨", "雨还"]


def generate_scene_ir(
    source_scene: SourceScene,
    analysis: StoryAnalysis,
    pov_state: POVKnowledgeState,
    chapter_index: int,
    pov_character: str = "",
) -> dict[str, Any]:
    scene_id = f"common_{chapter_index:03d}_{source_scene.index:03d}"
    character_names = [character.name for character in analysis.characters]
    blocks: list[dict[str, Any]] = []

    narration_text = _remove_dialogue(source_scene.text).strip()
    if narration_text:
        for text in _playable_lines(polish_game_text(_compact_text(narration_text))):
            blocks.append(_block_for_pov_text(text, pov_character))

    for quote_text, tail in QUOTE_RE.findall(source_scene.text):
        speaker = _infer_speaker(tail, character_names)
        polished_quote = polish_game_text(quote_text)
        if not polished_quote:
            continue
        block: dict[str, Any] = {"type": "dialogue", "text": polished_quote}
        if speaker:
            block["speaker"] = speaker
            block["speaker_key"] = _speaker_key(speaker)
        blocks.append(block)

    if _should_add_choice(source_scene.text, analysis, pov_state):
        blocks.append(build_concrete_choice_block(scene_id, source_scene.text))

    return {
        "scene_id": scene_id,
        "title": source_scene.title,
        "background": _background_key(source_scene.text),
        "bgm": _bgm_key(source_scene.text),
        "blocks": blocks,
        "required_assets": _required_assets(source_scene.text),
        "stage": infer_stage(source_scene.text, character_names),
        "pov_after_event_order": pov_state.after_event_order,
    }


def _remove_dialogue(text: str) -> str:
    return QUOTE_RE.sub("", text)


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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


def _infer_speaker(tail: str, character_names: list[str]) -> str:
    for name in character_names:
        if name in tail:
            return name
    return ""


def _speaker_key(name: str) -> str:
    return KNOWN_KEYS.get(name, f"char_{abs(hash(name)) % 10000}")


def _should_add_choice(text: str, analysis: StoryAnalysis, pov_state: POVKnowledgeState) -> bool:
    has_multiple_characters = sum(1 for character in analysis.characters if character.name in text) >= 2
    has_question = any(term in text for term in ["？", "?", "为什么", "怎么", "什么", "谁", "哪", "要不要", "能不能", "可不可以", "行不行", "问"])
    has_suspicion = bool(pov_state.suspected_facts) or any(term in text for term in ["藏", "隐瞒", "为什么"])
    return has_question or (has_multiple_characters and has_suspicion)


def _block_for_pov_text(text: str, pov_character: str) -> dict[str, Any]:
    rewritten = text.replace("你们", "我们").replace("你", "我")
    if pov_character:
        rewritten = re.sub(rf"^{re.escape(pov_character)}", "我", rewritten)
        rewritten = rewritten.replace(f"{pov_character}心里", "我心里")
        rewritten = _rewrite_third_person_reference_to_pov(rewritten)
    if rewritten.startswith("我") or rewritten.startswith("（"):
        return {"type": "dialogue", "speaker": "我", "speaker_key": "pov", "text": rewritten}
    return {"type": "narration", "text": rewritten}


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


def _background_key(text: str) -> str:
    inferred = infer_background_key(text)
    if inferred != "bg_default":
        return inferred
    if "旧教学楼" in text:
        return "bg_old_school_night"
    if "教室" in text:
        return "bg_classroom"
    return "bg_default"


def _bgm_key(text: str) -> str:
    if _has_rain_weather(text) or any(term in text for term in ["藏", "旧案", "为什么"]):
        return "bgm_suspense_low"
    return "bgm_daily"


def _required_assets(text: str) -> list[dict[str, str]]:
    assets = [{"type": "background", "key": _background_key(text), "description": "根据原文场景生成的背景需求"}]
    if _has_rain_weather(text):
        assets.append({"type": "sfx", "key": "sfx_rain_loop", "description": "持续雨声"})
    return assets


def _has_rain_weather(text: str) -> bool:
    return any(term in text for term in RAIN_TERMS)
