"""A provider that answers by itself, for trying the screens and for the browser tests (M5 5l).

It speaks the same interface as the real adapters, never touches the network and needs no real key,
so a person (or a browser test) can run every AI screen end to end: refresh the models, tag, solve,
verify, translate, and an Economy run. Its answers are made from the request alone, so they are
always valid for the question asked, and they are plainly fake (a translation is the same text with
the language name added). It is **never** on by itself: ``AI_DEMO_PROVIDER=true`` turns it on for
the whole process, and the settings refuse that outside local development and tests.

Because the API and the worker are separate processes, it keeps no state. A batch's id carries what
the worker needs later (when it was sent, which answer it is for), and a batch is "done" a few
seconds after it was sent. That is enough for an Economy *verification* to complete; the other
operations' answers need the question itself, which a stateless batch no longer has, so they end as
an unusable answer. Documented in ``docs/operations/m5-demo.md``.
"""

import json
import re
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import (
    BatchAnswer,
    BatchState,
    ModelInfo,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
    StructuredResult,
)

BATCH_SECONDS = 3  # how long after it was sent a demo batch counts as done
_DATA = re.compile(r'<data name="([a-z_]+)">\n(.*?)\n</data>', re.DOTALL)
_BATCH = re.compile(r"demo-(\d{1,12})-([a-z_]{1,40})-([A-Za-z0-9-]{1,64})")
_TRANSLATABLE = ("text", "caption", "alt_text")
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

MODELS = (
    ModelInfo(
        "demo-small",
        "Demo small",
        supports_vision=False,
        supports_json=True,
        context_tokens=128_000,
        price_in_per_mtok=Decimal("0.5"),
        price_out_per_mtok=Decimal("1.5"),
    ),
    ModelInfo(
        "demo-large",
        "Demo large",
        supports_vision=True,
        supports_json=True,
        context_tokens=200_000,
        price_in_per_mtok=Decimal("5"),
        price_out_per_mtok=Decimal("15"),
    ),
)

_REVIEW_FINDINGS = [
    {
        "path": "stem",
        "severity": "note",
        "message": "Demo provider: this is a made-up finding, not a real check.",
    }
]


def _blocks(request: StructuredRequest) -> dict[str, str]:
    return {name: body for name, body in _DATA.findall(request.user)}


def _json(text: str | None) -> Any:
    try:
        return json.loads(text) if text else None
    except ValueError:
        return None


def _suffixed(node: Any, suffix: str) -> Any:
    """The same structure with the words of every translatable text marked; nothing else moves."""
    if isinstance(node, dict):
        return {
            key: value + suffix
            if key in _TRANSLATABLE and isinstance(value, str)
            else _suffixed(value, suffix)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_suffixed(item, suffix) for item in node]
    return node


def _tokens(request: StructuredRequest) -> tuple[int, int]:
    return max(1, (len(request.system) + len(request.user)) // 4), 120


class DemoProvider:
    """Stands in for any provider (``name`` says which one it is playing)."""

    def __init__(self, name: Provider = Provider.OPENAI) -> None:
        self.name = name

    def list_models(self, api_key: str) -> list[ModelInfo]:
        del api_key
        return list(MODELS)

    # --- The answers, one per locked schema ------------------------------------------------------

    def _tag(self, request: StructuredRequest) -> dict[str, Any]:
        lines = _blocks(request).get("syllabus", "").splitlines()
        chapter = topic = concept = None
        for line in lines:
            kind, _, rest = line.partition(" ")
            first = re.match(_UUID, rest)
            if first is None:
                continue
            if kind == "chapter" and chapter is None:
                chapter = first.group(0)
            elif kind == "concept" and concept is None:
                concept = first.group(0)
        for line in lines:
            if line.startswith("topic "):
                ids = re.findall(_UUID, line)
                if len(ids) == 2 and ids[1] == chapter:
                    topic = ids[0]
                    break
        if chapter is None or concept is None:
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)
        return {
            "chapter_id": chapter,
            "topic_id": topic,
            "primary_concept_id": concept,
            "difficulty": 6,
            "bloom_level": "APPLY",
        }

    def _solve(self, request: StructuredRequest) -> dict[str, Any]:
        shape = request.schema["properties"]["answer"]
        needs = shape.get("required", [])
        if needs == ["option_id"]:
            answer: dict[str, Any] = {"option_id": shape["properties"]["option_id"]["enum"][0]}
        elif needs == ["option_ids"]:
            answer = {"option_ids": [shape["properties"]["option_ids"]["items"]["enum"][0]]}
        elif needs == ["value"]:
            answer = {"value": 7}  # a whole number valid for an integer and for a single digit
        else:
            answer = {"mode": "exact", "value": "9.81", "lower": None, "upper": None}
        return {
            "answer": answer,
            "solution": "Demo provider: this worked solution is made up.\n\nSo the answer follows.",
        }

    def _verify(self, request: StructuredRequest) -> dict[str, Any]:
        blocks = _blocks(request)
        question = _json(blocks.get("question"))
        corrected: str | None = None
        stem = question.get("stem") if isinstance(question, dict) else None
        answer = _json(blocks.get("answer"))
        if (
            isinstance(stem, list)
            and stem
            and isinstance(stem[0], dict)
            and "text" in stem[0]
            and isinstance(answer, dict)  # an unfinished question is only commented on
        ):
            question = {**question, "answer": answer}
            question["solution"] = _json(blocks.get("solution"))
            question["stem"] = [{**stem[0], "text": stem[0]["text"] + " (checked)"}, *stem[1:]]
            corrected = json.dumps(question, ensure_ascii=False)
        return {"findings": _REVIEW_FINDINGS, "corrected_content_json": corrected}

    def _translate(self, request: StructuredRequest) -> dict[str, Any]:
        blocks = _blocks(request)
        question = _json(blocks.get("question"))
        if not isinstance(question, dict):
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT)
        suffix = f" [{blocks.get('target_language', 'translated')}]"
        return {"content_json": json.dumps(_suffixed(question, suffix), ensure_ascii=False)}

    def generate_structured(self, api_key: str, request: StructuredRequest) -> StructuredResult:
        del api_key
        answers: dict[str, Callable[[StructuredRequest], dict[str, Any]]] = {
            "question_labels": self._tag,
            "question_answer": self._solve,
            "question_review": self._verify,
            "question_translation": self._translate,
            "page_questions": self._page_questions,
            "smoke": self._smoke,
        }
        make = answers.get(request.schema_name)
        if make is None:
            raise ProviderError(ProviderErrorKind.BAD_REQUEST)
        tokens_in, tokens_out = _tokens(request)
        return StructuredResult(make(request), tokens_in, tokens_out)

    def _page_questions(self, request: StructuredRequest) -> dict[str, Any]:
        """A page of a document: one single-correct question built from the page's own text, so the
        review screen has something real to show (a page with no text says it has no questions)."""
        blocks = _blocks(request)
        number = blocks.get("page_number", "1").strip()
        text = blocks.get("page_text", "").strip()
        if not text and not request.images:
            return {"questions": [], "unreadable": [], "no_questions": True}
        stem = text.splitlines()[0][:300] if text else f"Demo question read from page {number}"
        question = {
            "question_type": "SCQ",
            "language": "en",
            "stem": stem,
            "options": ["4", "5", "6", "7"],
            "statements": [],
            "assertion": None,
            "reason": None,
            "left": [],
            "right": [],
            "matching_options": [],
            "answer_text": "B",
            "solution": None,
            "region": {"x": 0.05, "y": 0.1, "w": 0.9, "h": 0.3},
            "confidence": "HIGH",
            "handwritten": False,
            "notes": "Demo provider: a made-up reading, not a real one.",
        }
        return {"questions": [question], "unreadable": [], "no_questions": False}

    def _smoke(self, request: StructuredRequest) -> dict[str, Any]:
        del request
        return {"ok": True}

    # --- Economy: a stateless batch service ------------------------------------------------------

    def submit_batch(self, api_key: str, *, tag: str, request: StructuredRequest) -> str:
        del api_key
        return f"demo-{int(time.time())}-{request.schema_name}-{tag}"

    def _parse(self, batch_id: str) -> tuple[int, str, str]:
        found = _BATCH.fullmatch(batch_id)
        if found is None:
            raise ProviderError(ProviderErrorKind.BAD_REQUEST)
        return int(found.group(1)), found.group(2), found.group(3)

    def batch_status(self, api_key: str, batch_id: str) -> BatchState:
        del api_key
        sent, _, _ = self._parse(batch_id)
        return BatchState.DONE if time.time() >= sent + BATCH_SECONDS else BatchState.IN_PROGRESS

    def fetch_batch_answer(self, api_key: str, batch_id: str, *, tag: str) -> BatchAnswer:
        del api_key
        _, schema_name, found_tag = self._parse(batch_id)
        if found_tag != tag or schema_name != "question_review":
            return BatchAnswer(error=ProviderErrorKind.BAD_OUTPUT)  # see the module's note
        data = {"findings": _REVIEW_FINDINGS, "corrected_content_json": None}
        return BatchAnswer(result=StructuredResult(data, 200, 60))

    def cancel_batch(self, api_key: str, batch_id: str) -> None:
        del api_key, batch_id

    def find_batches_by_tag(self, api_key: str, tag: str) -> list[str]:
        del api_key, tag
        return []  # nothing is kept: a lost submission cannot be looked up in the demo
