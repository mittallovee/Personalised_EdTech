"""The two ETag spaces: ``"rev-N"`` for the text being edited and ``"flow-N"`` for the review
workflow of a question version (M4). One must never be accepted for the other."""

import pytest

from qbank.core.errors import PreconditionFailed, PreconditionRequired
from qbank.core.etag import etag, flow_etag, require_flow_if_match, require_if_match


def test_the_two_etags_look_different() -> None:
    assert etag(3) == '"rev-3"'
    assert flow_etag(3) == '"flow-3"'


def test_a_matching_etag_passes_and_a_weak_one_is_forgiven() -> None:
    require_if_match('"rev-4"', 4)
    require_if_match('W/"rev-4"', 4)
    require_flow_if_match('"flow-4"', 4)
    require_flow_if_match(' W/"flow-4" ', 4)


@pytest.mark.parametrize("missing", [None, ""])
def test_a_missing_if_match_is_428(missing: str | None) -> None:
    with pytest.raises(PreconditionRequired):
        require_flow_if_match(missing, 1)


@pytest.mark.parametrize(
    "sent", ['"flow-2"', '"flow-0"', '"rev-3"', "flow-3", '"flow-"', '"flow-3x"', "*", '"FLOW-3"']
)
def test_anything_but_the_current_flow_etag_is_412_with_the_current_one(sent: str) -> None:
    with pytest.raises(PreconditionFailed) as caught:
        require_flow_if_match(sent, 3)
    assert caught.value.details == {"current_etag": '"flow-3"'}


def test_a_workflow_etag_is_not_accepted_for_a_revision_or_the_other_way_round() -> None:
    with pytest.raises(PreconditionFailed) as caught:
        require_if_match('"flow-3"', 3)
    assert caught.value.details == {"current_etag": '"rev-3"'}
    with pytest.raises(PreconditionFailed):
        require_flow_if_match('"rev-3"', 3)
