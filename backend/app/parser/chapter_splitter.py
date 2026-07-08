from __future__ import annotations

import re
from dataclasses import dataclass


CHAPTER_HEADING_RE = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百千万两0-9]+[章节卷回].*|chapter\s+\d+.*|CHAPTER\s+\d+.*)\s*$",
    re.MULTILINE,
)
TOC_LIKE_BODY_MAX_CHARS = 12
TOC_LIKE_RUN_MIN_CHAPTERS = 5
AUTO_CHAPTER_TARGET_CHARS = 4500
AUTO_CHAPTER_TRANSITIONS = (
    "第二天",
    "第三天",
    "清晨",
    "早晨",
    "上午",
    "中午",
    "午休",
    "下午",
    "傍晚",
    "晚上",
    "夜里",
    "后来",
    "几天后",
    "回到",
    "来到",
    "离开",
)


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    text: str
    start_offset: int
    end_offset: int


def split_chapters(text: str) -> list[Chapter]:
    normalized = text.strip()
    if not normalized:
        return []

    matches = list(CHAPTER_HEADING_RE.finditer(normalized))
    if not matches:
        return _split_unheaded_long_text(normalized)

    chapters: list[Chapter] = []
    for index, match in enumerate(matches, start=1):
        content_start = match.end()
        content_end = matches[index].start() if index < len(matches) else len(normalized)
        body = normalized[content_start:content_end].strip()
        chapters.append(
            Chapter(
                index=index,
                title=match.group(0).strip(),
                text=body,
                start_offset=content_start,
                end_offset=content_end,
            )
        )
    return _renumber_chapters(_drop_toc_like_heading_runs(chapters))


def _drop_toc_like_heading_runs(chapters: list[Chapter]) -> list[Chapter]:
    cleaned: list[Chapter] = []
    index = 0
    while index < len(chapters):
        if not _is_toc_like_chapter(chapters[index]):
            cleaned.append(chapters[index])
            index += 1
            continue

        run_start = index
        while index < len(chapters) and _is_toc_like_chapter(chapters[index]):
            index += 1

        run = chapters[run_start:index]
        if len(run) >= TOC_LIKE_RUN_MIN_CHAPTERS and index < len(chapters):
            continue
        cleaned.extend(run)
    return cleaned


def _is_toc_like_chapter(chapter: Chapter) -> bool:
    compact_body = "".join(chapter.text.split())
    return len(compact_body) <= TOC_LIKE_BODY_MAX_CHARS


def _renumber_chapters(chapters: list[Chapter]) -> list[Chapter]:
    return [
        Chapter(
            index=index,
            title=chapter.title,
            text=chapter.text,
            start_offset=chapter.start_offset,
            end_offset=chapter.end_offset,
        )
        for index, chapter in enumerate(chapters, start=1)
    ]


def _split_unheaded_long_text(text: str) -> list[Chapter]:
    if len(text) <= AUTO_CHAPTER_TARGET_CHARS * 2:
        return [Chapter(index=1, title="Chapter 1", text=text, start_offset=0, end_offset=len(text))]

    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", text) if paragraph.strip()]
    chapters: list[Chapter] = []
    current: list[str] = []
    current_start = 0
    search_from = 0
    current_len = 0
    for paragraph in paragraphs:
        paragraph_start = text.find(paragraph, search_from)
        if paragraph_start < 0:
            paragraph_start = search_from
        starts_new = current and current_len >= AUTO_CHAPTER_TARGET_CHARS and _starts_auto_chapter(paragraph)
        too_long = current and current_len >= AUTO_CHAPTER_TARGET_CHARS * 1.45
        if starts_new or too_long:
            body = "\n\n".join(current).strip()
            chapters.append(
                Chapter(
                    index=len(chapters) + 1,
                    title=f"自动章节 {len(chapters) + 1}",
                    text=body,
                    start_offset=current_start,
                    end_offset=current_start + len(body),
                )
            )
            current = []
            current_start = paragraph_start
            current_len = 0
        if not current:
            current_start = paragraph_start
        current.append(paragraph)
        current_len += len(paragraph)
        search_from = paragraph_start + len(paragraph)

    if current:
        body = "\n\n".join(current).strip()
        chapters.append(
            Chapter(
                index=len(chapters) + 1,
                title=f"自动章节 {len(chapters) + 1}",
                text=body,
                start_offset=current_start,
                end_offset=current_start + len(body),
            )
        )
    return chapters or [Chapter(index=1, title="Chapter 1", text=text, start_offset=0, end_offset=len(text))]


def _starts_auto_chapter(text: str) -> bool:
    stripped = text.lstrip(" ，。；;“\"")
    return any(stripped.startswith(term) for term in AUTO_CHAPTER_TRANSITIONS)
