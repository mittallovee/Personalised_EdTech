"""What a syllabus file would do to the syllabus: the plan behind the import preview (C-03).

``build_plan`` is pure: it takes the rows of a file (``import_file.Table``) and a ``Snapshot`` of
the syllabus as it is now, and says for every row whether it would add something (NEW), change
something (CHANGED), change nothing (UNCHANGED), or cannot be done (ERROR, with the reason in plain
words). Nothing is written. Rows are matched by their path of names (compared without regard to
case or spacing), so a file uploaded twice changes nothing the second time.

An import only adds and fills in. A blank cell never removes anything, a name is never changed
(renaming is done on the item), and nothing is retired or restored; those are deliberate clicks.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from qbank.core.errors import ValidationFailed
from qbank.modules.taxonomy.catalogues import LANGUAGES, name_key
from qbank.modules.taxonomy.import_file import ImportFileInvalid, Table
from qbank.modules.taxonomy.schemas import Name

Status = Literal["NEW", "CHANGED", "UNCHANGED", "ERROR"]

# Depth of each kind in a path: "Class 11 > Physics > Kinematics" is a chapter.
DEPTH = {"CLASS": 1, "SUBJECT": 2, "CHAPTER": 3, "TOPIC": 4, "SUBTOPIC": 5}
CONCEPT = "CONCEPT"  # its path is the subject's path and then the concept's name
MAX_SORT = 100_000
MAX_ALIASES = 10
OTHER_LANGUAGES = tuple(language.tag for language in LANGUAGES if language.tag != "en")
LABEL_COLUMNS = {f"label_{tag}": tag for tag in OTHER_LANGUAGES}
COLUMNS = ("kind", "path", "sort", "aliases", *LABEL_COLUMNS)

_NAME = TypeAdapter(Name)


@dataclass(frozen=True)
class SnapNode:
    id: UUID
    kind: str
    parent_id: UUID | None
    name_key: str
    state: str
    sort_order: int
    revision: int
    labels: dict[str, str]


@dataclass(frozen=True)
class SnapConcept:
    id: UUID
    subject_id: UUID
    name: str
    name_key: str
    state: str
    revision: int
    labels: dict[str, str]
    alias_keys: frozenset[str]


@dataclass(frozen=True)
class Snapshot:
    nodes: list[SnapNode]
    concepts: list[SnapConcept]

    def fingerprint(self) -> str:
        """A hash of what the syllabus is (its items, revisions and states). It changes when any
        item is added or changed, so a preview made before is known to be out of date."""
        lines = [f"N:{n.id}:{n.revision}:{n.state}" for n in self.nodes]
        lines += [f"C:{c.id}:{c.revision}:{c.state}" for c in self.concepts]
        return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()


@dataclass
class PlannedRow:
    number: int
    kind: str
    path: str
    status: Status
    message: str | None = None
    names: list[str] = field(default_factory=list)  # the path split into names, as written
    sort_order: int | None = None
    labels: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "kind": self.kind,
            "path": self.path,
            "status": self.status,
            "message": self.message,
            "names": self.names,
            "sort_order": self.sort_order,
            "labels": self.labels,
            "aliases": self.aliases,
        }


@dataclass(frozen=True)
class Plan:
    rows: list[PlannedRow]
    base_fingerprint: str

    @property
    def counts(self) -> dict[str, int]:
        counts = {"NEW": 0, "CHANGED": 0, "UNCHANGED": 0, "ERROR": 0}
        for row in self.rows:
            counts[row.status] += 1
        return counts


@dataclass
class _Entry:
    """A place in the syllabus as the import sees it: already there, or added by an earlier row."""

    kind: str
    state: str
    node: SnapNode | None
    row: int | None  # the file row that adds it, if it is not there yet


@dataclass
class _Concept:
    owner: str  # who holds the name: a concept id, or "row N" for one this file adds
    snap: SnapConcept | None
    row: int | None


@dataclass
class _Subject:
    taken: dict[str, str] = field(default_factory=dict)  # name or alias key -> owner
    concepts: dict[str, _Concept] = field(default_factory=dict)  # concept name key -> concept


class _RowError(Exception):
    """One row cannot be imported; the message says why, in words an admin can act on."""


def _label(kind: str) -> str:
    return kind.lower()


def _clean(value: str, what: str) -> str:
    """A name, label or alias as the rest of the app would accept it."""
    try:
        return _NAME.validate_python(value)
    except ValidationError as error:
        raise _RowError(f"{what} is not valid: {error.errors()[0]['msg']}.") from None


def _key(value: str) -> str:
    try:
        return name_key(value)
    except ValidationFailed as error:
        raise _RowError(str(error.message)) from None


def _split_path(path: str) -> list[str]:
    """The parts of a path, split at ">". A name that contains ">" (or "\\") is written with a
    backslash before it: ``Acceleration when v \\> u``. Any other backslash is just a backslash."""
    parts: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(path):
        char = path[index]
        if char == "\\" and path[index + 1 : index + 2] in (">", "\\"):
            current.append(path[index + 1])
            index += 2
            continue
        if char == ">":
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    parts.append("".join(current).strip())
    return parts


def _write_path(names: list[str]) -> str:
    """A path as it is written in a file: the inverse of ``_split_path``."""
    return " > ".join(name.replace("\\", "\\\\").replace(">", "\\>") for name in names)


def _parse_row(number: int, cells: dict[str, str]) -> PlannedRow:
    """Check one row on its own (its path, kind, labels...). Raises ``_RowError``."""
    kind = cells.get("kind", "").upper()
    path = cells.get("path", "")
    if kind != CONCEPT and kind not in DEPTH:
        shown = cells.get("kind", "") or "(empty)"
        raise _RowError(
            f"The kind {shown!r} is not one of CLASS, SUBJECT, CHAPTER, TOPIC, SUBTOPIC, CONCEPT."
        )
    parts = _split_path(path)
    if not path or "" in parts:
        raise _RowError("The path is empty or has an empty part. Write it as Class 11 > Physics.")
    depth = 3 if kind == CONCEPT else DEPTH[kind]
    if len(parts) != depth:
        want = (
            "the class, the subject and the concept (Class 11 > Physics > Newton's second law)"
            if kind == CONCEPT
            else f"{depth} part{'s' if depth > 1 else ''} for a {_label(kind)}"
        )
        raise _RowError(f"The path has {len(parts)} part(s); it needs {want}.")
    names = [_clean(part, f"The name {part!r}") for part in parts]
    sort_text = cells.get("sort", "")
    aliases_text = cells.get("aliases", "")
    sort_order: int | None = None
    if sort_text:
        if kind == CONCEPT:
            raise _RowError("A concept has no sort order; leave the sort cell empty.")
        if not (sort_text.isascii() and sort_text.isdigit()) or int(sort_text) > MAX_SORT:
            raise _RowError(
                f"The sort order {sort_text!r} must be a whole number up to {MAX_SORT}."
            )
        sort_order = int(sort_text)
    aliases: list[str] = []
    if aliases_text:
        if kind != CONCEPT:
            raise _RowError("Only a concept has aliases; leave the aliases cell empty.")
        aliases = [
            _clean(part, f"The alias {part!r}") for part in aliases_text.split(";") if part.strip()
        ]
        if len(aliases) > MAX_ALIASES:
            raise _RowError(f"A concept can have at most {MAX_ALIASES} aliases.")
    labels = {
        tag: _clean(cells[column], f"The {tag} name")
        for column, tag in LABEL_COLUMNS.items()
        if cells.get(column)
    }
    return PlannedRow(
        number=number,
        kind=kind,
        path=_write_path(names),
        status="NEW",
        names=names,
        sort_order=sort_order,
        labels=labels,
        aliases=aliases,
    )


def _paths(snapshot: Snapshot) -> dict[UUID, tuple[str, ...]]:
    """The path of name keys of every existing node."""
    by_id = {node.id: node for node in snapshot.nodes}
    paths: dict[UUID, tuple[str, ...]] = {}

    def path_of(node: SnapNode) -> tuple[str, ...]:
        if node.id not in paths:
            parent = by_id.get(node.parent_id) if node.parent_id else None
            paths[node.id] = (path_of(parent) if parent else ()) + (node.name_key,)
        return paths[node.id]

    for node in snapshot.nodes:
        path_of(node)
    return paths


def check_columns(table: Table) -> None:
    """The file's columns are known and the two that every row needs are there."""
    unknown = [column for column in table.columns if column not in COLUMNS]
    if unknown:
        raise ImportFileInvalid(
            f"The column {unknown[0]!r} is not one of the template's columns: {', '.join(COLUMNS)}."
        )
    for needed in ("kind", "path"):
        if needed not in table.columns:
            raise ImportFileInvalid(f"The file needs a column named {needed!r}.")


def build_plan(table: Table, snapshot: Snapshot) -> Plan:
    check_columns(table)
    paths = _paths(snapshot)
    entries: dict[tuple[str, ...], _Entry] = {
        paths[node.id]: _Entry(node.kind, node.state, node, None) for node in snapshot.nodes
    }
    by_id = {node.id: node for node in snapshot.nodes}
    subjects: dict[tuple[str, ...], _Subject] = {}
    for concept in snapshot.concepts:
        subject = by_id.get(concept.subject_id)
        if subject is None:
            continue
        registry = subjects.setdefault(paths[subject.id], _Subject())
        owner = str(concept.id)
        registry.concepts[concept.name_key] = _Concept(owner, concept, None)
        registry.taken[concept.name_key] = owner
        for alias_key in concept.alias_keys:
            registry.taken[alias_key] = owner

    parsed: list[PlannedRow] = []
    rows: list[PlannedRow] = []
    for line in table.rows:
        try:
            parsed.append(_parse_row(line.number, line.cells))
        except _RowError as error:
            rows.append(
                PlannedRow(
                    number=line.number,
                    kind=line.cells.get("kind", ""),
                    path=line.cells.get("path", ""),
                    status="ERROR",
                    message=str(error),
                )
            )

    # Syllabus items first, shallowest first (a parent before its children, wherever they are in
    # the file), then the concepts. Within each, in file order.
    ordered = sorted(parsed, key=lambda r: (r.kind == CONCEPT, DEPTH.get(r.kind, 0), r.number))
    seen: dict[tuple[str, ...], int] = {}
    for row in ordered:
        try:
            _plan_row(row, entries, subjects, seen)
        except _RowError as error:
            row.status, row.message = "ERROR", str(error)
        rows.append(row)
    rows.sort(key=lambda r: r.number)
    return Plan(rows=rows, base_fingerprint=snapshot.fingerprint())


def _plan_row(
    row: PlannedRow,
    entries: dict[tuple[str, ...], _Entry],
    subjects: dict[tuple[str, ...], _Subject],
    seen: dict[tuple[str, ...], int],
) -> None:
    keys = tuple(_key(name) for name in row.names)
    marker = keys + ((CONCEPT,) if row.kind == CONCEPT else ())
    if marker in seen:
        raise _RowError(f"This is the same item as row {seen[marker]}; it appears twice.")
    seen[marker] = row.number
    if row.kind == CONCEPT:
        _plan_concept(row, keys, entries, subjects)
    else:
        _plan_node(row, keys, entries)


def _plan_node(
    row: PlannedRow, keys: tuple[str, ...], entries: dict[tuple[str, ...], _Entry]
) -> None:
    here = entries.get(keys)
    if here is not None:
        if here.state != "ACTIVE":
            raise _RowError("This item is retired. Restore it in the syllabus first.")
        node = here.node
        if node is None:  # added by an earlier row; the twin check normally catches this first
            raise _RowError("This is the same item as an earlier row; it appears twice.")
        changed = any(node.labels.get(tag) != text for tag, text in row.labels.items()) or (
            row.sort_order is not None and row.sort_order != node.sort_order
        )
        row.status = "CHANGED" if changed else "UNCHANGED"
        return
    if len(keys) > 1:
        parent = entries.get(keys[:-1])
        if parent is None:
            raise _RowError(
                f"Its parent {' > '.join(row.names[:-1])!r} is not in the syllabus and not in the"
                " file."
            )
        if parent.state != "ACTIVE":
            raise _RowError("Its parent is retired. Restore it in the syllabus first.")
    entries[keys] = _Entry(row.kind, "ACTIVE", None, row.number)
    row.status = "NEW"


def _plan_concept(
    row: PlannedRow,
    keys: tuple[str, ...],
    entries: dict[tuple[str, ...], _Entry],
    subjects: dict[tuple[str, ...], _Subject],
) -> None:
    subject_key = keys[:2]
    subject = entries.get(subject_key)
    if subject is None or subject.kind != "SUBJECT":
        raise _RowError(
            f"The subject {' > '.join(row.names[:2])!r} is not in the syllabus and not in the file."
        )
    if subject.state != "ACTIVE":
        raise _RowError("The subject is retired. Restore it in the syllabus first.")
    registry = subjects.setdefault(subject_key, _Subject())
    concept_key = keys[2]
    alias_keys = {_key(alias): alias for alias in row.aliases}
    if concept_key in alias_keys:
        raise _RowError("An alias cannot be the same as the concept's own name.")
    existing = registry.concepts.get(concept_key)
    if existing is not None:
        snap = existing.snap
        if snap is None:  # added by an earlier row; the twin check normally catches this first
            raise _RowError("This is the same concept as an earlier row; it appears twice.")
        if snap.state != "ACTIVE":
            raise _RowError("This concept is retired. Restore it in the syllabus first.")
        new_aliases = {k: a for k, a in alias_keys.items() if k not in snap.alias_keys}
        if len(snap.alias_keys | new_aliases.keys()) > MAX_ALIASES:
            raise _RowError(
                f"With the aliases it already has, this would give the concept more than"
                f" {MAX_ALIASES} aliases."
            )
        _check_free(registry, existing.owner, new_aliases)
        changed = any(snap.labels.get(tag) != text for tag, text in row.labels.items())
        row.status = "CHANGED" if (changed or new_aliases) else "UNCHANGED"
        for key in new_aliases:
            registry.taken[key] = existing.owner
        return
    owner = f"row {row.number}"
    _check_free(registry, owner, {concept_key: row.names[2], **alias_keys})
    registry.concepts[concept_key] = _Concept(owner, None, row.number)
    for key in (concept_key, *alias_keys):
        registry.taken[key] = owner
    row.status = "NEW"


def _check_free(registry: _Subject, owner: str, wanted: dict[str, str]) -> None:
    """None of these names or aliases is already held by another concept of the subject."""
    for key, text in wanted.items():
        holder = registry.taken.get(key)
        if holder is not None and holder != owner:
            raise _RowError(
                f"{text!r} is already the name or an alias of another concept in this subject."
            )
