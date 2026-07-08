import unittest

from app.pov.pov_engine import build_pov_knowledge
from app.schemas.story import Clue, StoryEvent


class POVEngineTest(unittest.TestCase):
    def test_builds_known_unknown_and_forbidden_state_for_pov_character(self):
        events = [
            StoryEvent(
                event_id="E001",
                order=1,
                text="林雨发现苏晚藏起一张泛黄的纸。",
                participants=["林雨", "苏晚"],
                visible_to=["林雨", "苏晚"],
                hidden_meaning="纸与旧案有关，但林雨当前不知道。",
            ),
            StoryEvent(
                event_id="E002",
                order=2,
                text="苏晚独自读完纸上的内容。",
                participants=["苏晚"],
                visible_to=["苏晚"],
                hidden_meaning="纸上写着旧案关键姓名。",
            ),
        ]
        clues = [
            Clue(
                clue_id="C001",
                clue_name="泛黄的纸",
                first_appears_event_id="E001",
                hidden_meaning="纸与旧案有关",
                reveal_policy="do_not_reveal_before_reveal_scene",
            )
        ]

        states = build_pov_knowledge("project-1", "林雨", events, clues)

        self.assertEqual(len(states), 2)
        self.assertIn("林雨发现苏晚藏起一张泛黄的纸。", states[0].known_facts)
        self.assertIn("纸与旧案有关", states[0].forbidden_reveals)
        self.assertIn("苏晚独自读完纸上的内容。", states[1].unknown_facts)
