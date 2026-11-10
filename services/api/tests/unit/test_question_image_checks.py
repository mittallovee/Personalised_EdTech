from uuid import UUID

from qbank.modules.questions.findings import Level
from qbank.modules.questions.image_checks import MAX_PICTURES, check_images, image_ids, image_refs

A = UUID("00000000-0000-4000-8000-00000000000a")
B = UUID("00000000-0000-4000-8000-00000000000b")


def picture(asset: object) -> dict[str, object]:
    return {"kind": "image", "asset_id": asset, "alt_text": "x"}


def test_pictures_are_found_wherever_a_question_keeps_blocks() -> None:
    content = {
        "stem": [{"kind": "paragraph", "text": "p"}, picture(str(A))],
        "options": [{"id": "A", "content": [picture(str(B))]}, {"id": "B", "content": []}],
        "solution": [picture(str(A))],
        "metadata": {"difficulty": 1},
    }
    assert image_refs(content) == [
        ("options[0].content[0]", B),
        ("solution[0]", A),
        ("stem[1]", A),
    ]
    assert image_ids(content) == {A, B}


def test_a_picture_with_no_readable_id_is_left_to_the_shape_checks() -> None:
    content = {"stem": [picture(None), picture(12), picture("not-an-id"), picture(str(A))]}
    assert image_refs(content) == [("stem[3]", A)]


def test_other_content_is_not_mistaken_for_a_picture() -> None:
    content = {
        "stem": [{"kind": "paragraph", "text": str(A)}],
        "note": {"asset_id": str(A)},  # no kind: not a block
    }
    assert image_refs(content) == []
    assert image_refs("text") == []
    assert image_refs(None) == []
    assert image_refs([]) == []


def test_a_picture_that_is_not_available_is_an_error_at_its_id() -> None:
    content = {"stem": [picture(str(A)), picture(str(B))]}
    findings = check_images(content, {A})
    assert [(f.path, f.code, f.level) for f in findings] == [
        ("stem[1].asset_id", "IMAGE_NOT_AVAILABLE", Level.ERROR)
    ]


def test_no_findings_when_every_picture_is_available() -> None:
    assert check_images({"stem": [picture(str(A))]}, {A, B}) == []
    assert check_images({"stem": []}, set()) == []


def test_a_question_with_very_many_pictures_is_only_looked_up_in_part() -> None:
    many = {"stem": [picture(str(UUID(int=n + 1))) for n in range(MAX_PICTURES + 50)]}
    assert len(image_refs(many)) == MAX_PICTURES


def test_deeply_nested_content_does_not_overflow_the_stack() -> None:
    node: object = picture(str(A))
    for _ in range(5000):
        node = {"inner": node}
    assert image_refs(node)[0][1] == A
