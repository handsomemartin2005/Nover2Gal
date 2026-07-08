import json
import unittest

from app.adaptation.deepseek_scene_adapter import adapt_scene_with_deepseek
from app.parser.scene_splitter import SourceScene
from app.rag.retriever import RetrievedSnippet
from app.schemas.story import CharacterCard, POVKnowledgeState, StoryAnalysis, StoryBible


class FakeDeepSeekClient:
    def __init__(self, content: dict):
        self.content = content
        self.messages = []

    def chat(self, messages, json_output=False):
        self.messages = messages
        self.json_output = json_output
        return json.dumps(self.content, ensure_ascii=False)


class DeepSeekSceneAdapterTest(unittest.TestCase):
    def test_splits_long_ai_text_into_playable_lines(self):
        long_text = (
            "林雨把门推开，屋里的灯光落在桌面上。"
            "苏晚站在椅子旁边，没有立刻说话。"
            "窗外的雨声压低了两个人之间的呼吸。"
            "他看见桌角放着一只旧杯子，杯沿还留着水痕。"
            "这不是适合一次塞进游戏窗口的长段落。"
        )
        client = FakeDeepSeekClient(
            {
                "background": "bg_home_living",
                "bgm": "bgm_daily",
                "blocks": [{"type": "narration", "text": long_text}],
                "required_assets": [],
            }
        )

        scene_ir = adapt_scene_with_deepseek(
            source_scene=SourceScene(index=1, title="Scene 1", text=long_text, start_offset=0, end_offset=len(long_text)),
            analysis=_analysis(),
            pov_state=_pov_state(),
            chapter_index=1,
            rag_context=[],
            client=client,
        )

        narration_blocks = [block for block in scene_ir["blocks"] if block["type"] == "narration"]
        self.assertGreater(len(narration_blocks), 1)
        self.assertLessEqual(len(narration_blocks), 5)
        self.assertTrue(all(len(block["text"]) <= 56 for block in narration_blocks))

    def test_adapts_scene_ir_from_deepseek_json_with_rag_context(self):
        client = FakeDeepSeekClient(
            {
                "background": "bg_library_night",
                "bgm": "bgm_suspense_low",
                "blocks": [
                    {"type": "narration", "text": "林雨看见登记册里夹着旧钥匙。"},
                    {"type": "dialogue", "speaker": "苏晚", "text": "今晚不要相信任何人。"},
                    {
                        "type": "choice",
                        "choice_mode": "opposed",
                        "choices": [
                            {
                                "text": "追问钥匙",
                                "route": "mainline",
                                "branch_text": "林雨追问钥匙，苏晚被迫说出登记册的线索。",
                                "converge_text": "两人都看向登记册，回到寻找旧钥匙的主线。",
                                "effects": {"flag_key": True},
                                "next_label": "ask_key",
                            },
                            {
                                "text": "先藏起登记册",
                                "route": "divergent",
                                "branch_text": "林雨临时把登记册藏到书架后，避开门外脚步。",
                                "converge_text": "脚步声远去后，他仍然拿回登记册，继续追查旧钥匙。",
                                "effects": {"flag_hide_book": True},
                                "next_label": "hide_book",
                            },
                        ],
                    },
                ],
                "required_assets": [
                    {"type": "background", "key": "bg_library_night", "description": "夜晚图书馆"}
                ],
            }
        )
        scene = SourceScene(index=1, title="Scene 1", text="林雨看见纸角上写着自己的名字。", start_offset=0, end_offset=15)
        snippets = [RetrievedSnippet(chunk_index=2, text="苏晚把旧钥匙藏进图书馆登记册。", score=0.8)]

        scene_ir = adapt_scene_with_deepseek(
            source_scene=scene,
            analysis=_analysis(),
            pov_state=_pov_state(),
            chapter_index=3,
            rag_context=snippets,
            client=client,
        )

        self.assertEqual(scene_ir["scene_id"], "common_003_001")
        self.assertEqual(scene_ir["adapter"], "deepseek")
        self.assertEqual(scene_ir["background"], "bg_library_night")
        self.assertEqual(scene_ir["blocks"][1]["speaker"], "苏晚")
        self.assertEqual(scene_ir["blocks"][2]["choices"][0]["next_label"], "ask_key")
        self.assertEqual(scene_ir["blocks"][2]["choice_mode"], "opposed")
        self.assertEqual(scene_ir["blocks"][2]["choices"][0]["route"], "mainline")
        self.assertEqual(scene_ir["blocks"][2]["choices"][1]["route"], "divergent")
        self.assertIn("回到寻找旧钥匙", scene_ir["blocks"][2]["choices"][0]["converge_text"])
        self.assertIn("继续追查旧钥匙", scene_ir["blocks"][2]["choices"][1]["converge_text"])
        self.assertEqual(scene_ir["rag_chunk_indexes"], [2])
        self.assertTrue(client.json_output)
        self.assertIn("旧钥匙", client.messages[1]["content"])

    def test_adds_fallback_choices_when_deepseek_omits_choice_block(self):
        client = FakeDeepSeekClient(
            {
                "background": "bg_library_night",
                "bgm": "bgm_suspense_low",
                "blocks": [{"type": "narration", "text": "林雨停在门口。"}],
                "required_assets": [],
            }
        )

        scene_ir = adapt_scene_with_deepseek(
            source_scene=SourceScene(index=2, title="Scene 2", text="林雨停在门口。", start_offset=0, end_offset=7),
            analysis=_analysis(),
            pov_state=_pov_state(),
            chapter_index=1,
            rag_context=[],
            client=client,
        )

        choice_blocks = [block for block in scene_ir["blocks"] if block["type"] == "choice"]
        self.assertEqual(len(choice_blocks), 1)
        self.assertEqual(choice_blocks[0]["choice_mode"], "opposed")
        self.assertEqual([choice["route"] for choice in choice_blocks[0]["choices"]], ["mainline", "divergent"])
        self.assertTrue(choice_blocks[0]["choices"][1]["converge_text"])
        choice_text = "\n".join(
            str(choice.get(field, ""))
            for choice in choice_blocks[0]["choices"]
            for field in ("text", "branch_text", "converge_text")
        )
        for banned in ["原书", "主线", "核心事实", "关键行动", "暂时观察"]:
            self.assertNotIn(banned, choice_text)
        self.assertIn("门", choice_text)

    def test_cleans_ai_choice_route_labels_from_player_text(self):
        client = FakeDeepSeekClient(
            {
                "background": "bg_restaurant",
                "bgm": "bgm_daily",
                "blocks": [
                    {
                        "type": "choice",
                        "choice_mode": "parallel",
                        "choices": [
                            {
                                "text": "继续问清楚 · 并行 · 主线",
                                "route": "mainline",
                                "branch_text": "这一步贴合主线。",
                                "converge_text": "回到原书主线的关键行动。",
                            },
                            {
                                "text": "改吃汉堡 · 并行 · 偏离后回收",
                                "route": "divergent",
                                "branch_text": "短暂偏离后回收。",
                                "converge_text": "收束回核心事实。",
                            },
                        ],
                    }
                ],
                "required_assets": [],
            }
        )

        scene_ir = adapt_scene_with_deepseek(
            source_scene=SourceScene(index=1, title="Scene 1", text="她问晚饭吃什么。", start_offset=0, end_offset=8),
            analysis=_analysis(),
            pov_state=_pov_state(),
            chapter_index=1,
            rag_context=[],
            client=client,
        )

        choices = scene_ir["blocks"][0]["choices"]
        self.assertEqual([choice["text"] for choice in choices], ["按她说的点", "换一道菜"])
        visible_text = "\n".join(
            str(choice.get(field, ""))
            for choice in choices
            for field in ("text", "branch_text", "converge_text")
        )
        for banned in ["主线", "偏离", "回收", "收束", "核心事实", "关键行动", "并行"]:
            self.assertNotIn(banned, visible_text)

    def test_question_scene_inserts_choice_near_question_and_rewrites_pov_line(self):
        client = FakeDeepSeekClient(
            {
                "background": "bg_home_living",
                "bgm": "bgm_daily",
                "blocks": [
                    {"type": "narration", "text": "林雨伸出手，心里还是犹豫了一下。"},
                    {"type": "dialogue", "speaker": "苏晚", "text": "你愿意跟我走吗？"},
                    {"type": "narration", "text": "屋里安静下来。"},
                ],
                "required_assets": [],
            }
        )

        scene_ir = adapt_scene_with_deepseek(
            source_scene=SourceScene(index=1, title="Scene 1", text="苏晚问林雨：“你愿意跟我走吗？”", start_offset=0, end_offset=18),
            analysis=_analysis(),
            pov_state=_pov_state(),
            chapter_index=1,
            rag_context=[],
            client=client,
            pov_character="林雨",
        )

        self.assertEqual(scene_ir["blocks"][0]["type"], "dialogue")
        self.assertEqual(scene_ir["blocks"][0]["speaker"], "我")
        choice_index = next(index for index, block in enumerate(scene_ir["blocks"]) if block["type"] == "choice")
        self.assertLess(choice_index, len(scene_ir["blocks"]) - 1)
        branch_text = "\n".join(choice["branch_text"] for choice in scene_ir["blocks"][choice_index]["choices"])
        self.assertIn("我", branch_text)
        self.assertIn("（", branch_text)

    def test_empty_ai_blocks_fallback_still_rewrites_pov_character(self):
        client = FakeDeepSeekClient({"background": "bg_home_living", "bgm": "bgm_daily", "blocks": []})

        scene_ir = adapt_scene_with_deepseek(
            source_scene=SourceScene(index=1, title="Scene 1", text="林雨站在门口，苏晚问他为什么不进去。", start_offset=0, end_offset=20),
            analysis=_analysis(),
            pov_state=_pov_state(),
            chapter_index=1,
            rag_context=[],
            client=client,
            pov_character="林雨",
        )

        self.assertEqual(scene_ir["blocks"][0]["type"], "dialogue")
        self.assertEqual(scene_ir["blocks"][0]["speaker"], "我")
        self.assertTrue(scene_ir["blocks"][0]["text"].startswith("我"))
        self.assertIn("问我", scene_ir["blocks"][0]["text"])


def _analysis():
    return StoryAnalysis(
        title="雨夜旧楼",
        characters=[
            CharacterCard(
                character_id="char_1",
                name="林雨",
                aliases=[],
                role="主角",
                personality="谨慎",
                speech_style="简短",
                relationship_map={},
                secrets=[],
                visual_notes={},
                do_not_do=[],
                source_evidence=[],
            ),
            CharacterCard(
                character_id="char_2",
                name="苏晚",
                aliases=[],
                role="主要角色",
                personality="冷静",
                speech_style="克制",
                relationship_map={},
                secrets=[],
                visual_notes={},
                do_not_do=[],
                source_evidence=[],
            ),
        ],
        events=[],
        clues=[],
        story_bible=StoryBible(
            title="雨夜旧楼",
            main_plot="林雨追查纸条。",
            core_conflict="信息不对称。",
            themes=["悬疑"],
            style_notes="视觉小说。",
            forbidden_changes=[],
        ),
    )


def _pov_state():
    return POVKnowledgeState(
        project_id="project-1",
        after_event_order=1,
        known_facts=["林雨看到自己的名字。"],
        unknown_facts=["苏晚为什么藏钥匙。"],
        suspected_facts=["苏晚隐瞒了部分信息。"],
        false_beliefs=[],
        forbidden_reveals=["不要提前说明钥匙用途。"],
    )
