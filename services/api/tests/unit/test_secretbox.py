"""M5 PR 5a-1: sealing a secret with a master key that stays outside the database (ADR-0023; T43).

AES-256-GCM: a stored secret opens only with the master key that sealed it, in the context it was
sealed for, and nothing about a failure says what the secret was.
"""

import base64
import dataclasses

import pytest

from qbank.core.config import AppEnv, Settings
from qbank.core.secretbox import (
    KEY_BYTES,
    NONCE_BYTES,
    Keyring,
    KeyUnreadable,
    build_keyring,
    parse_master_key,
    parse_previous,
)

RAW = bytes(range(32))
OTHER = bytes(range(1, 33))
CONTEXT = "ai-key|org-1|ANTHROPIC"


def ring(current: str = "k1", **more: bytes) -> Keyring:
    keys = {"k1": RAW, **more}
    return Keyring(current, keys)


def test_a_secret_opens_with_the_key_and_context_it_was_sealed_with() -> None:
    sealed = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    assert ring().open(sealed, context=CONTEXT) == "sk-ant-secret-1234"
    assert sealed.key_id == "k1"
    assert len(sealed.nonce) == NONCE_BYTES


def test_the_ciphertext_does_not_contain_the_secret_and_every_seal_is_different() -> None:
    first = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    second = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    assert b"secret" not in first.ciphertext
    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


def test_a_ciphertext_moved_to_another_context_does_not_open() -> None:
    sealed = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    with pytest.raises(KeyUnreadable):
        ring().open(sealed, context="ai-key|org-2|ANTHROPIC")
    with pytest.raises(KeyUnreadable):
        ring().open(sealed, context="ai-key|org-1|OPENAI")


def test_a_changed_ciphertext_nonce_or_key_id_does_not_open() -> None:
    sealed = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    flipped = bytes([sealed.ciphertext[0] ^ 1]) + sealed.ciphertext[1:]
    for tampered in (
        dataclasses.replace(sealed, ciphertext=flipped),
        dataclasses.replace(sealed, nonce=bytes(NONCE_BYTES)),
        dataclasses.replace(sealed, ciphertext=sealed.ciphertext[:-1]),
    ):
        with pytest.raises(KeyUnreadable):
            ring().open(tampered, context=CONTEXT)
    # The master key's id is part of what is bound, so renaming it fails even with the same bytes.
    renamed = Keyring("k2", {"k1": RAW, "k2": RAW})
    with pytest.raises(KeyUnreadable):
        renamed.open(dataclasses.replace(sealed, key_id="k2"), context=CONTEXT)


def test_a_wrong_or_missing_master_key_does_not_open() -> None:
    sealed = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    with pytest.raises(KeyUnreadable):
        Keyring("k1", {"k1": OTHER}).open(sealed, context=CONTEXT)
    with pytest.raises(KeyUnreadable):
        Keyring("k9", {"k9": OTHER}).open(sealed, context=CONTEXT)  # no key named k1


def test_after_a_rotation_the_new_key_seals_and_the_previous_one_still_opens_old_rows() -> None:
    old = ring().seal("sk-ant-secret-1234", context=CONTEXT)
    rotated = Keyring("k2", {"k1": RAW, "k2": OTHER})
    assert rotated.open(old, context=CONTEXT) == "sk-ant-secret-1234"
    assert rotated.seal("x" * 10, context=CONTEXT).key_id == "k2"


def test_master_keys_are_32_bytes_of_base64_in_either_alphabet() -> None:
    standard = base64.b64encode(RAW).decode()
    urlsafe = base64.urlsafe_b64encode(bytes([251, 255] * 16)).decode()
    assert parse_master_key(standard) == RAW
    assert parse_master_key(f"  {standard}\n") == RAW
    assert len(parse_master_key(urlsafe)) == KEY_BYTES
    assert parse_master_key(standard.rstrip("=")) == RAW  # missing padding is fine


@pytest.mark.parametrize(
    "bad",
    ["", "not base64 !!", base64.b64encode(b"short").decode(), base64.b64encode(RAW * 2).decode()],
)
def test_a_malformed_master_key_is_refused_without_quoting_it(bad: str) -> None:
    with pytest.raises(ValueError) as problem:
        parse_master_key(bad)
    assert bad.strip() == "" or bad not in str(problem.value)


def test_earlier_keys_are_listed_as_id_equals_base64() -> None:
    one = base64.b64encode(RAW).decode()
    two = base64.b64encode(OTHER).decode()
    assert parse_previous(f"k1={one}, k0={two}") == {"k1": RAW, "k0": OTHER}
    assert parse_previous("") == {}
    for bad in ("k1", "=abc", f"K!={one}", "k1="):
        with pytest.raises(ValueError):
            parse_previous(bad)


def test_the_current_key_must_be_among_the_keys_and_its_id_must_be_plain() -> None:
    with pytest.raises(ValueError):
        Keyring("k1", {})
    with pytest.raises(ValueError):
        Keyring("K 1", {"K 1": RAW})
    with pytest.raises(ValueError):
        Keyring("k1", {"k1": b"short"})


def test_no_master_key_means_no_keyring() -> None:
    assert build_keyring(None, "k1", None) is None
    assert build_keyring("  ", "k1", None) is None
    built = build_keyring(base64.b64encode(RAW).decode(), "k7", None)
    assert built is not None
    assert built.current_id == "k7"


def test_settings_refuse_a_malformed_master_key_at_start_and_never_quote_it() -> None:
    secret = "definitely-not-a-valid-key"
    with pytest.raises(ValueError) as problem:
        Settings(
            app_env=AppEnv.TEST,
            database_url="postgresql+psycopg://x:y@127.0.0.1:1/z",
            ai_keys_master_key=secret,  # type: ignore[arg-type]
        )
    assert "AI_KEYS_MASTER_KEY" in str(problem.value)
    assert secret not in str(problem.value)


def test_settings_accept_no_key_a_blank_key_and_a_good_key() -> None:
    url = "postgresql+psycopg://x:y@127.0.0.1:1/z"
    assert Settings(app_env=AppEnv.TEST, database_url=url).ai_keyring() is None
    blank = Settings(app_env=AppEnv.TEST, database_url=url, ai_keys_master_key="  ")  # type: ignore[arg-type]
    assert blank.ai_keyring() is None
    good = Settings(
        app_env=AppEnv.TEST,
        database_url=url,
        ai_keys_master_key=base64.b64encode(RAW).decode(),  # type: ignore[arg-type]
    )
    keyring = good.ai_keyring()
    assert keyring is not None
    assert keyring.current_id == "k1"
    assert base64.b64encode(RAW).decode() not in repr(good)  # a SecretStr, never printed
