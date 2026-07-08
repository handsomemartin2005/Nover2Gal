import tempfile
import unittest
from pathlib import Path

from app.importers.document_importer import import_document, import_document_bytes
from tests.helpers import write_sample_epub


class DocumentImporterTest(unittest.TestCase):
    def test_imports_txt_as_utf8_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_text("第一章 雨夜\n林雨推开门。", encoding="utf-8")

            document = import_document(path)

            self.assertEqual(document.title, "sample")
            self.assertEqual(document.source_type, "txt")
            self.assertIn("林雨推开门。", document.text)

    def test_imports_epub_spine_order_as_plain_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.epub"
            write_sample_epub(path)

            document = import_document(path)

            self.assertEqual(document.title, "雨夜旧楼")
            self.assertEqual(document.source_type, "epub")
            self.assertIn("第一章 雨夜", document.text)
            self.assertIn("林雨推开旧教学楼的门。", document.text)
            self.assertIn("第二章 清晨", document.text)
            self.assertLess(document.text.index("第一章 雨夜"), document.text.index("第二章 清晨"))

    def test_importer_drops_common_non_body_preamble_and_watermark_lines(self):
        raw = "\n".join(
            [
                "目录",
                "版权信息",
                "z-library.sk",
                "第一章 雨夜",
                "林雨推开门。",
                "www.example.com",
                "苏晚问他为什么回来。",
            ]
        ).encode("utf-8")

        document = import_document_bytes("demo.txt", raw)

        self.assertTrue(document.text.startswith("第一章 雨夜"))
        self.assertIn("林雨推开门。", document.text)
        self.assertNotIn("z-library", document.text)
        self.assertNotIn("www.example.com", document.text)
