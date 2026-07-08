from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceScene:
    index: int
    title: str
    text: str
    start_offset: int
    end_offset: int


SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")
TRANSITION_TERMS = (
    "第二天",
    "第三天",
    "清晨",
    "早晨",
    "上午",
    "中午",
    "午休",
    "午休时间",
    "课间",
    "下午",
    "傍晚",
    "晚上",
    "夜里",
    "后来",
    "这时",
    "随后",
    "回到",
    "走进",
    "来到",
    "到了",
    "离开",
    "进了",
    "出了",
    "院子",
    "院里",
    "窑洞",
    "教室",
    "课堂",
    "讲台",
    "走廊",
    "楼道",
    "浴室",
    "洗澡",
    "厕所",
    "女厕",
    "男厕",
    "卫生间",
    "洗手间",
    "更衣室",
    "宿舍",
    "街上",
    "路上",
    "车站",
    "饭店",
    "医院",
    "家里",
    "屋里",
    "门口",
    "楼上",
    "楼下",
)

STRONG_TRANSITION_TERMS = (
    "午休",
    "午休时间",
    "课间",
    "教室",
    "课堂",
    "讲台",
    "走廊",
    "楼道",
    "浴室",
    "厕所",
    "女厕",
    "男厕",
    "卫生间",
    "洗手间",
    "更衣室",
    "宿舍",
    "天台",
    "楼顶",
    "车站",
    "饭店",
    "医院",
)


def split_scenes(chapter_text: str, min_scene_chars: int = 80) -> list[SourceScene]:
    text = chapter_text.strip()
    if not text:
        return []
    if min_scene_chars < 1:
        raise ValueError("min_scene_chars must be positive")

    parts = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if not parts:
        return []

    expanded_parts: list[str] = []
    for part in parts:
        expanded_parts.extend(_split_part_on_transitions(part, min_scene_chars))

    merged: list[str] = []
    for part in expanded_parts:
        if not merged:
            merged.append(part)
            continue
        starts_strong_transition = _starts_with_strong_transition(part)
        should_merge = (len(merged[-1]) < min_scene_chars and not starts_strong_transition) or (
            len(part) < min_scene_chars and not _starts_with_transition(part)
        )
        if should_merge:
            merged[-1] = f"{merged[-1]}\n\n{part}"
        else:
            merged.append(part)

    scenes: list[SourceScene] = []
    search_from = 0
    for idx, part in enumerate(merged, start=1):
        start = text.find(part.split("\n", 1)[0], search_from)
        if start < 0:
            start = search_from
        end = start + len(part)
        scenes.append(SourceScene(index=idx, title=f"Scene {idx}", text=part, start_offset=start, end_offset=end))
        search_from = end
    return scenes


def _split_part_on_transitions(part: str, min_scene_chars: int) -> list[str]:
    sentences = [sentence.strip() for sentence in SENTENCE_RE.findall(part) if sentence.strip()]
    if len(sentences) <= 1:
        return [part]

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        starts_new_scene = bool(current) and _starts_with_transition(sentence) and (
            current_len >= min_scene_chars
            or (current_len >= 10 and _starts_with_strong_transition(sentence))
        )
        if starts_new_scene:
            pieces.append("".join(current).strip())
            current = [sentence]
            current_len = len(sentence)
            continue
        current.append(sentence)
        current_len += len(sentence)
    if current:
        pieces.append("".join(current).strip())
    return pieces or [part]


def _starts_with_transition(text: str) -> bool:
    stripped = text.lstrip(" ，,。；;“”\"")
    return any(stripped.startswith(term) for term in TRANSITION_TERMS)


def _starts_with_strong_transition(text: str) -> bool:
    stripped = text.lstrip(" ，,。；;“”\"")
    return any(stripped.startswith(term) for term in STRONG_TRANSITION_TERMS)
