"""M3 PR 2b: page cursors of the catalogue lists hold the ordering values, within a known limit."""

from uuid import UUID

import pytest

from qbank.core.errors import MalformedRequest
from qbank.modules.taxonomy.catalogues import MAX_NAME_KEY_LENGTH
from qbank.modules.taxonomy.cursors import MAX_CURSOR_LENGTH, decode_cursor, encode_cursor

ITEM = UUID("01a16663-fd91-7438-9f2b-4c28d9a37e10")


@pytest.mark.parametrize("key", ["", "kinematics", "क" * 200, "\U0001f600" * 400])
@pytest.mark.parametrize("sort_order", [0, 7, 100_000])
def test_a_cursor_gives_back_what_went_in(key: str, sort_order: int) -> None:
    assert decode_cursor(encode_cursor(sort_order, key, ITEM)) == (sort_order, key, ITEM)


def test_the_longest_possible_cursor_fits_the_limit_the_api_sets() -> None:
    """A name key of the most characters, each needing the most bytes (4 in UTF-8)."""
    worst = encode_cursor(100_000, "\U0001f600" * MAX_NAME_KEY_LENGTH, ITEM)

    assert len(worst) <= MAX_CURSOR_LENGTH
    assert len(worst) > MAX_CURSOR_LENGTH - 200  # and the limit is not needlessly large


@pytest.mark.parametrize(
    "cursor",
    ["", "not-a-cursor", "c2hvcnQ", encode_cursor(0, "x" * (MAX_NAME_KEY_LENGTH + 1), ITEM)],
)
def test_a_damaged_cursor_is_refused(cursor: str) -> None:
    with pytest.raises(MalformedRequest):
        decode_cursor(cursor)
