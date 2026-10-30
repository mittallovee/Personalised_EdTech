"""Matching, assertion-reason, multiple-statement questions and the passage context (D-01, D-14).

- Matching: left and right items (2 to 10 each by default) and exactly four options, each a mapping
  from every left item to one or more right items. Exactly one option is correct; in the *correct*
  mapping a right item may not be used under two left items. Distractors may do so, and unused right
  items are fine.
- Assertion-reason: an assertion, a reason and four options whose wording is the author's.
- Multiple statement: 2 to 10 statements and four options.
- Context: a child of a passage names the passage revision it was written with and its order.
  That the revision exists and is reachable is checked where the database is (a later pull request).

Item and option ids are unique across the whole question.
"""

from uuid import UUID

from qbank.modules.questions.answers import check_option_count, is_id, is_whole_number
from qbank.modules.questions.blocks import as_dict, check_blocks, has_content
from qbank.modules.questions.findings import Findings, at_index, at_key
from qbank.modules.questions.rules import Rules

_MAX_ORDINAL = 1_000


def check_text_part(content: dict[str, object], field: str, rules: Rules, out: Findings) -> None:
    """The assertion or the reason of an assertion-reason question: a list of blocks."""
    blocks = content.get(field)
    if blocks is not None:
        check_blocks(blocks, field, rules, out)
    if blocks is None or (isinstance(blocks, list) and not has_content(blocks)):
        out.incomplete(field, f"{field.upper()}_MISSING", f"Write the {field}.")


def check_items(
    content: dict[str, object],
    field: str,
    low: int,
    high: int,
    noun: str,
    rules: Rules,
    out: Findings,
    taken: set[str],
) -> list[str] | None:
    """Items with an id and content: the left or right column, or the statements.

    ``taken`` holds the ids already used elsewhere in the question and grows with this list's ids.
    Returns this list's usable ids, or ``None`` when the list is missing or not a list.
    """
    items = content.get(field)
    if items is None:
        out.incomplete(field, f"{field.upper()}_MISSING", f"Add the {noun}.")
        return None
    if not isinstance(items, list):
        out.error(field, f"{field.upper()}_NOT_LIST", f"The {noun} must be a list.")
        return None
    if len(items) < low:
        out.incomplete(field, f"{field.upper()}_COUNT", f"Add at least {low} {noun}.")
    elif len(items) > high:
        out.error(field, f"{field.upper()}_COUNT", f"At most {high} {noun} are allowed.")
    ids: list[str] = []
    for index, item in enumerate(items[: high + 1]):
        where = at_index(field, index)
        obj = as_dict(item)
        if obj is None:
            out.error(where, "ITEM_NOT_OBJECT", "Each entry needs an id and content.")
            continue
        for key in obj:
            if key not in ("id", "content"):
                out.error(at_key(where, str(key)), "UNKNOWN_FIELD", f"An entry has no '{key}'.")
        item_id = obj.get("id")
        if not isinstance(item_id, str) or not is_id(item_id):
            out.error(
                at_key(where, "id"),
                "ITEM_ID_INVALID",
                "An id is 1 to 20 letters, digits, '_' or '-' (for example L1).",
            )
        elif item_id in taken:
            out.error(
                at_key(where, "id"),
                "ITEM_ID_DUPLICATE",
                f"The id {item_id} is used twice. Ids must be different across the whole question.",
            )
        else:
            taken.add(item_id)
            ids.append(item_id)
        blocks = obj.get("content")
        if blocks is not None:
            check_blocks(blocks, at_key(where, "content"), rules, out)
        if blocks is None or (isinstance(blocks, list) and not has_content(blocks)):
            out.incomplete(at_key(where, "content"), "ITEM_EMPTY", "This entry has no content yet.")
    return ids


def check_mapping_options(
    content: dict[str, object],
    left_ids: list[str] | None,
    right_ids: list[str] | None,
    taken: set[str],
    rules: Rules,
    out: Findings,
) -> tuple[list[str] | None, dict[str, dict[str, list[str]]]]:
    """The four options of a matching question, each a mapping from left ids to right ids.

    Returns the option ids that can be answered with (or ``None`` when there are no options yet) and
    the mappings that were read cleanly, by option id.
    """
    options = content.get("options")
    if options is None:
        out.incomplete("options", "OPTIONS_MISSING", f"Add the {rules.option_count} options.")
        return None, {}
    if not isinstance(options, list):
        out.error("options", "OPTIONS_NOT_LIST", "The options must be a list.")
        return None, {}
    check_option_count(options, rules, out)
    ids: list[str] = []
    mappings: dict[str, dict[str, list[str]]] = {}
    for index, option in enumerate(options[: rules.option_count + 1]):
        where = at_index("options", index)
        obj = as_dict(option)
        if obj is None:
            out.error(where, "OPTION_NOT_OBJECT", "An option needs an id and a mapping.")
            continue
        for key in obj:
            if key not in ("id", "mapping"):
                out.error(at_key(where, str(key)), "UNKNOWN_FIELD", f"An option has no '{key}'.")
        option_id = obj.get("id")
        if not isinstance(option_id, str) or not is_id(option_id):
            out.error(
                at_key(where, "id"),
                "OPTION_ID_INVALID",
                "An option id is 1 to 20 letters, digits, '_' or '-' (for example A).",
            )
            option_id = None
        elif option_id in taken:
            out.error(
                at_key(where, "id"),
                "OPTION_ID_DUPLICATE",
                f"The id {option_id} is used twice. "
                "Ids must be different across the whole question.",
            )
        else:
            taken.add(option_id)
            ids.append(option_id)
        mapping = _check_mapping(
            obj.get("mapping"), at_key(where, "mapping"), left_ids, right_ids, out
        )
        if mapping is not None and option_id is not None and option_id in ids:
            mappings[option_id] = mapping
    return ids, mappings


def _check_mapping(
    value: object,
    path: str,
    left_ids: list[str] | None,
    right_ids: list[str] | None,
    out: Findings,
) -> dict[str, list[str]] | None:
    if value is None:
        out.incomplete(path, "MAPPING_MISSING", "This option needs a mapping.")
        return None
    mapping = as_dict(value)
    if mapping is None:
        out.error(
            path, "MAPPING_NOT_OBJECT", "A mapping lists, for each left item, its right items."
        )
        return None
    clean: dict[str, list[str]] = {}
    for left, rights in mapping.items():
        where = at_key(path, str(left))
        if left_ids is not None and left not in left_ids:
            out.error(where, "MAPPING_LEFT_UNKNOWN", f"{left} is not a left item.")
            continue
        if not isinstance(rights, list) or not all(isinstance(r, str) for r in rights):
            out.error(
                where, "MAPPING_NOT_LIST", "Name the right items as a list of ids, like [R1]."
            )
            continue
        if not rights:
            out.incomplete(where, "MAPPING_EMPTY", f"{left} needs at least one right item.")
            continue
        names = [str(r) for r in rights]
        if len(set(names)) != len(names):
            out.error(where, "MAPPING_RIGHT_DUPLICATE", "A right item is named twice.")
            continue
        unknown = [r for r in names if right_ids is not None and r not in right_ids]
        if unknown:
            out.error(where, "MAPPING_RIGHT_UNKNOWN", f"{unknown[0]} is not a right item.")
            continue
        clean[str(left)] = names
    if left_ids is not None:
        for left in left_ids:
            if left not in mapping:
                out.incomplete(
                    at_key(path, left),
                    "MAPPING_LEFT_MISSING",
                    f"This mapping has nothing for {left}.",
                )
    return clean


def check_correct_mapping(
    answer: object, mappings: dict[str, dict[str, list[str]]], out: Findings
) -> None:
    """In the chosen (correct) mapping no right item may appear under two left items."""
    obj = as_dict(answer)
    chosen = obj.get("option_id") if obj is not None else None
    if not isinstance(chosen, str) or chosen not in mappings:
        return
    used: dict[str, str] = {}
    for left, rights in mappings[chosen].items():
        for right in rights:
            if right in used and used[right] != left:
                out.error(
                    at_key("answer", "option_id"),
                    "ANSWER_MAPPING_SHARES_RIGHT",
                    f"The correct mapping uses {right} for both {used[right]} and {left}. "
                    "In the correct answer a right item can match only one left item.",
                )
                return
            used[right] = left


def check_context(value: object, out: Findings) -> None:
    """A child of a passage: which passage revision it was written with, and its order."""
    if value is None:
        return
    obj = as_dict(value)
    if obj is None:
        out.error("context", "CONTEXT_NOT_OBJECT", "The context must name a passage and an order.")
        return
    for key in obj:
        if key not in ("passage_revision_id", "ordinal"):
            out.error(at_key("context", str(key)), "UNKNOWN_FIELD", f"The context has no '{key}'.")
    passage = obj.get("passage_revision_id")
    where = at_key("context", "passage_revision_id")
    if passage is None:
        out.incomplete(
            where, "CONTEXT_PASSAGE_MISSING", "Choose the passage this question belongs to."
        )
    else:
        try:
            if not isinstance(passage, str):
                raise ValueError
            UUID(passage)
        except ValueError:
            out.error(where, "CONTEXT_PASSAGE_INVALID", "The passage's id is not valid.")
    ordinal = obj.get("ordinal")
    where = at_key("context", "ordinal")
    if ordinal is None:
        out.incomplete(
            where, "CONTEXT_ORDINAL_MISSING", "Give the question's number within the passage."
        )
    elif (
        not is_whole_number(ordinal)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= _MAX_ORDINAL
    ):
        out.error(
            where,
            "CONTEXT_ORDINAL_INVALID",
            f"The number within the passage must be a whole number from 1 to {_MAX_ORDINAL}.",
        )
