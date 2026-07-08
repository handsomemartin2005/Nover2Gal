import unittest

from app.parser.chapter_splitter import split_chapters


class ChapterSplitterTest(unittest.TestCase):
    def test_splits_chinese_chapter_headings(self):
        text = "序言\n不进章节。\n\n第一章 雨夜\n林雨推开门。\n\n第二章 清晨\n苏晚没有出现。"

        chapters = split_chapters(text)

        self.assertEqual([chapter.title for chapter in chapters], ["第一章 雨夜", "第二章 清晨"])
        self.assertEqual(chapters[0].index, 1)
        self.assertIn("林雨推开门。", chapters[0].text)
        self.assertNotIn("第二章", chapters[0].text)

    def test_falls_back_to_single_chapter_when_no_heading_exists(self):
        chapters = split_chapters("林雨推开旧教学楼的门。")

        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "Chapter 1")
        self.assertEqual(chapters[0].text, "林雨推开旧教学楼的门。")

    def test_auto_splits_long_unheaded_text_by_story_flow(self):
        text = "\n\n".join(
            [
                "上午，林雨留在教室里。" + "他看着窗外。" * 700,
                "午休时间，苏晚走进走廊。" + "她没有说话。" * 700,
                "晚上，两个人回到旧楼。" + "雨声越来越近。" * 700,
            ]
        )

        chapters = split_chapters(text)

        self.assertGreaterEqual(len(chapters), 2)
        self.assertTrue(chapters[0].title.startswith("自动章节"))

    def test_drops_toc_like_heading_runs_before_real_chapters(self):
        toc_headings = "\n".join(["第一章", "第二章", "第三章", "第四章", "第五章", "第六章"])
        text = (
            f"{toc_headings}\n\n"
            "第一章\n林雨推开旧教学楼的门，雨声压在窗外。\n\n"
            "第二章\n苏晚把纸条藏到身后。"
        )

        chapters = split_chapters(text)

        self.assertEqual([chapter.title for chapter in chapters], ["第一章", "第二章"])
        self.assertEqual(chapters[0].index, 1)
        self.assertIn("林雨推开旧教学楼", chapters[0].text)

    def test_keeps_isolated_short_chapter_body(self):
        text = "第一章\n一行短正文。\n\n第二章\n林雨推开旧教学楼的门。"

        chapters = split_chapters(text)

        self.assertEqual([chapter.title for chapter in chapters], ["第一章", "第二章"])
        self.assertEqual(chapters[0].text, "一行短正文。")
