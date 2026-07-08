from __future__ import annotations

from typing import Any

from app.schemas.story import ConsistencyReport, POVKnowledgeState


def check_scene(scene: dict[str, Any], pov_state: POVKnowledgeState) -> ConsistencyReport:
    text = _scene_text(scene)
    issues: list[dict[str, Any]] = []

    for forbidden in pov_state.forbidden_reveals:
        if forbidden and forbidden in text:
            issues.append(
                {
                    "type": "premature_reveal",
                    "severity": "high",
                    "text": f"Scene reveals forbidden information: {forbidden}",
                    "suggestion": "Rewrite as suspicion, silence, evasive dialogue, or observable behavior.",
                }
            )

    score = 1.0 if not issues else max(0.0, 1.0 - 0.35 * len(issues))
    return ConsistencyReport(scene_id=scene.get("scene_id", ""), passed=not issues, score=score, issues=issues)


def _scene_text(scene: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in scene.get("blocks", []):
        if "text" in block:
            parts.append(str(block["text"]))
        for choice in block.get("choices", []):
            parts.append(str(choice.get("text", "")))
    return "\n".join(parts)
