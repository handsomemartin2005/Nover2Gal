from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.adaptation.deepseek_scene_adapter import ChatClient, adapt_scene_with_deepseek
from app.adaptation.script_generator import generate_scene_ir
from app.analysis.deepseek_story_analyzer import refine_analysis_with_deepseek
from app.analysis.simple_analyzer import analyze_story
from app.consistency.checker import check_scene
from app.core.config import Settings
from app.exporters.markdown_exporter import export_project_to_markdown
from app.exporters.renpy_exporter import export_scene_to_renpy
from app.llm.deepseek_client import DeepSeekClient
from app.parser.chapter_splitter import Chapter, split_chapters
from app.parser.chunker import TextChunk, chunk_text
from app.parser.scene_splitter import SourceScene, split_scenes
from app.pov.pov_engine import build_pov_knowledge
from app.rag.retriever import retrieve_context
from app.schemas.story import PipelineResult


def run_pipeline(
    title: str,
    text: str,
    pov_character: str,
    settings: Settings | None = None,
    llm_client: ChatClient | None = None,
    max_scenes: int | None = None,
    llm_model: str | None = None,
) -> PipelineResult:
    settings = settings or Settings.from_env()
    if llm_model:
        settings = replace(settings, llm_model=_normalize_llm_model(llm_model))
    chapters = split_chapters(text)
    scenes_by_chapter: dict[int, list[SourceScene]] = {
        chapter.index: split_scenes(chapter.text, min_scene_chars=40) for chapter in chapters
    }
    source_scenes = [scene for chapter_scenes in scenes_by_chapter.values() for scene in chapter_scenes]
    source_chunks = _chunk_scenes(chapters, scenes_by_chapter, settings)
    client = llm_client or (DeepSeekClient(settings) if settings.llm_api_key else None)
    analysis = analyze_story(title, chapters, scenes_by_chapter)
    analysis = _refine_analysis_with_adapter(title, text, analysis, settings, client)
    pov_character = _choose_pov_character(pov_character, analysis)
    pov_states = build_pov_knowledge("project-1", pov_character, analysis.events, analysis.clues)

    adaptation_scenes: list[dict] = []
    reports = []
    state = pov_states[0] if pov_states else _empty_state(pov_character)
    adapted_count = 0
    scene_limit = _normalize_max_scenes(max_scenes)
    for chapter in chapters:
        for scene in scenes_by_chapter.get(chapter.index, []):
            if scene_limit is not None and adapted_count >= scene_limit:
                break
            state = _state_for_scene(pov_states, scene.index, default=state)
            titled_scene = _scene_with_chapter_title(scene, chapter)
            scene_ir = _generate_scene_with_adapter(
                scene=titled_scene,
                analysis=analysis,
                state=state,
                pov_character=pov_character,
                chapter_index=chapter.index,
                source_chunks=source_chunks,
                settings=settings,
                client=client,
            )
            report = check_scene(scene_ir, state)
            adaptation_scenes.append(scene_ir)
            reports.append(report)
            adapted_count += 1
        if scene_limit is not None and adapted_count >= scene_limit:
            break

    partial = PipelineResult(
        title=title,
        pov_character=pov_character,
        chapters=chapters,
        source_scenes=source_scenes,
        source_chunks=source_chunks,
        analysis=analysis,
        pov_states=pov_states,
        adaptation_scenes=adaptation_scenes,
        consistency_reports=reports,
        exports={},
    )
    renpy = "\n".join(export_scene_to_renpy(scene) for scene in adaptation_scenes)
    markdown = export_project_to_markdown(partial)
    return PipelineResult(
        title=title,
        pov_character=pov_character,
        chapters=chapters,
        source_scenes=source_scenes,
        source_chunks=source_chunks,
        analysis=analysis,
        pov_states=pov_states,
        adaptation_scenes=adaptation_scenes,
        consistency_reports=reports,
        exports={"markdown": markdown, "renpy": renpy},
    )


def _refine_analysis_with_adapter(
    title: str,
    text: str,
    analysis,
    settings: Settings,
    client: ChatClient | None,
):
    if not client or not settings.llm_api_key:
        return analysis
    try:
        return refine_analysis_with_deepseek(title=title, text=text, base_analysis=analysis, client=client)
    except Exception:
        return analysis


def _generate_scene_with_adapter(
    scene: SourceScene,
    analysis,
    state,
    pov_character: str,
    chapter_index: int,
    source_chunks: list[TextChunk],
    settings: Settings,
    client: ChatClient | None,
) -> dict[str, Any]:
    if client and settings.llm_api_key:
        rag_context = retrieve_context(scene.text, source_chunks, max_chunks=settings.max_retrieved_chunks)
        try:
            return adapt_scene_with_deepseek(
                source_scene=scene,
                analysis=analysis,
                pov_state=state,
                chapter_index=chapter_index,
                rag_context=rag_context,
                client=client,
                pov_character=pov_character,
            )
        except Exception as exc:
            fallback = generate_scene_ir(scene, analysis, state, chapter_index, pov_character=pov_character)
            fallback["adapter"] = "rules_fallback"
            fallback["adapter_error"] = str(exc)
            fallback["rag_chunk_indexes"] = [snippet.chunk_index for snippet in rag_context]
            return fallback

    scene_ir = generate_scene_ir(scene, analysis, state, chapter_index, pov_character=pov_character)
    scene_ir["adapter"] = "rules"
    scene_ir["rag_chunk_indexes"] = []
    return scene_ir


def _chunk_scenes(
    chapters: list[Chapter],
    scenes_by_chapter: dict[int, list[SourceScene]],
    settings: Settings,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for chapter in chapters:
        for scene in scenes_by_chapter.get(chapter.index, []):
            for chunk in chunk_text(
                scene.text,
                max_chars=settings.max_chunk_chars,
                overlap_chars=settings.chunk_overlap_chars,
            ):
                chunks.append(chunk)
    return chunks


def _normalize_max_scenes(value: int | None) -> int | None:
    if value is None or value <= 0:
        return None
    return value


def _scene_with_chapter_title(scene: SourceScene, chapter: Chapter) -> SourceScene:
    chapter_title = (chapter.title or "").strip()
    if not chapter_title or scene.title.startswith(chapter_title):
        return scene
    return replace(scene, title=f"{chapter_title} · {scene.title}")


def _choose_pov_character(value: str, analysis) -> str:
    requested = value.strip()
    if requested:
        character_names = {character.name for character in analysis.characters}
        if not character_names or requested in character_names:
            return requested
    if analysis.characters:
        non_supporting = [
            character for character in analysis.characters if "配角" not in str(character.role)
        ]
        return (non_supporting[0] if non_supporting else analysis.characters[0]).name
    return requested or "我"


def _normalize_llm_model(value: str) -> str:
    allowed = {"deepseek-v4-pro", "deepseek-v4-flash"}
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"Unsupported LLM model: {value}")
    return normalized


def _state_for_scene(states, scene_index: int, default):
    if not states:
        return default
    index = min(max(scene_index - 1, 0), len(states) - 1)
    return states[index]


def _empty_state(pov_character: str):
    from app.schemas.story import POVKnowledgeState

    return POVKnowledgeState(
        project_id="project-1",
        after_event_order=0,
        known_facts=[],
        unknown_facts=[],
        suspected_facts=[f"{pov_character}当前只知道自己亲历或观察到的信息。"],
        false_beliefs=[],
        forbidden_reveals=[],
    )
