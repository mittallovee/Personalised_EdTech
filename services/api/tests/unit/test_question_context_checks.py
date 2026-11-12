from uuid import UUID

import pytest

from qbank.modules.questions.context_checks import check_pin, passage_pin
from qbank.modules.questions.findings import Level

A = UUID("00000000-0000-4000-8000-00000000000a")
B = UUID("00000000-0000-4000-8000-00000000000b")


def child(pin: object) -> dict[str, object]:
    return {"context": {"passage_revision_id": pin, "ordinal": 1}}


def test_the_pinned_revision_is_read_from_the_context() -> None:
    assert passage_pin(child(str(A))) == A


@pytest.mark.parametrize(
    "content",
    [None, [], "x", {}, {"context": None}, {"context": "x"}, child(None), child(5), child("nope")],
)
def test_anything_else_has_no_pin_and_is_left_to_the_shape_checks(content: object) -> None:
    assert passage_pin(content) is None
    assert check_pin(content, set()) == []


def test_a_pin_that_is_a_checkpoint_of_this_coaching_is_fine() -> None:
    assert check_pin(child(str(A)), {A, B}) == []


def test_a_pin_that_is_not_available_is_an_error_at_the_pin() -> None:
    findings = check_pin(child(str(A)), {B})
    assert [(f.path, f.code, f.level) for f in findings] == [
        ("context.passage_revision_id", "CONTEXT_PASSAGE_NOT_AVAILABLE", Level.ERROR)
    ]


@pytest.mark.parametrize(
    "spelling",
    [
        str(A).upper(),
        str(A).replace("-", ""),
        "{" + str(A) + "}",
        "urn:uuid:" + str(A),
        " " + str(A),
    ],
)
def test_only_the_standard_spelling_of_an_id_is_a_pin(spelling: str) -> None:
    # The passage's children are found by matching this text, so one spelling is allowed.
    assert passage_pin(child(spelling)) is None
