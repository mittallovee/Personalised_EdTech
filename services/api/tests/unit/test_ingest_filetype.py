"""M6 PR 6b: the kind of an upload comes from its first bytes only (T56, threat U8)."""

import pytest

from qbank.modules.ingestion.filetype import MAX_DOCUMENT_BYTES, MAX_IMAGE_BYTES, clean_name, sniff

HEADS = {
    "PDF": b"%PDF-1.7\n%\xe2\xe3\xcf\xd3",
    "DOCX": b"PK\x03\x04\x14\x00\x06\x00\x08\x00",
    "JPEG": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01",
    "PNG": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
    "WEBP": b"RIFF\x24\x00\x00\x00WEBPVP8 ",
    "HEIC": b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00",
}


@pytest.mark.parametrize(("kind", "head"), HEADS.items())
def test_each_kind_is_recognised_from_its_first_bytes(kind: str, head: bytes) -> None:
    found = sniff(head)
    assert found is not None and found.kind == kind


def test_documents_may_be_larger_than_pictures() -> None:
    assert sniff(HEADS["PDF"]).max_bytes == MAX_DOCUMENT_BYTES  # type: ignore[union-attr]
    assert sniff(HEADS["PNG"]).max_bytes == MAX_IMAGE_BYTES  # type: ignore[union-attr]
    assert MAX_IMAGE_BYTES < MAX_DOCUMENT_BYTES


@pytest.mark.parametrize(
    "head",
    [
        b"",
        b"MZ\x90\x00\x03\x00\x00\x00",  # a Windows program
        b"\x7fELF\x02\x01\x01\x00",  # a Linux program
        b"<svg xmlns='http://www.w3.org/2000/svg'>",  # SVG can carry script
        b"GIF89a\x01\x00\x01\x00",
        b"#!/bin/sh\nrm -rf /\n",
        b"<html><script>alert(1)</script>",
        b"RIFF\x24\x00\x00\x00WAVEfmt ",  # RIFF, but a sound
        b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00",  # a video, not a HEIC picture
        b" %PDF-1.7",  # the signature must be first
    ],
)
def test_anything_else_is_not_a_kind_we_read(head: bytes) -> None:
    assert sniff(head) is None


def test_a_name_is_only_a_label() -> None:
    assert clean_name("paper 1.pdf") == "paper 1.pdf"
    assert clean_name("../../etc/passwd") == "passwd"
    assert clean_name("C:\\Users\\me\\paper.pdf") == "paper.pdf"
    assert clean_name("a\x00b\nc.pdf") == "abc.pdf"
    assert clean_name("") == "document"
    assert clean_name("/") == "document"
    assert len(clean_name("x" * 500)) == 200
