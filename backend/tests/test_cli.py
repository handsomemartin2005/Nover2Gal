import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.cli import run_cli
from tests.helpers import write_sample_epub


class CLITest(unittest.TestCase):
    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_cli_writes_markdown_json_and_renpy_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "sample.txt"
            output_dir = root / "exports"
            input_path.write_text(
                "第一章 雨夜\n林雨推开门。\n苏晚把纸藏到身后。\n“别问。”苏晚说。",
                encoding="utf-8",
            )

            exit_code = run_cli([
                str(input_path),
                "--title",
                "雨夜旧楼",
                "--pov",
                "林雨",
                "--out",
                str(output_dir),
            ])

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "script.md").exists())
            self.assertTrue((output_dir / "project.json").exists())
            self.assertTrue((output_dir / "game" / "script.rpy").exists())

    @patch.dict("os.environ", {"DEEPSEEK_API": "", "LLM_API_KEY": ""})
    def test_cli_accepts_epub_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "sample.epub"
            output_dir = root / "exports"
            write_sample_epub(input_path)

            exit_code = run_cli([
                str(input_path),
                "--pov",
                "林雨",
                "--out",
                str(output_dir),
            ])

            self.assertEqual(exit_code, 0)
            self.assertIn("label common_001_001:", (output_dir / "game" / "script.rpy").read_text(encoding="utf-8"))
