"""What kind of file an upload is, from its first bytes (M6 6b, G-01, threat U8).

This is a **sniff**, not a parse: it reads a few bytes and nothing else, so it is safe to run in
the API process (ADR-0024). The name and the declared ``Content-Type`` are never used. A file that
passes here is still opened only in the sandbox, which checks its real structure and fails it if
it is not what its first bytes said.
"""

from dataclasses import dataclass

from qbank.core.errors import AppError

MB = 1024 * 1024
MAX_DOCUMENT_BYTES = 50 * MB
MAX_IMAGE_BYTES = 10 * MB

_HEIC_BRANDS = frozenset(
    {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs", b"mif1", b"msf1"}
)


@dataclass(frozen=True, slots=True)
class Detected:
    kind: str  # PDF, DOCX, JPEG, PNG, WEBP, HEIC
    content_type: str  # what the original is served as, fixed by us, never from the upload
    max_bytes: int


_PDF = Detected("PDF", "application/pdf", MAX_DOCUMENT_BYTES)
_DOCX = Detected(
    "DOCX",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    MAX_DOCUMENT_BYTES,
)


def sniff(head: bytes) -> Detected | None:
    """The kind of file these first bytes (at least 16 if the file has them) say it is, else None.

    A ZIP is taken to be a Word file only provisionally: whether it really is one is for the sandbox
    to say; every other ZIP is refused there as an unreadable document."""
    if head.startswith(b"%PDF-"):
        return _PDF
    if head.startswith(b"PK\x03\x04"):
        return _DOCX
    if head.startswith(b"\xff\xd8\xff"):
        return Detected("JPEG", "image/jpeg", MAX_IMAGE_BYTES)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return Detected("PNG", "image/png", MAX_IMAGE_BYTES)
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return Detected("WEBP", "image/webp", MAX_IMAGE_BYTES)
    if head[4:8] == b"ftyp" and head[8:12] in _HEIC_BRANDS:
        return Detected("HEIC", "image/heic", MAX_IMAGE_BYTES)
    return None


def clean_name(raw: str) -> str:
    """The file name as a label: control characters and path parts removed, at most 200 characters.
    Never used to build a path or a storage key."""
    name = raw.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:200] or "document"


class DocumentTooLarge(AppError):
    status_code = 413
    code = "INGEST_FILE_TOO_LARGE"


class DocumentInvalid(AppError):
    status_code = 422
    code = "INGEST_FILE_INVALID"
