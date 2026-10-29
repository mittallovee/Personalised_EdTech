"""The five content blocks and their checks (ADR-0016, D-04, D-05).

A question's text is a list of typed blocks: ``paragraph``, ``equation``, ``image``, ``table`` and
``list``. There is no HTML or Markdown. Equations are LaTeX source: displayed ones are ``equation``
blocks, inline ones sit in paragraph text between ``\\(`` and ``\\)``.

The server checks structure and size, not that the LaTeX typesets (Python cannot run KaTeX).
Nothing here raises on bad input: every problem becomes a finding.
"""

from uuid import UUID

from qbank.modules.questions.findings import Findings, at_index, at_key
from qbank.modules.questions.rules import Rules

PARAGRAPH = "paragraph"
EQUATION = "equation"
IMAGE = "image"
TABLE = "table"
LIST = "list"
ALL_KINDS = frozenset({PARAGRAPH, EQUATION, IMAGE, TABLE, LIST})
# Inside a table cell or a list item only text and equations are allowed (design note §5.2).
INNER_KINDS = frozenset({PARAGRAPH, EQUATION})

_KEYS: dict[str, frozenset[str]] = {
    PARAGRAPH: frozenset({"kind", "text"}),
    EQUATION: frozenset({"kind", "format", "source"}),
    IMAGE: frozenset({"kind", "asset_id", "caption", "alt_text"}),
    TABLE: frozenset({"kind", "rows"}),
    LIST: frozenset({"kind", "ordered", "items"}),
}


def as_dict(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def check_blocks(
    value: object,
    path: str,
    rules: Rules,
    out: Findings,
    allowed: frozenset[str] = ALL_KINDS,
) -> int:
    """Check a list of blocks; returns how many blocks it holds (0 when it is not a list)."""
    if not isinstance(value, list):
        out.error(path, "BLOCKS_NOT_LIST", "This must be a list of content blocks.")
        return 0
    if len(value) > rules.blocks_per_list:
        out.error(
            path,
            "TOO_MANY_BLOCKS",
            f"At most {rules.blocks_per_list} blocks are allowed here; this has {len(value)}.",
        )
    # Only the first blocks are looked at when there are too many: the work stays bounded.
    for index, block in enumerate(value[: rules.blocks_per_list]):
        _check_block(block, at_index(path, index), rules, out, allowed)
    return len(value)


def _check_block(
    block: object, path: str, rules: Rules, out: Findings, allowed: frozenset[str]
) -> None:
    obj = as_dict(block)
    if obj is None:
        out.error(path, "BLOCK_NOT_OBJECT", "A content block must be an object with a 'kind'.")
        return
    kind = obj.get("kind")
    if not isinstance(kind, str) or kind not in ALL_KINDS:
        out.error(
            at_key(path, "kind"),
            "BLOCK_KIND_UNKNOWN",
            "The block kind must be paragraph, equation, image, table or list.",
        )
        return
    if kind not in allowed:
        out.error(
            at_key(path, "kind"),
            "BLOCK_KIND_NOT_ALLOWED",
            f"A {kind} block can't be used here.",
        )
        return
    for key in obj:
        if key not in _KEYS[kind]:
            out.error(at_key(path, str(key)), "UNKNOWN_FIELD", f"A {kind} block has no '{key}'.")
    if kind == PARAGRAPH:
        _check_paragraph(obj, path, rules, out)
    elif kind == EQUATION:
        _check_equation(obj, path, rules, out)
    elif kind == IMAGE:
        _check_image(obj, path, out)
    elif kind == TABLE:
        _check_table(obj, path, rules, out)
    else:
        _check_list(obj, path, rules, out)


def _check_paragraph(obj: dict[str, object], path: str, rules: Rules, out: Findings) -> None:
    text = obj.get("text")
    where = at_key(path, "text")
    if not isinstance(text, str):
        out.error(where, "TEXT_NOT_STRING", "The text of a paragraph must be text.")
        return
    if len(text) > rules.paragraph_chars:
        out.error(
            where,
            "PARAGRAPH_TOO_LONG",
            f"A paragraph can have at most {rules.paragraph_chars} characters; "
            f"this has {len(text)}.",
        )
        return  # a huge text is not scanned further
    if not text.strip():
        out.warning(where, "PARAGRAPH_EMPTY", "This paragraph is empty.")
        return
    _check_inline_equations(text, where, rules, out)


def _check_inline_equations(text: str, path: str, rules: Rules, out: Findings) -> None:
    r"""Inline equations sit between ``\(`` and ``\)``; a literal backslash is written ``\\``."""
    i, n = 0, len(text)
    start: int | None = None
    while i < n:
        if text[i] == "\\" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "\\":
                i += 2
                continue
            if nxt == "(":
                if start is not None:
                    out.error(
                        path,
                        "INLINE_EQUATION_NESTED",
                        r"An inline equation \( ... \) was opened inside another one.",
                    )
                    return
                start = i + 2
                i += 2
                continue
            if nxt == ")":
                if start is None:
                    out.error(
                        path,
                        "INLINE_EQUATION_UNBALANCED",
                        r"Found \) without a matching \( before it.",
                    )
                    return
                if i - start > rules.equation_chars:
                    out.error(
                        path,
                        "EQUATION_TOO_LONG",
                        f"An equation can have at most {rules.equation_chars} characters.",
                    )
                start = None
                i += 2
                continue
        i += 1
    if start is not None:
        out.error(
            path,
            "INLINE_EQUATION_UNBALANCED",
            r"An inline equation was opened with \( but never closed with \).",
        )


def _check_equation(obj: dict[str, object], path: str, rules: Rules, out: Findings) -> None:
    fmt = obj.get("format")
    if fmt != "latex":
        out.error(
            at_key(path, "format"),
            "EQUATION_FORMAT_UNSUPPORTED",
            "Equations are stored as LaTeX: the format must be 'latex'.",
        )
    source = obj.get("source")
    where = at_key(path, "source")
    if not isinstance(source, str):
        out.error(where, "EQUATION_SOURCE_NOT_STRING", "The source of an equation must be text.")
    elif len(source) > rules.equation_chars:
        out.error(
            where,
            "EQUATION_TOO_LONG",
            f"An equation can have at most {rules.equation_chars} characters; "
            f"this has {len(source)}.",
        )
    elif not source.strip():
        out.incomplete(where, "EQUATION_EMPTY", "This equation has no content yet.")


def _check_image(obj: dict[str, object], path: str, out: Findings) -> None:
    asset = obj.get("asset_id")
    where = at_key(path, "asset_id")
    if asset is None:
        out.incomplete(where, "IMAGE_ASSET_MISSING", "This image block has no picture yet.")
    else:
        try:
            if not isinstance(asset, str):
                raise ValueError
            UUID(asset)
        except ValueError:
            out.error(where, "IMAGE_ASSET_ID_INVALID", "The picture's id is not valid.")
    alt = obj.get("alt_text")
    if alt is None or (isinstance(alt, str) and not alt.strip()):
        out.incomplete(
            at_key(path, "alt_text"),
            "IMAGE_ALT_MISSING",
            "Describe the picture in words (alt text), so it can be understood without seeing it.",
        )
    elif not isinstance(alt, str):
        out.error(at_key(path, "alt_text"), "TEXT_NOT_STRING", "The alt text must be text.")
    caption = obj.get("caption")
    if caption is not None and not isinstance(caption, str):
        out.error(at_key(path, "caption"), "TEXT_NOT_STRING", "The caption must be text.")


def _check_table(obj: dict[str, object], path: str, rules: Rules, out: Findings) -> None:
    rows = obj.get("rows")
    where = at_key(path, "rows")
    if not isinstance(rows, list):
        out.error(where, "TABLE_ROWS_NOT_LIST", "A table needs a list of rows.")
        return
    if not rows:
        out.incomplete(where, "TABLE_EMPTY", "This table has no rows yet.")
        return
    if len(rows) > rules.table_rows:
        out.error(where, "TABLE_TOO_BIG", f"A table can have at most {rules.table_rows} rows.")
        return
    width: int | None = None
    for r, row in enumerate(rows):
        row_path = at_index(where, r)
        if not isinstance(row, list):
            out.error(row_path, "TABLE_ROW_NOT_LIST", "Each table row must be a list of cells.")
            continue
        if len(row) > rules.table_columns:
            out.error(
                row_path,
                "TABLE_TOO_BIG",
                f"A table can have at most {rules.table_columns} columns.",
            )
            continue
        if width is None:
            width = len(row)
        elif len(row) != width:
            out.error(
                row_path,
                "TABLE_NOT_RECTANGULAR",
                f"Every row needs the same number of cells: this has {len(row)}, "
                f"the first has {width}.",
            )
        for c, cell in enumerate(row):
            check_blocks(cell, at_index(row_path, c), rules, out, INNER_KINDS)


def _check_list(obj: dict[str, object], path: str, rules: Rules, out: Findings) -> None:
    ordered = obj.get("ordered", False)
    if not isinstance(ordered, bool):
        out.error(
            at_key(path, "ordered"), "LIST_ORDERED_NOT_BOOLEAN", "'ordered' must be true or false."
        )
    items = obj.get("items")
    where = at_key(path, "items")
    if not isinstance(items, list):
        out.error(where, "LIST_ITEMS_NOT_LIST", "A list needs a list of items.")
        return
    if not items:
        out.incomplete(where, "LIST_EMPTY", "This list has no items yet.")
        return
    if len(items) > rules.list_items:
        out.error(where, "LIST_TOO_BIG", f"A list can have at most {rules.list_items} items.")
        return
    for i, item in enumerate(items):
        check_blocks(item, at_index(where, i), rules, out, INNER_KINDS)
