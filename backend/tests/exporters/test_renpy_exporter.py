import unittest

from app.exporters.renpy_exporter import export_scene_to_renpy


class RenpyExporterTest(unittest.TestCase):
    def test_exports_dialogue_and_choice_blocks(self):
        scene = {
            "scene_id": "common_001_001",
            "background": "bg_old_school_night_rain",
            "bgm": "bgm_suspense_low",
            "blocks": [
                {"type": "narration", "text": "雨声还没有停。"},
                {"type": "dialogue", "speaker_key": "lin", "text": "你为什么在这里？"},
                {
                    "type": "choice",
                    "choices": [
                        {
                            "text": "继续追问她",
                            "effects": {"affection_suwan": -1, "flag_questioned_suwan": True},
                            "next_label": "common_001_001_ask",
                        }
                    ],
                },
            ],
        }

        script = export_scene_to_renpy(scene)

        self.assertIn("label common_001_001:", script)
        self.assertIn("scene bg_old_school_night_rain", script)
        self.assertIn('play music "bgm_suspense_low.ogg"', script)
        self.assertIn('narrator "雨声还没有停。"', script)
        self.assertIn('lin "你为什么在这里？"', script)
        self.assertIn('"继续追问她":', script)
        self.assertIn("$ affection_suwan -= 1", script)
        self.assertIn("$ flag_questioned_suwan = True", script)
        self.assertIn("jump common_001_001_ask", script)
