"""Made-up physics-like questions for load tests (K-08, M4 design note §7.3).

Every question is generated from small word lists and a seed, so a run is repeatable and nothing
here is real coaching content. The text has the shape of real questions (a stem of a few sentences,
sometimes an equation, four options, a solution most of the time, about one in ten in Hindi) so the
word and trigram indexes see realistic text, including words that are in almost every question.
"""

import random
from dataclasses import dataclass
from typing import Any
from uuid import UUID

BLOOM = ("REMEMBER", "UNDERSTAND", "APPLY", "ANALYZE", "EVALUATE", "CREATE")

OBJECTS = (
    "block",
    "ball",
    "cart",
    "pendulum",
    "spring",
    "rod",
    "disc",
    "ring",
    "sphere",
    "car",
    "train",
    "satellite",
    "projectile",
    "wire",
    "capacitor",
    "resistor",
    "lens",
    "mirror",
    "piston",
    "rope",
    "pulley",
    "wedge",
    "bead",
    "boat",
    "rocket",
    "magnet",
    "coil",
    "prism",
)
QUANTITIES = (
    "acceleration",
    "velocity",
    "displacement",
    "momentum",
    "energy",
    "power",
    "tension",
    "friction",
    "torque",
    "frequency",
    "wavelength",
    "current",
    "resistance",
    "charge",
    "potential",
    "capacitance",
    "pressure",
    "density",
    "temperature",
    "entropy",
    "impulse",
    "work",
    "speed",
    "force",
    "inductance",
    "flux",
    "intensity",
    "amplitude",
    "period",
)
SURFACES = (
    "horizontal floor",
    "smooth incline",
    "rough incline",
    "frictionless track",
    "vertical wall",
    "circular path",
    "table top",
    "conveyor belt",
)
VERBS = (
    "slides",
    "rolls",
    "falls",
    "oscillates",
    "rotates",
    "moves",
    "accelerates",
    "rests",
    "collides",
    "bounces",
    "hangs",
    "floats",
)
ASKS = (
    "Find the {q} of the {o}.",
    "What is the {q} of the {o} after {t} seconds?",
    "Calculate the {q} when the {o} reaches the bottom.",
    "Which of the following gives the {q} of the {o}?",
    "Determine the ratio of the initial and final {q}.",
    "Estimate the {q} needed to stop the {o}.",
)
REASONS = (
    "Use conservation of {q}.",
    "Apply Newton's second law to the {o}.",
    "Resolve the forces along the {s}.",
    "The {q} stays constant because no external force acts.",
    "Write the equation of motion and integrate.",
    "Take the {o} as a point mass.",
    "Energy lost to friction equals the work done against it.",
    "Use the work-energy theorem.",
)
EQUATIONS = (
    r"v = u + a t",
    r"s = u t + \frac{1}{2} a t^2",
    r"F = m a",
    r"E = \frac{1}{2} m v^2",
    r"T = 2 \pi \sqrt{\frac{l}{g}}",
    r"p = m v",
    r"P = \frac{W}{t}",
    r"V = I R",
    r"\tau = r F \sin\theta",
    r"\omega = 2 \pi f",
)
HINDI_STEMS = (
    "एक {o} का द्रव्यमान {m} किलोग्राम है। उसका त्वरण ज्ञात कीजिए।",
    "किसी वस्तु का वेग {t} सेकंड बाद क्या होगा?",
    "घर्षण बल का मान ज्ञात कीजिए जब वस्तु ढलान पर फिसलती है।",
    "संवेग संरक्षण का उपयोग करके अंतिम वेग निकालिए।",
    "स्प्रिंग की ऊर्जा और आवर्तकाल ज्ञात कीजिए।",
)
HINDI_OBJECTS = ("गेंद", "गुटका", "गाड़ी", "लोलक", "पत्थर")


@dataclass(frozen=True, slots=True)
class Syllabus:
    """Label ids to draw from: classes > subjects > chapters > topics > concepts, and exams."""

    classes: tuple[UUID, ...]
    subjects: dict[UUID, tuple[UUID, ...]]  # class -> subjects
    chapters: dict[UUID, tuple[UUID, ...]]  # subject -> chapters
    topics: dict[UUID, tuple[UUID, ...]]  # chapter -> topics
    concepts: dict[UUID, tuple[UUID, ...]]  # subject -> concepts
    exams: tuple[UUID, ...]


def _uuid(rng: random.Random) -> UUID:
    return UUID(int=rng.getrandbits(128), version=4)


def make_syllabus(rng: random.Random) -> Syllabus:
    """2 classes, 3 subjects each, 12 chapters per subject, 4 topics per chapter, 30 concepts per
    subject and 3 exams: about the size of one coaching's real syllabus."""
    classes = tuple(_uuid(rng) for _ in range(2))
    subjects = {c: tuple(_uuid(rng) for _ in range(3)) for c in classes}
    all_subjects = [s for group in subjects.values() for s in group]
    chapters = {s: tuple(_uuid(rng) for _ in range(12)) for s in all_subjects}
    topics = {
        ch: tuple(_uuid(rng) for _ in range(4)) for group in chapters.values() for ch in group
    }
    concepts = {s: tuple(_uuid(rng) for _ in range(30)) for s in all_subjects}
    exams = tuple(_uuid(rng) for _ in range(3))
    return Syllabus(classes, subjects, chapters, topics, concepts, exams)


def _para(text: str) -> dict[str, str]:
    return {"kind": "paragraph", "text": text}


def _english_stem(rng: random.Random) -> list[dict[str, Any]]:
    o, q, s = rng.choice(OBJECTS), rng.choice(QUANTITIES), rng.choice(SURFACES)
    first = (
        f"A {o} of mass {rng.randint(1, 20)} kg {rng.choice(VERBS)} on a {s}"
        f" inclined at {rng.choice((15, 30, 37, 45, 53, 60))} degrees."
    )
    middle = (
        f"The {rng.choice(QUANTITIES)} at the start is {rng.randint(2, 40)} units and the"
        f" {rng.choice(QUANTITIES)} changes steadily."
    )
    ask = rng.choice(ASKS).format(q=q, o=o, t=rng.randint(2, 10))
    blocks: list[dict[str, Any]] = [_para(first), _para(middle)]
    if rng.random() < 0.4:
        blocks.append({"kind": "equation", "format": "latex", "source": rng.choice(EQUATIONS)})
    blocks.append(_para(ask))
    return blocks


def _hindi_stem(rng: random.Random) -> list[dict[str, Any]]:
    template = rng.choice(HINDI_STEMS)
    return [
        _para(
            template.format(o=rng.choice(HINDI_OBJECTS), m=rng.randint(1, 20), t=rng.randint(2, 10))
        )
    ]


def _labels(rng: random.Random, syllabus: Syllabus) -> dict[str, Any]:
    class_id = rng.choice(syllabus.classes)
    subject_id = rng.choice(syllabus.subjects[class_id])
    chapter_id = rng.choice(syllabus.chapters[subject_id])
    concepts = rng.sample(syllabus.concepts[subject_id], k=rng.randint(1, 3))
    is_pyq = rng.random() < 0.15
    meta: dict[str, Any] = {
        "class_id": str(class_id),
        "subject_id": str(subject_id),
        "chapter_id": str(chapter_id),
        "topic_id": str(rng.choice(syllabus.topics[chapter_id])),
        "subtopic_id": None,
        "primary_concept_id": str(concepts[0]),
        "secondary_concept_ids": [str(c) for c in concepts[1:]],
        "difficulty": rng.randint(1, 10),
        "bloom_level": rng.choice(BLOOM),
        "is_pyq": is_pyq,
    }
    if is_pyq:
        meta["exam_id"] = str(rng.choice(syllabus.exams))
        meta["exam_year"] = rng.randint(2005, 2025)
    return meta


def synthetic_question(rng: random.Random, syllabus: Syllabus) -> dict[str, Any]:
    """One complete single-correct question (content ready for review), made up from the lists."""
    hindi = rng.random() < 0.1
    stem = _hindi_stem(rng) if hindi else _english_stem(rng)
    correct = rng.choice("ABCD")
    unit = rng.choice(("m/s", "J", "N", "W", "kg m/s", "Hz", "ohm"))
    values = rng.sample(range(2, 99), k=4)
    content: dict[str, Any] = {
        "schema_version": 1,
        "question_type": "SCQ",
        "language": "hi" if hindi else "en",
        "stem": stem,
        "options": [
            {"id": letter, "content": [_para(f"{value} {unit}")]}
            for letter, value in zip("ABCD", values, strict=True)
        ],
        "answer": {"option_id": correct},
        "metadata": _labels(rng, syllabus),
    }
    if rng.random() < 0.6:
        reason = rng.choice(REASONS).format(
            q=rng.choice(QUANTITIES), o=rng.choice(OBJECTS), s=rng.choice(SURFACES)
        )
        content["solution"] = [_para(reason), _para(f"So the answer is option {correct}.")]
    return content
