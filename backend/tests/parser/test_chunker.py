import unittest

from app.parser.chunker import chunk_text


class ChunkerTest(unittest.TestCase):
    def test_chunks_text_with_overlap(self):
        text = "一二三四五六七八九十"

        chunks = chunk_text(text, max_chars=4, overlap_chars=1)

        self.assertEqual([chunk.text for chunk in chunks], ["一二三四", "四五六七", "七八九十"])
        self.assertEqual(chunks[1].start_offset, 3)

    def test_rejects_overlap_not_smaller_than_max_chars(self):
        with self.assertRaises(ValueError):
            chunk_text("abc", max_chars=3, overlap_chars=3)
