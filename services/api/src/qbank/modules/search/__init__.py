"""Search: the bank index and the questions it finds (M4 design note §7, ADR-0008).

``bank_index`` is derived data, one row per question, written by the questions module in the same
transaction as every change and rebuilt from the revisions by ``qbank reindex-bank``. This module
owns the table and the reads; it knows nothing of how a question is stored, and the questions
module reaches it only through ``search.public``.
"""
