"""M6 PR 6j (T63): scoring what a model read against a key a person finished."""

from typing import Any

from qbank.modules.ingestion.golden_score import compare, score_page, summarise


def paragraph(text: str) -> list[dict[str, str]]:
    return [{"kind": "paragraph", "text": text}]


def scq(stem: str = "What is 2 + 3?", answer: str = "B", **changes: Any) -> dict[str, Any]:
    content: dict[str, Any] = {
        "question_type": "SCQ",
        "stem": paragraph(stem),
        "options": [
            {"id": letter, "content": paragraph(text)}
            for letter, text in zip("ABCD", "4567", strict=True)
        ],
        "answer": {"option_id": answer},
    }
    content.update(changes)
    return content


def test_an_identical_reading_is_entirely_right() -> None:
    result = compare(scq(), scq())
    assert result.found and result.perfect


def test_spacing_and_case_are_not_errors_but_a_changed_digit_is() -> None:
    assert compare(scq(), scq("what is   2 + 3?")).perfect
    wrong = compare(scq(), scq(answer="C"))
    assert wrong.right == {"kind": True, "text": True, "options": True, "answer": False}
    digit = scq(options=[{"id": "A", "content": paragraph("40")}])
    assert compare(scq(), digit).right["options"] is False


def test_each_field_is_scored_on_its_own() -> None:
    result = compare(scq(), scq(question_type="MULTI_CORRECT"))
    assert result.right["kind"] is False and result.right["text"] is True


def test_matching_options_compare_by_what_each_pairs() -> None:
    key = {
        "question_type": "MATCHING",
        "stem": paragraph("Match"),
        "options": [{"id": "A", "mapping": {"L1": ["R2"], "L2": ["R1"]}}],
    }
    same = {
        "question_type": "MATCHING",
        "stem": paragraph("Match"),
        "options": [{"id": "A", "mapping": {"L2": ["R1"], "L1": ["R2"]}}],
    }
    other = {
        "question_type": "MATCHING",
        "stem": paragraph("Match"),
        "options": [{"id": "A", "mapping": {"L1": ["R1"], "L2": ["R2"]}}],
    }
    assert compare(key, same).right["options"] is True
    assert compare(key, other).right["options"] is False


def test_keys_are_matched_to_the_closest_question_and_each_read_is_used_once() -> None:
    keys = [scq("What is 2 + 3?"), scq("A ball falls for two seconds. How far?")]
    read = [scq("A ball falls for two seconds. How far?"), scq("What is 2 + 3?"), scq("Unrelated")]
    results, extra = score_page(keys, read)
    assert [r.perfect for r in results] == [True, True]
    assert extra == 1  # the unrelated question matched no key


def test_a_key_question_nothing_like_it_was_read_is_not_found() -> None:
    results, extra = score_page([scq("What is 2 + 3?")], [scq("Completely different words here")])
    assert results[0].found is False and not results[0].perfect and extra == 1
    assert score_page([scq()], []) == ([results[0].__class__(False)], 0)


def test_the_report_counts_and_prints_honestly() -> None:
    results, extra = score_page([scq("one"), scq("two zzz")], [scq("one"), scq("two zzz", "C")])
    report = summarise(results, extra=extra, pages_failed=1, tokens_in=10, tokens_out=5)
    assert (report.cases, report.found, report.perfect) == (2, 2, 1)
    assert report.right == {"kind": 2, "text": 2, "options": 2, "answer": 1}
    text = "\n".join(report.lines())
    assert "Entirely right (type, text, options, answer): 1/2 (50%)" in text
    assert "answer: 1/2 (50%)" in text and "Pages the model could not read: 1" in text
    assert "Tokens used: 10 in, 5 out" in text


def test_an_empty_key_does_not_divide_by_zero() -> None:
    report = summarise([], extra=0, pages_failed=0, tokens_in=0, tokens_out=0)
    assert "none to score" in "\n".join(report.lines())


def test_blank_texts_never_match_each_other() -> None:
    blank = {"question_type": "SCQ", "stem": paragraph("")}
    results, extra = score_page([blank], [blank])
    assert results[0].found is False and extra == 1
