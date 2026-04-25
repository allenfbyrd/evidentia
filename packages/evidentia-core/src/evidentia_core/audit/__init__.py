"""Audit primitives: structured logging, retry, and provenance (v0.7.0).

Four modules power the Evidentia enterprise-grade audit trail:

- :mod:`.logger` — ECS 8.11 + NIST AU-3 structured logging, with
  Rich-console and JSON output modes.
- :mod:`.retry` — bounded exponential-backoff retry decorator that
  emits retry events on every attempt.
- :mod:`.provenance` — per-finding and per-run metadata Pydantic
  models that satisfy checklist items H5 (collector metadata) and
  B5 (completeness attestation).
- :mod:`.events` — curated ``event.action`` vocabulary.
"""

from evidentia_core.audit.events import (
    EventAction,
    EventCategory,
    EventOutcome,
    EventType,
)
from evidentia_core.audit.logger import (
    ECS_VERSION,
    ECSFormatter,
    EvidentiaLogger,
    enable_json_logs,
    get_logger,
    is_json_mode,
)
from evidentia_core.audit.provenance import (
    CollectionContext,
    CollectionManifest,
    CoverageCount,
    GenerationContext,
    PaginationContext,
    compute_prompt_hash,
    new_run_id,
)
from evidentia_core.audit.retry import (
    DEFAULT_INITIAL_BACKOFF_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_MAX_BACKOFF_SECONDS,
    TEST_MODE_ENV,
    build_async_retrying,
    build_retrying,
    is_test_mode,
    with_retry,
    with_retry_async,
)

__all__ = [
    "DEFAULT_INITIAL_BACKOFF_SECONDS",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "ECS_VERSION",
    "TEST_MODE_ENV",
    "CollectionContext",
    "CollectionManifest",
    "CoverageCount",
    "ECSFormatter",
    "EventAction",
    "EventCategory",
    "EventOutcome",
    "EventType",
    "EvidentiaLogger",
    "GenerationContext",
    "PaginationContext",
    "build_async_retrying",
    "build_retrying",
    "compute_prompt_hash",
    "enable_json_logs",
    "get_logger",
    "is_json_mode",
    "is_test_mode",
    "new_run_id",
    "with_retry",
    "with_retry_async",
]
