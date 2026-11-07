"""Checking and cleaning an uploaded picture (M3 design note §5.7, threat T29).

The bytes are trusted for nothing: the format is found from the content (never the file name or the
declared type), the size in pixels is checked before the picture is decoded, and the picture is then
**re-encoded** from its pixels, so nothing else hiding in the file survives and location and camera
data are gone. PNG, JPEG and WebP only; SVG, GIF, HEIC, animation and anything else are refused.
"""

import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from qbank.core.errors import AppError

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SIDE = 20_000

# Pillow's name for each format we accept -> what we store it as.
_FORMATS: dict[str, tuple[str, str]] = {
    "PNG": ("image/png", "PNG"),
    "JPEG": ("image/jpeg", "JPEG"),
    "WEBP": ("image/webp", "WEBP"),
}


class ImageInvalid(AppError):
    status_code = 422
    code = "IMAGE_INVALID"


class ImageTooLarge(AppError):
    status_code = 413
    code = "IMAGE_TOO_LARGE"


@dataclass(frozen=True)
class CleanImage:
    data: bytes
    content_type: str
    width: int
    height: int


def clean_image(data: bytes) -> CleanImage:
    """The picture re-encoded from its pixels, or an error saying why it cannot be used."""
    if len(data) > MAX_BYTES:
        raise ImageTooLarge(f"The picture is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    if not data:
        raise ImageInvalid("The file is empty.")
    try:
        with warnings.catch_warnings():
            # A huge picture is refused below by our own, stricter limit; Pillow's warning about it
            # is not needed (and must not become an error).
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            picture = Image.open(io.BytesIO(data), formats=list(_FORMATS))
            return _reencode(picture)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ImageInvalid("This is not a PNG, JPEG or WebP picture that can be read.") from exc


def _reencode(picture: Image.Image) -> CleanImage:
    name = picture.format or ""
    if name not in _FORMATS:
        raise ImageInvalid("Only PNG, JPEG and WebP pictures can be used.")
    width, height = picture.size
    if width < 1 or height < 1 or width > MAX_SIDE or height > MAX_SIDE:
        raise ImageInvalid("The picture's size is not usable.")
    if width * height > MAX_PIXELS:
        raise ImageTooLarge("The picture has more than 40 megapixels.")
    if getattr(picture, "n_frames", 1) > 1:
        raise ImageInvalid("Animated pictures cannot be used.")
    picture.load()  # decode now, inside the guarded block
    content_type, save_as = _FORMATS[name]
    upright = ImageOps.exif_transpose(picture)  # honour the camera's rotation before dropping it
    # Keep transparency where the format has it; otherwise a plain RGB picture.
    has_alpha = "A" in upright.getbands() or "transparency" in upright.info
    if save_as == "JPEG" or not has_alpha:
        upright = upright.convert("RGB")
    else:
        upright = upright.convert("RGBA")
    # The encoders fall back to what the picture carries (a colour profile, text, EXIF) when they
    # are not given any, so what it carries is emptied: only the pixels go on.
    upright.info.clear()
    out = io.BytesIO()
    if save_as == "PNG":
        upright.save(out, "PNG", optimize=True)
    elif save_as == "JPEG":
        upright.save(out, "JPEG", quality=90, optimize=True)
    else:
        upright.save(out, "WEBP", quality=90, method=4)
    return CleanImage(out.getvalue(), content_type, upright.width, upright.height)
