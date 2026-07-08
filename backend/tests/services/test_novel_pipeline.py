import unittest

from app.core.config import Settings
from app.services.novel_pipeline import run_pipeline


SAMPLE_TEXT = """第一章 雨夜

林雨推开旧教学楼的门时，雨声正从身后涌来。
三楼的教室亮着一盏灯。
苏晚站在讲台旁，手里攥着一张泛黄的纸。

“你为什么在这里？”林雨问。

苏晚把纸藏到身后。
“这句话应该我问你。”苏晚说。
"""


class NovelPipelineTest(unittest.TestCase):
    def test_limits_adaptation_to_first_n_scenes(self):
        text = (
            "第一章 雨夜\n"
            "林雨停在门口，苏晚把纸条藏到身后。雨声压住了走廊里的脚步声，他还是听见门缝后有人移动，便伸手按住门把。\n\n"
            "林雨走进教室，苏晚退到讲台旁边。那张泛黄的纸被她压在书本下面，只露出一个角，像是在等他主动开口。\n\n"
            "走廊尽头的灯忽然暗了一下。林雨回头看去，门外已经没有人影，只剩下湿漉漉的脚印，一直延伸到楼梯口。"
        )

        result = run_pipeline("雨夜旧楼", text, "林雨", settings=Settings.from_env({}), max_scenes=1)

        self.assertGreater(len(result.source_scenes), 1)
        self.assertEqual(len(result.adaptation_scenes), 1)
        self.assertEqual(len(result.consistency_reports), 1)
        self.assertIn("label common_001_001:", result.exports["renpy"])

    def test_runs_end_to_end_backend_mvp_flow(self):
        result = run_pipeline("雨夜旧楼", SAMPLE_TEXT, "林雨", settings=Settings.from_env({}))

        self.assertEqual(result.title, "雨夜旧楼")
        self.assertEqual(len(result.chapters), 1)
        self.assertGreaterEqual(len(result.source_scenes), 1)
        self.assertGreaterEqual(len(result.source_chunks), 1)
        self.assertIn("林雨", [character.name for character in result.analysis.characters])
        self.assertIn("苏晚", [character.name for character in result.analysis.characters])
        self.assertGreaterEqual(len(result.pov_states), 1)
        self.assertGreaterEqual(len(result.adaptation_scenes), 1)
        self.assertTrue(result.consistency_reports[0].passed)

        first_scene = result.adaptation_scenes[0]
        self.assertEqual(first_scene["scene_id"], "common_001_001")
        self.assertIn("第一章 雨夜", first_scene["title"])
        self.assertTrue(any(block["type"] == "choice" for block in first_scene["blocks"]))
        self.assertIn("renpy", result.exports)
        self.assertIn("label common_001_001:", result.exports["renpy"])

    def test_auto_selects_pov_when_input_is_blank_or_not_a_character(self):
        result = run_pipeline("雨夜旧楼", SAMPLE_TEXT, "作者名", settings=Settings.from_env({}), max_scenes=1)

        self.assertIn(result.pov_character, [character.name for character in result.analysis.characters])
        self.assertNotEqual(result.pov_character, "作者名")

    def test_uses_deepseek_rag_adapter_when_api_key_exists(self):
        client = FakeDeepSeekClient(
            [
                """
                {
                  "characters": [
                    {"name": "林雨", "role": "主角", "personality": "谨慎", "speech_style": "直接"},
                    {"name": "苏晚", "role": "主要角色", "personality": "克制", "speech_style": "低声"}
                  ],
                  "not_characters": ["低声", "纸条"]
                }
                """,
                """
                {
                  "background": "bg_ai_library",
                  "bgm": "bgm_ai_tension",
                  "blocks": [
                    {"type": "narration", "text": "AI改编的旁白。"},
                    {"type": "dialogue", "speaker": "苏晚", "text": "AI改编的对白。"},
                    {"type": "choice", "choices": [{"text": "询问纸条", "effects": {"flag_note": true}, "next_label": "ask_note"}]}
                  ],
                  "required_assets": [{"type": "background", "key": "bg_ai_library", "description": "AI布景"}]
                }
                """,
            ]
        )

        result = run_pipeline(
            "雨夜旧楼",
            SAMPLE_TEXT,
            "林雨",
            settings=Settings.from_env({"DEEPSEEK_API": "test-key"}),
            llm_client=client,
        )

        first_scene = result.adaptation_scenes[0]
        self.assertEqual(first_scene["adapter"], "deepseek")
        self.assertEqual(first_scene["background"], "bg_ai_library")
        self.assertEqual(first_scene["blocks"][0]["text"], "AI改编的旁白。")
        self.assertIn("rag_chunk_indexes", first_scene)
        self.assertGreaterEqual(len(first_scene["rag_chunk_indexes"]), 1)
        self.assertEqual([character.name for character in result.analysis.characters], ["林雨", "苏晚"])
        self.assertEqual(client.call_count, 2)

    def test_falls_back_to_rule_adapter_when_deepseek_fails(self):
        result = run_pipeline(
            "雨夜旧楼",
            SAMPLE_TEXT,
            "林雨",
            settings=Settings.from_env({"DEEPSEEK_API": "test-key"}),
            llm_client=FailingDeepSeekClient(),
        )

        first_scene = result.adaptation_scenes[0]
        self.assertEqual(first_scene["adapter"], "rules_fallback")
        self.assertIn("adapter_error", first_scene)
        self.assertGreaterEqual(len(first_scene["blocks"]), 1)


class FakeDeepSeekClient:
    def __init__(self, contents: list[str]):
        self.contents = contents
        self.call_count = 0
        self.messages = []

    def chat(self, messages, json_output=False):
        index = self.call_count
        self.call_count += 1
        self.messages.append(messages)
        self.json_output = json_output
        return self.contents[index]


class FailingDeepSeekClient:
    def chat(self, messages, json_output=False):
        raise RuntimeError("deepseek unavailable")
