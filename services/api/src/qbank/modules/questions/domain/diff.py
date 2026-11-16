"""What changed between two saved texts of a question (M4 design note §8, E-08).

Pure code: it knows nothing about the database or HTTP. ``diff_content(old, new)`` returns a list
of ``Change``; ``apply_changes(old, changes)`` replays them on ``old`` and gives back ``new`` (the
tests check that for any two JSON documents). A change is one of three things at a path inside the
content:

- ``ADD``: a key or list item that is new;
- ``REMOVE``: one that is gone;
- ``REPLACE``: a value that differs. For text it carries **word-level segments** (equal / insert /
  delete), so a screen can draw an edited sentence with the changed words marked.

An equation, picture, table or list block is one item: if it differs it is replaced as a whole, so
an edited equation reads as "old removed, new added" and is never half-compared.

Lists are matched by content (so an inserted option does not make every later option look edited);
where a run of items was edited in place they are compared one to one. Paths are those of the list
as the changes are applied in order: an item inserted at index 2 shifts the ones after it, and the
changes after that already count from the new positions.

Everything is bounded: a very deep value, a huge list or a very long text is compared as one piece
instead of item by item, so no content, however it was saved, can make this slow.
"""

import copy
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from typing import Any

# A block of these kinds is one item (a paragraph, by contrast, is compared word by word).
_ATOMIC_BLOCKS = frozenset({"equation", "image", "table", "list"})
_MAX_DEPTH = 16
_MAX_LIST_PAIRS = 250_000  # len(old) * len(new) above which a list is compared as one piece
_MAX_TOKEN_PAIRS = 6_000_000  # the same for the words of a text
_TOKEN = re.compile(r"\S+\s*|\s+")  # a word and the spaces after it; the tokens add up to the text

Path = tuple[str | int, ...]


class Op(StrEnum):
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"


class SegmentKind(StrEnum):
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class Segment:
    kind: SegmentKind
    text: str


@dataclass(frozen=True, slots=True)
class Change:
    """One difference. ``before`` is set for REMOVE and REPLACE, ``after`` for ADD and REPLACE (a
    JSON ``null`` is a value like any other: the op says which one is meant)."""

    op: Op
    path: Path
    before: Any = None
    after: Any = None
    segments: tuple[Segment, ...] | None = None


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _is_atomic(value: Any) -> bool:
    return isinstance(value, dict) and value.get("kind") in _ATOMIC_BLOCKS


def word_segments(old: str, new: str) -> tuple[Segment, ...]:
    """The words of ``old`` and ``new`` side by side: joining the equal and delete segments gives
    ``old``, and joining the equal and insert segments gives ``new``."""
    before = _TOKEN.findall(old)
    after = _TOKEN.findall(new)
    if len(before) * len(after) > _MAX_TOKEN_PAIRS:
        return _whole(old, new)
    segments: list[Segment] = []

    def add(kind: SegmentKind, text: str) -> None:
        if text:
            if segments and segments[-1].kind is kind:
                segments[-1] = Segment(kind, segments[-1].text + text)
            else:
                segments.append(Segment(kind, text))

    for tag, i1, i2, j1, j2 in SequenceMatcher(None, before, after).get_opcodes():
        if tag == "equal":
            add(SegmentKind.EQUAL, "".join(before[i1:i2]))
        else:
            add(SegmentKind.DELETE, "".join(before[i1:i2]))
            add(SegmentKind.INSERT, "".join(after[j1:j2]))
    return tuple(segments)


def _whole(old: str, new: str) -> tuple[Segment, ...]:
    return tuple(
        Segment(kind, text)
        for kind, text in ((SegmentKind.DELETE, old), (SegmentKind.INSERT, new))
        if text
    )


def _replace(path: Path, old: Any, new: Any, out: list[Change]) -> None:
    segments = word_segments(old, new) if isinstance(old, str) and isinstance(new, str) else None
    out.append(Change(Op.REPLACE, path, before=old, after=new, segments=segments))


def _diff_lists(old: list[Any], new: list[Any], path: Path, depth: int, out: list[Change]) -> None:
    if len(old) * len(new) > _MAX_LIST_PAIRS:
        _replace(path, old, new, out)
        return
    matcher = SequenceMatcher(
        None, [_canonical(item) for item in old], [_canonical(item) for item in new], autojunk=False
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        # Everything before ``j1`` already equals the new list, so ``j1`` is where this run sits
        # in the list as the earlier changes leave it.
        paired = min(i2 - i1, j2 - j1)
        for offset in range(paired):
            _diff(old[i1 + offset], new[j1 + offset], (*path, j1 + offset), depth + 1, out)
        for offset in range(paired, j2 - j1):
            out.append(Change(Op.ADD, (*path, j1 + offset), after=new[j1 + offset]))
        for offset in range(paired, i2 - i1):
            out.append(Change(Op.REMOVE, (*path, j1 + paired), before=old[i1 + offset]))


def _diff(old: Any, new: Any, path: Path, depth: int, out: list[Change]) -> None:
    if _canonical(old) == _canonical(new):
        return
    if depth >= _MAX_DEPTH or _is_atomic(old) or _is_atomic(new):
        _replace(path, old, new, out)
    elif isinstance(old, dict) and isinstance(new, dict):
        for key, value in new.items():
            if key in old:
                _diff(old[key], value, (*path, key), depth + 1, out)
            else:
                out.append(Change(Op.ADD, (*path, key), after=value))
        for key, value in old.items():
            if key not in new:
                out.append(Change(Op.REMOVE, (*path, key), before=value))
    elif isinstance(old, list) and isinstance(new, list):
        _diff_lists(old, new, path, depth, out)
    else:
        _replace(path, old, new, out)


def diff_content(old: Any, new: Any) -> list[Change]:
    """The changes that turn ``old`` into ``new``; empty if they are the same."""
    out: list[Change] = []
    try:
        _diff(old, new, (), 0, out)
    except RecursionError:  # a value nested so deeply that even reading it overflows: one piece
        return [Change(Op.REPLACE, (), before=old, after=new)]
    return out


def apply_changes(old: Any, changes: list[Change]) -> Any:
    """Replay ``changes`` (in order) on a copy of ``old``. The inverse of ``diff_content``."""
    document = copy.deepcopy(old)
    for change in changes:
        if not change.path:
            document = copy.deepcopy(change.after)
            continue
        parent = document
        for step in change.path[:-1]:
            parent = parent[step]
        last = change.path[-1]
        if change.op is Op.REMOVE:
            del parent[last]
        elif isinstance(parent, list):
            if change.op is Op.ADD:
                parent.insert(int(last), copy.deepcopy(change.after))
            else:
                parent[int(last)] = copy.deepcopy(change.after)
        else:
            parent[last] = copy.deepcopy(change.after)
    return document
