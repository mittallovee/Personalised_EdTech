"""Page cursors for the catalogue lists: where the last item shown sits in the list's order.

A cursor holds the ordering values of the last item *as they were when the page was sent* (its
sort order, normalised name and id), not just its id. If that item is renamed or moved before the
next request, the next page still starts where the first one ended, with nothing skipped or
repeated. Nothing in a cursor is a secret or grants anything: it only positions a read inside the
caller's own, row-level-secured list, so a forged one reveals nothing.

Layout (then URL-safe base64): 1 format byte, 16 bytes of id, 4 bytes of sort order, then the name
key as UTF-8. The format byte means a cursor from any other format (the syllabus list once used
base64 JSON) is refused with a 400 and never misread.
"""

import base64
import binascii
import struct
from uuid import UUID

from qbank.core.errors import MalformedRequest
from qbank.modules.taxonomy.catalogues import MAX_NAME_KEY_LENGTH

INVALID_CURSOR = "The page cursor is not valid. Start again from the first page."
_FORMAT = b"\x01"
_ID_AND_ORDER = 21  # bytes before the name key: format, id, sort order
# The longest cursor possible: a name key of MAX_NAME_KEY_LENGTH characters at 4 bytes each in
# UTF-8, plus the 21 fixed bytes, as base64 (4 characters per 3 bytes) is 2,160. The limit leaves a
# little room; it was 300 before names could produce cursors that long.
MAX_CURSOR_LENGTH = 2300


def encode_cursor(sort_order: int, key: str, item_id: UUID) -> str:
    raw = _FORMAT + item_id.bytes + struct.pack(">i", sort_order) + key.encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[int, str, UUID]:
    """Inverse of ``encode_cursor``; a damaged cursor is a 400, never a 500."""
    try:
        raw = base64.urlsafe_b64decode((cursor + "=" * (-len(cursor) % 4)).encode())
        if len(raw) < _ID_AND_ORDER or raw[:1] != _FORMAT:
            raise ValueError("too short, or another format")
        item_id = UUID(bytes=raw[1:17])
        (sort_order,) = struct.unpack(">i", raw[17:_ID_AND_ORDER])
        key = raw[_ID_AND_ORDER:].decode()
        if len(key) > MAX_NAME_KEY_LENGTH:
            raise ValueError("name too long")
    except binascii.Error, UnicodeDecodeError, ValueError, struct.error:
        raise MalformedRequest(INVALID_CURSOR) from None
    return sort_order, key, item_id
