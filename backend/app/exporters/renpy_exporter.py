from __future__ import annotations

from typing import Any


def export_scene_to_renpy(scene: dict[str, Any]) -> str:
    scene_id = scene["scene_id"]
    lines = [f"label {scene_id}:", ""]

    background = scene.get("background")
    if background:
        lines.append(f"    scene {background}")

    bgm = scene.get("bgm")
    if bgm:
        lines.append(f'    play music "{bgm}.ogg"')

    for block in scene.get("blocks", []):
        block_type = block.get("type")
        if block_type == "narration":
            lines.append(f'    narrator "{_escape_text(block["text"])}"')
        elif block_type == "dialogue":
            speaker = block.get("speaker_key") or block.get("speaker") or "narrator"
            lines.append(f'    {speaker} "{_escape_text(block["text"])}"')
        elif block_type == "choice":
            lines.extend(_render_choice(block))

    return "\n".join(lines).rstrip() + "\n"


def _render_choice(block: dict[str, Any]) -> list[str]:
    lines = ["", "    menu:"]
    for choice in block.get("choices", []):
        lines.append(f'        "{_escape_text(choice["text"])}":')
        for key, value in choice.get("effects", {}).items():
            lines.append(f"            {_render_effect(key, value)}")
        next_label = choice.get("next_label")
        if next_label:
            lines.append(f"            jump {next_label}")
    return lines


def _render_effect(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return f"$ {key} = {value}"
    if isinstance(value, int | float):
        operator = "+=" if value >= 0 else "-="
        return f"$ {key} {operator} {abs(value)}"
    return f'$ {key} = "{_escape_text(str(value))}"'


def _escape_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')
