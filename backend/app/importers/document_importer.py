from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path, PurePosixPath
import re
from xml.etree import ElementTree
from zipfile import ZipFile


@dataclass(frozen=True)
class ImportedDocument:
    title: str
    text: str
    source_type: str
    metadata: dict[str, str]


def import_document(path: str | Path) -> ImportedDocument:
    document_path = Path(path)
    suffix = document_path.suffix.lower().lstrip(".")
    if suffix in {"txt", "md", "markdown"}:
        return _import_plain_text(document_path, suffix)
    if suffix == "epub":
        return _import_epub(document_path)
    raise ValueError(f"Unsupported document format: {document_path.suffix}")


def import_document_bytes(filename: str, content: bytes) -> ImportedDocument:
    path = Path(filename)
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"txt", "md", "markdown"}:
        text = content.decode("utf-8-sig", errors="replace")
        return ImportedDocument(title=path.stem, text=_clean_imported_text(text), source_type=suffix, metadata={"filename": filename})
    if suffix == "epub":
        with ZipFile(BytesIO(content)) as archive:
            return _import_epub_archive(archive, path.stem, filename)
    raise ValueError(f"Unsupported document format: {path.suffix}")


def _import_plain_text(path: Path, source_type: str) -> ImportedDocument:
    text = path.read_text(encoding="utf-8-sig")
    return ImportedDocument(title=path.stem, text=_clean_imported_text(text), source_type=source_type, metadata={"filename": path.name})


def _import_epub(path: Path) -> ImportedDocument:
    with ZipFile(path) as archive:
        return _import_epub_archive(archive, path.stem, path.name)


def _import_epub_archive(archive: ZipFile, fallback_title: str, filename: str) -> ImportedDocument:
    opf_path = _find_opf_path(archive)
    opf_xml = archive.read(opf_path)
    opf_root = ElementTree.fromstring(opf_xml)
    title = _find_first_text(opf_root, "title") or fallback_title
    item_paths = _spine_item_paths(opf_root, opf_path)
    sections = []
    for item_path in item_paths:
        if item_path not in archive.namelist():
            continue
        html_text = archive.read(item_path).decode("utf-8", errors="replace")
        section_text = _html_to_text(html_text)
        if section_text:
            sections.append(section_text)
    return ImportedDocument(
        title=title.strip(),
        text=_clean_imported_text("\n\n".join(sections)),
        source_type="epub",
        metadata={"filename": filename},
    )


def _find_opf_path(archive: ZipFile) -> str:
    container_xml = archive.read("META-INF/container.xml")
    root = ElementTree.fromstring(container_xml)
    for element in root.iter():
        if _local_name(element.tag) == "rootfile" and element.attrib.get("full-path"):
            return element.attrib["full-path"]
    raise ValueError("EPUB container.xml does not contain a rootfile")


def _spine_item_paths(opf_root: ElementTree.Element, opf_path: str) -> list[str]:
    manifest: dict[str, str] = {}
    for element in opf_root.iter():
        if _local_name(element.tag) == "item":
            item_id = element.attrib.get("id")
            href = element.attrib.get("href")
            media_type = element.attrib.get("media-type", "")
            if item_id and href and ("html" in media_type or href.lower().endswith((".html", ".xhtml"))):
                manifest[item_id] = href

    opf_dir = PurePosixPath(opf_path).parent
    paths: list[str] = []
    for element in opf_root.iter():
        if _local_name(element.tag) == "itemref":
            href = manifest.get(element.attrib.get("idref", ""))
            if href:
                paths.append(str(opf_dir / href))
    return paths


def _find_first_text(root: ElementTree.Element, local_name: str) -> str:
    for element in root.iter():
        if _local_name(element.tag) == local_name and element.text:
            return element.text
    return ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _html_to_text(html: str) -> str:
    parser = _HTMLTextParser()
    parser.feed(html)
    parser.close()
    return parser.text()


CHAPTER_START_RE = re.compile(r"^\s*(第[一二三四五六七八九十百千万〇零0-9]+[章节卷回].*|chapter\s+\d+.*)\s*$", re.IGNORECASE | re.MULTILINE)
NON_BODY_LINE_RE = re.compile(
    r"(z-?library|1lib|本书由|电子书|版权|版权所有|ISBN|出版社|责任编辑|图书在版|目录|封面|书名|作者简介|内容简介|前言|序言|购买正版|www\.|http)",
    re.IGNORECASE,
)


def _clean_imported_text(text: str) -> str:
    normalized = text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = _drop_non_body_preamble(normalized)
    lines = []
    for line in normalized.splitlines():
        stripped = " ".join(line.split())
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if NON_BODY_LINE_RE.search(stripped) and len(stripped) < 80:
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def _drop_non_body_preamble(text: str) -> str:
    match = CHAPTER_START_RE.search(text)
    if not match:
        return text
    preamble = text[: match.start()]
    if len(preamble) <= 4000 or NON_BODY_LINE_RE.search(preamble):
        return text[match.start() :]
    return text


class _HTMLTextParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "h5", "h6", "li", "br"}
    SKIP_TAGS = {"script", "style", "head", "nav"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self._newline()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self._parts.append(cleaned)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        return "\n".join(line for line in lines if line).strip()

    def _newline(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")
