"""Curated event vocabulary for Evidentia structured logs (v0.7.0).

Rather than letting every caller invent its own ``event.action`` string,
we enumerate the full set here. Operators building SIEM alerts, FedRAMP
3PAOs running audit queries, and Big-4 reviewers correlating evidence
all need a stable vocabulary they can pin to. Ad-hoc action names break
audit-trail continuity across releases; a registry fixes the vocabulary
so a query like ``event.action:evidentia.collect.finding_retrieved`` is
meaningful at v0.6.0, v0.7.0, and v0.8.0 alike.

Adding a new event:
    1. Append to :class:`EventAction`.
    2. Document in ``docs/log-schema.md``.
    3. Add a test in ``tests/unit/test_audit/test_events.py`` asserting the
       name matches the ``evidentia.<namespace>.<verb>`` convention.

ECS categorization primers (see https://www.elastic.co/guide/en/ecs/):

- ``event.category`` = coarse bucket (``configuration``, ``iam``, ``process``)
- ``event.type`` = action-specific sub-type (``info``, ``change``, ``error``)
- ``event.outcome`` = outcome (``success``, ``failure``, ``unknown``)

NIST SP 800-53 Rev 5 AU-3 (Content of Audit Records) requires each
audit record to capture: what happened, when, where, source, outcome,
and identity. The structured logger populates all six from the fields
documented below plus the :class:`EventAction` vocabulary.
"""

from __future__ import annotations

from enum import Enum


class EventAction(str, Enum):
    """Authoritative list of ``event.action`` values emitted by Evidentia.

    Names follow the ``evidentia.<namespace>.<verb>`` convention so SIEM
    operators can filter by prefix (e.g., ``event.action:evidentia.collect.*``).
    Unknown actions are accepted by the logger but tagged with a warning
    so audit-reviewers see the full picture while we learn what emitters
    are missing from this registry.
    """

    # Collection lifecycle ─ the verbs that move a collector from "starting"
    # to "completed". A run begins with COLLECT_STARTED, ends with either
    # COLLECT_COMPLETED (clean) or COLLECT_FAILED / COLLECT_ABORTED.
    COLLECT_STARTED = "evidentia.collect.started"
    COLLECT_FINDING_RETRIEVED = "evidentia.collect.finding_retrieved"
    COLLECT_FINDING_SKIPPED = "evidentia.collect.finding_skipped"
    COLLECT_PAGE_FETCHED = "evidentia.collect.page_fetched"
    COLLECT_RETRY = "evidentia.collect.retry"
    COLLECT_COMPLETED = "evidentia.collect.completed"
    COLLECT_FAILED = "evidentia.collect.failed"
    COLLECT_ABORTED = "evidentia.collect.aborted"

    # Authentication events ─ tracks credential resolution at collection time.
    # Required by NIST SP 800-53 AU-2 (Event Logging) to identify the
    # authenticating principal on every evidence record.
    AUTH_CREDENTIAL_RESOLVED = "evidentia.auth.credential_resolved"
    AUTH_CREDENTIAL_REFRESH = "evidentia.auth.credential_refresh"
    AUTH_CREDENTIAL_FAILED = "evidentia.auth.credential_failed"

    # Configuration events ─ config loaded, overridden, or rejected.
    # Required for H12 (config audit trail) of the enterprise checklist.
    CONFIG_LOADED = "evidentia.config.loaded"
    CONFIG_RESOLVED = "evidentia.config.resolved"
    CONFIG_OVERRIDE_APPLIED = "evidentia.config.override_applied"
    CONFIG_INVALID = "evidentia.config.invalid"

    # Signing events ─ GPG and Sigstore cover distinct signing paths.
    # SIGSTORE_SKIPPED_AIRGAP emitted when Sigstore is requested but
    # air-gap mode forbids the Fulcio/Rekor network calls.
    SIGN_GPG_SIGNED = "evidentia.sign.gpg_signed"
    SIGN_SIGSTORE_SIGNED = "evidentia.sign.sigstore_signed"
    SIGN_SIGSTORE_SKIPPED_AIRGAP = "evidentia.sign.sigstore_skipped_airgap"
    SIGN_FAILED = "evidentia.sign.signing_failed"

    # Verification events ─ mirror SIGN_* for the verify path. Digest and
    # signature outcomes are emitted separately so auditors can filter on
    # either dimension.
    VERIFY_STARTED = "evidentia.verify.started"
    VERIFY_DIGEST_PASSED = "evidentia.verify.digest_passed"
    VERIFY_DIGEST_FAILED = "evidentia.verify.digest_failed"
    VERIFY_SIGNATURE_PASSED = "evidentia.verify.signature_passed"
    VERIFY_SIGNATURE_FAILED = "evidentia.verify.signature_failed"
    VERIFY_COMPLETED = "evidentia.verify.completed"

    # Manifest events ─ completeness attestation B5 emits these. Empty-set
    # attestation is a first-class event so "no findings" is distinguishable
    # from "collection failed" in the audit log.
    MANIFEST_GENERATED = "evidentia.manifest.generated"
    MANIFEST_EMPTY_SET_ATTESTED = "evidentia.manifest.empty_set_attested"
    MANIFEST_INCOMPLETE = "evidentia.manifest.incomplete"


class EventCategory(str, Enum):
    """ECS ``event.category`` values Evidentia uses.

    ECS defines a controlled vocabulary for event.category. We use a
    subset relevant to GRC evidence collection.
    """

    CONFIGURATION = "configuration"
    IAM = "iam"
    AUTHENTICATION = "authentication"
    PROCESS = "process"
    FILE = "file"
    NETWORK = "network"


class EventType(str, Enum):
    """ECS ``event.type`` values Evidentia uses."""

    INFO = "info"
    ACCESS = "access"
    ALLOWED = "allowed"
    CHANGE = "change"
    CREATION = "creation"
    DELETION = "deletion"
    END = "end"
    START = "start"
    ERROR = "error"


class EventOutcome(str, Enum):
    """ECS ``event.outcome`` values — pinned to the three-value ECS enum."""

    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"
