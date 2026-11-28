"""M6 PR 6c/6d, test T58: rendering documents and surviving hostile ones (threats U1 to U9).

These run the renderers themselves on made-up documents. A hostile file must end as a plain
``RenderError`` (or a failed page), never as a crash, a hang or a read outside the file.
"""

import io
import time
import zipfile

import pytest
from PIL import Image

from qbank.modules.ingestion.render import docx as docx_mod
from qbank.modules.ingestion.render import images, limits
from qbank.modules.ingestion.render import pdf as pdf_mod
from qbank.modules.ingestion.render.errors import RenderError
from tests import ingest_samples as samples

NEVER = time.monotonic() + 10_000


def codes(call: object) -> str:
    with pytest.raises(RenderError) as caught:
        call()  # type: ignore[operator]
    return caught.value.code


def jpeg_ok(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    assert image.format == "JPEG"
    return image


# --- Pictures ---------------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP", "HEIF"])
def test_every_picture_kind_becomes_our_own_jpeg_and_a_thumbnail(fmt: str) -> None:
    page = images.from_bytes(samples.picture(fmt, (400, 300)))
    assert (jpeg_ok(page.jpeg).size, page.width, page.height) == ((400, 300), 400, 300)
    assert max(jpeg_ok(page.thumb).size) <= limits.THUMB_SIDE


def test_a_large_picture_is_fitted_to_the_page_size() -> None:
    page = images.from_bytes(samples.picture("PNG", (4000, 1000)))
    assert page.width == limits.PAGE_MAX_SIDE and page.height == 550


def test_a_picture_with_transparency_is_flattened_on_white() -> None:
    out = io.BytesIO()
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(out, "PNG")
    assert jpeg_ok(images.from_bytes(out.getvalue()).jpeg).getpixel((5, 5)) == (255, 255, 255)


def test_nothing_of_the_original_survives_the_reencoding() -> None:
    out = io.BytesIO()
    image = Image.new("RGB", (50, 50), (10, 10, 10))
    exif = Image.Exif()
    exif[0x010E] = "SECRET-COMMENT-AND-LOCATION"
    image.save(out, "JPEG", exif=exif)
    assert b"SECRET-COMMENT" in out.getvalue()
    assert b"SECRET-COMMENT" not in images.from_bytes(out.getvalue()).jpeg


def test_a_picture_declaring_too_many_pixels_is_refused_before_it_is_decoded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(images, "MAX_SOURCE_PIXELS", 1000)
    assert (
        codes(lambda: images.from_bytes(samples.picture("PNG", (100, 100)))) == "PICTURE_TOO_LARGE"
    )


@pytest.mark.parametrize(
    "data",
    [
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 40,
        samples.picture("PNG")[:60],  # cut off
        b"\xff\xd8\xff\xe0" + b"junk" * 50,
        b"\x00\x00\x00\x18ftypheic" + b"\x00" * 50,  # a corrupted HEIC
        b"",
    ],
)
def test_a_corrupt_picture_is_a_plain_failure(data: bytes) -> None:
    assert codes(lambda: images.from_bytes(data)) == "UNREADABLE_PICTURE"


# --- PDF --------------------------------------------------------------------------------------


def test_a_pdf_becomes_one_picture_and_its_text_per_page() -> None:
    document = pdf_mod.open_pdf(samples.pdf(samples.PAGE_TEXT))
    pages = list(pdf_mod.render_pages(document, skip=set(), deadline=NEVER))
    assert [p.page_no for p in pages] == [1, 2, 3]
    assert all(p.error is None and p.image is not None for p in pages)
    assert "What is 2 + 3?" in (pages[0].text or "")
    assert jpeg_ok(pages[0].image.jpeg).size == (900, 600)  # type: ignore[union-attr]  # a small page, drawn at 3x


def test_pages_already_made_are_skipped_on_a_retry() -> None:
    document = pdf_mod.open_pdf(samples.pdf(samples.PAGE_TEXT))
    pages = list(pdf_mod.render_pages(document, skip={1, 2}, deadline=NEVER))
    assert [p.page_no for p in pages] == [3]


@pytest.mark.parametrize(
    "data", [b"%PDF-1.7 this is not really a pdf", b"%PDF-" + b"\x00" * 100, samples.pdf()[:80]]
)
def test_a_broken_pdf_is_a_plain_failure(data: bytes) -> None:
    assert codes(lambda: pdf_mod.open_pdf(data)) in {"UNREADABLE_DOCUMENT", "EMPTY_DOCUMENT"}


def test_too_many_pages_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_mod, "MAX_PAGES", 2)
    assert codes(lambda: pdf_mod.open_pdf(samples.pdf(samples.PAGE_TEXT))) == "TOO_MANY_PAGES"


def test_an_absurdly_large_page_fails_alone_and_the_rest_is_kept() -> None:
    big = samples.pdf(("huge",), page_size=(50_000, 50_000))
    page = next(iter(pdf_mod.render_pages(pdf_mod.open_pdf(big), skip=set(), deadline=NEVER)))
    assert page.error == "PAGE_TOO_LARGE" and page.image is None


def test_time_running_out_stops_the_render() -> None:
    document = pdf_mod.open_pdf(samples.pdf(samples.PAGE_TEXT))
    assert (
        codes(lambda: list(pdf_mod.render_pages(document, skip=set(), deadline=0.0))) == "TOO_SLOW"
    )


def test_active_content_in_a_pdf_is_never_run() -> None:
    hostile = samples.pdf().replace(
        b"/Type /Catalog",
        b"/Type /Catalog /OpenAction << /S /JavaScript /JS (app.alert(1)) >> "
        b"/AA << /O << /S /Launch /F (calc.exe) >> >> /Names << /EmbeddedFiles << >> >>",
    )
    document = pdf_mod.open_pdf(hostile)
    pages = list(pdf_mod.render_pages(document, skip=set(), deadline=NEVER))
    assert pages and all(p.error is None for p in pages)  # drawn like any page: nothing launched


# --- Word -------------------------------------------------------------------------------------


def read(data: bytes, skip: set[int] | None = None) -> list[pdf_mod.RenderedPage]:
    return list(docx_mod.read_pages(docx_mod.open_docx(data), skip=skip or set()))


def test_a_word_file_gives_its_text_in_order() -> None:
    pages = read(samples.docx())
    assert len(pages) == 1
    assert pages[0].text == "What is 2 + 3?\n\nA. 4  B. 5" and pages[0].image is None


def test_a_page_break_and_a_long_run_of_text_start_a_new_page() -> None:
    body = (
        samples.paragraph("first")
        + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        + samples.paragraph("second")
        + samples.paragraph("x" * (limits.DOCX_PAGE_CHARS + 1))
        + samples.paragraph("fourth")
    )
    assert [p.text for p in read(samples.docx(body))] == [
        "first",
        "second\n\n" + "x" * (limits.DOCX_PAGE_CHARS + 1),
        "fourth",
    ]


def test_a_table_is_kept_as_rows_of_text() -> None:
    cell = "<w:tc><w:p><w:r><w:t>{}</w:t></w:r></w:p></w:tc>"
    table = f"<w:tbl><w:tr>{cell.format('L1')}{cell.format('R1')}</w:tr></w:tbl>"
    assert read(samples.docx(table))[0].text == "L1\tR1"


def test_an_equation_is_kept_as_text_and_the_page_is_flagged_for_a_person() -> None:
    body = "<w:p><m:oMath><m:r><m:t>x=2</m:t></m:r></m:oMath></w:p>"
    page = read(samples.docx(body))[0]
    assert page.text == "x=2" and page.warnings == ["EQUATION_AS_TEXT"]


def test_embedded_pictures_are_reencoded_and_kept_with_their_page() -> None:
    data = samples.docx(
        samples.drawing("rId1") + samples.paragraph("see the figure"),
        parts={"word/media/image1.png": samples.picture("PNG", (60, 40))},
        rels=samples.image_rels("media/image1.png"),
    )
    page = read(data)[0]
    assert len(page.figures) == 1 and jpeg_ok(page.figures[0].jpeg).size == (60, 40)


def test_pictures_that_leave_the_archive_or_the_package_are_never_followed(
    tmp_path: pytest.TempPathFactory,
) -> None:
    data = samples.docx(
        samples.drawing("rId1")
        + samples.drawing("rId2")
        + samples.drawing("rId3")
        + samples.paragraph("t"),
        rels=samples.image_rels("../../etc/passwd.png", "/etc/hostname.png", "media/../../x.png"),
    )
    page = read(data)[0]
    assert page.figures == [] and page.text == "t"


def test_an_external_picture_link_is_not_fetched() -> None:
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" TargetMode="External" Type="http://schemas.openxmlformats.org/'
        'officeDocument/2006/relationships/image" Target="http://127.0.0.1:9/x.png"/></Relationships>'
    )
    page = read(samples.docx(samples.drawing("rId1") + samples.paragraph("t"), rels=rels))[0]
    assert page.figures == []


@pytest.mark.parametrize(
    "entity",
    [
        '<!DOCTYPE d [<!ENTITY x SYSTEM "file:///etc/passwd">]>',
        '<!DOCTYPE d [<!ENTITY x SYSTEM "http://127.0.0.1:9/">]>',
        '<!DOCTYPE d [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>',
    ],
)
def test_xml_entities_are_refused_so_nothing_is_read_or_fetched(entity: str) -> None:
    xml = (
        f"<?xml version='1.0'?>{entity}<w:document {samples._NS}><w:body>"
        f"{samples.paragraph('&x;')}</w:body></w:document>"
    ).encode()
    assert codes(lambda: read(samples.docx(document_xml=xml))) == "UNREADABLE_DOCUMENT"


def test_a_zip_that_is_not_a_word_file_is_refused() -> None:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("hello.txt", "hi")
    assert codes(lambda: docx_mod.open_docx(out.getvalue())) == "NOT_A_WORD_FILE"
    assert codes(lambda: docx_mod.open_docx(b"PK\x03\x04 not a zip")) == "UNREADABLE_DOCUMENT"


def test_a_zip_bomb_is_refused_from_its_directory_before_anything_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docx_mod, "DOCX_MAX_UNPACKED", 10_000)
    bomb = samples.docx(parts={"word/media/big.bin": b"\x00" * 200_000})
    assert codes(lambda: docx_mod.open_docx(bomb)) == "DOCUMENT_TOO_LARGE"


def test_a_zip_with_very_many_parts_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docx_mod, "DOCX_MAX_PARTS", 10)
    many = samples.docx(parts={f"word/p{i}.xml": b"x" for i in range(20)})
    assert codes(lambda: docx_mod.open_docx(many)) == "DOCUMENT_TOO_LARGE"


def test_a_document_part_larger_than_its_limit_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docx_mod, "DOCX_MAX_XML", 1000)
    big = samples.docx(samples.paragraph("y" * 5000))
    assert codes(lambda: docx_mod.open_docx(big)) == "DOCUMENT_TOO_LARGE"


def test_too_many_elements_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docx_mod, "DOCX_MAX_ELEMENTS", 20)
    assert codes(lambda: read(samples.docx(samples.paragraph("a") * 50))) == "DOCUMENT_TOO_LARGE"


def test_an_empty_word_file_is_refused() -> None:
    assert codes(lambda: read(samples.docx(""))) == "EMPTY_DOCUMENT"


def test_a_word_file_with_too_many_pages_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docx_mod, "MAX_PAGES", 3)
    breaks = ('<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + samples.paragraph("p")) * 10
    assert codes(lambda: read(samples.docx(breaks))) == "TOO_MANY_PAGES"
