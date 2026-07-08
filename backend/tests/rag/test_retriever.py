import unittest

from app.parser.chunker import TextChunk
from app.rag.retriever import retrieve_context


class RetrieverTest(unittest.TestCase):
    def test_retrieves_chunks_related_to_query_first(self):
        chunks = [
            TextChunk(index=1, text="林雨走进操场，听见远处有人争吵。", start_offset=0, end_offset=18),
            TextChunk(index=2, text="苏晚把旧钥匙藏进图书馆登记册，纸角写着林雨的名字。", start_offset=19, end_offset=48),
            TextChunk(index=3, text="早餐铺的蒸汽挡住了街口。", start_offset=49, end_offset=62),
        ]

        snippets = retrieve_context("林雨发现图书馆钥匙", chunks, max_chunks=2)

        self.assertEqual([snippet.chunk_index for snippet in snippets], [2, 1])
        self.assertGreater(snippets[0].score, snippets[1].score)
        self.assertIn("旧钥匙", snippets[0].text)

    def test_returns_empty_context_for_blank_query(self):
        chunks = [TextChunk(index=1, text="任意文本", start_offset=0, end_offset=4)]

        self.assertEqual(retrieve_context("   ", chunks, max_chunks=3), [])
