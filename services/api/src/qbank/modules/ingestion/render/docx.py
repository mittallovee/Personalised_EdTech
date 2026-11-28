"""A Word file read directly as XML (design note D1, option A; threats U3, U5, U6, U7).

A ``.docx`` is a ZIP of XML parts. It is read **in memory**: sizes are checked from the ZIP's
directory before any part is read, parts are looked up by name (never by a path or address taken
from the file), the XML is read with ``defusedxml`` (no entities, no external references) and
streamed with limits, and nothing is executed: macros, linked or embedded objects and remote
templates are ignored. Text and tables are kept as text; the pictures inside are re-encoded. An
equation written in Word's equation editor cannot be drawn without a program that renders Word, so
its text is kept and the page is flagged ``EQUATION_AS_TEXT`` for a person to check.
"""

import io
import posixpath
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element  # nosec B405 - a type only; parsing uses defusedxml

from defusedxml import ElementTree as SafeET

from qbank.modules.ingestion.render import images
from qbank.modules.ingestion.render.errors import RenderError
from qbank.modules.ingestion.render.limits import (
    DOCX_MAX_ELEMENTS,
    DOCX_MAX_FIGURES,
    DOCX_MAX_PARTS,
    DOCX_MAX_UNPACKED,
    DOCX_MAX_XML,
    DOCX_PAGE_CHARS,
    MAX_PAGES,
    MAX_TEXT_CHARS,
)
from qbank.modules.ingestion.render.pdf import RenderedPage

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_DOCUMENT = "word/document.xml"
_RELS = "word/_rels/document.xml.rels"
_PICTURE_TYPES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")


@dataclass
class _Page:
    parts: list[str] = field(default_factory=list)
    figures: list[images.PageImage] = field(default_factory=list)
    warnings: set[str] = field(default_factory=set)
    size: int = 0


def open_docx(data: bytes) -> zipfile.ZipFile:
    """The archive, once its directory has been checked. A bad one is ``UNREADABLE_DOCUMENT``."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
    except Exception:  # not a ZIP, or a damaged one
        raise RenderError("UNREADABLE_DOCUMENT") from None
    names = {info.filename for info in infos}
    if len(infos) > DOCX_MAX_PARTS or sum(info.file_size for info in infos) > DOCX_MAX_UNPACKED:
        raise RenderError(
            "DOCUMENT_TOO_LARGE"
        )  # a decompression bomb, refused before anything is read
    if "[Content_Types].xml" not in names or _DOCUMENT not in names:
        raise RenderError("NOT_A_WORD_FILE")  # a ZIP, but not a Word document
    if archive.getinfo(_DOCUMENT).file_size > DOCX_MAX_XML:
        raise RenderError("DOCUMENT_TOO_LARGE")
    return archive


def _read(archive: zipfile.ZipFile, name: str, limit: int) -> bytes:
    """One part, read no further than ``limit`` bytes even if the directory lied about its size."""
    try:
        with archive.open(name) as part:
            data = part.read(limit + 1)
    except Exception:
        raise RenderError("UNREADABLE_DOCUMENT") from None
    if len(data) > limit:
        raise RenderError("DOCUMENT_TOO_LARGE")
    return data


def _relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    """Relationship id to the name of a picture part inside the archive. Nothing else is followed:
    external targets, links and objects are dropped."""
    if _RELS not in {info.filename for info in archive.infolist()}:
        return {}
    wanted: dict[str, str] = {}
    try:
        root = SafeET.fromstring(_read(archive, _RELS, 2 * 1024 * 1024))
    except RenderError:
        raise
    except Exception:
        raise RenderError("UNREADABLE_DOCUMENT") from None
    for rel in root.iter(f"{_REL}Relationship"):
        if rel.get("TargetMode") == "External":
            continue
        target = rel.get("Target") or ""
        rid = rel.get("Id")
        if rid is None or not rel.get("Type", "").endswith("/image"):
            continue
        name = (
            posixpath.normpath(posixpath.join("word", target))
            if not target.startswith("/")
            else target[1:]
        )
        if name.startswith("word/") and ".." not in name and name.lower().endswith(_PICTURE_TYPES):
            wanted[rid] = name
    return wanted


def _text_of(node: Element) -> str:
    """The text of a paragraph, tabs and breaks as spaces, an equation marked as such."""
    out: list[str] = []
    for child in node.iter():
        if child.tag == f"{_W}t" and child.text:
            out.append(child.text)
        elif child.tag in (f"{_W}tab", f"{_W}br", f"{_W}cr"):
            out.append(" ")
        elif child.tag == f"{_M}t" and child.text:
            out.append(child.text)
    return "".join(out).strip()


def read_pages(archive: zipfile.ZipFile, *, skip: set[int]) -> Iterator[RenderedPage]:
    """The document as pages of text (and pictures), in order. A page is a page break, or about
    ``DOCX_PAGE_CHARS`` characters of paragraphs, whichever comes first."""
    pictures = _relationships(archive)
    try:
        root = SafeET.fromstring(_read(archive, _DOCUMENT, DOCX_MAX_XML))
    except RenderError:
        raise
    except Exception:
        raise RenderError("UNREADABLE_DOCUMENT") from None
    body = root.find(f"{_W}body")
    if body is None:
        raise RenderError("NOT_A_WORD_FILE")
    if sum(1 for _ in root.iter()) > DOCX_MAX_ELEMENTS:
        raise RenderError("DOCUMENT_TOO_LARGE")

    figures_used = 0
    pages: list[_Page] = [_Page()]

    def add(text: str, *, equation: bool) -> None:
        page = pages[-1]
        if text:
            page.parts.append(text)
            page.size += len(text)
            if equation:
                page.warnings.add("EQUATION_AS_TEXT")
        if page.size >= DOCX_PAGE_CHARS:
            pages.append(_Page())

    for block in body:
        if len(pages) > MAX_PAGES:
            raise RenderError("TOO_MANY_PAGES")
        if block.tag == f"{_W}p":
            has_math = block.find(f".//{_M}oMath") is not None
            for blip in block.iter(f"{_A}blip"):
                name = pictures.get(blip.get(f"{_R}embed", ""))
                if name is None or figures_used >= DOCX_MAX_FIGURES:
                    continue
                try:
                    pages[-1].figures.append(
                        images.from_bytes(_read(archive, name, 20 * 1024 * 1024))
                    )
                    figures_used += 1
                except RenderError:
                    pages[-1].warnings.add("PICTURE_SKIPPED")
            add(_text_of(block), equation=has_math)
            if block.find(f".//{_W}br[@{_W}type='page']") is not None:
                pages.append(_Page())
        elif block.tag == f"{_W}tbl":
            rows = []
            for row in block.iter(f"{_W}tr"):
                cells = [_text_of(cell) for cell in row.findall(f"{_W}tc")]
                rows.append("\t".join(cells))
            add("\n".join(rows), equation=block.find(f".//{_M}oMath") is not None)
    produced = [page for page in pages if page.parts or page.figures]
    if not produced:
        raise RenderError("EMPTY_DOCUMENT")
    for number, page in enumerate(produced, start=1):
        if number in skip:
            continue
        text = "\n\n".join(page.parts)[:MAX_TEXT_CHARS] or None
        yield RenderedPage(
            number, image=None, text=text, figures=page.figures, warnings=sorted(page.warnings)
        )
