import unittest

from app.parser.scene_splitter import split_scenes


class SceneSplitterTest(unittest.TestCase):
    def test_splits_on_blank_line_transition_cues(self):
        text = (
            "林雨推开旧教学楼的门，雨水落在身后。\n"
            "苏晚站在讲台旁。\n\n"
            "第二天清晨，教室里只剩下粉笔灰。\n"
            "林雨想起昨晚那张纸。"
        )

        scenes = split_scenes(text, min_scene_chars=10)

        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[0].index, 1)
        self.assertIn("旧教学楼", scenes[0].text)
        self.assertIn("第二天清晨", scenes[1].text)

    def test_keeps_short_fragments_with_previous_scene(self):
        text = "林雨推门。\n\n雨声。\n\n苏晚沉默了很久。"

        scenes = split_scenes(text, min_scene_chars=20)

        self.assertEqual(len(scenes), 1)
        self.assertIn("雨声。", scenes[0].text)

    def test_splits_long_paragraph_on_time_and_location_transition(self):
        text = (
            "孙少平站在院子里，听见屋里有人压低声音说话。田晓霞把书放在桌上，问他要不要进去。"
            "到了县城车站，天已经黑了，路边的灯一盏盏亮起来。"
            "回到家里，他才想起刚才那句话还没有回答。"
        )

        scenes = split_scenes(text, min_scene_chars=35)

        self.assertGreaterEqual(len(scenes), 2)
        self.assertIn("院子", scenes[0].text)
        self.assertTrue(any("县城车站" in scene.text for scene in scenes[1:]))

    def test_splits_school_bathroom_and_toilet_transitions(self):
        text = (
            "午休时间，教室里只剩下窗边的风声，她把课本合上，慢慢站起来。"
            "走廊尽头，她停在女厕门口，压低声音问了一句。"
            "回到浴室时，水汽已经漫过镜子。"
        )

        scenes = split_scenes(text, min_scene_chars=20)

        self.assertGreaterEqual(len(scenes), 3)
        self.assertTrue(any("女厕" in scene.text for scene in scenes))
        self.assertTrue(any("浴室" in scene.text for scene in scenes))
