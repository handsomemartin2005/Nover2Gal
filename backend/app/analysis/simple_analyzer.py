from __future__ import annotations

import re
from collections import Counter

from app.parser.chapter_splitter import Chapter
from app.parser.scene_splitter import SourceScene
from app.schemas.story import CharacterCard, Clue, StoryAnalysis, StoryBible, StoryEvent


NAME_RE = re.compile("[\u4e00-\u9fff]{2,4}")
ACTION_NAME_RE = re.compile("([\u4e00-\u9fff]{2,5})(?:说|问|道|喊|叫|笑|哭|推|站|走|跑|看|望|把|想|发现|沉默|回答|递|拿|伸手|抬头)")
SENTENCE_RE = re.compile(r"[^。！？!?]+[。！？!?]?")
STOP_NAMES = {
    "第一章",
    "第二章",
    "第三章",
    "第四章",
    "旧教学楼",
    "三楼",
    "教室",
    "雨声",
    "讲台",
    "身后",
    "这里",
    "这句话",
    "该我",
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
    "朋友",
    "同学",
}
PRONOUN_CHARS = {"我", "你", "他", "她", "它", "咱", "谁"}
INVALID_NAME_PARTS = {"这个", "那个", "任何", "什么", "怎么", "应该", "没有", "人的", "心的", "角色", "人物", "原文", "原书"}
NAME_ENDING_STOP_CHARS = set("的了是不么吗呢啊吧中上下来去到")
NAME_PREFIX_NOISE = set("对向跟和同把被让给叫")
TRAILING_MODIFIERS = ("低声", "轻声", "小声", "大声", "慢慢", "忽然", "突然", "转身", "抬头")
CLUE_TERMS = ["泛黄的纸", "录音笔", "旧案", "日记", "信件", "照片", "钥匙"]


def analyze_story(title: str, chapters: list[Chapter], scenes_by_chapter: dict[int, list[SourceScene]]) -> StoryAnalysis:
    all_text = "\n".join(chapter.text for chapter in chapters)
    character_names = _extract_character_names(all_text)
    characters = [_build_character_card(name, index, all_text) for index, name in enumerate(character_names, start=1)]
    events = _extract_events(scenes_by_chapter, character_names)
    clues = _extract_clues(events)
    story_bible = _build_story_bible(title, chapters, events)
    return StoryAnalysis(title=title, characters=characters, events=events, clues=clues, story_bible=story_bible)


def _extract_character_names(text: str) -> list[str]:
    candidates: Counter[str] = Counter()
    for name in ACTION_NAME_RE.findall(text):
        cleaned = _trim_to_likely_name(name)
        if _is_valid_name_candidate(cleaned, text):
            candidates[cleaned] += text.count(cleaned)

    return sorted(candidates, key=lambda name: text.find(name))


def _trim_to_likely_name(value: str) -> str:
    cleaned = value.strip()
    while len(cleaned) > 2 and any(cleaned.endswith(modifier) for modifier in TRAILING_MODIFIERS):
        for modifier in TRAILING_MODIFIERS:
            if cleaned.endswith(modifier):
                cleaned = cleaned[: -len(modifier)]
                break
    while len(cleaned) > 2 and cleaned[0] in NAME_PREFIX_NOISE:
        cleaned = cleaned[1:]
    return cleaned


def _looks_like_character(name: str, text: str) -> bool:
    if not name:
        return False
    pattern = re.compile(
        rf"{re.escape(name)}(?:低声|轻声|小声|大声|慢慢|忽然|突然|转身|抬头)?"
        r"(?:说|问|道|喊|叫|笑|哭|推|站|走|跑|看|望|把|想|发现|沉默|回答|递|拿|伸手|抬头)"
    )
    quote_pattern = re.compile(rf"[“\"][^”\"]+[”\"]\s*{re.escape(name)}(?:说|问|道|喊|回答)")
    return bool(pattern.search(text) or quote_pattern.search(text))


def _is_valid_name_candidate(name: str, text: str) -> bool:
    if not name or name in STOP_NAMES:
        return False
    if any(part in name for part in INVALID_NAME_PARTS):
        return False
    if len(name) < 2 or len(name) > 4:
        return False
    if name[-1] in NAME_ENDING_STOP_CHARS:
        return False
    if set(name) & PRONOUN_CHARS:
        return False
    if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", name):
        return False
    return _looks_like_character(name, text)


def _build_character_card(name: str, index: int, text: str = "") -> CharacterCard:
    key = _character_key(name, index)
    evidence = _character_evidence(name, text)
    return CharacterCard(
        character_id=key,
        name=name,
        aliases=[],
        role="主要角色" if index <= 3 else "配角",
        personality=_infer_personality(name, text),
        speech_style=_infer_speech_style(name, text),
        relationship_map={},
        secrets=_infer_secrets(name, text),
        visual_notes=_infer_visual_notes(name, text),
        do_not_do=["不要说出当前视角人物尚未知晓的信息。"],
        source_evidence=evidence,
    )


def _extract_events(scenes_by_chapter: dict[int, list[SourceScene]], character_names: list[str]) -> list[StoryEvent]:
    events: list[StoryEvent] = []
    order = 1
    for chapter_index in sorted(scenes_by_chapter):
        for scene in scenes_by_chapter[chapter_index]:
            for sentence in SENTENCE_RE.findall(scene.text):
                event_text = sentence.strip()
                if len(event_text) < 4:
                    continue
                participants = [name for name in character_names if name in event_text]
                if not participants:
                    continue
                hidden_meaning = _infer_hidden_meaning(event_text)
                events.append(
                    StoryEvent(
                        event_id=f"E{order:03d}",
                        order=order,
                        text=event_text,
                        participants=participants,
                        visible_to=participants,
                        chapter_index=chapter_index,
                        scene_index=scene.index,
                        hidden_meaning=hidden_meaning,
                        source_evidence=[event_text],
                    )
                )
                order += 1
    return events


def _infer_hidden_meaning(text: str) -> str:
    if "泛黄的纸" in text or "纸藏" in text or "藏到身后" in text:
        return "纸与旧案有关"
    if "录音笔" in text:
        return "录音笔可能保存关键证据"
    if "隐瞒" in text or "藏" in text:
        return "该动作暗示角色正在隐瞒信息"
    return ""


def _extract_clues(events: list[StoryEvent]) -> list[Clue]:
    clues: list[Clue] = []
    seen: set[str] = set()
    for event in events:
        for term in CLUE_TERMS:
            if term in event.text and term not in seen:
                seen.add(term)
                hidden = event.hidden_meaning or f"{term}的真实含义尚未揭露"
                clues.append(
                    Clue(
                        clue_id=f"C{len(clues) + 1:03d}",
                        clue_name=term,
                        first_appears_event_id=event.event_id,
                        hidden_meaning=hidden,
                        reveal_policy="do_not_reveal_before_reveal_scene",
                        source_evidence=[event.text],
                    )
                )
    return clues


def _build_story_bible(title: str, chapters: list[Chapter], events: list[StoryEvent]) -> StoryBible:
    chapter_titles = "、".join(chapter.title for chapter in chapters) or "未分章"
    main_plot = f"{title}：当前包含 {len(chapters)} 个章节（{chapter_titles}）和 {len(events)} 个可见剧情事件。"
    return StoryBible(
        title=title,
        main_plot=main_plot,
        core_conflict="MVP 根据事件和线索保守推断核心冲突，后续由 AI 分析补充。",
        themes=["悬疑", "角色视角", "信息差"],
        style_notes="视觉小说化时保留原文关键信息，使用旁白、对白和少量选项增强可玩性。",
        forbidden_changes=["不得提前揭露视角人物不知道的线索真相。"],
    )


def _character_key(name: str, index: int) -> str:
    known = {"林雨": "lin", "苏晚": "suwan", "陈默": "chenmo"}
    return known.get(name, f"char_{index}")


def _character_evidence(name: str, text: str) -> list[str]:
    evidence = []
    for sentence in SENTENCE_RE.findall(text):
        if name in sentence:
            evidence.append(sentence.strip())
        if len(evidence) >= 3:
            break
    return evidence


def _infer_personality(name: str, text: str) -> str:
    around = "。".join(_character_evidence(name, text))
    traits = []
    if any(term in around for term in ["沉默", "没有立刻", "低头", "犹豫"]):
        traits.append("谨慎")
    if any(term in around for term in ["问", "追", "看着", "发现"]):
        traits.append("敏感")
    if any(term in around for term in ["藏", "隐瞒", "避开"]):
        traits.append("克制")
    if any(term in around for term in ["帮", "递", "照顾"]):
        traits.append("体贴")
    return "、".join(dict.fromkeys(traits)) or "性格暂按原文保守处理"


def _infer_speech_style(name: str, text: str) -> str:
    around = "。".join(_character_evidence(name, text))
    if any(term in around for term in ["低声", "小声", "轻声"]):
        return "声音压低，话不多"
    if any(term in around for term in ["喊", "吼"]):
        return "情绪外放，说话直接"
    if "问" in around:
        return "提问直接，关注细节"
    return "贴近原文语气，避免突然转性"


def _infer_secrets(name: str, text: str) -> list[str]:
    around = "。".join(_character_evidence(name, text))
    secrets = []
    if any(term in around for term in ["藏", "隐瞒", "秘密"]):
        secrets.append("可能隐瞒了部分信息，未到揭露场景前不要说破。")
    return secrets


def _infer_visual_notes(name: str, text: str) -> dict:
    around = name + " " + "。".join(_character_evidence(name, text))
    age = "elder" if any(term in around for term in ["爷爷", "奶奶", "老人", "父亲", "母亲"]) else "young"
    style = _infer_visual_style(text)
    gender = _infer_gender(name, around)
    return {"age": age, "gender": gender, "style": style, "expressions": ["normal", "serious", "surprised"]}


def _infer_visual_style(text: str) -> str:
    anime_terms = ["二次元", "动漫", "动画", "异世界", "魔法", "勇者", "精灵", "轻小说", "galgame", "Galgame"]
    return "anime" if any(term in text for term in anime_terms) else "real"


def _infer_gender(name: str, around: str) -> str:
    if any(term in around for term in ["她", "女孩", "少女", "姑娘", "姐姐", "妹妹", "母亲", "妻子", "玲奈", "琴", "月", "花"]):
        return "female"
    if any(term in around for term in ["他", "男人", "男孩", "少年", "哥哥", "弟弟", "父亲", "丈夫"]):
        return "male"
    return "unknown"
