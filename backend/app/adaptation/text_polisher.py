from __future__ import annotations

import re


AIISH_REPLACEMENTS = {
    "你沿着原书线索继续追问": "你顺着刚才的话问下去",
    "对方的反应把注意力拉回当前疑点": "她停了一下，还是看着你",
    "剧情继续进入原书的下一个关键行动": "事情继续往下走",
    "观察没有改变核心事实": "你这一停，没有改变结果",
    "获得一段额外缓冲": "气氛缓了一点",
    "暂时偏离原书行动": "你换了个做法",
    "贴合主线": "照原来的事走",
    "偏离后回收": "绕了一下又回到眼前的事",
    "核心事实": "这件事",
    "关键行动": "下一步",
    "原书": "之前",
    "主线": "正事",
    "收束": "停住",
    "回收": "带回",
    "偏离": "绕开",
    "并行": "同时",
}

FILLER_PATTERNS = [
    r"^这一步完成后[，,]?",
    r"^接下来[，,]?",
    r"^总之[，,]?",
    r"^于是[，,]?\s*于是[，,]?",
]


def polish_game_text(text: str) -> str:
    polished = re.sub(r"\s+", " ", text).strip()
    polished = _strip_orphan_quote_marks(polished)
    for pattern in FILLER_PATTERNS:
        polished = re.sub(pattern, "", polished).strip()
    for source, target in AIISH_REPLACEMENTS.items():
        polished = polished.replace(source, target)
    polished = _fix_punctuation(polished)
    return polished


def polish_choice_text(text: str) -> str:
    polished = polish_game_text(text)
    polished = re.sub(r"\s*[·・|｜/\\-]\s*(并行|反向|主线|偏离后回收|偏离|回收|收束)\s*", " ", polished)
    return re.sub(r"\s+", " ", polished).strip(" ：:，,。")


def _fix_punctuation(text: str) -> str:
    text = re.sub(r"([。！？]){2,}", r"\1", text)
    text = re.sub(r"([，,]){2,}", "，", text)
    text = text.replace(" ,", "，").replace(" .", "。")
    return text.strip()


def _strip_orphan_quote_marks(text: str) -> str:
    stripped = text.strip()
    if re.fullmatch(r"[「」『』“”\"'，,。！？!?、；;：:\s]+", stripped):
        return ""
    if stripped.startswith(("」", "』", "”")) and not any(mark in stripped[1:] for mark in ("「", "『", "“")):
        stripped = stripped[1:].lstrip()
    if stripped.endswith(("「", "『", "“")) and not any(mark in stripped[:-1] for mark in ("」", "』", "”")):
        stripped = stripped[:-1].rstrip()
    return stripped
