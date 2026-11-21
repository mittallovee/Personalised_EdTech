"""Sealing a secret with a master key that never touches the database (ADR-0023).

AES-256-GCM through the ``cryptography`` library. Each stored key has its own random 96-bit nonce,
and a caller-chosen ``context`` (for AI keys: the coaching and the provider) plus the master
key's id are bound to it as associated data, so a ciphertext copied to another row, coaching or
provider does not open. The clear key exists only in
memory, for the length of a call.

The master keys come from the environment (``Settings``): one current key (new keys are sealed with
it) and any number of previous ones (they only open what was sealed before a rotation).
"""

import base64
import binascii
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32
NONCE_BYTES = 12
_KEY_ID = re.compile(r"[a-z0-9_-]{1,20}")


class KeyUnreadable(Exception):
    """A sealed secret could not be opened: wrong or missing master key, or a changed row."""


@dataclass(frozen=True, slots=True)
class Sealed:
    ciphertext: bytes
    nonce: bytes
    key_id: str


def parse_master_key(encoded: str) -> bytes:
    """A master key as given in the environment: standard or URL-safe base64 of 32 bytes."""
    text = encoded.strip()
    try:
        raw = base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)
    except binascii.Error, ValueError:
        raise ValueError("is not valid base64") from None
    if len(raw) != KEY_BYTES:
        raise ValueError(f"must decode to {KEY_BYTES} bytes")
    return raw


def parse_previous(encoded: str) -> dict[str, bytes]:
    """``id=base64,id=base64``: the earlier master keys, still needed to open older rows."""
    keys: dict[str, bytes] = {}
    for part in (p.strip() for p in encoded.split(",")):
        if not part:
            continue
        key_id, _, value = part.partition("=")
        if not _KEY_ID.fullmatch(key_id) or not value:
            raise ValueError("must look like id=base64,id=base64")
        keys[key_id] = parse_master_key(value)
    return keys


def build_keyring(master: str | None, key_id: str, previous: str | None) -> Keyring | None:
    """The keyring for the environment's values, or None when no master key is set. Raises
    ``ValueError`` (never quoting a value) when one is malformed."""
    if master is None or not master.strip():
        return None
    keys = parse_previous(previous) if previous else {}
    keys[key_id] = parse_master_key(master)
    return Keyring(key_id, keys)


class Keyring:
    """The master keys of this process: seals with the current one, opens with any."""

    def __init__(self, current_id: str, keys: Mapping[str, bytes]) -> None:
        if not _KEY_ID.fullmatch(current_id):
            raise ValueError("the master key id must be 1 to 20 of a-z, 0-9, _ or -")
        if current_id not in keys:
            raise ValueError("the current master key is missing")
        if any(len(key) != KEY_BYTES for key in keys.values()):
            raise ValueError(f"every master key must be {KEY_BYTES} bytes")
        self.current_id = current_id
        self._keys = dict(keys)

    @staticmethod
    def _bound(key_id: str, context: str) -> bytes:
        return f"qbank-secretbox|{key_id}|{context}".encode()

    def seal(self, plaintext: str, *, context: str) -> Sealed:
        nonce = secrets.token_bytes(NONCE_BYTES)
        aad = self._bound(self.current_id, context)
        ciphertext = AESGCM(self._keys[self.current_id]).encrypt(
            nonce, plaintext.encode("utf-8"), aad
        )
        return Sealed(ciphertext, nonce, self.current_id)

    def open(self, sealed: Sealed, *, context: str) -> str:
        key = self._keys.get(sealed.key_id)
        if key is None:
            raise KeyUnreadable("the master key that sealed this key is not configured")
        aad = self._bound(sealed.key_id, context)
        try:
            return AESGCM(key).decrypt(sealed.nonce, sealed.ciphertext, aad).decode("utf-8")
        except InvalidTag, UnicodeDecodeError, ValueError:
            raise KeyUnreadable("the stored key could not be opened") from None
