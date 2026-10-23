"""K-04: property-based tests for the syllabus import reader and plan engine (C-03, T25).

A normal test checks the cases someone thought of. A property test states a rule that must hold
for *every* input, and the Hypothesis library then tries hundreds of generated inputs (and, when one
breaks the rule, shrinks it to the smallest example). Here the rules are:

- reading a file: any bytes either give a table that respects every limit, or are refused with
  ``ImportFileInvalid``; nothing else ever escapes. A CSV written from a table reads back the same.
- planning: every row gets exactly one outcome, the counts add up, the plan is a pure function of
  its inputs, a file's rows do not depend on their order, and applying the plan then planning the
  same file again changes nothing ("a file uploaded twice changes nothing the second time").

The tests are deterministic in CI (``derandomize``) so a red build is always reproducible; run
``HYPOTHESIS_PROFILE=explore`` locally to try new random inputs.
"""

import copy
import csv
import dataclasses
import io
import os
import unicodedata
from uuid import uuid4

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from openpyxl import Workbook

from qbank.modules.taxonomy.catalogues import name_key
from qbank.modules.taxonomy.import_file import (
    MAX_CELL_CHARS,
    MAX_COLUMNS,
    MAX_ROWS,
    ImportFileInvalid,
    Table,
    TableRow,
    read_table,
)
from qbank.modules.taxonomy.import_plan import (
    CONCEPT,
    DEPTH,
    Plan,
    SnapConcept,
    SnapNode,
    Snapshot,
    _split_path,
    _write_path,
    build_plan,
)

settings.register_profile(
    "ci",
    max_examples=150,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "explore", max_examples=2_000, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))


# --- Reading a file ------------------------------------------------------------------------------

# Text a cell can hold: anything that can be written as UTF-8 except NUL (which marks a file as
# binary and is refused on purpose).
CELL_TEXT = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), max_size=30
)
COLUMN_NAMES = ["kind", "path", "sort", "aliases", "label_hi", "label_ta", "notes"]


def _valid_xlsx() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Kind", "Path", "Sort", "Aliases"])
    sheet.append(["CLASS", "Class 11", 1, ""])
    sheet.append(["SUBJECT", "Class 11 > Physics", 2, ""])
    sheet.append(["CONCEPT", "Class 11 > Physics > Newton's law", None, "F = ma; second law"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


VALID_XLSX = _valid_xlsx()


def _check_limits(table: Table) -> None:
    """What every table that ``read_table`` hands back must satisfy."""
    assert len(table.columns) <= MAX_COLUMNS
    assert len(set(table.columns)) == len(table.columns)
    assert all(name and name == name.lower() for name in table.columns)
    assert len(table.rows) <= MAX_ROWS
    numbers = [row.number for row in table.rows]
    assert numbers == sorted(set(numbers)) and all(number >= 2 for number in numbers)
    for row in table.rows:
        assert set(row.cells) <= set(table.columns)
        assert all(len(value) <= MAX_CELL_CHARS for value in row.cells.values())
        assert any(row.cells.values())  # a blank row is dropped, never returned


def _read_or_refuse(data: bytes) -> None:
    try:
        table = read_table(data)
    except ImportFileInvalid:
        return  # the one way a file may be refused
    _check_limits(table)


@given(st.binary(max_size=4_000))
def test_any_bytes_are_read_within_the_limits_or_refused_cleanly(data: bytes) -> None:
    _read_or_refuse(data)


@given(st.binary(max_size=4_000))
def test_any_bytes_behind_a_zip_header_are_read_or_refused_cleanly(data: bytes) -> None:
    _read_or_refuse(b"PK\x03\x04" + data)


@given(st.text(max_size=400))
def test_any_text_is_read_as_csv_or_refused_cleanly(text: str) -> None:
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:  # a lone surrogate cannot be written as UTF-8
        return
    _read_or_refuse(data)


@st.composite
def damaged_spreadsheets(draw: st.DrawFn) -> bytes:
    """A real spreadsheet with bytes flipped, removed, added or cut off."""
    data = bytearray(VALID_XLSX)
    for _ in range(draw(st.integers(1, 6))):
        action = draw(st.sampled_from(["flip", "delete", "insert", "truncate"]))
        position = draw(st.integers(0, max(len(data) - 1, 0)))
        if action == "flip" and data:
            data[position] ^= draw(st.integers(1, 255))
        elif action == "delete":
            del data[position : position + draw(st.integers(1, 40))]
        elif action == "insert":
            data[position:position] = draw(st.binary(min_size=1, max_size=40))
        else:
            del data[position:]
    return bytes(data)


@given(damaged_spreadsheets())
def test_a_damaged_spreadsheet_is_read_or_refused_cleanly(data: bytes) -> None:
    _read_or_refuse(data)


@st.composite
def csv_tables(draw: st.DrawFn) -> tuple[list[str], list[list[str]]]:
    """A header (unique names, in any letter case) and rows with one cell per column."""
    names = draw(st.lists(st.sampled_from(COLUMN_NAMES), min_size=1, max_size=5, unique=True))
    header = [name.upper() if draw(st.booleans()) else name for name in names]
    rows = draw(
        st.lists(st.lists(CELL_TEXT, min_size=len(names), max_size=len(names)), max_size=12)
    )
    return header, rows


@given(csv_tables())
def test_a_csv_written_from_a_table_reads_back_the_same(
    table: tuple[list[str], list[list[str]]],
) -> None:
    header, rows = table
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)

    result = read_table(buffer.getvalue().encode("utf-8"))

    def text(cell: str) -> str:
        return unicodedata.normalize("NFC", cell).strip()

    assert result.columns == [name.lower() for name in header]
    expected = [
        TableRow(
            number=number,
            cells={name.lower(): text(cell) for name, cell in zip(header, row, strict=True)},
        )
        for number, row in enumerate(rows, start=2)
        if any(text(cell) for cell in row)  # a row with nothing in it is dropped
    ]
    assert result.rows == expected


@given(st.integers(MAX_CELL_CHARS - 20, MAX_CELL_CHARS + 20), st.sampled_from(["a", "भ", "ﬁ"]))
def test_a_cell_is_accepted_up_to_the_length_limit_and_refused_beyond_it(
    length: int, char: str
) -> None:
    data = f"kind,path\nCLASS,{char * length}\n".encode()

    if length <= MAX_CELL_CHARS:
        assert read_table(data).rows[0].cells["path"] == char * length
    else:
        try:
            read_table(data)
        except ImportFileInvalid:
            return
        raise AssertionError("A cell over the limit was accepted.")


# --- Planning ------------------------------------------------------------------------------------

# Names that collide on purpose: the same name in other case or spacing, a name with the path
# separator in it, a ligature that expands when normalised, non-Latin text.
NAMES = [
    "Class 11",
    "class  11",
    "Physics",
    "PHYSICS ",
    "Chemistry",
    "Kinematics",
    "Laws",
    "Newton's law",
    "Acceleration when v > u",
    "back\\slash",
    "ﬁeld",
    "भौतिकी",
]
KINDS = [*DEPTH, CONCEPT]
PLAN_COLUMNS = ["kind", "path", "sort", "aliases", "label_hi"]


@st.composite
def snapshots(draw: st.DrawFn) -> Snapshot:
    """A small syllabus: a few classes, with subjects, chapters... under them, and concepts."""
    nodes: list[SnapNode] = []
    by_depth: dict[int, list[SnapNode]] = {}
    for kind, depth in DEPTH.items():
        parents: list[SnapNode | None] = [None] if depth == 1 else list(by_depth.get(depth - 1, []))
        for parent in parents:
            taken: set[str] = set()
            for name in draw(st.lists(st.sampled_from(NAMES), max_size=3, unique=True)):
                key = name_key(name)
                if key in taken:
                    continue
                taken.add(key)
                made = SnapNode(
                    id=uuid4(),
                    kind=kind,
                    parent_id=parent.id if parent else None,
                    name_key=key,
                    state=draw(st.sampled_from(["ACTIVE", "ACTIVE", "ACTIVE", "RETIRED"])),
                    sort_order=draw(st.integers(0, 5)),
                    revision=draw(st.integers(1, 3)),
                    labels=draw(st.sampled_from([{}, {}, {"hi": "हिन्दी"}])),
                )
                nodes.append(made)
                by_depth.setdefault(depth, []).append(made)
    concepts: list[SnapConcept] = []
    for subject in by_depth.get(2, []):
        taken_keys: set[str] = set()
        for name in draw(st.lists(st.sampled_from(NAMES), max_size=3, unique=True)):
            aliases = {
                name_key(alias): alias
                for alias in draw(st.lists(st.sampled_from(NAMES), max_size=2, unique=True))
            }
            keys = {name_key(name), *aliases}
            if keys & taken_keys or name_key(name) in aliases:
                continue  # in a real syllabus a name or alias belongs to one concept only
            taken_keys |= keys
            concepts.append(
                SnapConcept(
                    id=uuid4(),
                    subject_id=subject.id,
                    name=name,
                    name_key=name_key(name),
                    state=draw(st.sampled_from(["ACTIVE", "ACTIVE", "ACTIVE", "RETIRED"])),
                    revision=draw(st.integers(1, 3)),
                    labels=draw(st.sampled_from([{}, {"hi": "हिन्दी"}])),
                    aliases=aliases,
                )
            )
    return Snapshot(nodes=nodes, concepts=concepts)


def _names_of(snapshot: Snapshot) -> list[tuple[str, ...]]:
    """The path (as name keys) of every node of a snapshot."""
    by_id = {node.id: node for node in snapshot.nodes}

    def path(node: SnapNode) -> tuple[str, ...]:
        parent = by_id.get(node.parent_id) if node.parent_id else None
        return (path(parent) if parent else ()) + (node.name_key,)

    return [path(node) for node in snapshot.nodes]


@st.composite
def tables(draw: st.DrawFn, snapshot: Snapshot, *, unique_paths: bool = False) -> Table:
    """Rows that mostly build on the snapshot and on each other, some of them wrong on purpose."""
    known: list[tuple[str, ...]] = _names_of(snapshot)
    rows: list[TableRow] = []
    used: set[tuple[str, str]] = set()
    for number in range(2, 2 + draw(st.integers(0, 14))):
        kind = draw(st.sampled_from(KINDS))
        depth = 3 if kind == CONCEPT else DEPTH[kind]
        parents = [p for p in known if len(p) == (2 if kind == CONCEPT else depth - 1)]
        if depth == 1:
            prefix: tuple[str, ...] = ()
        elif parents and draw(st.integers(0, 9)) > 0:
            prefix = draw(st.sampled_from(parents))
        else:  # a parent that does not exist anywhere
            prefix = tuple(draw(st.sampled_from(NAMES)) for _ in range(depth - 1))
        names = (*prefix, draw(st.sampled_from(NAMES)))
        if draw(st.integers(0, 14)) == 0:
            names = names[:-1]  # the wrong number of parts
        if unique_paths:
            marker = ("c" if kind == CONCEPT else "n", "\0".join(name_key(n) for n in names))
            if marker in used:
                continue
            used.add(marker)
        if len(names) == depth:
            known.append(tuple(names))
        cells = {"kind": kind, "path": _write_path(list(names))}
        if kind != CONCEPT and draw(st.booleans()):
            cells["sort"] = str(draw(st.integers(0, 6)))
        if kind == CONCEPT and draw(st.booleans()):
            cells["aliases"] = "; ".join(
                draw(st.lists(st.sampled_from(NAMES), min_size=1, max_size=3))
            )
        if draw(st.integers(0, 3)) == 0:
            cells["label_hi"] = draw(st.sampled_from(["हिन्दी", "नाम", "x"]))
        rows.append(TableRow(number=number, cells=cells))
    return Table(columns=PLAN_COLUMNS, rows=rows)


@st.composite
def snapshot_and_table(draw: st.DrawFn, *, unique_paths: bool = False) -> tuple[Snapshot, Table]:
    snapshot = draw(snapshots())
    return snapshot, draw(tables(snapshot, unique_paths=unique_paths))


def _outcomes(plan: Plan) -> list[dict[str, object]]:
    return [row.as_json() for row in plan.rows]


@given(snapshot_and_table())
def test_every_row_gets_exactly_one_outcome_and_the_counts_add_up(
    case: tuple[Snapshot, Table],
) -> None:
    snapshot, table = case
    plan = build_plan(table, snapshot)

    assert [row.number for row in plan.rows] == [row.number for row in table.rows]
    assert sum(plan.counts.values()) == len(table.rows)
    for row in plan.rows:
        assert row.status in {"NEW", "CHANGED", "UNCHANGED", "ERROR"}
        assert (row.status == "ERROR") == bool(row.message)  # a reason for every error, only then
    assert plan.base_fingerprint == snapshot.fingerprint()


@given(snapshot_and_table())
def test_a_plan_is_a_pure_function_of_the_file_and_the_syllabus(
    case: tuple[Snapshot, Table],
) -> None:
    snapshot, table = case
    # Independent copies, taken before planning: the lists and the dictionaries inside them are new
    # objects, so a change made to the originals cannot also show in the copies.
    snapshot_before, table_before = copy.deepcopy(snapshot), copy.deepcopy(table)

    first, second = build_plan(table, snapshot), build_plan(table, snapshot)

    assert _outcomes(first) == _outcomes(second)
    assert snapshot == snapshot_before and table == table_before  # planning wrote nothing


@given(snapshot_and_table(unique_paths=True), st.randoms(use_true_random=False))
def test_the_order_of_the_rows_in_the_file_does_not_change_what_the_syllabus_items_get(
    case: tuple[Snapshot, Table], random: object
) -> None:
    """A parent can come after its children, so the plan must not depend on file order. (Concepts
    are left out: which of two concepts that claim the same alias gets it is first come, first
    served, by design.)"""
    snapshot, table = case
    items = Table(columns=table.columns, rows=[r for r in table.rows if r.cells["kind"] != CONCEPT])
    shuffled_rows = list(items.rows)
    random.shuffle(shuffled_rows)  # type: ignore[attr-defined]
    # Renumbered in the new order: the planner goes by row number, so the numbers have to move too
    # for a child to really come before its parent.
    shuffled = Table(
        columns=items.columns,
        rows=[
            TableRow(number=number, cells=row.cells)
            for number, row in enumerate(shuffled_rows, start=2)
        ],
    )

    def by_item(plan: Plan) -> dict[tuple[str, str], str]:
        return {(row.kind, row.path): row.status for row in plan.rows}

    assert by_item(build_plan(shuffled, snapshot)) == by_item(build_plan(items, snapshot))


def _apply(plan: Plan, snapshot: Snapshot) -> Snapshot:
    """What the import would do to the syllabus, as the plan describes it (a model of the apply
    step, in memory)."""
    nodes = list(snapshot.nodes)
    concepts = list(snapshot.concepts)
    paths = {path: node for path, node in zip(_names_of(snapshot), nodes, strict=True)}
    for row in sorted(plan.rows, key=lambda r: (r.kind == CONCEPT, DEPTH.get(r.kind, 0), r.number)):
        if row.status not in {"NEW", "CHANGED"}:
            continue
        keys = tuple(name_key(name) for name in row.names)
        if row.kind == CONCEPT:
            subject = paths[keys[:2]]
            found = next(
                (c for c in concepts if c.subject_id == subject.id and c.name_key == keys[2]), None
            )
            aliases = {name_key(alias): alias for alias in row.aliases}
            if found is None:
                concepts.append(
                    SnapConcept(
                        id=uuid4(),
                        subject_id=subject.id,
                        name=row.names[2],
                        name_key=keys[2],
                        state="ACTIVE",
                        revision=1,
                        labels=dict(row.labels),
                        aliases=aliases,
                    )
                )
            else:
                merged = {**aliases, **found.aliases}
                concepts[concepts.index(found)] = dataclasses.replace(
                    found, labels={**found.labels, **row.labels}, aliases=merged
                )
        elif keys in paths:
            old = paths[keys]
            changed = dataclasses.replace(
                old,
                labels={**old.labels, **row.labels},
                sort_order=old.sort_order if row.sort_order is None else row.sort_order,
            )
            nodes[nodes.index(old)] = changed
            paths[keys] = changed
        else:
            parent = paths[keys[:-1]] if len(keys) > 1 else None
            made = SnapNode(
                id=uuid4(),
                kind=row.kind,
                parent_id=parent.id if parent else None,
                name_key=keys[-1],
                state="ACTIVE",
                sort_order=row.sort_order or 0,
                revision=1,
                labels=dict(row.labels),
            )
            nodes.append(made)
            paths[keys] = made
    return Snapshot(nodes=nodes, concepts=concepts)


@given(snapshot_and_table())
def test_a_file_with_errors_is_refused_whole_and_what_remains_plans_the_same(
    case: tuple[Snapshot, Table],
) -> None:
    """An import with any row in error applies nothing (``apply_import`` refuses it). The admin
    fixes the file; taking out the rows that failed must leave a file with no errors, in which
    every other row gets the outcome it had before."""
    snapshot, table = case
    first = build_plan(table, snapshot)
    failed = {row.number for row in first.rows if row.status == "ERROR"}

    remaining = Table(columns=table.columns, rows=[r for r in table.rows if r.number not in failed])
    again = build_plan(remaining, snapshot)

    assert again.counts["ERROR"] == 0
    assert [(r.number, r.status) for r in again.rows] == [
        (r.number, r.status) for r in first.rows if r.number not in failed
    ]


@given(snapshot_and_table())
def test_a_file_uploaded_twice_changes_nothing_the_second_time(
    case: tuple[Snapshot, Table],
) -> None:
    snapshot, table = case
    failed = {r.number for r in build_plan(table, snapshot).rows if r.status == "ERROR"}
    file = Table(columns=table.columns, rows=[r for r in table.rows if r.number not in failed])
    first = build_plan(file, snapshot)
    assert first.counts["ERROR"] == 0  # a file the import would accept

    second = build_plan(file, _apply(first, snapshot))

    assert {row.status for row in second.rows} <= {"UNCHANGED"}


@given(st.lists(st.sampled_from([*NAMES, "", "  ", "a>b", "\\", ">"]), min_size=1, max_size=5))
def test_writing_a_path_and_splitting_it_gives_the_same_names(names: list[str]) -> None:
    stripped = [name.strip() for name in names]
    assert _split_path(_write_path(stripped)) == stripped
