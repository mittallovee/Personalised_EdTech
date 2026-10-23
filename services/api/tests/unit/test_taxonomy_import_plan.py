"""M3 PR 2c-2: what a syllabus file would do to the syllabus (C-03, T25). Pure: no database."""

from uuid import uuid4

import pytest

from qbank.modules.taxonomy.import_file import ImportFileInvalid, read_table
from qbank.modules.taxonomy.import_plan import (
    Plan,
    SnapConcept,
    SnapNode,
    Snapshot,
    build_plan,
)

HEADER = "kind,path,sort,aliases,label_hi"


def plan(rows: list[str], snapshot: Snapshot | None = None, header: str = HEADER) -> Plan:
    table = read_table(("\n".join([header, *rows]) + "\n").encode())
    return build_plan(table, snapshot or Snapshot(nodes=[], concepts=[]))


def statuses(result: Plan) -> list[str]:
    return [row.status for row in result.rows]


def messages(result: Plan) -> list[str | None]:
    return [row.message for row in result.rows]


def node(kind: str, key: str, parent: SnapNode | None = None, **more: object) -> SnapNode:
    fields: dict[str, object] = {
        "state": "ACTIVE",
        "sort_order": 0,
        "revision": 1,
        "labels": {},
    }
    return SnapNode(
        id=uuid4(),
        kind=kind,
        parent_id=parent.id if parent else None,
        name_key=key,
        **{**fields, **more},  # type: ignore[arg-type]
    )


def concept(
    subject: SnapNode, key: str, aliases: frozenset[str] = frozenset(), **more: object
) -> SnapConcept:
    fields: dict[str, object] = {"state": "ACTIVE", "revision": 1, "labels": {}}
    return SnapConcept(
        id=uuid4(),
        subject_id=subject.id,
        name=key.title(),
        name_key=key,
        alias_keys=aliases,
        **{**fields, **more},  # type: ignore[arg-type]
    )


def tree() -> tuple[Snapshot, dict[str, SnapNode]]:
    cls = node("CLASS", "class 11", sort_order=1)
    physics = node("SUBJECT", "physics", cls)
    kinematics = node("CHAPTER", "kinematics", physics)
    nodes = {"class": cls, "subject": physics, "chapter": kinematics}
    return Snapshot(nodes=list(nodes.values()), concepts=[]), nodes


# --- A file into an empty syllabus ---------------------------------------------------------------


def test_every_row_of_a_file_into_an_empty_syllabus_is_new_whatever_the_order() -> None:
    result = plan(
        [
            "CHAPTER,Class 11 > Physics > Kinematics,2,,",  # before its parents
            "SUBJECT,Class 11 > Physics,1,,",
            "CLASS,Class 11,1,,कक्षा 11",
            "CONCEPT,Class 11 > Physics > Newton's second law,,Newton's 2nd law; F = ma,",
        ]
    )
    assert statuses(result) == ["NEW"] * 4
    assert result.counts == {"NEW": 4, "CHANGED": 0, "UNCHANGED": 0, "ERROR": 0}
    chapter = result.rows[0]
    assert (chapter.number, chapter.names, chapter.sort_order) == (
        2,
        ["Class 11", "Physics", "Kinematics"],
        2,
    )
    assert result.rows[2].labels == {"hi": "कक्षा 11"}
    assert result.rows[3].aliases == ["Newton's 2nd law", "F = ma"]


def test_the_same_file_against_what_it_created_changes_nothing() -> None:
    snapshot, items = tree()
    rows = [
        "CLASS,class  11,1,,",  # other case and spacing: the same item
        "SUBJECT,Class 11 > PHYSICS,,,",
        "CHAPTER,Class 11 > Physics > Kinematics,,,",
    ]
    assert statuses(plan(rows, snapshot)) == ["UNCHANGED"] * 3
    assert items["class"].sort_order == 1


def test_a_blank_cell_never_removes_what_is_there() -> None:
    cls = node("CLASS", "class 11", sort_order=5, labels={"hi": "कक्षा 11"})
    result = plan(["CLASS,Class 11,,,"], Snapshot(nodes=[cls], concepts=[]))
    assert statuses(result) == ["UNCHANGED"]


# --- Filling in --------------------------------------------------------------------------------


def test_a_new_label_or_sort_order_is_a_change() -> None:
    cls = node("CLASS", "class 11", sort_order=5, labels={"hi": "कक्षा 11"})
    snapshot = Snapshot(nodes=[cls], concepts=[])
    assert statuses(plan(["CLASS,Class 11,6,,"], snapshot)) == ["CHANGED"]
    assert statuses(plan(["CLASS,Class 11,5,,कक्षा ११"], snapshot)) == ["CHANGED"]
    assert statuses(plan(["CLASS,Class 11,5,,कक्षा 11"], snapshot)) == ["UNCHANGED"]


def test_new_aliases_or_labels_of_an_existing_concept_are_a_change() -> None:
    snapshot, items = tree()
    law = concept(items["subject"], "newton's second law", frozenset({"newton's 2nd law"}))
    snapshot = Snapshot(nodes=snapshot.nodes, concepts=[law])
    path = "CONCEPT,Class 11 > Physics > Newton's second law,,"
    assert statuses(plan([path + "Newton's 2nd law,"], snapshot)) == ["UNCHANGED"]
    assert statuses(plan([path + "Newton's 2nd law; F = ma,"], snapshot)) == ["CHANGED"]
    assert statuses(plan([path + ",न्यूटन का दूसरा नियम"], snapshot)) == ["CHANGED"]


# --- Rows that cannot be imported ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        ("BOOK,Class 11,,,", "not one of"),
        ("CLASS,,,,", "path is empty"),
        ("CLASS,Class 11 > ,,,", "empty part"),
        ("SUBJECT,Class 11,,,", "needs 2 parts for a subject"),
        ("CONCEPT,Class 11 > Physics,,,", "the class, the subject and the concept"),
        ("CLASS,Class 11,x,,", "whole number"),
        ("CLASS,Class 11,100001,,", "whole number"),
        ("CLASS,Class 11,²,,", "whole number"),  # isdigit() is true for these, int() fails
        ("CLASS,Class 11,①,,", "whole number"),
        ("CLASS,Class 11,٣,,", "whole number"),
        ("CONCEPT,Class 11 > Physics > Work,5,,", "no sort order"),
        ("CLASS,Class 11,,Alias,", "Only a concept has aliases"),
        ("CLASS,Class\x07 11,,,", "not valid"),
        ("CLASS," + "x" * 201 + ",,,", "not valid"),
        ("CLASS,ﬃ" * 1 + "ﬃ" * 150 + ",,,", "too long once"),
    ],
)
def test_a_row_that_is_wrong_on_its_own_says_why(row: str, reason: str) -> None:
    result = plan([row])
    assert statuses(result) == ["ERROR"]
    assert reason in (result.rows[0].message or "")


def test_too_many_aliases_is_an_error() -> None:
    aliases = ";".join(f"alias {n}" for n in range(11))
    snapshot, _ = tree()
    result = plan([f"CONCEPT,Class 11 > Physics > Work,,{aliases},"], snapshot)
    assert "at most 10" in (result.rows[0].message or "")


def test_an_item_whose_parent_is_nowhere_is_an_error() -> None:
    result = plan(["CHAPTER,Class 11 > Physics > Kinematics,,,", "CLASS,Class 12,,,"])
    assert statuses(result) == ["ERROR", "NEW"]
    assert "not in the syllabus and not in the file" in (result.rows[0].message or "")


def test_a_concept_needs_its_subject_to_exist() -> None:
    result = plan(["CLASS,Class 11,,,", "CONCEPT,Class 11 > Physics > Work,,,"])
    assert statuses(result) == ["NEW", "ERROR"]
    assert "subject" in (result.rows[1].message or "")


def test_retired_items_are_never_touched_or_built_under() -> None:
    snapshot, items = tree()
    retired = node("CHAPTER", "dynamics", items["subject"], state="DEPRECATED")
    old_subject = node("SUBJECT", "chemistry", items["class"], state="DEPRECATED")
    snapshot = Snapshot(nodes=[*snapshot.nodes, retired, old_subject], concepts=[])
    result = plan(
        [
            "CHAPTER,Class 11 > Physics > Dynamics,,,",
            "CHAPTER,Class 11 > Chemistry > Atoms,,,",
            "CONCEPT,Class 11 > Chemistry > Mole,,,",
        ],
        snapshot,
    )
    assert statuses(result) == ["ERROR"] * 3
    assert all("etired" in (message or "") for message in messages(result))


def test_a_retired_concept_is_an_error() -> None:
    snapshot, items = tree()
    old = concept(items["subject"], "work", state="DEPRECATED")
    result = plan(
        ["CONCEPT,Class 11 > Physics > Work,,,"],
        Snapshot(nodes=snapshot.nodes, concepts=[old]),
    )
    assert statuses(result) == ["ERROR"]


def test_the_same_item_twice_in_a_file_is_an_error_on_the_second() -> None:
    result = plan(["CLASS,Class 11,,,", "CLASS,class 11,,,"])
    assert statuses(result) == ["NEW", "ERROR"]
    assert "row 2" in (result.rows[1].message or "")


def test_a_concept_may_share_its_name_with_a_chapter() -> None:
    result = plan(
        [
            "CLASS,Class 11,,,",
            "SUBJECT,Class 11 > Physics,,,",
            "CHAPTER,Class 11 > Physics > Work,,,",
            "CONCEPT,Class 11 > Physics > Work,,,",
        ]
    )
    assert statuses(result) == ["NEW"] * 4


# --- Names and aliases that clash ----------------------------------------------------------------


def test_names_and_aliases_cannot_clash_inside_a_subject() -> None:
    snapshot, items = tree()
    law = concept(items["subject"], "newton's second law", frozenset({"f = ma"}))
    snapshot = Snapshot(nodes=snapshot.nodes, concepts=[law])
    head = "CONCEPT,Class 11 > Physics > "
    result = plan(
        [
            head + "Force,,F = MA,",  # an alias another concept has
            head + "F = ma,,,",  # a name another concept has as an alias
            head + "Newton's  Second law 2,,Newton's second law,",  # an alias that is a name
            head + "Torque,,Moment; moment,",  # the same alias twice is one alias
            head + "Moment,,,",  # now a name an earlier row took as an alias
            head + "Power,,Power,",  # an alias equal to its own name
        ],
        snapshot,
    )
    assert statuses(result) == ["ERROR", "ERROR", "ERROR", "NEW", "ERROR", "ERROR"]
    assert "already the name or an alias" in (result.rows[0].message or "")
    assert "own name" in (result.rows[5].message or "")


def test_clashes_are_only_within_a_subject() -> None:
    snapshot, items = tree()
    chemistry = node("SUBJECT", "chemistry", items["class"])
    law = concept(items["subject"], "work", frozenset({"labour"}))
    snapshot = Snapshot(nodes=[*snapshot.nodes, chemistry], concepts=[law])
    result = plan(["CONCEPT,Class 11 > Chemistry > Work,,Labour,"], snapshot)
    assert statuses(result) == ["NEW"]


# --- The file as a whole -------------------------------------------------------------------------


def test_unknown_or_missing_columns_refuse_the_whole_file() -> None:
    with pytest.raises(ImportFileInvalid, match="'lable_hi'"):
        plan(["CLASS,Class 11,,,"], header="kind,path,lable_hi")
    with pytest.raises(ImportFileInvalid, match="'path'"):
        plan(["CLASS"], header="kind")


def test_the_fingerprint_changes_when_the_syllabus_does() -> None:
    snapshot, items = tree()
    again = Snapshot(nodes=list(reversed(snapshot.nodes)), concepts=[])
    assert snapshot.fingerprint() == again.fingerprint()  # the order does not matter
    changed = items["chapter"].__class__(**{**items["chapter"].__dict__, "revision": 2})
    assert Snapshot(nodes=[*snapshot.nodes[:2], changed], concepts=[]).fingerprint() != (
        snapshot.fingerprint()
    )
    assert plan(["CLASS,Class 11,,,"], snapshot).base_fingerprint == snapshot.fingerprint()


def test_new_aliases_cannot_take_an_existing_concept_past_ten() -> None:
    snapshot, items = tree()
    full = frozenset(f"alias {n}" for n in range(10))
    work = concept(items["subject"], "work", full)
    snapshot = Snapshot(nodes=snapshot.nodes, concepts=[work])
    head = "CONCEPT,Class 11 > Physics > Work,,"
    result = plan([head + "alias 3,", head.replace("Work", "Work") + "one more,"], snapshot)
    # the first row repeats an alias it has (nothing new); the second is the same concept again
    assert statuses(result) == ["UNCHANGED", "ERROR"]
    over = plan([head + "alias 3; one more,"], snapshot)
    assert statuses(over) == ["ERROR"]
    assert "more than 10 aliases" in (over.rows[0].message or "")


def test_a_name_with_a_greater_than_sign_is_written_with_a_backslash() -> None:
    cls = node("CLASS", "class 11")
    physics = node("SUBJECT", "physics", cls)
    odd = node("CHAPTER", "acceleration when v > u", physics)
    snapshot = Snapshot(nodes=[cls, physics, odd], concepts=[])
    result = plan(
        [
            r"CHAPTER,Class 11 > Physics > Acceleration when v \> u,,,",  # already there
            r"TOPIC,Class 11 > Physics > Acceleration when v \> u > Cases for a \\ b,,,",
            r"CONCEPT,Class 11 > Physics > Is v \> u,,,",
            r"CONCEPT,Class 11 > Physics > C:\path\file,,,",  # a lone backslash is a backslash
        ],
        snapshot,
    )
    assert statuses(result) == ["UNCHANGED", "NEW", "NEW", "NEW"]
    assert result.rows[1].names == [
        "Class 11",
        "Physics",
        "Acceleration when v > u",
        "Cases for a \\ b",
    ]
    assert (
        result.rows[1].path == r"Class 11 > Physics > Acceleration when v \> u > Cases for a \\ b"
    )
    assert result.rows[3].names[2] == "C:\\path\\file"


def test_an_unescaped_greater_than_sign_still_separates_parts() -> None:
    result = plan(["CHAPTER,Class 11 > Physics > v > u,,,"])
    assert statuses(result) == ["ERROR"]
    assert "4 part(s)" in (result.rows[0].message or "")
