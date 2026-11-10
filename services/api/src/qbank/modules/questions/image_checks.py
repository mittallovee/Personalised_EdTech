"""The pictures a question refers to (M3 design note §5.7, D-07).

``blocks.py`` checks the shape of an image block. Here every picture it names is checked against
what the lookup found for this coaching, and the list of pictures is read out so that a saved
revision can record which ones it uses. A pure function of the content and the lookup: the service
does the database reading.

A picture is found by looking for image blocks anywhere in the content, so every place a question
keeps blocks (stem, options, items, solution, and the formats added later) is covered, and the path
in a finding is the same path the shape checks use.
"""

from collections.abc import Collection
from contextlib import suppress
from uuid import UUID

from qbank.modules.questions.findings import Finding, Findings, at_index, at_key

# More than this many pictures in one question is not looked up (the shape checks and the size
# limit of a revision stop such a question long before; this only bounds the lookup).
MAX_PICTURES = 200


def image_refs(content: object) -> list[tuple[str, UUID]]:
    """Every image block with a readable ``asset_id``: the path of the block and the id."""
    found: list[tuple[str, UUID]] = []
    stack: list[tuple[str, object]] = [("", content)]
    while stack and len(found) < MAX_PICTURES:
        path, value = stack.pop()
        if isinstance(value, dict):
            if value.get("kind") == "image":
                asset = value.get("asset_id")
                if isinstance(asset, str):
                    with suppress(ValueError):  # the shape check reports an unreadable id
                        found.append((path, UUID(asset)))
                continue
            for key, child in value.items():
                stack.append((at_key(path, str(key)), child))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                stack.append((at_index(path, index), child))
    found.sort()
    return found


def image_ids(content: object) -> set[UUID]:
    return {asset for _, asset in image_refs(content)}


def check_images(content: object, available: Collection[UUID]) -> list[Finding]:
    """An error for each picture that is not one of this coaching's own."""
    out = Findings()
    for path, asset in image_refs(content):
        if asset not in available:
            out.error(
                at_key(path, "asset_id"),
                "IMAGE_NOT_AVAILABLE",
                "This picture is not available in your coaching. Upload it again.",
            )
    return out.items
