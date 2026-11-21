"""C-14 (ADR-0022): every built-in starter syllabus is a valid import file."""

import re
from collections import Counter

import pytest

from qbank.core.errors import NotFound
from qbank.modules.taxonomy import starter_syllabus
from qbank.modules.taxonomy.import_file import read_table
from qbank.modules.taxonomy.import_plan import MAX_APPLY_ROWS, Plan, Snapshot, build_plan
from qbank.modules.taxonomy.starter_syllabus import STARTERS, StarterSyllabus

by_key = pytest.mark.parametrize("starter", STARTERS, ids=lambda starter: starter.key)


def plan_of(starter: StarterSyllabus) -> Plan:
    """What the starter would do to a coaching with an empty syllabus."""
    return build_plan(read_table(starter_syllabus.read(starter)), Snapshot(nodes=[], concepts=[]))


@by_key
def test_a_starter_has_no_error_rows_and_fits_in_one_import(starter: StarterSyllabus) -> None:
    plan = plan_of(starter)
    problems = [(row.number, row.path, row.message) for row in plan.rows if row.status == "ERROR"]
    assert problems == []
    assert plan.counts["NEW"] == len(plan.rows) <= MAX_APPLY_ROWS


@by_key
def test_a_starter_covers_both_classes_down_to_subtopics_and_concepts(
    starter: StarterSyllabus,
) -> None:
    plan = plan_of(starter)
    kinds = Counter(row.kind for row in plan.rows)
    assert kinds["CLASS"] == 2 and kinds["SUBJECT"] == 2
    assert min(kinds["CHAPTER"], kinds["TOPIC"], kinds["SUBTOPIC"], kinds["CONCEPT"]) > 0
    assert {row.names[0] for row in plan.rows} == {"Class 11", "Class 12"}
    subjects = {row.names[1] for row in plan.rows if row.kind != "CLASS"}
    assert len(subjects) == 1  # one subject per starter


@by_key
def test_the_row_count_shown_to_the_admin_is_the_number_of_rows_read(
    starter: StarterSyllabus,
) -> None:
    assert starter_syllabus.row_count(starter) == len(plan_of(starter).rows)


def test_keys_are_unique_and_safe_to_put_in_an_address() -> None:
    keys = [starter.key for starter in STARTERS]
    assert len(set(keys)) == len(keys) > 0
    assert all(re.fullmatch("[a-z0-9-]{1,40}", key) for key in keys)
    assert starter_syllabus.find(keys[0]) is STARTERS[0]


def test_an_unknown_key_is_not_found() -> None:
    with pytest.raises(NotFound):
        starter_syllabus.find("neet-biology")
