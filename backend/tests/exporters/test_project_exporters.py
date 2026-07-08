import json
import unittest

from app.exporters.json_exporter import export_project_to_json
from app.exporters.markdown_exporter import export_project_to_markdown
from app.services.novel_pipeline import run_pipeline


class ProjectExportersTest(unittest.TestCase):
    def test_exports_pipeline_result_to_markdown_and_json(self):
        result = run_pipeline(
            "雨夜旧楼",
            "第一章 雨夜\n林雨推开门。\n苏晚把纸藏到身后。\n“别问。”苏晚说。",
            "林雨",
        )

        markdown = export_project_to_markdown(result)
        payload = json.loads(export_project_to_json(result))

        self.assertIn("# 雨夜旧楼", markdown)
        self.assertIn("## Characters", markdown)
        self.assertEqual(payload["title"], "雨夜旧楼")
        self.assertIn("adaptation_scenes", payload)
