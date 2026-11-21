"""A stand-in provider that gives sensible answers: for trying the screens and the browser tests.

``FakeProvider`` answers from a script, which suits unit tests. This one reads the request and
answers it the way a careful but unambitious model would: it tags with the first chapter, a topic
under it and the first concept of the syllabus it is shown, solves with the first option, finds
nothing serious when asked to verify, and "translates" by marking each piece of text. Every answer
passes the same checks as a real one, so the whole path (prompt, budget, check, apply) is exercised
without a key, a network or a bill.

It is switched on only by ``AI_DEMO_PROVIDER=true``, which staging and production refuse. It is
never offered as a provider a coaching can choose: it takes the place of the OpenAI adapter.
"""

import json
import re
from typing import Any

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    ModelInfo,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.providers.fake import DEFAULT_MODELS

_DATA = re.compile(r'<data name="(\w+)">\n(.*?)\n</data>', re.DOTALL)
_ID = r"[0-9a-fA-F-]{36}"
_TRANSLATABLE = ("text", "caption", "alt_text")


def _sections(user: str) -> dict[str, str]:
    return {name: body.replace("<\\/data", "</data") for name, body in _DATA.findall(user)}


def _labels(syllabus: str) -> dict[str, Any]:
    chapters = re.findall(rf"^chapter ({_ID}) \|", syllabus, re.MULTILINE)
    topics = re.findall(rf"^topic ({_ID}) \| .* \| chapter ({_ID})$", syllabus, re.MULTILINE)
    concepts = re.findall(rf"^concept ({_ID}) \|", syllabus, re.MULTILINE)
    chapter = chapters[0] if chapters else ""
    topic = next((t for t, c in topics if c == chapter), None)
    return {
        "chapter_id": chapter,
        "topic_id": topic,
        "primary_concept_id": concepts[0] if concepts else "",
        "difficulty": 6,
        "bloom_level": "APPLY",
    }


def _answer(format_text: str) -> dict[str, Any]:
    if format_text.startswith("NUMERICAL"):
        return {"mode": "exact", "value": "9.80", "lower": None, "upper": None}
    if format_text.startswith("MULTI_CORRECT"):
        listed = re.search(r"from ([^.]*)\.", format_text)
        first = (listed.group(1).split(",")[0].strip() if listed else "A") or "A"
        return {"option_ids": [first]}
    if format_text.startswith(("INTEGER", "SINGLE_DIGIT")):
        return {"value": 7}
    listed = re.search(r"one of ([^.]*)\.", format_text)
    return {"option_id": (listed.group(1).split(",")[0].strip() if listed else "A") or "A"}


def _mark(value: Any) -> Any:
    """The question with the words of its text fields marked as translated, everything else kept."""
    if isinstance(value, dict):
        return {
            key: (
                f"[translated] {item}"
                if key in _TRANSLATABLE and isinstance(item, str)
                else _mark(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_mark(item) for item in value]
    return value


class DemoProvider:
    name = Provider.OPENAI

    def list_models(self, api_key: str) -> list[ModelInfo]:
        return list(DEFAULT_MODELS)

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        parts = _sections(request.user)
        data: dict[str, Any]
        if request.schema_name == "question_labels":
            data = _labels(parts.get("syllabus", ""))
        elif request.schema_name == "question_answer":
            data = {
                "answer": _answer(parts.get("format", "")),
                "solution": "Worked out by the demo provider.\n\nThis is not a real solution.",
            }
        elif request.schema_name == "question_review":
            data = {
                "findings": [
                    {
                        "path": "stem",
                        "severity": "note",
                        "message": "Demo check: nothing serious found. This is not a real review.",
                    }
                ],
                "corrected_content_json": None,
            }
        elif request.schema_name == "question_translation":
            question = json.loads(parts.get("question", "{}"))
            data = {"content_json": json.dumps(_mark(question), ensure_ascii=False)}
        else:
            data = {}
        return StructuredResult(data, tokens_in=1200, tokens_out=300)
