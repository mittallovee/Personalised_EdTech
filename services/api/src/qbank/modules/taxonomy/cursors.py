"""Page cursors for the catalogue lists: just the id of the last item shown.

A cursor never carries a name, however long or non-Latin it is, so it stays short. The next page
starts after that item's current position in the list's order. An id that is not in this coaching
(or that nobody has) is a damaged cursor, never a way to learn that it exists elsewhere.
"""

import base64
import binascii
from uuid import UUID

from qbank.core.errors import MalformedRequest

INVALID_CURSOR = "The page cursor is not valid. Start again from the first page."
# A cursor is 48 characters. The limit stays at 300, what the syllabus list already allowed: a lower
# one would be a breaking change to a published endpoint.
MAX_CURSOR_LENGTH = 300


def encode_cursor(item_id: UUID) -> str:
    return base64.urlsafe_b64encode(str(item_id).encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> UUID:
    """Inverse of ``encode_cursor``; a damaged cursor is a 400, never a 500."""
    try:
        text = base64.urlsafe_b64decode((cursor + "=" * (-len(cursor) % 4)).encode()).decode()
        return UUID(text)
    except binascii.Error, UnicodeDecodeError, ValueError:
        raise MalformedRequest(INVALID_CURSOR) from None
