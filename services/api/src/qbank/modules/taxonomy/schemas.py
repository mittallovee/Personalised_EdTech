from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from qbank.core.pagination import PageInfo
from qbank.modules.taxonomy.catalogues import LANGUAGE_TAGS

NodeKind = Literal["CLASS", "SUBJECT", "CHAPTER", "TOPIC", "SUBTOPIC"]
NodeState = Literal["ACTIVE", "DEPRECATED"]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def _other_languages(labels: dict[str, str]) -> dict[str, str]:
    for tag in labels:
        if tag == "en":
            raise ValueError("The English name is `name`, not a label.")
        if tag not in LANGUAGE_TAGS:
            raise ValueError(f"'{tag}' is not a language of this app.")
    return labels


# Names in the other languages, keyed by language tag (hi, gu, bn, mr, te, ta).
Labels = Annotated[dict[str, Name], AfterValidator(_other_languages), Field(max_length=10)]


class CreateNode(BaseModel):
    kind: NodeKind
    parent_id: UUID | None = Field(
        default=None,
        description="The item it sits under (a subject sits under a class). None for a class.",
    )
    name: Name = Field(description="The English name.", examples=["Kinematics"])
    labels: Labels = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0, le=100_000, description="Smaller comes first.")


class UpdateNode(BaseModel):
    name: Name | None = None
    labels: Labels | None = Field(
        default=None, description="Replaces all the other-language names when sent."
    )
    sort_order: int | None = Field(default=None, ge=0, le=100_000)


class NodeOut(BaseModel):
    id: UUID
    kind: NodeKind
    parent_id: UUID | None
    name: str
    labels: dict[str, str]
    state: NodeState = Field(description="DEPRECATED items cannot be chosen for new questions.")
    sort_order: int
    revision: int
    created_at: datetime
    updated_at: datetime


class NodePage(BaseModel):
    data: list[NodeOut]
    page: PageInfo


class LanguageOut(BaseModel):
    tag: str = Field(examples=["hi"])
    english_name: str
    native_name: str


class BloomLevelOut(BaseModel):
    key: str = Field(examples=["APPLY"])
    label: str


class DifficultyLevelOut(BaseModel):
    level: int = Field(ge=1, le=10)
    meaning: str
