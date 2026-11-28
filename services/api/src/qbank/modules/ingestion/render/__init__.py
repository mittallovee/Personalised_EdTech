"""Turning an untrusted document into page pictures and text.

**Only the sandboxed worker (``qbank.ingest_worker``) may import this package.** Nothing else
opens a document: an import-linter contract in ``pyproject.toml`` enforces it (ADR-0024, K-17). It
never executes or follows anything in a file, and runs with no network and a read-only filesystem.
"""
