"""Public interface of the ingestion module: what other modules, the workers and the API use.

Only names here may be imported from outside the module. Nothing here opens an untrusted document:
parsing lives in ``qbank.modules.ingestion.render``, which only the sandboxed worker imports.
"""

# Jobs only the sandboxed worker may take (it opens untrusted files); the normal worker skips them.
RENDER_JOB = "ingest.render"
SANDBOX_JOB_TYPES = frozenset({RENDER_JOB})

__all__ = ["RENDER_JOB", "SANDBOX_JOB_TYPES"]
