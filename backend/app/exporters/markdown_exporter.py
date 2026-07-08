from __future__ import annotations

from app.schemas.story import PipelineResult


def export_project_to_markdown(result: PipelineResult) -> str:
    lines = [
        f"# {result.title}",
        "",
        f"POV: {result.pov_character}",
        "",
        "## Story Bible",
        "",
        result.analysis.story_bible.main_plot,
        "",
        "## Characters",
        "",
    ]
    for character in result.analysis.characters:
        lines.append(f"- {character.name}: {character.role}")

    lines.extend(["", "## Galgame Scenes", ""])
    for scene in result.adaptation_scenes:
        lines.append(f"### {scene['scene_id']} {scene.get('title', '')}".strip())
        for block in scene.get("blocks", []):
            if block["type"] == "narration":
                lines.append(block["text"])
            elif block["type"] == "dialogue":
                speaker = block.get("speaker", block.get("speaker_key", "角色"))
                lines.append(f"{speaker}: {block['text']}")
            elif block["type"] == "choice":
                lines.append("[choice]")
                for choice in block.get("choices", []):
                    lines.append(f"- {choice['text']} -> {choice.get('next_label', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
