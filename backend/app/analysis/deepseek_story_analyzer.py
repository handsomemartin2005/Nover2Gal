from __future__ import annotations

from dataclasses import replace
import json
import re
from typing import Any, Protocol

from app.schemas.story import CharacterCard, StoryAnalysis


class ChatClient(Protocol):
    def chat(self, messages: list[dict[str, str]], json_output: bool = False) -> str:
        ...


NOT_CHARACTER_NAMES = {
    "这个",
    "那个",
    "任何",
    "何人",
    "什么",
    "怎么",
    "应该",
    "没有",
    "到了",
    "下来",
    "当中",
    "顶楼",
    "慢地",
    "心的",
    "像是",
    "人的",
    "恋人",
    "主要",
    "角色",
    "旁白",
    "玩家",
    "问题",
    "选择",
    "选项",
    "原文",
    "原书",
    "主线",
    "剧情",
    "场景",
    "晚饭",
    "披萨",
    "汉堡",
    "低声",
    "纸条",
    "钥匙",
    "教室",
    "旧楼",
    "雨声",
    "时候",
    "地方",
    "事情",
    "东西",
    "眼前",
    "心里",
    "耳边",
    "身后",
    "面前",
    "声音",
    "男人",
    "女人",
    "女孩",
    "男孩",
    "恋人",
    "朋友",
    "同学",
}
NAME_ENDING_STOP_CHARS = set("的了是不么吗呢啊吧中上下来去到")
INVALID_NAME_PARTS = {"这个", "那个", "任何", "什么", "怎么", "应该", "没有", "人的", "心的", "角色", "人物", "原文", "原书"}
SPEECH_OR_ACTION_RE = re.compile(r"({name})(?:说|问|道|喊|叫|笑|哭|看|望|推|站|走|跑|把|想|发现|沉默|回答|递|拿|伸手|低声|抬头)")
QUOTE_SPEAKER_RE = re.compile(r"[“\"]([^”\"]+)[”\"]\s*([^。！？!?]{0,12})")


def refine_analysis_with_deepseek(
    title: str,
    text: str,
    base_analysis: StoryAnalysis,
    client: ChatClient,
) -> StoryAnalysis:
    messages = _build_messages(title, text, base_analysis)
    payload = json.loads(client.chat(messages, json_output=True))
    rejected = set(_string_list(payload.get("not_characters"))) | NOT_CHARACTER_NAMES
    visual_style = _normalize_visual_style(payload.get("visual_style"), text)
    characters = _normalize_characters(payload.get("characters", []), base_analysis, text, rejected, visual_style)
    characters = _merge_base_characters(characters, base_analysis, rejected, text, visual_style)
    if not characters:
        characters = [_with_visual_style(character, visual_style) for character in base_analysis.characters]
    if not characters:
        return base_analysis
    return StoryAnalysis(
        title=base_analysis.title,
        characters=characters,
        events=base_analysis.events,
        clues=base_analysis.clues,
        story_bible=base_analysis.story_bible,
    )


def _merge_base_characters(
    characters: list[CharacterCard],
    base_analysis: StoryAnalysis,
    rejected: set[str],
    source_text: str,
    visual_style: str,
) -> list[CharacterCard]:
    merged: list[CharacterCard] = []
    seen: set[str] = set()
    base_names = {character.name for character in base_analysis.characters}
    ordered_sources = (
        [*base_analysis.characters, *characters]
        if len(characters) < 2 and len(base_analysis.characters) >= 2
        else [*characters, *base_analysis.characters]
    )
    for character in ordered_sources:
        if character.name in seen:
            continue
        if character.name in base_names and not _is_valid_character_name(character.name, source_text, rejected, base_names):
            continue
        merged.append(_with_visual_style(character, visual_style))
        seen.add(character.name)
        if len(merged) >= 16:
            break
    return merged


def _with_visual_style(character: CharacterCard, visual_style: str) -> CharacterCard:
    visual_notes = {
        **character.visual_notes,
        "style": character.visual_notes.get("style") or visual_style,
        "gender": character.visual_notes.get("gender") or "unknown",
    }
    if visual_style == "anime":
        visual_notes["style"] = "anime"
    return replace(character, visual_notes=visual_notes)


def _build_messages(title: str, text: str, base_analysis: StoryAnalysis) -> list[dict[str, str]]:
    user_payload = {
        "title": title,
        "task": "识别小说里真正的人物，只返回人物，不要把物品、动作、语气、地点、食物、章节名当人物。",
        "rule_candidates": [character.name for character in base_analysis.characters],
        "not_characters": sorted(NOT_CHARACTER_NAMES),
        "source_text": text,
        "required_json_schema": {
            "characters": [
                {
                    "name": "人物姓名",
                    "role": "主角/主要角色/配角",
                    "personality": "基于原文证据的简短性格",
                    "speech_style": "说话风格",
                    "relationship_map": {"其他人物": "关系"},
                    "secrets": ["不能提前暴露的秘密或隐情"],
                    "do_not_do": ["此人物不应该做/说的事"],
                    "visual_notes": {
                        "age": "child/young/adult/elder",
                        "gender": "female/male/unknown",
                        "style": "real/anime",
                        "appearance": "视觉描述",
                    },
                    "source_evidence": ["支持判断的原文短句"],
                    "aliases": ["别名"],
                }
            ],
            "visual_style": "real 或 anime；先判断全文是真实世界还是二次元/动漫风格",
            "not_characters": ["被排除的名词"],
        },
    }
    return [
        {
            "role": "system",
            "content": (
                "你是小说人物表抽取器。只输出合法 JSON。"
                "先通读全文，再列人物。"
                "人物必须是具备行动、说话、心理或社会关系的实体。"
                "每个人物必须能在 source_text 中找到原文证据。"
                "禁止把代词、连词、副词、地点、物品、剧情术语、玩家选项当人物。"
                "不要输出解释、推理过程或 Markdown。"
            ),
        },
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _normalize_characters(
    value: Any,
    base_analysis: StoryAnalysis,
    source_text: str,
    rejected: set[str],
    visual_style: str,
) -> list[CharacterCard]:
    if not isinstance(value, list):
        return []
    characters: list[CharacterCard] = []
    seen: set[str] = set()
    valid_base_names = {character.name for character in base_analysis.characters}
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _clean_name(item.get("name"))
        if not name or name in seen:
            continue
        if not _is_valid_character_name(name, source_text, rejected, valid_base_names):
            continue
        seen.add(name)
        characters.append(_build_card(item, name, len(characters) + 1, base_analysis, visual_style))
        if len(characters) >= 16:
            break
    return characters


def _build_card(
    item: dict[str, Any],
    name: str,
    index: int,
    base_analysis: StoryAnalysis,
    visual_style: str,
) -> CharacterCard:
    existing = next((character for character in base_analysis.characters if character.name == name), None)
    visual_notes = _value_dict(item.get("visual_notes"), existing.visual_notes if existing else {"expressions": ["normal", "serious"]})
    visual_notes = {
        **visual_notes,
        "style": visual_notes.get("style") or visual_style,
        "gender": visual_notes.get("gender") or _infer_gender(name, item, existing),
    }
    return CharacterCard(
        character_id=existing.character_id if existing else f"char_{index}",
        name=name,
        aliases=_string_list(item.get("aliases")),
        role=_string_value(item.get("role"), existing.role if existing else ("主角" if index == 1 else "主要角色")),
        personality=_string_value(item.get("personality"), existing.personality if existing else "由 AI 根据原文识别。"),
        speech_style=_string_value(item.get("speech_style"), existing.speech_style if existing else "贴近原文语气。"),
        relationship_map=_string_dict(item.get("relationship_map"), existing.relationship_map if existing else {}),
        secrets=_string_list(item.get("secrets")) or (existing.secrets if existing else []),
        visual_notes=visual_notes,
        do_not_do=_string_list(item.get("do_not_do")) or (existing.do_not_do if existing else ["不要把普通名词当成人物。"]),
        source_evidence=_string_list(item.get("source_evidence")) or (existing.source_evidence if existing else []),
    )


def _clean_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if len(cleaned) < 2 or len(cleaned) > 6:
        return ""
    return cleaned


def _is_valid_character_name(name: str, source_text: str, rejected: set[str], valid_base_names: set[str]) -> bool:
    if name in rejected:
        return False
    if any(part in name for part in INVALID_NAME_PARTS):
        return False
    if name[-1] in NAME_ENDING_STOP_CHARS:
        return False
    if not re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·]{2,6}", name):
        return False
    if name not in source_text:
        return False
    if name in valid_base_names:
        return True
    action_re = re.compile(SPEECH_OR_ACTION_RE.pattern.format(name=re.escape(name)))
    if action_re.search(source_text):
        return True
    for _, tail in QUOTE_SPEAKER_RE.findall(source_text):
        if name in tail:
            return True
    return False


def _normalize_visual_style(value: Any, source_text: str) -> str:
    if isinstance(value, str) and value.lower().strip() in {"anime", "real"}:
        return value.lower().strip()
    anime_terms = ["二次元", "动漫", "动画", "异世界", "魔法", "勇者", "精灵", "轻小说", "galgame", "Galgame"]
    return "anime" if any(term in source_text for term in anime_terms) else "real"


def _infer_gender(name: str, item: dict[str, Any], existing: CharacterCard | None) -> str:
    raw = " ".join(
        str(value)
        for value in [
            name,
            item.get("role", ""),
            item.get("personality", ""),
            item.get("speech_style", ""),
            item.get("visual_notes", ""),
        ]
    )
    if any(term in raw for term in ["女", "她", "少女", "姐姐", "妹妹", "母亲", "妻", "玲奈", "琴", "月"]):
        return "female"
    if any(term in raw for term in ["男", "他", "少年", "哥哥", "弟弟", "父亲", "丈夫"]):
        return "male"
    if existing:
        return str(existing.visual_notes.get("gender") or "unknown")
    return "unknown"


def _string_value(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _string_dict(value: Any, default: dict[str, str]) -> dict[str, str]:
    if not isinstance(value, dict):
        return default
    cleaned = {str(key).strip(): str(item).strip() for key, item in value.items() if str(key).strip() and str(item).strip()}
    return cleaned or default


def _value_dict(value: Any, default: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return default
    cleaned = {str(key).strip(): item for key, item in value.items() if str(key).strip() and item not in (None, "")}
    return cleaned or default
