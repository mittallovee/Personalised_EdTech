"""The passage a child question sits under (M3 design note §5.6, D-14).

``formats.check_context`` checks the shape of ``context``. Here the passage revision it names is
checked against what the lookup found for this coaching: it must be a checkpoint (a frozen
revision), because a child pins one exact revision and a draft would change underneath it. A pure
function of the content and the lookup: the service does the database reading.
"""

from collections.abc import Collection
from uuid import UUID

from qbank.modules.questions.blocks import as_dict
from qbank.modules.questions.findings import Finding, Findings, at_key


def passage_pin(content: object) -> UUID | None:
    """The passage revision a question names in its ``context``, when that is a readable id."""
    obj = as_dict(content)
    context = as_dict(obj.get("context")) if obj is not None else None
    pinned = context.get("passage_revision_id") if context is not None else None
    if not isinstance(pinned, str):
        return None
    try:
        parsed = UUID(pinned)
    except ValueError:
        return None
    # Only the standard spelling counts as a pin: children are found by matching this text.
    return parsed if str(parsed) == pinned else None


def check_pin(content: object, checkpoints: Collection[UUID]) -> list[Finding]:
    """An error when the passage revision is not a checkpoint of this coaching."""
    pinned = passage_pin(content)
    if pinned is None or pinned in checkpoints:
        return []
    out = Findings()
    out.error(
        at_key("context", "passage_revision_id"),
        "CONTEXT_PASSAGE_NOT_AVAILABLE",
        "This passage is not available: choose a saved checkpoint of a passage in your coaching.",
    )
    return out.items
