"""Tagging: choose the chapter, topic, main concept, difficulty and Bloom level (H-07).

The model is shown the coaching's own syllabus under the question's subject and may answer only with
ids from it; any other id, or a topic that is not under the chosen chapter, rejects the whole
answer.
A good answer fills those labels on the working revision (a person can change them afterwards).
"""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import ValidationFailed
from qbank.modules.ai.operations.base import BadOutput, Prepared
from qbank.modules.questions.public import Applied, QuestionForAi, apply_labels
from qbank.modules.taxonomy.public import SubjectSyllabus, bloom_keys, syllabus_of

MAX_OUTPUT_TOKENS = 400
MOST_SYLLABUS_CHARS = 30_000


def _uuid(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _syllabus_text(syllabus: SubjectSyllabus) -> str:
    lines = [f"chapter {item.id} | {item.name}" for item in syllabus.chapters]
    lines += [
        f"topic {item.id} | {item.name} | chapter {item.parent_id}" for item in syllabus.topics
    ]
    lines += [f"concept {item.id} | {item.name}" for item in syllabus.concepts]
    return "\n".join(lines)


def _schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["chapter_id", "topic_id", "primary_concept_id", "difficulty", "bloom_level"],
        "properties": {
            "chapter_id": {"type": "string"},
            "topic_id": {"type": ["string", "null"]},
            "primary_concept_id": {"type": "string"},
            "difficulty": {"type": "integer", "minimum": 1, "maximum": 10},
            "bloom_level": {"type": "string", "enum": list(bloom_keys())},
        },
    }


def _checker(syllabus: SubjectSyllabus) -> Any:
    chapters = {item.id for item in syllabus.chapters}
    topics = {item.id: item.parent_id for item in syllabus.topics}
    concepts = {item.id for item in syllabus.concepts}
    blooms = set(bloom_keys())

    def check(data: dict[str, Any]) -> dict[str, Any]:
        chapter = _uuid(data.get("chapter_id"))
        if chapter is None or chapter not in chapters:
            raise BadOutput("The chapter is not one of this subject's chapters.")
        topic_value = data.get("topic_id")
        topic = _uuid(topic_value)
        if topic_value is not None and (topic is None or topics.get(topic) != chapter):
            raise BadOutput("The topic is not under the chosen chapter.")
        concept = _uuid(data.get("primary_concept_id"))
        if concept is None or concept not in concepts:
            raise BadOutput("The concept is not one of this subject's concepts.")
        difficulty = data.get("difficulty")
        if not isinstance(difficulty, int) or isinstance(difficulty, bool):
            raise BadOutput("The difficulty is not a whole number.")
        if not 1 <= difficulty <= 10:
            raise BadOutput("The difficulty is not between 1 and 10.")
        bloom = data.get("bloom_level")
        if not isinstance(bloom, str) or bloom not in blooms:
            raise BadOutput("The Bloom level is not one of the known levels.")
        labels: dict[str, Any] = {
            "chapter_id": str(chapter),
            "primary_concept_id": str(concept),
            "difficulty": difficulty,
            "bloom_level": bloom,
        }
        if topic is not None:
            labels["topic_id"] = str(topic)
        return labels

    return check


def _apply(
    session: Session, principal: Principal, question: QuestionForAi, labels: dict[str, Any]
) -> Applied:
    return apply_labels(
        session,
        principal,
        question.question_id,
        revision_id=question.revision_id,
        revision=question.revision,
        labels=labels,
    )


def prepare(session: Session, question: QuestionForAi) -> Prepared:
    subject = _uuid(question.metadata.get("subject_id"))
    syllabus = syllabus_of(session, subject) if subject is not None else None
    if syllabus is None:
        raise ValidationFailed(
            "Choose the subject of this question before tagging it.", code="AI_TAG_NEEDS_SUBJECT"
        )
    if not syllabus.chapters or not syllabus.concepts:
        raise ValidationFailed(
            "This subject has no chapters or concepts to choose from yet.",
            code="AI_TAG_NO_SYLLABUS",
        )
    text = _syllabus_text(syllabus)
    if len(text) > MOST_SYLLABUS_CHARS:
        raise ValidationFailed(
            "This subject's syllabus is too large to send in one request.",
            code="AI_TAG_SYLLABUS_TOO_LARGE",
        )
    return Prepared(
        values={"question": question.text, "syllabus": text},
        schema_name="question_labels",
        schema=_schema(),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        check=_checker(syllabus),
        before={
            key: question.metadata.get(key)
            for key in ("chapter_id", "topic_id", "primary_concept_id", "difficulty", "bloom_level")
        },
        apply=_apply,
    )
