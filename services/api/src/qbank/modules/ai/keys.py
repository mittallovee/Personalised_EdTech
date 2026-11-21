"""Storing, showing (masked) and removing a coaching's provider keys (H-02, ADR-0023).

Only admins and the Owner manage keys. A key goes in through ``set_key`` and is sealed at once; the
only things that come back out are whether one is stored and its last four characters. ``open_key``
is for the server's own provider calls and is never behind a route.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PreconditionFailed, ValidationFailed
from qbank.core.permissions import Action, require
from qbank.core.secretbox import Keyring, KeyUnreadable, Sealed
from qbank.modules.ai.models import ProviderKey
from qbank.modules.ai.names import Provider
from qbank.modules.audit.public import record_event

ENTITY_TYPE = "ai_provider_key"


def _context(organization_id: UUID, provider: Provider) -> str:
    """What a sealed key is bound to: the coaching and the provider it belongs to."""
    return f"ai-key|{organization_id}|{provider.value}"


MIN_KEY = 8
MAX_KEY = 512


@dataclass(frozen=True, slots=True)
class KeyStatus:
    provider: Provider
    configured: bool
    last4: str | None
    updated_at: datetime | None


def not_configured() -> Conflict:
    return Conflict(
        "AI keys cannot be stored on this server yet: ask whoever runs it to set the master"
        " encryption key (AI_KEYS_MASTER_KEY).",
        code="AI_NOT_CONFIGURED",
    )


def _organization_id(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to keep keys for.")
    return organization_id


def clean_key(typed: str) -> str:
    """The key without the spaces around it, if it looks like an API key: printable ASCII with no
    space inside, 8 to 512 characters. Anything else is refused without echoing it."""
    key = typed.strip()
    if not MIN_KEY <= len(key) <= MAX_KEY or any(not 0x21 <= ord(c) <= 0x7E for c in key):
        raise ValidationFailed(
            f"That does not look like an API key ({MIN_KEY} to {MAX_KEY} letters, digits or"
            " symbols, no spaces). Copy it again from the provider.",
            code="AI_KEY_INVALID",
        )
    return key


def list_keys(session: Session, principal: Principal) -> list[KeyStatus]:
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _organization_id(principal)
    rows = {
        row.provider: row
        for row in session.scalars(
            select(ProviderKey).where(ProviderKey.organization_id == organization_id)
        )
    }
    out: list[KeyStatus] = []
    for provider in Provider:
        row = rows.get(provider.value)
        out.append(
            KeyStatus(
                provider,
                row is not None,
                row.last4 if row is not None else None,
                row.updated_at if row is not None else None,
            )
        )
    return out


def set_key(
    session: Session,
    principal: Principal,
    keyring: Keyring | None,
    provider: Provider,
    typed: str,
    *,
    request_id: str | None,
) -> KeyStatus:
    """Store (or replace) the coaching's key for a provider. The change is audited with the last
    four characters only."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    if keyring is None:
        raise not_configured()
    organization_id = _organization_id(principal)
    key = clean_key(typed)
    sealed = keyring.seal(key, context=_context(organization_id, provider))
    row = session.scalars(
        select(ProviderKey)
        .where(
            ProviderKey.organization_id == organization_id, ProviderKey.provider == provider.value
        )
        .with_for_update()
    ).first()
    before: dict[str, object] = {"configured": False}
    if row is None:
        row = ProviderKey(
            organization_id=organization_id,
            provider=provider.value,
            ciphertext=sealed.ciphertext,
            nonce=sealed.nonce,
            key_id=sealed.key_id,
            last4=key[-4:],
            created_by=principal.user_id,
        )
        session.add(row)
    else:
        before = {"configured": True, "last4": row.last4}
        row.ciphertext = sealed.ciphertext
        row.nonce = sealed.nonce
        row.key_id = sealed.key_id
        row.last4 = key[-4:]
        row.updated_at = datetime.now(UTC)
        row.revision += 1
    session.flush()
    record_event(
        session,
        action="AI_KEY_REPLACED" if before["configured"] else "AI_KEY_SET",
        entity_type=ENTITY_TYPE,
        entity_id=row.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before=before,
        after={"provider": provider.value, "configured": True, "last4": row.last4},
    )
    return KeyStatus(provider, True, row.last4, row.updated_at)


def delete_key(
    session: Session, principal: Principal, provider: Provider, *, request_id: str | None
) -> None:
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _organization_id(principal)
    row = session.scalars(
        select(ProviderKey)
        .where(
            ProviderKey.organization_id == organization_id, ProviderKey.provider == provider.value
        )
        .with_for_update()
    ).first()
    if row is None:
        raise NotFound("No key is stored for that provider.")
    last4 = row.last4
    row_id = row.id
    session.delete(row)
    session.flush()
    record_event(
        session,
        action="AI_KEY_DELETED",
        entity_type=ENTITY_TYPE,
        entity_id=row_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before={"provider": provider.value, "configured": True, "last4": last4},
        after={"provider": provider.value, "configured": False},
    )


def open_key(
    session: Session, keyring: Keyring | None, organization_id: UUID, provider: Provider
) -> str | None:
    """The clear key for a provider call, or ``None`` when the coaching has none stored. For the
    server's own calls only: never returned by a route, never logged. Raises ``KeyUnreadable`` when
    a stored key cannot be opened (the master key was changed without a rotation)."""
    row = session.scalars(
        select(ProviderKey).where(
            ProviderKey.organization_id == organization_id, ProviderKey.provider == provider.value
        )
    ).first()
    if row is None:
        return None
    if keyring is None:
        raise KeyUnreadable("no master key is configured")
    return keyring.open(
        Sealed(row.ciphertext, row.nonce, row.key_id), context=_context(organization_id, provider)
    )


def reseal_all(session: Session, keyring: Keyring, organization_id: UUID) -> tuple[int, int]:
    """Seal every key of one coaching again under the current master key (``qbank
    rotate-ai-keys``). Returns how many were resealed and how many were already current. A key that
    cannot be opened stops the rotation with ``KeyUnreadable`` rather than being left behind."""
    resealed = current = 0
    for row in session.scalars(
        select(ProviderKey).where(ProviderKey.organization_id == organization_id).with_for_update()
    ):
        if row.key_id == keyring.current_id:
            current += 1
            continue
        provider = Provider(row.provider)
        context = _context(organization_id, provider)
        clear = keyring.open(Sealed(row.ciphertext, row.nonce, row.key_id), context=context)
        sealed = keyring.seal(clear, context=context)
        row.ciphertext = sealed.ciphertext
        row.nonce = sealed.nonce
        row.key_id = sealed.key_id
        row.updated_at = datetime.now(UTC)
        row.revision += 1
        resealed += 1
    session.flush()
    return resealed, current
