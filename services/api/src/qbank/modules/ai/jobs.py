"""Background jobs of the AI module (ADR-0007).

``ai.refresh_models`` fetches one provider's model list with the coaching's stored key and brings
the coaching's ``ai_models`` rows up to date. It runs in the worker, in the coaching that asked, and
it never retries by itself: a failure is recorded on the provider's key (the kind of failure only)
and the admin presses Refresh again, so a wrong key is not tried over and over.
"""

import structlog
from sqlalchemy.orm import Session

from qbank.core.jobs import Job, JobHandler, JobRegistry, PermanentJobError
from qbank.core.secretbox import Keyring, KeyUnreadable
from qbank.modules.ai.catalogue import apply_listing, record_refresh
from qbank.modules.ai.economy import claim_submit, collect_handler, submit_handler
from qbank.modules.ai.keys import open_key
from qbank.modules.ai.names import Provider
from qbank.modules.ai.orchestrator import CLAIM_SUBMIT, COLLECT_BATCH, SUBMIT_BATCH, ProviderFactory
from qbank.modules.ai.providers.base import ProviderError
from qbank.modules.ai.providers.registry import provider_for

log = structlog.get_logger("qbank.ai")

REFRESH_MODELS = "ai.refresh_models"


def refresh_models_handler(keyring: Keyring | None) -> JobHandler:
    """The handler for ``ai.refresh_models``, holding the process's master keys."""

    def handle(session: Session, job: Job) -> None:
        organization_id = job.organization_id
        try:
            provider = Provider(str(job.payload.get("provider")))
        except ValueError:
            raise PermanentJobError("the job names no known provider") from None
        if organization_id is None:
            raise PermanentJobError("the job has no coaching")
        try:
            key = open_key(session, keyring, organization_id, provider)
        except KeyUnreadable:
            record_refresh(session, organization_id, provider, error="KEY_UNREADABLE")
            log.warning("ai_models_refresh_failed", provider=provider.value, kind="KEY_UNREADABLE")
            return
        if key is None:
            log.warning("ai_models_refresh_failed", provider=provider.value, kind="NO_KEY")
            return
        try:
            listed = provider_for(provider).list_models(key)
        except ProviderError as problem:
            record_refresh(session, organization_id, provider, error=problem.kind.value)
            log.warning(
                "ai_models_refresh_failed", provider=provider.value, kind=problem.kind.value
            )
            return
        applied = apply_listing(session, organization_id, provider, listed)
        record_refresh(session, organization_id, provider, error=None)
        log.info(
            "ai_models_refreshed",
            provider=provider.value,
            listed=len(listed),
            added=applied.added,
            updated=applied.updated,
            gone=applied.gone,
        )

    return handle


def register_jobs(
    registry: JobRegistry, keyring: Keyring | None, providers: ProviderFactory = provider_for
) -> None:
    registry.register(REFRESH_MODELS, refresh_models_handler(keyring))
    # Economy (batch) runs, M5 5h: claim, submit, collect.
    registry.register(CLAIM_SUBMIT, claim_submit)
    registry.register(SUBMIT_BATCH, submit_handler(keyring, providers))
    registry.register(COLLECT_BATCH, collect_handler(keyring, providers))
