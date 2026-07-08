from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    start_offset: int
    end_offset: int


def chunk_text(text: str, max_chars: int = 1500, overlap_chars: int = 200) -> list[TextChunk]:
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must not be negative")
    if overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be smaller than max_chars")

    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[TextChunk] = []
    start = 0
    step = max_chars - overlap_chars
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        chunks.append(TextChunk(index=len(chunks) + 1, text=normalized[start:end], start_offset=start, end_offset=end))
        if end == len(normalized):
            break
        start += step
    return chunks
