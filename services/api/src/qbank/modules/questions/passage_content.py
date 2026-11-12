"""What is wrong with a passage's content (M3 design note §5.6, D-14).

A passage is shared text that several questions sit under. Its content is a small object: a short
title, so it can be found in a list, and a body made of the same content blocks as a question's
stem. Like a question, a draft with gaps is normal, so every problem is a finding, never an error.
"""

import json
import unicodedata

from qbank.modules.questions.blocks import as_dict, check_blocks, has_content
from qbank.modules.questions.findings import Finding, Findings
from qbank.modules.questions.rules import DEFAULT_RULES, Rules

SCHEMA_VERSION = 1
TITLE_CHARS = 200
_FIELDS = frozenset({"schema_version", "title", "body"})


def empty_passage() -> dict[str, object]:
    """The content a new passage starts from."""
    return {"schema_version": SCHEMA_VERSION, "title": "", "body": []}


def validate_passage(content: object, rules: Rules = DEFAULT_RULES) -> list[Finding]:
    """The findings for a passage's content (an empty list means nothing is wrong)."""
    out = Findings()
    obj = as_dict(content)
    if obj is None:
        out.error("", "CONTENT_NOT_OBJECT", "The passage content must be an object.")
        return out.items
    try:
        size = len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    except TypeError, ValueError:
        out.error("", "CONTENT_NOT_JSON", "The passage content has a value that is not plain data.")
        return out.items
    if size > rules.revision_bytes:
        out.error(
            "",
            "CONTENT_TOO_LARGE",
            f"This passage is {size // 1024} KB; the limit is {rules.revision_bytes // 1024} KB.",
        )
        return out.items  # a huge document is not walked further

    version = obj.get("schema_version")
    if version != SCHEMA_VERSION or isinstance(version, bool):
        out.error(
            "schema_version",
            "SCHEMA_VERSION_UNSUPPORTED",
            f"The content must have schema_version {SCHEMA_VERSION}.",
        )
    for key in obj:
        if key not in _FIELDS:
            out.error(str(key), "FIELD_NOT_ALLOWED", f"A passage has no '{key}'.")

    _check_title(obj.get("title"), out)

    body = obj.get("body")
    if body is not None:
        check_blocks(body, "body", rules, out)
    if body is None or (isinstance(body, list) and not has_content(body)):
        out.incomplete("body", "PASSAGE_BODY_EMPTY", "Write the passage.")
    return out.items


def _check_title(title: object, out: Findings) -> None:
    if title is None or (isinstance(title, str) and not title.strip()):
        out.incomplete(
            "title", "PASSAGE_TITLE_MISSING", "Give the passage a short title so it can be found."
        )
    elif not isinstance(title, str):
        out.error("title", "TEXT_NOT_STRING", "The title must be text.")
    elif len(title) > TITLE_CHARS:
        out.error(
            "title",
            "PASSAGE_TITLE_TOO_LONG",
            f"A title can have at most {TITLE_CHARS} characters; this has {len(title)}.",
        )
    elif any(unicodedata.category(char) == "Cc" for char in title):
        out.error(
            "title",
            "PASSAGE_TITLE_NOT_ONE_LINE",
            "The title is one line: no new lines, tabs or other control characters.",
        )
