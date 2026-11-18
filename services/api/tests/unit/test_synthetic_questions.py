"""K-08: the made-up questions of the load-test bank are complete, valid and repeatable."""

import json
import random

from qbank.modules.questions.public import validate_content
from tests.load.synthetic import make_syllabus, synthetic_question


def bank(seed: int, count: int) -> list[dict[str, object]]:
    rng = random.Random(seed)  # noqa: S311 - made-up data that must repeat, not a secret
    syllabus = make_syllabus(rng)
    return [synthetic_question(rng, syllabus) for _ in range(count)]


def test_every_synthetic_question_is_complete_and_valid() -> None:
    for content in bank(seed=7, count=500):
        assert validate_content(content) == [], json.dumps(content, ensure_ascii=False)


def test_the_same_seed_gives_the_same_bank_and_another_seed_does_not() -> None:
    assert bank(seed=3, count=50) == bank(seed=3, count=50)
    assert bank(seed=3, count=50) != bank(seed=4, count=50)


def test_the_bank_has_the_mix_the_indexes_must_cope_with() -> None:
    contents = bank(seed=11, count=2_000)
    hindi = sum(1 for c in contents if c["language"] == "hi")
    with_solution = sum(1 for c in contents if "solution" in c)
    with_equation = sum(
        1
        for c in contents
        if any(block["kind"] == "equation" for block in c["stem"])  # type: ignore[attr-defined]
    )
    assert 100 < hindi < 300  # about one in ten
    assert 1_000 < with_solution < 1_400  # about six in ten
    assert with_equation > 500
