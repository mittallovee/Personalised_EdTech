"""Small made-up documents for the ingestion tests: a PDF, a Word file, pictures, and hostile ones.

Everything is built here from text and a few bytes, so no real coaching content and no binary file
is ever committed. A PDF is written by hand (pdfium repairs what a strict reader would not need).
"""

import io
import zipfile
from typing import Any

import pillow_heif
from PIL import Image

pillow_heif.register_heif_opener()

PAGE_TEXT = ("What is 2 + 3?", "A ball falls for two seconds.", "Choose the correct option.")


def picture(
    fmt: str = "PNG", size: tuple[int, int] = (120, 80), colour: Any = (30, 90, 200)
) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, colour).save(out, fmt)
    return out.getvalue()


def pdf(
    texts: tuple[str, ...] = PAGE_TEXT[:2],
    *,
    page_size: tuple[int, int] | list[tuple[int, int]] = (300, 200),
) -> bytes:
    """A PDF with one page per text. ``page_size`` is in points (it may be made absurdly big)."""
    objects: list[bytes] = []

    def add(body: str) -> int:
        objects.append(body.encode("latin-1"))
        return len(objects)

    add("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(texts)))
    add(f"<< /Type /Pages /Kids [{kids}] /Count {len(texts)} >>")
    add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")  # object 3
    sizes = page_size if isinstance(page_size, list) else [page_size] * len(texts)
    for text, (width, height) in zip(texts, sizes, strict=True):
        stream = f"BT /F1 18 Tf 20 100 Td ({text}) Tj ET"
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}]"
            f" /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects) + 2} 0 R >>"
        )
        add(page)
        add(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    )
    return bytes(out)


_CONTENT_TYPES = (
    '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/></Types>'
)
_NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)


def paragraph(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def docx(
    body: str | None = None,
    *,
    parts: dict[str, bytes] | None = None,
    rels: str | None = None,
    document_xml: bytes | None = None,
) -> bytes:
    """A Word file. ``body`` is the XML inside ``w:body``; ``parts`` adds or replaces ZIP parts."""
    body = body if body is not None else paragraph("What is 2 + 3?") + paragraph("A. 4  B. 5")
    document = (
        document_xml
        or f"<?xml version='1.0'?><w:document {_NS}><w:body>{body}</w:body></w:document>".encode()
    )
    files: dict[str, bytes] = {
        "[Content_Types].xml": _CONTENT_TYPES.encode(),
        "word/document.xml": document,
    }
    if rels is not None:
        files["word/_rels/document.xml.rels"] = rels.encode()
    files.update(parts or {})
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return out.getvalue()


def image_rels(*targets: str) -> str:
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        f'relationships/image" Target="{target}"/>'
        for i, target in enumerate(targets, start=1)
    )
    return f'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'


def drawing(rid: str) -> str:
    return f'<w:p><w:r><w:drawing><a:blip r:embed="{rid}"/></w:drawing></w:r></w:p>'
