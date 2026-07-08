from __future__ import annotations

import json

from app.schemas.story import PipelineResult, to_plain


def export_project_to_json(result: PipelineResult) -> str:
    return json.dumps(to_plain(result), ensure_ascii=False, indent=2)
