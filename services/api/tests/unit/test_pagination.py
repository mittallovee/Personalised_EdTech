from datetime import UTC, datetime

import pytest

from qbank.core.errors import MalformedRequest
from qbank.core.ids import new_id
from qbank.core.pagination import decode_cursor, encode_cursor


def test_cursor_round_trip() -> None:
    position = (datetime(2026, 10, 21, 9, 30, 0, 123456, tzinfo=UTC), new_id())
    assert decode_cursor(encode_cursor(*position)) == position


@pytest.mark.parametrize(
    "cursor",
    [
        "",
        "not base64 at all!",
        "bm90IGpzb24",  # "not json"
        "WzEsIDJd",  # a JSON list, not an object
        "eyJ0IjogIjIwMjYtMTAtMjFUMDk6MzA6MDAiLCAiaWQiOiAieCJ9",  # bad id, naive time
        # valid id, but a time without a time zone
        "eyJ0IjogIjIwMjYtMTAtMjFUMDk6MzA6MDAiLCAiaWQiOiAiMDE5YTAwMDAtMDAwMC03MDAwLTgwMDAtMDAwMDAwMDAwMDAwIn0",
    ],
)
def test_damaged_cursor_is_a_malformed_request(cursor: str) -> None:
    with pytest.raises(MalformedRequest):
        decode_cursor(cursor)
