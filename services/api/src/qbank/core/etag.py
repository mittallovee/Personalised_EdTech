"""Revisions and ``If-Match`` (API style guide §6).

Editable resources carry a ``revision`` number, sent to clients as the ``ETag`` header
(``"rev-12"``). A change must send the ETag it was based on in ``If-Match``. If someone else
changed the resource in between, the revisions differ and the change is refused with 412, so a
stale screen never silently overwrites newer work.
"""

import re

from fastapi import Header

from qbank.core.errors import PreconditionFailed, PreconditionRequired

_ETAG = re.compile(r'(?:W/)?"rev-(\d{1,9})"')
_FLOW_ETAG = re.compile(r'(?:W/)?"flow-(\d{1,9})"')

IfMatchHeader = Header(
    alias="If-Match",
    max_length=64,
    description='The ETag from your last read, e.g. "rev-3". Required; a newer revision gives 412.',
)


def etag(revision: int) -> str:
    return f'"rev-{revision}"'


def flow_etag(flow_revision: int) -> str:
    """The workflow ETag of a question version (M4): it moves with every change of state, and is a
    different value space from ``"rev-N"``, so the two cannot be mixed up."""
    return f'"flow-{flow_revision}"'


def require_if_match(if_match: str | None, current_revision: int) -> None:
    """Raise 428 if ``If-Match`` is missing, 412 if it names another revision."""
    if not if_match:
        raise PreconditionRequired("Send the If-Match header with the ETag you last read.")
    match = _ETAG.fullmatch(if_match.strip())
    if match is None or int(match.group(1)) != current_revision:
        raise PreconditionFailed(
            "Someone else changed this in the meantime. Reload it and try again.",
            details={"current_etag": etag(current_revision)},
        )


def require_flow_if_match(if_match: str | None, current_flow_revision: int) -> None:
    """Like ``require_if_match`` for the workflow ETag: 428 if missing, 412 if it names another."""
    if not if_match:
        raise PreconditionRequired("Send the If-Match header with the ETag you last read.")
    match = _FLOW_ETAG.fullmatch(if_match.strip())
    if match is None or int(match.group(1)) != current_flow_revision:
        raise PreconditionFailed(
            "Someone else changed this in the meantime. Reload it and try again.",
            details={"current_etag": flow_etag(current_flow_revision)},
        )
