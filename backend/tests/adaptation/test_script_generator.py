import unittest

from app.adaptation.choice_fallback import build_concrete_choice_block
from app.adaptation.script_generator import generate_scene_ir
from app.adaptation.text_polisher import polish_game_text
from app.parser.scene_splitter import SourceScene
from app.schemas.story import CharacterCard, POVKnowledgeState, StoryAnalysis, StoryBible


class ScriptGeneratorTest(unittest.TestCase):
    def test_does_not_treat_character_name_lin_yu_as_rain_weather(self):
        scene = SourceScene(index=1, title="Scene 1", text="林雨再次回到教室。", start_offset=0, end_offset=9)
        analysis = StoryAnalysis(
            title="雨夜旧楼",
            characters=[],
            events=[],
            clues=[],
            story_bible=StoryBible(
                title="雨夜旧楼",
                main_plot="",
                core_conflict="",
                themes=[],
                style_notes="",
                forbidden_changes=[],
            ),
        )
        state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=[],
            false_beliefs=[],
            forbidden_reveals=[],
        )

        scene_ir = generate_scene_ir(scene, analysis, state, chapter_index=2)

        self.assertEqual(scene_ir["bgm"], "bgm_daily")
        self.assertFalse(any(asset["key"] == "sfx_rain_loop" for asset in scene_ir["required_assets"]))

    def test_rule_narration_is_split_into_short_clicks(self):
        scene = SourceScene(
            index=1,
            title="Scene 1",
            text=(
                "林雨推开门，屋里的灯光落在桌面上。苏晚站在椅子旁边，没有立刻说话。"
                "窗外的雨声压低了两个人之间的呼吸。他看见桌角放着一只旧杯子，杯沿还留着水痕。"
                "这段文字不应该一次全部塞进对话框。"
            ),
            start_offset=0,
            end_offset=80,
        )
        analysis = StoryAnalysis(
            title="雨夜旧楼",
            characters=[_character("林雨"), _character("苏晚")],
            events=[],
            clues=[],
            story_bible=StoryBible(title="雨夜旧楼", main_plot="", core_conflict="", themes=[], style_notes="", forbidden_changes=[]),
        )
        state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=[],
            false_beliefs=[],
            forbidden_reveals=[],
        )

        scene_ir = generate_scene_ir(scene, analysis, state, chapter_index=1)

        narration_blocks = [block for block in scene_ir["blocks"] if block["type"] == "narration"]
        self.assertGreater(len(narration_blocks), 1)
        self.assertLessEqual(len(narration_blocks), 5)
        self.assertTrue(all(len(block["text"]) <= 56 for block in narration_blocks))

    def test_polisher_drops_orphan_quote_marks(self):
        self.assertEqual(polish_game_text("」"), "")
        self.assertEqual(polish_game_text("」  "), "")
        self.assertEqual(polish_game_text("真唯说「不行。」"), "真唯说“不行。”")

    def test_rule_choices_use_concrete_actions_instead_of_generic_observe(self):
        scene = SourceScene(index=1, title="Scene 1", text="林雨停在门口，苏晚把纸条藏到身后。", start_offset=0, end_offset=20)
        analysis = StoryAnalysis(
            title="雨夜旧楼",
            characters=[
                _character("林雨"),
                _character("苏晚"),
            ],
            events=[],
            clues=[],
            story_bible=StoryBible(
                title="雨夜旧楼",
                main_plot="",
                core_conflict="",
                themes=[],
                style_notes="",
                forbidden_changes=[],
            ),
        )
        state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=["苏晚藏起了纸条。"],
            false_beliefs=[],
            forbidden_reveals=[],
        )

        scene_ir = generate_scene_ir(scene, analysis, state, chapter_index=2)

        choice_block = next(block for block in scene_ir["blocks"] if block["type"] == "choice")
        choice_text = "\n".join(
            str(choice.get(field, ""))
            for choice in choice_block["choices"]
            for field in ("text", "branch_text", "converge_text")
        )
        self.assertNotIn("暂时观察", choice_text)
        self.assertIn("纸", choice_text)
        self.assertTrue(all(choice.get("branch_text") for choice in choice_block["choices"]))
        self.assertTrue(all(choice.get("converge_text") for choice in choice_block["choices"]))
        for banned in [
            "这一步",
            "现场仍",
            "局面",
            "原来的节奏",
            "重新面对",
            "眼前的事",
            "继续问清楚",
            "先绕到侧面",
            "主线",
            "偏离后回收",
            "并行",
        ]:
            self.assertNotIn(banned, choice_text)

    def test_rule_choices_are_daily_decisions_for_food_and_agreement(self):
        food_choice = _choice_texts_for("苏晚问晚饭吃什么，原先说好吃披萨。")
        self.assertEqual(food_choice, ["吃披萨", "改吃汉堡"])

        agreement_choice = _choice_texts_for("苏晚问林雨要不要答应这件事，林雨没有立刻同意。")
        self.assertEqual(agreement_choice, ["答应她", "先拒绝"])

    def test_question_choices_are_answer_oriented_and_first_person(self):
        choice_block = build_concrete_choice_block("common_001_002", "田晓霞问孙少平：“你到底愿不愿意跟我走？”")

        choice_texts = [choice["text"] for choice in choice_block["choices"]]
        branch_text = "\n".join(choice["branch_text"] for choice in choice_block["choices"])

        self.assertNotIn("继续问清楚", choice_texts)
        self.assertNotIn("暂时观察", choice_texts)
        self.assertTrue(any(text in choice_texts for text in ["实话回答", "点头承认", "反问一句", "把话说透", "答应对方", "先拒绝"]))
        self.assertIn("我", branch_text)
        self.assertIn("（", branch_text)

    def test_infers_home_living_room_stage_assets(self):
        scene = SourceScene(index=1, title="Scene 1", text="家里的会客厅里，主人公坐在椅子旁，桌子上放着茶杯。", start_offset=0, end_offset=30)
        analysis = StoryAnalysis(
            title="家中会客",
            characters=[_character("主人公")],
            events=[],
            clues=[],
            story_bible=StoryBible(
                title="家中会客",
                main_plot="",
                core_conflict="",
                themes=[],
                style_notes="",
                forbidden_changes=[],
            ),
        )
        state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=[],
            false_beliefs=[],
            forbidden_reveals=[],
        )

        scene_ir = generate_scene_ir(scene, analysis, state, chapter_index=1)

        self.assertEqual(scene_ir["background"], "bg_home_living")
        self.assertEqual(scene_ir["stage"]["location"], "home_living")
        self.assertIn("table", scene_ir["stage"]["props"])
        self.assertIn("chair", scene_ir["stage"]["props"])
        self.assertIn("protagonist", scene_ir["stage"]["characters"])

    def test_infers_more_common_props_and_visible_characters(self):
        scene = SourceScene(
            index=1,
            title="Scene 1",
            text="卧室里，林雨把书包放到床边，苏晚站在书柜旁，桌上的台灯照着纸条和手机。",
            start_offset=0,
            end_offset=42,
        )
        analysis = StoryAnalysis(
            title="卧室谈话",
            characters=[_character("林雨"), _character("苏晚")],
            events=[],
            clues=[],
            story_bible=StoryBible(title="卧室谈话", main_plot="", core_conflict="", themes=[], style_notes="", forbidden_changes=[]),
        )
        state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=[],
            false_beliefs=[],
            forbidden_reveals=[],
        )

        scene_ir = generate_scene_ir(scene, analysis, state, chapter_index=1)

        self.assertEqual(scene_ir["stage"]["location"], "bedroom")
        for prop in ["bed", "bag", "bookshelf", "table", "lamp", "paper", "phone"]:
            self.assertIn(prop, scene_ir["stage"]["props"])
        self.assertIn("林雨", scene_ir["stage"]["characters"])
        self.assertIn("苏晚", scene_ir["stage"]["characters"])

    def test_infers_bathroom_and_toilet_backgrounds(self):
        bathroom_scene = SourceScene(index=1, title="Scene 1", text="浴室里，镜子蒙着水汽，毛巾搭在浴缸旁。", start_offset=0, end_offset=24)
        toilet_scene = SourceScene(index=2, title="Scene 2", text="午休时，她停在女厕门口，洗手台边没有别人。", start_offset=25, end_offset=50)
        analysis = StoryAnalysis(
            title="学校午休",
            characters=[_character("苏晚")],
            events=[],
            clues=[],
            story_bible=StoryBible(title="学校午休", main_plot="", core_conflict="", themes=[], style_notes="", forbidden_changes=[]),
        )
        state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=[],
            false_beliefs=[],
            forbidden_reveals=[],
        )

        bathroom_ir = generate_scene_ir(bathroom_scene, analysis, state, chapter_index=1)
        toilet_ir = generate_scene_ir(toilet_scene, analysis, state, chapter_index=1)

        self.assertEqual(bathroom_ir["background"], "bg_bathroom")
        self.assertEqual(bathroom_ir["stage"]["location"], "bathroom")
        self.assertIn("mirror", bathroom_ir["stage"]["props"])
        self.assertEqual(toilet_ir["background"], "bg_toilet")
        self.assertEqual(toilet_ir["stage"]["location"], "toilet")
        self.assertIn("sink", toilet_ir["stage"]["props"])


def _choice_texts_for(text: str) -> list[str]:
    choice_block = build_concrete_choice_block("common_001_001", text)
    return [choice["text"] for choice in choice_block["choices"]]


def _character(name: str) -> CharacterCard:
    return CharacterCard(
        character_id=f"char_{name}",
        name=name,
        aliases=[],
        role="主要角色",
        personality="",
        speech_style="",
        relationship_map={},
        secrets=[],
        visual_notes={},
        do_not_do=[],
        source_evidence=[],
    )
