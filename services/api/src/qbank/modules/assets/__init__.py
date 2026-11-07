"""Assets: files that belong to a coaching, starting with the pictures in questions.

M3 design note §5.7, ADR-0012. A picture is checked, decoded and re-encoded on upload, stored
through ``core/storage.py``, and served only through an API route that checks the caller's coaching.
"""
