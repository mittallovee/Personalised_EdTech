"""Built-in starter syllabuses (C-14, ADR-0022): a ready-made syllabus a coaching can load.

Each one is a file in the import format (M3 design note §4.4) kept in ``starter/`` beside this
module. Loading one makes an ordinary import preview from that file, so the admin sees every row
before anything changes, and the coaching's copy is edited afterwards like any other syllabus.
"""

from dataclasses import dataclass
from functools import cache
from importlib.resources import files

from qbank.core.errors import NotFound


@dataclass(frozen=True)
class StarterSyllabus:
    key: str  # used in the address: lower-case letters, digits and dashes
    title: str
    description: str


_COVERS = "Chapters, topics, subtopics and concepts for JEE Main and JEE Advanced"

STARTERS: tuple[StarterSyllabus, ...] = (
    StarterSyllabus("jee-physics", "JEE Physics (Class 11 and 12)", f"{_COVERS} physics."),
    StarterSyllabus("jee-chemistry", "JEE Chemistry (Class 11 and 12)", f"{_COVERS} chemistry."),
    StarterSyllabus(
        "jee-mathematics", "JEE Mathematics (Class 11 and 12)", f"{_COVERS} mathematics."
    ),
)


def find(key: str) -> StarterSyllabus:
    for starter in STARTERS:
        if starter.key == key:
            return starter
    raise NotFound("No such starter syllabus.")


def read(starter: StarterSyllabus) -> bytes:
    """The starter's file, exactly as an admin could have uploaded it (UTF-8 CSV)."""
    return (files(__package__) / "starter" / f"{starter.key}.csv").read_bytes()


@cache
def row_count(starter: StarterSyllabus) -> int:
    """How many rows the file has, not counting the heading row."""
    return len(read(starter).splitlines()) - 1
