"""The limits and answer rules (D-03). Defaults here; an admin can change them later (PR 3i).

A changed rule never rewrites old revisions; it only changes what the findings say.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Rules:
    # Limits that keep storage and rendering safe (ADR-0016).
    equation_chars: int = 2_000
    paragraph_chars: int = 10_000
    blocks_per_list: int = 100
    revision_bytes: int = 256 * 1024
    table_rows: int = 50
    table_columns: int = 12
    list_items: int = 50
    # What an answer may be.
    option_count: int = 4
    matching_min_items: int = 2
    matching_max_items: int = 10
    statements_min: int = 2
    statements_max: int = 10
    integer_min: int = 0
    integer_max: int = 999
    digit_min: int = 0
    digit_max: int = 9
    numeric_min: Decimal = Decimal("0.00")
    numeric_max: Decimal = Decimal("999.00")


DEFAULT_RULES = Rules()
