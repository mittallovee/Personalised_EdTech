import copy

import pytest

from qbank.modules.questions.findings import Level
from qbank.modules.questions.passage_content import (
    SCHEMA_VERSION,
    TITLE_CHARS,
    empty_passage,
    validate_passage,
)
from qbank.modules.questions.rules import Rules

READY = {
    "schema_version": SCHEMA_VERSION,
    "title": "Free fall",
    "body": [{"kind": "paragraph", "text": "A stone is dropped from a tower."}],
}


def codes(content: object) -> list[tuple[str, str, Level]]:
    return [(f.path, f.code, f.level) for f in validate_passage(content)]


def test_a_complete_passage_has_no_findings() -> None:
    assert codes(READY) == []


def test_a_new_passage_says_what_is_still_to_do() -> None:
    assert codes(empty_passage()) == [
        ("title", "PASSAGE_TITLE_MISSING", Level.INCOMPLETE),
        ("body", "PASSAGE_BODY_EMPTY", Level.INCOMPLETE),
    ]


def test_blank_blocks_do_not_count_as_a_body() -> None:
    content = copy.deepcopy(READY)
    content["body"] = [
        {"kind": "paragraph", "text": "  "},
        {"kind": "equation", "format": "latex", "source": ""},
    ]
    assert ("body", "PASSAGE_BODY_EMPTY", Level.INCOMPLETE) in codes(content)


@pytest.mark.parametrize("content", [None, [], "text", 3])
def test_content_that_is_not_an_object_is_an_error(content: object) -> None:
    assert codes(content) == [("", "CONTENT_NOT_OBJECT", Level.ERROR)]


def test_unknown_fields_and_versions_are_errors() -> None:
    content = {**READY, "schema_version": 2, "stem": []}
    assert codes(content) == [
        ("schema_version", "SCHEMA_VERSION_UNSUPPORTED", Level.ERROR),
        ("stem", "FIELD_NOT_ALLOWED", Level.ERROR),
    ]
    assert ("schema_version", "SCHEMA_VERSION_UNSUPPORTED", Level.ERROR) in codes(
        {**READY, "schema_version": True}
    )


def test_a_passage_cannot_have_a_context_so_it_cannot_sit_under_another() -> None:
    content = {**READY, "context": {"passage_revision_id": "x", "ordinal": 1}}
    assert codes(content) == [("context", "FIELD_NOT_ALLOWED", Level.ERROR)]


def test_the_title_is_one_short_line_of_text() -> None:
    assert codes({**READY, "title": 5}) == [("title", "TEXT_NOT_STRING", Level.ERROR)]
    assert codes({**READY, "title": "x" * (TITLE_CHARS + 1)}) == [
        ("title", "PASSAGE_TITLE_TOO_LONG", Level.ERROR)
    ]
    assert codes({**READY, "title": "x" * TITLE_CHARS}) == []
    assert codes({**READY, "title": "two\nlines"}) == [
        ("title", "PASSAGE_TITLE_NOT_ONE_LINE", Level.ERROR)
    ]


def test_the_body_uses_the_same_block_checks_as_a_question() -> None:
    content = {**READY, "body": [{"kind": "poem"}, {"kind": "paragraph", "text": 5}]}
    found = codes(content)
    assert ("body[0].kind", "BLOCK_KIND_UNKNOWN", Level.ERROR) in found
    assert ("body[1].text", "TEXT_NOT_STRING", Level.ERROR) in found
    assert codes({**READY, "body": "text"}) == [("body", "BLOCKS_NOT_LIST", Level.ERROR)]


def test_pictures_are_allowed_but_need_a_description() -> None:
    content = {
        **READY,
        "body": [{"kind": "image", "asset_id": "00000000-0000-4000-8000-00000000000a"}],
    }
    assert ("body[0].alt_text", "IMAGE_ALT_MISSING", Level.INCOMPLETE) in codes(content)


def test_a_passage_over_the_size_limit_is_an_error_and_is_not_walked() -> None:
    small = Rules(revision_bytes=100)
    content = {**READY, "body": [{"kind": "paragraph", "text": "x" * 500}]}
    found = validate_passage(content, small)
    assert [f.code for f in found] == ["CONTENT_TOO_LARGE"]


def test_content_that_is_not_plain_data_is_an_error() -> None:
    assert codes({**READY, "title": {1, 2}}) == [("", "CONTENT_NOT_JSON", Level.ERROR)]
