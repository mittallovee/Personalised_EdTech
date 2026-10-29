"""Questions: what a question's content is, and what is wrong with it (M3 design note §5, ADR-0016).

This part is pure logic: it reads a question's content (JSON) and returns findings. It knows nothing
about the database; saving, revisions and codes arrive in a later pull request.
"""
