import io
import struct
import zlib

import pytest
from PIL import Image

from qbank.modules.assets.images import (
    MAX_BYTES,
    ImageInvalid,
    ImageTooLarge,
    clean_image,
)


def _encode(picture: Image.Image, fmt: str, **options: object) -> bytes:
    out = io.BytesIO()
    picture.save(out, fmt, **options)
    return out.getvalue()


def _read(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def _png_header(width: int, height: int) -> bytes:
    """Just the start of a PNG that claims a size; nothing could be decoded from it."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body)
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    # The reader looks for the first picture-data chunk before it says what it found.
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b""))


@pytest.mark.parametrize(
    ("fmt", "content_type"),
    [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")],
)
def test_each_allowed_format_comes_back_as_the_same_kind_of_picture(
    fmt: str, content_type: str
) -> None:
    result = clean_image(_encode(Image.new("RGB", (30, 20), (200, 30, 30)), fmt))
    assert result.content_type == content_type
    assert (result.width, result.height) == (30, 20)
    assert _read(result.data).format == fmt
    assert _read(result.data).size == (30, 20)


def test_transparency_in_a_png_is_kept() -> None:
    result = clean_image(_encode(Image.new("RGBA", (4, 4), (255, 0, 0, 0)), "PNG"))
    assert _read(result.data).convert("RGBA").getpixel((0, 0))[3] == 0


def test_location_and_camera_data_are_removed_from_a_jpeg() -> None:
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"  # Make
    exif[0x8825] = {1: "N", 2: (28.0, 36.0, 0.0)}  # a GPS block
    original = _encode(Image.new("RGB", (10, 10)), "JPEG", exif=exif)
    assert b"SecretCameraMaker" in original
    result = clean_image(original)
    assert b"SecretCameraMaker" not in result.data
    assert len(_read(result.data).getexif()) == 0


def test_text_chunks_are_removed_from_a_png() -> None:
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text("Comment", "TextHiddenInThePng")
    original = _encode(Image.new("RGB", (6, 6)), "PNG", pnginfo=info)
    assert b"TextHiddenInThePng" in original
    assert b"TextHiddenInThePng" not in clean_image(original).data


def test_the_camera_rotation_is_applied_before_it_is_dropped() -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees to show it upright
    original = _encode(Image.new("RGB", (40, 20)), "JPEG", exif=exif)
    result = clean_image(original)
    assert (result.width, result.height) == (20, 40)


def test_bytes_hidden_after_the_picture_do_not_survive() -> None:
    picture = _encode(Image.new("RGB", (8, 8)), "PNG")
    polyglot = picture + b"<script>alert(1)</script>PK\x03\x04hidden-archive"
    result = clean_image(polyglot)
    assert b"<script>" not in result.data
    assert b"hidden-archive" not in result.data


def test_the_file_name_and_declared_type_do_not_matter_only_the_bytes() -> None:
    # A PNG is accepted whatever it is called; there is no name to trust in the first place.
    assert clean_image(_encode(Image.new("RGB", (3, 3)), "PNG")).content_type == "image/png"


@pytest.mark.parametrize(
    "data",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b"GIF89a\x01\x00\x01\x00\x00\x00\x00;",
        b"%PDF-1.7 not a picture",
        b"MZ\x90\x00 an executable",
        b"not a picture at all",
        b"\x89PNG\r\n\x1a\n",  # a signature and nothing else
    ],
)
def test_things_that_are_not_png_jpeg_or_webp_are_refused(data: bytes) -> None:
    with pytest.raises(ImageInvalid):
        clean_image(data)


def test_a_gif_is_refused_even_though_pillow_can_read_it() -> None:
    with pytest.raises(ImageInvalid):
        clean_image(_encode(Image.new("P", (4, 4)), "GIF"))


def test_a_bmp_and_a_tiff_are_refused() -> None:
    for fmt in ("BMP", "TIFF"):
        with pytest.raises(ImageInvalid):
            clean_image(_encode(Image.new("RGB", (4, 4)), fmt))


def test_an_animated_webp_is_refused() -> None:
    frames = [Image.new("RGB", (6, 6), (n * 40, 0, 0)) for n in range(3)]
    animated = _encode(frames[0], "WEBP", save_all=True, append_images=frames[1:], duration=50)
    with pytest.raises(ImageInvalid):
        clean_image(animated)


def test_an_empty_upload_is_refused() -> None:
    with pytest.raises(ImageInvalid):
        clean_image(b"")


def test_a_file_over_the_byte_limit_is_refused_before_it_is_read() -> None:
    with pytest.raises(ImageTooLarge):
        clean_image(b"\x89PNG" + b"0" * MAX_BYTES)


def test_a_picture_over_40_megapixels_is_refused_without_decoding_it() -> None:
    # 7,000 x 7,000 = 49 megapixels. Only the header exists, so a decode would fail differently.
    with pytest.raises(ImageTooLarge):
        clean_image(_png_header(7000, 7000))


def test_a_very_long_thin_picture_is_refused() -> None:
    with pytest.raises(ImageInvalid):
        clean_image(_png_header(30_000, 1))


def test_a_picture_that_claims_billions_of_pixels_is_refused_not_a_crash() -> None:
    with pytest.raises((ImageInvalid, ImageTooLarge)):
        clean_image(_png_header(2**31 - 1, 2**31 - 1))
