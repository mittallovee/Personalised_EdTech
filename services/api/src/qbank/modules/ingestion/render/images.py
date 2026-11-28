"""A picture, or any rendered page, as a re-encoded JPEG and a thumbnail (threat U2, U8, U9).

Everything that leaves here is **our own encoding**: the original's bytes, metadata (location,
camera, comments) and anything hidden in it are gone. The pixel count is read from the header before
anything is decoded, and a picture that declares too many is refused.
"""

import io
from dataclasses import dataclass

import pillow_heif
from PIL import Image, ImageOps

from qbank.modules.ingestion.render.errors import RenderError
from qbank.modules.ingestion.render.limits import (
    JPEG_QUALITY,
    MAX_SOURCE_PIXELS,
    PAGE_MAX_SIDE,
    THUMB_SIDE,
)

pillow_heif.register_heif_opener()  # lets Pillow read HEIC (phone photographs)


@dataclass(frozen=True, slots=True)
class PageImage:
    jpeg: bytes
    width: int
    height: int
    thumb: bytes


def _jpeg(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


def from_pil(image: Image.Image) -> PageImage:
    """Flatten onto white (a picture with transparency), fit within the page size, encode."""
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.split()[-1])
        image = flat
    else:
        image = image.convert("RGB")
    image.thumbnail((PAGE_MAX_SIDE, PAGE_MAX_SIDE))
    thumb = image.copy()
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE))
    return PageImage(_jpeg(image), image.width, image.height, _jpeg(thumb))


def from_bytes(data: bytes, *, code: str = "UNREADABLE_PICTURE") -> PageImage:
    """The first frame of an uploaded picture as a page. ``code`` is what a failure is called."""
    try:
        with Image.open(io.BytesIO(data)) as opened:
            width, height = opened.size  # from the header: nothing is decoded yet
            if width < 1 or height < 1 or width * height > MAX_SOURCE_PIXELS:
                raise RenderError("PICTURE_TOO_LARGE")
            opened.seek(0)
            fixed = ImageOps.exif_transpose(opened)  # a phone photograph's own orientation
            return from_pil(fixed)
    except RenderError:
        raise
    except Exception:  # a corrupt or hostile picture, however the library reports it
        raise RenderError(code) from None
