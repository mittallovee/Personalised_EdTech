"""Translations of a question: the link to the source and the "source updated" flag (H-08, D-13).

A translation is an ordinary question of its own. ``question_links`` records which version of the
source it was made from; whether the source has since published a newer version is worked out here
when a question is read, and is never stored.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.modules.questions.models import (
    QuestionLink,
    QuestionMaster,
    QuestionVersion,
)


@dataclass(frozen=True, slots=True)
class TranslationOf:
    """What a translated question says about its source."""

    source_id: UUID
    source_code: str
    source_version_number: int  # the version that was translated
    language: str
    source_updated: bool  # the source has published a newer version (D-13)


def translation_of(session: Session, master_id: UUID) -> TranslationOf | None:
    """The source of a translation, or ``None`` when the question is not a translation."""
    link = session.scalars(
        select(QuestionLink).where(
            QuestionLink.target_master_id == master_id, QuestionLink.kind == "TRANSLATION"
        )
    ).first()
    if link is None:
        return None
    source = session.get(QuestionMaster, link.source_master_id)
    if source is None:  # cannot happen (composite key); a read never fails because of it
        return None
    published = (
        session.get(QuestionVersion, source.published_version_id)
        if source.published_version_id is not None
        else None
    )
    return TranslationOf(
        source_id=source.id,
        source_code=source.code,
        source_version_number=link.source_version_number,
        language=link.language,
        source_updated=published is not None and published.number > link.source_version_number,
    )


def add_link(
    session: Session,
    principal: Principal,
    *,
    organization_id: UUID,
    source_id: UUID,
    source_version_number: int,
    target_id: UUID,
    language: str,
) -> None:
    session.add(
        QuestionLink(
            organization_id=organization_id,
            kind="TRANSLATION",
            source_master_id=source_id,
            source_version_number=source_version_number,
            target_master_id=target_id,
            language=language,
            created_by=principal.user_id,
        )
    )
    session.flush()


def structure_matches(source: Any, translated: Any, *, translatable: frozenset[str]) -> bool:
    """Whether ``translated`` has exactly the shape of ``source``: the same keys, list lengths and
    values everywhere, except that text under the ``translatable`` keys may differ. This is what
    stops a translation from changing the answer, the option ids, an equation or a picture."""
    if isinstance(source, dict):
        return (
            isinstance(translated, dict)
            and source.keys() == translated.keys()
            and all(_same_leaf(key, source[key], translated[key], translatable) for key in source)
        )
    if isinstance(source, list):
        return (
            isinstance(translated, list)
            and len(source) == len(translated)
            and all(
                structure_matches(a, b, translatable=translatable)
                for a, b in zip(source, translated, strict=True)
            )
        )
    return bool(source == translated and type(source) is type(translated))


def _same_leaf(key: str, source: Any, translated: Any, translatable: frozenset[str]) -> bool:
    if key in translatable and isinstance(source, str):
        return isinstance(translated, str)
    return structure_matches(source, translated, translatable=translatable)
