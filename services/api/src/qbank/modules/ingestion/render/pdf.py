"""PDF to page pictures and text, with pdfium (threat U1, U4, U5).

pdfium is run without a script engine and without form support, so nothing in the file is executed,
launched or fetched. Pages are rendered one at a time, each limited in size; a page that cannot be
read is reported, not fatal, so the rest of the file is kept.
"""

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

import pypdfium2 as pdfium

from qbank.modules.ingestion.render import images
from qbank.modules.ingestion.render.errors import RenderError
from qbank.modules.ingestion.render.limits import (
    MAX_PAGE_POINTS,
    MAX_PAGES,
    MAX_TEXT_CHARS,
    PAGE_MAX_SIDE,
)


@dataclass(frozen=True, slots=True)
class RenderedPage:
    page_no: int
    image: images.PageImage | None = None
    text: str | None = None
    figures: list[images.PageImage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def open_pdf(data: bytes) -> pdfium.PdfDocument:
    try:
        document = pdfium.PdfDocument(data)
        count = len(document)
    except Exception as problem:  # the library's own errors, whatever their type
        wanted = (
            "PASSWORD_PROTECTED" if "password" in str(problem).lower() else "UNREADABLE_DOCUMENT"
        )
        raise RenderError(wanted) from None
    if count < 1:
        raise RenderError("EMPTY_DOCUMENT")
    if count > MAX_PAGES:
        document.close()
        raise RenderError("TOO_MANY_PAGES")
    return document


def render_pages(
    document: pdfium.PdfDocument, *, skip: set[int], deadline: float
) -> Iterator[RenderedPage]:
    """Each page not in ``skip``, in order. Stops with ``TOO_SLOW`` when the time is up."""
    try:
        for index in range(len(document)):
            number = index + 1
            if number in skip:
                continue
            if time.monotonic() > deadline:
                raise RenderError("TOO_SLOW")
            yield _one(document, index, number)
    finally:
        document.close()


def _one(document: pdfium.PdfDocument, index: int, number: int) -> RenderedPage:
    page = None
    try:
        page = document[index]
        width, height = page.get_size()
        if not (0 < width <= MAX_PAGE_POINTS and 0 < height <= MAX_PAGE_POINTS):
            return RenderedPage(number, error="PAGE_TOO_LARGE")
        scale = min(3.0, PAGE_MAX_SIDE / max(width, height))
        bitmap = page.render(scale=scale)
        picture = images.from_pil(bitmap.to_pil())
        text: str | None = None
        try:
            textpage = page.get_textpage()
            text = textpage.get_text_range()[:MAX_TEXT_CHARS].strip() or None
            textpage.close()
        except Exception:  # a page with no readable text layer is a scan: the picture is enough
            text = None
        return RenderedPage(number, image=picture, text=text)
    except RenderError as problem:
        return RenderedPage(number, error=problem.code)
    except Exception:
        return RenderedPage(number, error="PAGE_UNREADABLE")
    finally:
        if page is not None:
            page.close()
