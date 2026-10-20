"""Cursor pagination for lists (API style guide §4).

A cursor is the position of the last row on a page, sent back to fetch the next page. It is opaque
to clients (base64 of JSON) and checked strictly here, so a damaged cursor is a 400, never a 500.
"""

import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.core.errors import MalformedRequest

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class PageInfo(BaseModel):
    next_cursor: str | None = Field(description="Pass as `cursor` to get the next page.")
    has_more: bool


def encode_cursor(created_at: datetime, row_id: UUID) -> str:
    raw = json.dumps({"t": created_at.isoformat(), "id": str(row_id)}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Inverse of ``encode_cursor``. Newest-first lists continue strictly after this position."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
        created_at = datetime.fromisoformat(data["t"])
        if created_at.tzinfo is None:
            raise ValueError("cursor time has no time zone")
        return created_at, UUID(data["id"])
    except (
        binascii.Error,
        json.JSONDecodeError,
        UnicodeDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        raise MalformedRequest(
            "The page cursor is not valid. Start again from the first page."
        ) from None
