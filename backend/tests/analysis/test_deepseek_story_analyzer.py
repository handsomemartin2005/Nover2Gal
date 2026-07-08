import json
import unittest

from app.analysis.deepseek_story_analyzer import refine_analysis_with_deepseek
from app.analysis.simple_analyzer import analyze_story
from app.parser.chapter_splitter import split_chapters
from app.parser.scene_splitter import split_scenes


class FakeDeepSeekClient:
    def __init__(self, payload):
        self.payload = payload
        self.messages = []

    def chat(self, messages, json_output=False):
        self.messages = messages
        self.json_output = json_output
        return json.dumps(self.payload, ensure_ascii=False)


class DeepSeekStoryAnalyzerTest(unittest.TestCase):
    def test_refines_characters_and_filters_common_nouns(self):
        text = (
            "第一章 晚饭\n"
            "林雨问苏晚晚饭吃什么。\n"
            "苏晚低声说原文里是披萨。\n"
            "汉堡只是玩家偏离选项。"
        )
        chapters = split_chapters(text)
        scenes_by_chapter = {chapter.index: split_scenes(chapter.text, min_scene_chars=10) for chapter in chapters}
        base = analyze_story("晚饭测试", chapters, scenes_by_chapter)
        client = FakeDeepSeekClient(
            {
                "characters": [
                    {"name": "林雨", "role": "主角", "personality": "谨慎", "speech_style": "直接"},
                    {"name": "苏晚", "role": "主要角色", "personality": "克制", "speech_style": "低声"},
                ],
                "not_characters": ["晚饭", "披萨", "汉堡", "低声"],
            }
        )

        refined = refine_analysis_with_deepseek(
            title="晚饭测试",
            text=text,
            base_analysis=base,
            client=client,
        )

        names = [character.name for character in refined.characters]
        self.assertEqual(names, ["林雨", "苏晚"])
        self.assertNotIn("低声", names)
        self.assertNotIn("晚饭", names)
        self.assertTrue(client.json_output)
        self.assertIn("not_characters", client.messages[1]["content"])

    def test_rejects_pronouns_places_and_abstract_words_as_characters(self):
        text = (
            "孙少平站在顶楼门口，田晓霞问他为什么不下来。\n"
            "这个时候，任何人的心里都像是压着事情。\n"
            "田晓霞低声说：“先跟我走。”"
        )
        chapters = split_chapters(text)
        scenes_by_chapter = {chapter.index: split_scenes(chapter.text, min_scene_chars=10) for chapter in chapters}
        base = analyze_story("人物过滤测试", chapters, scenes_by_chapter)
        client = FakeDeepSeekClient(
            {
                "visual_style": "real",
                "characters": [
                    {"name": "这个", "role": "主要角色"},
                    {"name": "任何", "role": "配角"},
                    {"name": "顶楼", "role": "配角"},
                    {"name": "心的", "role": "配角"},
                    {"name": "孙少平", "role": "主角", "personality": "谨慎"},
                    {"name": "田晓霞", "role": "主要角色", "personality": "直接"},
                ],
                "not_characters": ["这个", "任何", "顶楼", "心的"],
            }
        )

        refined = refine_analysis_with_deepseek("人物过滤测试", text, base, client)

        names = [character.name for character in refined.characters]
        self.assertEqual(names, ["孙少平", "田晓霞"])
        self.assertNotIn("这个", names)
        self.assertEqual(refined.characters[0].visual_notes["style"], "real")
