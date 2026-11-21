"""Translating a question into another language (H-08).

The model is given the whole question (without its labels), the coaching's glossary entries that
matter for it, and the languages. What comes back must have **exactly the structure of the source**:
the same keys, the same option ids, the same answer, the same equations and pictures; only the words
(text, captions, picture descriptions) may differ. It must also pass the question validator without
new errors. Nothing is created until a person applies the result, and then it becomes a **new draft
question** of that person, linked to its source; the source is never changed.
"""

import json
from typing import Any

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import ValidationFailed
from qbank.modules.ai import glossary
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
    create_translation,
    structure_matches,
    validate_content,
)
from qbank.modules.taxonomy.public import language_names

MAX_OUTPUT_TOKENS = 8000
MOST_CONTENT_CHARS = 60_000
TRANSLATABLE = frozenset({"text", "caption", "alt_text"})


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["content_json"],
        "properties": {
            "content_json": {
                "type": "string",
                "maxLength": MOST_CONTENT_CHARS,
                "description": "The whole translated question as JSON text, with exactly the"
                " structure of the question you were given.",
            }
        },
    }


def _errors(content: dict[str, Any]) -> set[tuple[str, str]]:
    return {(f.path, f.code) for f in validate_content(content) if f.level is Level.ERROR}


def prepare(session: Session, question: QuestionForAi, context: PrepareContext) -> Prepared:
    content = question.content
    languages = language_names()
    target = context.target_language
    if target is None or target not in languages:
        raise ValidationFailed(
            "Choose the language to translate into.", code="AI_TRANSLATE_LANGUAGE_INVALID"
        )
    source_language = content.get("language")
    if source_language == target:
        raise ValidationFailed(
            "The question is already in that language.", code="AI_TRANSLATE_SAME_LANGUAGE"
        )
    already = _errors(content)

    def check(data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("content_json")
        if not isinstance(text, str) or len(text) > MOST_CONTENT_CHARS:
            raise BadOutput("The translation is not usable text.")
        try:
            translated = json.loads(text)
        except ValueError:
            raise BadOutput("The translation is not valid JSON.") from None
        if not isinstance(translated, dict):
            raise BadOutput("The translation is not an object.")
        # The labels and the language are ours, not the model's: compare everything else.
        translated["metadata"] = content.get("metadata")
        translated["language"] = content.get("language")
        if not structure_matches(content, translated, translatable=TRANSLATABLE):
            raise BadOutput("The translation does not keep the structure of the question.")
        translated["language"] = target
        if _errors(translated) - already:
            raise BadOutput("The translation does not pass the question checks.")
        return {"language": target, "content": translated}

    terms = glossary.terms_for(session, context.organization_id, target, text=question.text)
    return Prepared(
        values={
            "question": question_json(content, ("metadata",)),
            "source_language": languages.get(str(source_language), str(source_language or "")),
            "target_language": languages[target],
            "glossary": glossary.render_terms(terms),
        },
        schema_name="question_translation",
        schema=_schema(),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        check=check,
        before={},
        apply=None,
    )


def accept(
    session: Session, principal: Principal, base: RunBase, output: dict[str, Any]
) -> Applied:
    """Make the translation a new draft question linked to its source. The new question's id and
    code are added to ``output`` (the caller stores it back on the run)."""
    status, created = create_translation(
        session,
        principal,
        base.question_id,
        revision_id=base.revision_id,
        revision=base.revision,
        language=output["language"],
        content=output["content"],
        request_id=base.request_id,
    )
    if created is not None:
        output["created_question"] = {"id": str(created.id), "code": created.code}
    return status
