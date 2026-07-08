import unittest

from app.analysis.simple_analyzer import analyze_story
from app.parser.chapter_splitter import split_chapters
from app.parser.scene_splitter import split_scenes


class SimpleAnalyzerTest(unittest.TestCase):
    def test_extracts_characters_events_clues_and_story_bible(self):
        text = (
            "第一章 雨夜\n"
            "林雨推开旧教学楼的门时，雨声正从身后涌来。\n"
            "三楼的教室亮着一盏灯。\n"
            "苏晚站在讲台旁，手里攥着一张泛黄的纸。\n"
            "“你为什么在这里？”林雨问。\n"
            "苏晚把纸藏到身后。\n"
            "“这句话应该我问你。”苏晚说。"
        )
        chapters = split_chapters(text)
        scenes_by_chapter = {chapter.index: split_scenes(chapter.text, min_scene_chars=10) for chapter in chapters}

        analysis = analyze_story("雨夜旧楼", chapters, scenes_by_chapter)

        self.assertIn("林雨", [character.name for character in analysis.characters])
        self.assertIn("苏晚", [character.name for character in analysis.characters])
        self.assertNotIn("该我", [character.name for character in analysis.characters])
        self.assertGreaterEqual(len(analysis.events), 2)
        self.assertTrue(any("泛黄的纸" in clue.clue_name for clue in analysis.clues))
        self.assertIn("雨夜旧楼", analysis.story_bible.main_plot)

    def test_does_not_promote_common_words_to_characters(self):
        text = (
            "第一章 顶楼\n"
            "孙少平站在顶楼门口，田晓霞问他为什么不下来。\n"
            "这个时候，任何人的心里都像是压着事情。\n"
            "田晓霞低声说：“先跟我走。”"
        )
        chapters = split_chapters(text)
        scenes_by_chapter = {chapter.index: split_scenes(chapter.text, min_scene_chars=10) for chapter in chapters}

        analysis = analyze_story("人物过滤测试", chapters, scenes_by_chapter)

        names = [character.name for character in analysis.characters]
        self.assertIn("孙少平", names)
        self.assertIn("田晓霞", names)
        for bad_name in ["这个", "任何", "人的", "顶楼", "心的", "下来"]:
            self.assertNotIn(bad_name, names)

    def test_marks_anime_style_for_anime_world_text(self):
        text = "第一章 学园\n星野站在魔法学园门口，铃音问他要不要加入勇者社团。"
        chapters = split_chapters(text)
        scenes_by_chapter = {chapter.index: split_scenes(chapter.text, min_scene_chars=10) for chapter in chapters}

        analysis = analyze_story("二次元测试", chapters, scenes_by_chapter)

        self.assertTrue(analysis.characters)
        self.assertEqual(analysis.characters[0].visual_notes["style"], "anime")
