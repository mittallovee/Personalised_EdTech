import pytest

from qbank.core.codes import ALPHABET, CODE_LENGTH, generate_code, normalize_code
from qbank.core.errors import ValidationFailed


def test_alphabet_is_crockford_base32() -> None:
    assert len(ALPHABET) == 32
    assert not set("ILOU") & set(ALPHABET)


def test_generated_codes_use_only_the_alphabet() -> None:
    codes = {generate_code() for _ in range(2000)}

    assert all(len(code) == CODE_LENGTH and set(code) <= set(ALPHABET) for code in codes)
    assert len(codes) == 2000  # no repeats in a small sample


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("7k2m9pqx", "7K2M9PQX"),
        (" 7K2M-9PQX ", "7K2M9PQX"),
        ("O0IL1234", "00111234"),  # O reads as 0, I and L as 1
    ],
)
def test_typed_codes_are_normalised(typed: str, expected: str) -> None:
    assert normalize_code(typed) == expected


@pytest.mark.parametrize("typed", ["7K2M9PQ", "7K2M9PQXY", "7K2M9PQU", "7K2M9PQ!", ""])
def test_invalid_codes_are_rejected(typed: str) -> None:
    with pytest.raises(ValidationFailed):
        normalize_code(typed)
