"""Verifying a question: findings about it, and a corrected version when the model is sure (H-10).

The findings are shown as text. A correction is a whole replacement of the question's content: it
must pass the same validator as a person's save, keeps the labels and the question type as they
were, and is applied only by an explicit "Apply correction" after old and new are shown.
"""

import json
from typing import Any

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.modules.ai.operations.base import (
    BadOutput,
    PrepareContext,
    Prepared,
    RunBase,
    question_json,
)
from qbank.modules.questions.public import (
    Applied,
    Level,
    QuestionForAi,
    apply_changes,
    validate_content,
)

MAX_OUTPUT_TOKENS = 4000
MOST_FINDINGS = 30
MOST_CORRECTED_CHARS = 30_000
_SEVERITIES = ("error", "warning", "note")


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["findings", "corrected_content_json"],
        "properties": {
            "findings": {
                "type": "array",
                "maxItems": MOST_FINDINGS,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "severity", "message"],
                    "properties": {
                        "path": {"type": "string", "maxLength": 200},
                        "severity": {"type": "string", "enum": list(_SEVERITIES)},
                        "message": {"type": "string", "maxLength": 500},
                    },
                },
            },
            "corrected_content_json": {
                "type": ["string", "null"],
                "maxLength": MOST_CORRECTED_CHARS,
            },
        },
    }


def _finding(item: object) -> dict[str, str]:
    if not isinstance(item, dict):
        raise BadOutput("A finding is not an object.")
    path, severity, message = item.get("path"), item.get("severity"), item.get("message")
    if not (isinstance(path, str) and isinstance(message, str) and message.strip()):
        raise BadOutput("A finding lacks its path or message.")
    if severity not in _SEVERITIES:
        raise BadOutput("A finding has an unknown severity.")
    return {"path": path[:200], "severity": severity, "message": message[:500]}


def prepare(session: Session, question: QuestionForAi, context: PrepareContext) -> Prepared:
    del context
    del session
    content = question.content
    original_type = content.get("question_type")
    labels = content.get("metadata")

    def check(data: dict[str, Any]) -> dict[str, Any]:
        raw = data.get("findings")
        if not isinstance(raw, list) or len(raw) > MOST_FINDINGS:
            raise BadOutput("The findings are not a short list.")
        output: dict[str, Any] = {"findings": [_finding(item) for item in raw]}
        corrected_text = data.get("corrected_content_json")
        if corrected_text is None:
            return output
        if not isinstance(corrected_text, str) or len(corrected_text) > MOST_CORRECTED_CHARS:
            raise BadOutput("The corrected content is not usable text.")
        try:
            corrected = json.loads(corrected_text)
        except ValueError:
            raise BadOutput("The corrected content is not valid JSON.") from None
        if not isinstance(corrected, dict) or corrected.get("question_type") != original_type:
            raise BadOutput("The corrected content is not the same kind of question.")
        corrected["metadata"] = labels  # a correction never changes the labels
        # A correction must be a finished question: no errors, and nothing left incomplete (the
        # labels are kept from the original, so they are not held against it).
        if any(
            finding.level is Level.ERROR
            or (finding.level is Level.INCOMPLETE and not finding.path.startswith("metadata"))
            for finding in validate_content(corrected)
        ):
            raise BadOutput("The corrected content does not pass the question checks.")
        output["corrected_content"] = corrected
        return output

    return Prepared(
        values={
            "question": question_json(content, ("metadata", "answer", "solution")),
            "answer": json.dumps(content.get("answer"), ensure_ascii=False),
            "solution": json.dumps(content.get("solution"), ensure_ascii=False),
        },
        schema_name="question_review",
        schema=_schema(),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        check=check,
        before={"content": {k: v for k, v in content.items() if k != "metadata"}},
        apply=None,
    )


def accept(
    session: Session, principal: Principal, base: RunBase, output: dict[str, Any]
) -> Applied:
    """Replace the working revision's content with the corrected content (labels kept)."""
    corrected = output.get("corrected_content")
    if not isinstance(corrected, dict):
        return "OUT_OF_DATE"
    return apply_changes(
        session,
        principal,
        base.question_id,
        revision_id=base.revision_id,
        revision=base.revision,
        change=lambda current: {**corrected, "metadata": current.get("metadata")},
    )
