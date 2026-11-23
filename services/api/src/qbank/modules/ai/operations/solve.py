"""Solving a question that has no answer: a suggested answer and a worked solution (H-09).

The model sees the question without its labels, answer or solution, and is told what shape the
answer must take for this question type. The answer is checked by the same validator that checks a
person's save. Nothing is written until a person applies the suggestion (old and new are shown).
"""

from typing import Any

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import ValidationFailed
from qbank.modules.ai.operations.base import (
    BadOutput,
    PrepareContext,
    Prepared,
    RunBase,
    question_json,
)
from qbank.modules.questions.public import (
    QUESTION_TYPES,
    Applied,
    Level,
    QuestionForAi,
    apply_changes,
    validate_content,
)

MAX_OUTPUT_TOKENS = 2000
MOST_SOLUTION_CHARS = 6000
_OPTION_TYPES = ("SCQ", "MATCHING", "ASSERTION_REASON", "MULTIPLE_STATEMENT", "PASSAGE_CHILD")


def _option_ids(content: dict[str, Any]) -> list[str]:
    options = content.get("options")
    if not isinstance(options, list):
        return []
    return [
        o["id"] for o in options if isinstance(o, dict) and isinstance(o.get("id"), str) and o["id"]
    ]


def _answer_schema(question_type: str, ids: list[str]) -> dict[str, Any]:
    if question_type in _OPTION_TYPES:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["option_id"],
            "properties": {"option_id": {"type": "string", "enum": ids}},
        }
    if question_type == "MULTI_CORRECT":
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["option_ids"],
            "properties": {
                "option_ids": {"type": "array", "items": {"type": "string", "enum": ids}}
            },
        }
    if question_type in ("INTEGER", "SINGLE_DIGIT"):
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["value"],
            "properties": {"value": {"type": "integer"}},
        }
    return {  # NUMERICAL: decimal text with two decimals, an exact value or one range
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "value", "lower", "upper"],
        "properties": {
            "mode": {"type": "string", "enum": ["exact", "range"]},
            "value": {"type": ["string", "null"]},
            "lower": {"type": ["string", "null"]},
            "upper": {"type": ["string", "null"]},
        },
    }


def _format_text(question_type: str, ids: list[str]) -> str:
    if question_type == "NUMERICAL":
        return (
            "NUMERICAL: give mode 'exact' with value, or mode 'range' with lower and upper, as"
            " decimal text with exactly two decimals; leave the unused fields null."
        )
    if question_type == "MULTI_CORRECT":
        return f"MULTI_CORRECT: option_ids, a list from {', '.join(ids)}."
    if question_type in ("INTEGER", "SINGLE_DIGIT"):
        return f"{question_type}: value, a whole number."
    return f"{question_type}: option_id, one of {', '.join(ids)}."


def _paragraphs(text: str) -> list[dict[str, str]]:
    return [
        {"kind": "paragraph", "text": part.strip()} for part in text.split("\n\n") if part.strip()
    ]


def prepare(session: Session, question: QuestionForAi, context: PrepareContext) -> Prepared:
    del context
    del session
    content = question.content
    question_type = content.get("question_type")
    if question_type not in (*QUESTION_TYPES, "PASSAGE_CHILD"):
        raise ValidationFailed(
            "This question's type is not known, so it cannot be solved.",
            code="AI_SOLVE_UNSUPPORTED",
        )
    ids = _option_ids(content)
    if question_type in (*_OPTION_TYPES, "MULTI_CORRECT") and not ids:
        raise ValidationFailed(
            "Add the answer options before asking the AI to solve it.",
            code="AI_SOLVE_NEEDS_OPTIONS",
        )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["answer", "solution"],
        "properties": {
            "answer": _answer_schema(str(question_type), ids),
            "solution": {"type": "string", "maxLength": MOST_SOLUTION_CHARS},
        },
    }

    def check(data: dict[str, Any]) -> dict[str, Any]:
        answer = data.get("answer")
        solution = data.get("solution")
        if not isinstance(answer, dict):
            raise BadOutput("The answer is not an object.")
        if not isinstance(solution, str) or not solution.strip():
            raise BadOutput("The worked solution is missing.")
        if len(solution) > MOST_SOLUTION_CHARS:
            raise BadOutput("The worked solution is too long.")
        if question_type == "NUMERICAL":  # the schema had the model fill every field; keep its own
            answer = {key: value for key, value in answer.items() if value is not None}
        blocks = _paragraphs(solution)
        candidate = {**content, "answer": answer, "solution": blocks}
        for finding in validate_content(candidate):
            if finding.level is Level.ERROR and finding.path.startswith(("answer", "solution")):
                raise BadOutput("The answer or the solution does not pass the question checks.")
        return {"answer": answer, "solution": blocks}

    return Prepared(
        values={
            "question": question_json(content, ("metadata", "answer", "solution")),
            "format": _format_text(str(question_type), ids),
        },
        schema_name="question_answer",
        schema=schema,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        check=check,
        before={"answer": content.get("answer"), "solution": content.get("solution")},
        apply=None,
    )


def accept(
    session: Session, principal: Principal, base: RunBase, output: dict[str, Any]
) -> Applied:
    """Put the suggested answer and solution into the working revision the run was based on."""
    return apply_changes(
        session,
        principal,
        base.question_id,
        revision_id=base.revision_id,
        revision=base.revision,
        change=lambda current: {
            **current,
            "answer": output["answer"],
            "solution": output["solution"],
        },
    )
