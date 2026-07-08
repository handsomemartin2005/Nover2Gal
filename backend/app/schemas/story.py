from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CharacterCard:
    character_id: str
    name: str
    aliases: list[str]
    role: str
    personality: str
    speech_style: str
    relationship_map: dict[str, str]
    secrets: list[str]
    visual_notes: dict[str, Any]
    do_not_do: list[str]
    source_evidence: list[str]


@dataclass(frozen=True)
class StoryEvent:
    event_id: str
    order: int
    text: str
    participants: list[str]
    visible_to: list[str]
    chapter_index: int | None = None
    scene_index: int | None = None
    location: str = ""
    cause: str = ""
    effect: str = ""
    hidden_meaning: str = ""
    source_evidence: list[str] | None = None


@dataclass(frozen=True)
class Clue:
    clue_id: str
    clue_name: str
    first_appears_event_id: str
    hidden_meaning: str
    reveal_policy: str
    clue_type: str = "item"
    must_keep: bool = True
    source_evidence: list[str] | None = None


@dataclass(frozen=True)
class StoryBible:
    title: str
    main_plot: str
    core_conflict: str
    themes: list[str]
    style_notes: str
    forbidden_changes: list[str]


@dataclass(frozen=True)
class StoryAnalysis:
    title: str
    characters: list[CharacterCard]
    events: list[StoryEvent]
    clues: list[Clue]
    story_bible: StoryBible


@dataclass(frozen=True)
class POVKnowledgeState:
    project_id: str
    after_event_order: int
    known_facts: list[str]
    unknown_facts: list[str]
    suspected_facts: list[str]
    false_beliefs: list[str]
    forbidden_reveals: list[str]


@dataclass(frozen=True)
class ConsistencyReport:
    scene_id: str
    passed: bool
    score: float
    issues: list[dict[str, Any]]


@dataclass(frozen=True)
class PipelineResult:
    title: str
    pov_character: str
    chapters: list[Any]
    source_scenes: list[Any]
    source_chunks: list[Any]
    analysis: StoryAnalysis
    pov_states: list[POVKnowledgeState]
    adaptation_scenes: list[dict[str, Any]]
    consistency_reports: list[ConsistencyReport]
    exports: dict[str, str]


def to_plain(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_plain(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain(item) for key, item in value.items()}
    return value


def to_api_payload(result: PipelineResult) -> dict[str, Any]:
    return {
        "title": result.title,
        "pov_character": result.pov_character,
        "stats": {
            "chapters": len(result.chapters),
            "source_scenes": len(result.source_scenes),
            "source_chunks": len(result.source_chunks),
            "adaptation_scenes": len(result.adaptation_scenes),
            "characters": len(result.analysis.characters),
            "events": len(result.analysis.events),
            "clues": len(result.analysis.clues),
        },
        "chapters": [
            {
                "index": chapter.index,
                "title": chapter.title,
                "char_count": len(chapter.text),
            }
            for chapter in result.chapters
        ],
        "source_scenes": [
            {
                "index": scene.index,
                "title": scene.title,
                "char_count": len(scene.text),
            }
            for scene in result.source_scenes
        ],
        "source_chunks": [
            {
                "index": chunk.index,
                "char_count": len(chunk.text),
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
            }
            for chunk in result.source_chunks
        ],
        "analysis": {
            "title": result.analysis.title,
            "characters": to_plain(result.analysis.characters),
            "story_bible": to_plain(result.analysis.story_bible),
            "events_count": len(result.analysis.events),
            "clues_count": len(result.analysis.clues),
        },
        "pov_states_count": len(result.pov_states),
        "adaptation_scenes": to_plain(result.adaptation_scenes),
        "consistency_reports": to_plain(result.consistency_reports),
        "exports": result.exports,
    }
