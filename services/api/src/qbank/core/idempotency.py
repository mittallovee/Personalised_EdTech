"""Safe retries for "create" requests (API style guide §6, ADR-0015).

A client sends an ``Idempotency-Key`` header (any unique string, usually a UUID) with a create
request. If the response is lost and the client sends the same request again with the same key,
the server must not create a second resource. ``claim`` records the key in the caller's
transaction and says whether this is the first time it was seen:

- first time: returns the new resource's id (the caller goes on to create it);
- a retry with the same body: returns the id of the resource the first request created;
- the same key with a different body: ``409 IDEMPOTENCY_KEY_REUSED``.

Keys belong to the person sending them and are scoped by operation. After 24 hours a key is
forgotten and may be used again.
"""

import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi import Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.errors import Conflict

KEEP_FOR = "24 hours"

# Header declared on create endpoints, so it appears in the API contract.
IdempotencyKeyHeader = Header(
    alias="Idempotency-Key",
    min_length=1,
    max_length=200,
    description="Any unique string (e.g. a UUID). Retrying with the same key never creates twice.",
)

_FORGET_EXPIRED = text(
    "DELETE FROM idempotency_keys WHERE actor_user_id = :actor AND operation = :operation"
    " AND key = :key AND created_at < now() - CAST(:keep_for AS interval)"
)
_CLAIM = text(
    "INSERT INTO idempotency_keys (actor_user_id, operation, key, request_hash, resource_id)"
    " VALUES (:actor, :operation, :key, :request_hash, :resource_id)"
    " ON CONFLICT (actor_user_id, operation, key) DO NOTHING"
)
_FIND = text(
    "SELECT request_hash, resource_id FROM idempotency_keys"
    " WHERE actor_user_id = :actor AND operation = :operation AND key = :key"
)


def request_hash(body: dict[str, Any]) -> str:
    """A stable fingerprint of a request body (key order and spacing don't matter)."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def claim(
    session: Session,
    *,
    actor_user_id: UUID,
    operation: str,
    key: str,
    body: dict[str, Any],
    new_resource_id: UUID,
) -> UUID:
    """Record ``key`` for this request; return the resource id it stands for (see module doc).

    Needs ``actor_user_id`` in the tenant context. A concurrent request with the same key waits
    for this transaction, then sees its outcome.
    """
    params = {"actor": actor_user_id, "operation": operation, "key": key}
    session.execute(_FORGET_EXPIRED, {**params, "keep_for": KEEP_FOR})
    session.execute(
        _CLAIM, {**params, "request_hash": request_hash(body), "resource_id": new_resource_id}
    )
    existing = session.execute(_FIND, params).one()
    if existing.request_hash != request_hash(body):
        raise Conflict(
            "This Idempotency-Key was already used for a different request.",
            code="IDEMPOTENCY_KEY_REUSED",
        )
    resource_id: UUID = existing.resource_id
    return resource_id
