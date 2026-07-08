import unittest

from app.consistency.checker import check_scene
from app.schemas.story import POVKnowledgeState


class ConsistencyCheckerTest(unittest.TestCase):
    def test_detects_forbidden_reveal_in_generated_scene(self):
        scene = {
            "scene_id": "common_001_001",
            "blocks": [
                {"type": "narration", "text": "我忽然明白，纸与旧案有关。"}
            ],
        }
        pov_state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=[],
            false_beliefs=[],
            forbidden_reveals=["纸与旧案有关"],
        )

        report = check_scene(scene, pov_state)

        self.assertFalse(report.passed)
        self.assertEqual(report.issues[0]["type"], "premature_reveal")

    def test_passes_when_scene_only_contains_suspicion(self):
        scene = {
            "scene_id": "common_001_001",
            "blocks": [
                {"type": "narration", "text": "苏晚把纸藏得太快，我总觉得她在隐瞒什么。"}
            ],
        }
        pov_state = POVKnowledgeState(
            project_id="project-1",
            after_event_order=1,
            known_facts=[],
            unknown_facts=[],
            suspected_facts=["苏晚可能在隐瞒纸的内容。"],
            false_beliefs=[],
            forbidden_reveals=["纸与旧案有关"],
        )

        report = check_scene(scene, pov_state)

        self.assertTrue(report.passed)
        self.assertEqual(report.issues, [])
