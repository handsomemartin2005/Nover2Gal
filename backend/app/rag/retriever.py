from __future__ import annotations

import re
from dataclasses import dataclass

from app.parser.chunker import TextChunk


@dataclass(frozen=True)
class RetrievedSnippet:
    chunk_index: int
    text: str
    score: float


def retrieve_context(query: str, chunks: list[TextChunk], max_chunks: int) -> list[RetrievedSnippet]:
    if max_chunks < 1:
        raise ValueError("max_chunks must be positive")

    query_terms = _tokenize(query)
    if not query_terms:
        return []

    scored: list[RetrievedSnippet] = []
    for chunk in chunks:
        score = _score(query_terms, _tokenize(chunk.text))
        if score > 0:
            scored.append(RetrievedSnippet(chunk_index=chunk.index, text=chunk.text, score=score))

    return sorted(scored, key=lambda item: (-item.score, item.chunk_index))[:max_chunks]


def _score(query_terms: set[str], chunk_terms: set[str]) -> float:
    overlap = query_terms & chunk_terms
    if not overlap:
        return 0.0
    return len(overlap) / max(len(query_terms), 1)


def _tokenize(text: str) -> set[str]:
    normalized = text.strip().lower()
    if not normalized:
        return set()

    terms = set(re.findall(r"[a-z0-9_]+", normalized))
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", normalized)
    terms.update(cjk_chars)
    terms.update("".join(cjk_chars[index : index + 2]) for index in range(max(len(cjk_chars) - 1, 0)))
    return {term for term in terms if term}
