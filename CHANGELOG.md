# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### v0.7.1 development — AI features hardening (in progress)

In-flight work bringing the `evidentia-ai` package up to the v0.7.0
collector enterprise-grade bar. See `docs/v0.7.1-plan.md` for the full
scope; below is what's landed on the development branch so far.

#### Added

- **`GenerationContext`** Pydantic model in
  `evidentia_core.audit.provenance`, sibling to `CollectionContext`.
  Captures per-output AI provenance: `model`, `temperature`,
  `prompt_hash` (SHA-256 of system+user prompts via the new
  `compute_prompt_hash()` helper), `run_id` (ULID),
  `generated_at` (microsecond UTC), `attempts` (network-layer retry
  count), `instructor_max_retries` (validation-layer cap),
  `credential_identity` (best-effort operator label per NIST AU-3),
  `evidentia_version`.
- **9 new `EventAction` entries** under the `evidentia.ai.*` namespace:
  `AI_RISK_GENERATED`, `AI_RISK_FAILED`, `AI_RISK_RETRY`,
  `AI_RISK_BATCH_COMPLETED`, `AI_EXPLAIN_GENERATED`,
  `AI_EXPLAIN_FAILED`, `AI_EXPLAIN_RETRY`, `AI_EXPLAIN_CACHE_HIT`,
  `AI_EXPLAIN_BATCH_COMPLETED`. Documented in `docs/log-schema.md`.
- **`with_retry_async`** decorator + **`build_retrying`** /
  **`build_async_retrying`** factory functions in
  `evidentia_core.audit.retry`, supporting async callers and
  per-call attempt tracking.
- **`event_action`** kwarg on `with_retry`/`with_retry_async` (default
  `EventAction.COLLECT_RETRY` preserves pre-v0.7.1 collector
  behaviour); AI generators pass `AI_RISK_RETRY` /
  `AI_EXPLAIN_RETRY` so SIEM operators can filter retry storms by
  namespace.
- **`evidentia_ai.exceptions`** module with the typed exception
  hierarchy (`EvidentiaAIError`, `LLMUnavailableError`,
  `LLMValidationError`, `RiskStatementError`, `RiskGenerationFailed`).
- **`evidentia_ai.client.get_operator_identity()`** helper returning
  `$EVIDENTIA_AI_OPERATOR` if set, else best-effort
  `user@hostname`. Populates
  `GenerationContext.credential_identity`.
- Optional **`generation_context`** field on
  `evidentia_core.models.risk.RiskStatement` AND
  `evidentia_ai.explain.models.PlainEnglishExplanation` (default
  `None` for v0.7.x backward compat; will tighten to required in v0.8
  with a deprecation cycle).
- Shared **`LLM_TRANSIENT_EXCEPTIONS`** tuple in
  `evidentia_ai.exceptions` so `risk_statements/` and `explain/`
  retry on identical conditions (single source of truth).
- **`ExplainError`** + **`ExplainGenerationFailed`** in
  `evidentia_ai.exceptions` (sibling of the risk-specific hierarchy
  under the shared `EvidentiaAIError` base).

#### Changed

- `risk_statements/generator.py`: replaced stdlib `logging` with
  `evidentia_core.audit.get_logger`; wrapped LLM calls in bounded
  retry against the LiteLLM transient-exception set
  (`RateLimitError`, `APIConnectionError`, `Timeout`,
  `InternalServerError`, `ServiceUnavailableError`,
  `BadGatewayError`); replaced two `except Exception` BLOCKER B3
  sites with the typed exception hierarchy; emits structured events
  for every state transition with `run_id` correlation across success,
  failure, retry, and batch-summary events. Air-gap policy violations
  (`OfflineViolationError`) propagate unchanged.
- `explain/generator.py`: same hardening pattern as
  `risk_statements/generator.py` \u2014 structured logger, `@with_retry`
  via `build_retrying`, typed exception hierarchy
  (`ExplainError`/`ExplainGenerationFailed`), `GenerationContext`
  attached on cache miss (cache hits preserve whatever was cached),
  structured `AI_EXPLAIN_GENERATED`/`AI_EXPLAIN_FAILED`/`AI_EXPLAIN_RETRY`/
  `AI_EXPLAIN_CACHE_HIT` events with `run_id` correlation. Closes
  the v0.7.0 BLOCKER B3 carry-over for the explain subsystem.

#### Breaking changes

- **`evidentia_core.models.risk` module is no longer re-exported from
  the `evidentia_core.models` package root.** Callers must now use
  `from evidentia_core.models.risk import RiskStatement, RiskRegister, ...`
  directly. This mirrors the v0.7.0 exclusion of
  `evidentia_core.models.finding` and is required to break a circular
  import (`risk.py` now references `evidentia_core.audit.provenance`,
  which already imports from `models.common`). All in-tree callers
  already use the direct submodule path; downstream callers using
  `from evidentia_core.models import RiskStatement` must update their
  imports.

#### Deserialization compatibility note

- v0.7.0 readers will **reject** v0.7.1 `RiskStatement` JSON because
  `EvidentiaModel` sets `extra='forbid'` and the new
  `generation_context` field is unknown to v0.7.0. This is the same
  forward-compat property that v0.7.0 introduced when adding
  `collection_context` to `SecurityFinding`. Mixed-version
  deployments must upgrade `evidentia-core` to v0.7.1 on every
  reader before v0.7.1 writers go live. v0.7.1 readers accept v0.7.0
  payloads cleanly (the optional field defaults to `None`).

## [0.7.0] - 2026-04-25

**The enterprise-grade release.** Closes all 10 BLOCKER items in
[`docs/enterprise-grade.md`](docs/enterprise-grade.md). Adds Sigstore/Rekor
signing, CycloneDX SBOM on every release, PyPI Trusted Publishers (OIDC)
with PEP 740 attestations on every wheel + sdist, OSCAL Assessment Results
schema conformance via [`compliance-trestle`](https://github.com/oscal-compass/compliance-trestle),
AWS IAM Access Analyzer + GitHub Dependabot collectors with explicit
blind-spot disclosures embedded in the AR back-matter, ECS-8.11 / NIST-AU-3 /
OpenTelemetry structured logs, and a consolidated GitHub Action at
`.github/actions/gap-analysis/`. The 6 v0.5.1 `controlbridge-*`
deprecation shims are removed at this release per the public migration
contract documented since v0.6.0.

**857 tests passing (8 skipped).** Includes 3 new trestle conformance
tests (`tests/unit/test_oscal/test_trestle_conformance.py`) that
round-trip the AR through pydantic.v1 with `Extra.forbid`, catching
unknown-field bugs that NIST's JSON Schema misses, plus 8 new
Sigstore-verify integration tests added during the pre-tag review
cycle (`tests/unit/test_oscal/test_verify.py`) that mock the Sigstore
client to exercise bundle detection, custom paths, identity policies,
warning emission, and require_signature satisfaction by either GPG
or Sigstore.

### Pre-tag review cycle (Steps 1-5)

Before v0.7.0 was tagged, a comprehensive 6-step review was run
against `main` to validate the release end-to-end. Outputs:

- **`docs/positioning-and-value.md`** — exhaustive ~12k-word synthesis
  of Evidentia's competitive positioning, intellectual ancestry, AI
  posture, industry voices to follow/cite/pitch, and 12-month
  direction. Compiled from 7 parallel research streams (commercial
  GRC vendors, OSS GRC ecosystem, regulatory + M&A signals, academic
  foundations, AI/LLM tools in GRC, named industry voices, internal
  capability inventory).
- **`docs/capability-matrix.md`** — 5 risk tiers + 5 surface tiers,
  functional + code-review + adversarial smoke tests. Surfaced 18
  bugs across 5 categorized buckets (CRITICAL all fixed, HIGH
  deferred to v0.7.1, MEDIUM fixed in same review, LOW accepted).
- **`docs/v0.7.1-plan.md`** — forward-looking plan for the AI features
  hardening + supply-chain polish minor release. 6-8 week ship target.

Critical bugs fixed during the review:

- **Inter-package version pins** were stale at `>=0.6.0,<0.7.0`
  across 5 pyproject.toml files (would have made `pip install evidentia
  ==0.7.0` resolve `evidentia-core` at 0.6.0). All bumped to
  `>=0.7.0,<0.8.0`.
- **LiteLLM** dep range tightened from `>=1.50,<2.0` to
  `>=1.83.0,<2.0` to exclude the compromised 1.82.7 / 1.82.8 versions
  from the March 24, 2026 PyPI supply chain incident.
- **Sigstore CLI integration**: added `--sign-with-sigstore`,
  `--sigstore-bundle`, `--sigstore-identity-token` to `evidentia gap
  analyze` (the library API existed but the CLI flag was missing).
- **Sigstore verification**: `verify_ar_file` now detects
  `<path>.sigstore.json` bundles and verifies them alongside GPG
  `.asc` signatures. New CLI flags `--check-sigstore`,
  `--sigstore-bundle`, `--expected-identity`, `--expected-issuer`.
  `evidentia oscal verify` rich + JSON output extended.
- **Composite action.yml** flag rename `--bundle` -> `--sigstore-bundle`
  to match the new CLI surface (the old flag would have failed at
  runtime).
- **Secret scrubber** patterns expanded to cover Slack tokens,
  Stripe API keys, Google API keys, npm tokens (in addition to the
  existing AWS / GitHub / JWT / generic password= shapes).
- **`oscal/signing.py`** logger consistency: switched from stdlib
  `logging` to the v0.7.0 ECS-8.11 structured logger to match
  `oscal/sigstore.py`. Both signing paths now emit comparable
  `evidentia.sign.*` events for SIEM ingestion.
- **README documentation accuracy**: corrected REST endpoint count
  (18 -> 26 routes across 12 router modules), workspace sub-package
  count (4 -> 5), CLI command list (added `gap diff`, `explain`,
  `collect`, `integrations`, `oscal verify`, `serve`, global flags).

### Deferred to v0.7.1 (with documented design rationale)

Bringing `evidentia-ai` (`risk_statements/` + `explain/`) up to the
v0.7.0 collector-pattern enterprise grade requires 4 design decisions
that benefit from focused thought, not rushed inclusion in this
release. See `docs/v0.7.1-plan.md` for the scope: typed exception
hierarchy + `@with_retry` + new `GenerationContext` type + 7 new
`EventAction` enum entries + 250+ lines of mocked LLM tests for
`risk_statements/`.

### Supply-chain hardening (v0.7.0)

- **Build provenance**: GitHub Actions workflow with OIDC identity, no
  long-lived publishing tokens.
- **Signed publish**: PyPI Trusted Publisher (OIDC). The legacy
  `PYPI_API_TOKEN` is removed from GitHub secrets after first OIDC
  publish.
- **Per-artifact attestations**: PEP 740 Sigstore attestations on every
  wheel + sdist, signed with the GitHub Actions OIDC identity and
  logged to the Rekor public transparency log. Verifiable via
  `pip install pypi-attestations` + `pypi-attestations verify-pypi
  --repository allenfbyrd/evidentia <file>` or
  `gh attestation verify <file> -R allenfbyrd/evidentia`.
- **Software bill of materials**: CycloneDX 1.6 SBOM generated from
  `uv.lock`, attached to every GitHub Release alongside the wheels.
- **Schema conformance**: `compliance-trestle>=4.0` round-trip in CI.
- **Evidence integrity**: SHA-256 digests + GPG signatures (air-gap)
  or Sigstore bundles (online) on every Assessment Results document.

### Removed — controlbridge shim packages (per the public contract)

The 6 v0.5.1 `controlbridge-*` deprecation shims published in v0.6.0
are removed from the workspace at v0.7.0 per the public migration
contract documented in README.md, RENAMED.md, and CHANGELOG.md. The
v0.5.1 shim wheels remain on PyPI for installed users (manually yanked
at the v0.7.0 ship); future builds no longer produce shim wheels.

Removed:

- `packages/shim-controlbridge/`
- `packages/shim-controlbridge-core/`
- `packages/shim-controlbridge-collectors/`
- `packages/shim-controlbridge-ai/`
- `packages/shim-controlbridge-api/`
- `packages/shim-controlbridge-integrations/`
- `tests/unit/test_rename_shims.py`

`scripts/_create_shim_packages.py` is retained for historical reference
only with a deprecation header.

### Added — Composite GitHub Action consolidation

The legacy standalone `allenfbyrd/evidentia-action` repo is archived
in favor of a composite action at `.github/actions/gap-analysis/`.
External users invoke as:

```yaml
- uses: allenfbyrd/evidentia/.github/actions/gap-analysis@v0
  with:
    inventory: inventory.yaml
    frameworks: nist-800-53-rev5-moderate,soc2-tsc
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

Surface: install evidentia-core from PyPI -> run `evidentia gap analyze`
against the user's inventory -> restore base-branch baseline from
actions/cache (cache key includes `hashFiles(inventory)`) -> run
`evidentia gap diff` -> post sticky PR comment via
`marocchino/sticky-pull-request-comment@v2` -> gate merge on
regressions when `fail-on-regression: true`. Optional OSCAL AR JSON
output and Sigstore signing of the AR via the workflow's ambient OIDC
identity (requires `id-token: write`).

See [`.github/actions/gap-analysis/README.md`](.github/actions/gap-analysis/README.md)
for the full input/output surface, SHA-pinned variant for audit
pipelines, and migration guide from `evidentia-action@v1`.

### Added — Evidence chain of custody (v0.7.0 scope)

Originally planned for v0.6.0, displaced by the rename release. Every
OSCAL Assessment Results export can now carry cryptographic proof of its
evidence payload and an optional GPG signature of the document itself.

#### Exporter (`evidentia_core.oscal.exporter`)

`gap_report_to_oscal_ar(report, *, findings=None)` now accepts an optional
list of `SecurityFinding` objects. When supplied:

- Each finding is serialised to canonical JSON (sorted keys, no whitespace),
  SHA-256 digested, and embedded in `back-matter.resources[]` with
  base64-encoded content — making the AR self-contained for later
  verification with no external files required.
- The digest is stored in two places: the OSCAL-standard
  `rlinks[].hashes[]` field (`{algorithm: "SHA-256", value: "<hex>"}`)
  and an Evidentia-namespaced prop `evidence-digest` under
  `https://evidentia.dev/oscal` (value formatted as `sha256:<hex>`).
- Observations whose `control-id` prop matches a finding's `control_ids`
  get a `relevant-evidence[]` cross-reference to the resource UUID, and
  their `methods` flips from `["EXAMINE"]` to `["TEST"]` (automated
  finding, not manual examination).

Back-compat: omitting `findings=` produces the exact same AR shape as
pre-v0.7.0 — the `back-matter` block is only emitted when there are
resources to include.

#### Digest primitives (`evidentia_core.oscal.digest`)

- `digest_bytes` / `digest_file` / `digest_model` / `digest_json` — pure,
  deterministic SHA-256 helpers. `digest_model` uses Pydantic's
  `model_dump(mode="json")` plus `sort_keys=True` so two callers with
  the same input produce bit-for-bit identical hashes.
- `format_digest` / `parse_digest` — wrap and unwrap the
  `"sha256:<hex>"` OSCAL prop convention.
- `verify_bytes` / `verify_file` — compare a payload against an
  expected prop value.

#### GPG signing (`evidentia_core.oscal.signing`)

Subprocess-based wrapper around `gpg` (no new Python dependency):

- `sign_file(path, *, key_id, signature_path=None, gnupghome=None)` —
  produces an ASCII-armored detached signature at `<path>.asc` by default.
- `verify_file(path, *, signature_path=None, gnupghome=None)` — returns
  a `VerifyResult` with `valid`, `signer_key_id`, and
  `signer_fingerprint`. Signature *mismatches* return
  `valid=False` rather than raising — infrastructure errors (missing
  files, GnuPG not installed) raise `GPGError` subclasses so the two
  failure modes are distinguishable.
- `gpg_available()` — returns True iff the `gpg` binary is on PATH.
  Callers should probe this before adding sign/verify buttons in UI.

Uses `--batch`, `--pinentry-mode loopback`, `--local-user`, and
`--status-fd 1` so all invocations are non-interactive and emit
machine-readable status output. `GNUPGHOME` overrides let callers
point at a CI-scoped keyring without touching the operator's default
`~/.gnupg`.

#### Verification orchestrator (`evidentia_core.oscal.verify`)

`verify_ar_file(path, *, require_signature=False, ...)` ties the two
checks together:

1. Re-hash every embedded evidence resource and compare to stored digests.
2. If `<path>.asc` exists (or `require_signature=True` and it's missing),
   run the signature check.

Returns a `VerifyReport` with per-resource `digest_checks` and an
`overall_valid` boolean. Missing signature counts as `None` (not
checked) unless `require_signature=True`.

#### CLI

- `evidentia gap analyze` grows two flags:
  - `--findings <path>` — embed collector output in the AR with digests
  - `--sign-with-gpg <key-id>` — write a detached signature alongside
    the AR JSON
- New subcommand tree `evidentia oscal`:
  - `evidentia oscal verify <path>` — check digests + optional
    signature. Exits 0 on pass, 1 on fail. `--require-signature`,
    `--signature`, `--gnupghome`, and `--json` options.

#### Testing

- New test modules: `test_oscal/test_digest.py` (22 tests), `test_verify.py`
  (10 tests), `test_signing.py` (7 GPG round-trip tests). Signing tests
  skip gracefully via `@pytest.mark.skipif(not gpg_available())` so CI
  matrices without GnuPG still pass.
- `test_exporter.py` extended with 7 new tests pinning the v0.7.0
  evidence-embedding shape (back-matter resources, digest prop values,
  observation cross-references, method-flip behaviour).

### Changed

- Project-folder rename (development-only, not a user-visible change):
  the repository moved from `.../Claude Code/ControlBridge/` to
  `.../Claude Code/Evidentia/`. All imports, editable-install pointers,
  and bytecode caches refreshed accordingly. Bundled Vite SPA
  (`packages/evidentia-api/src/evidentia_api/static/`) rebuilt from the
  already-renamed source so the browser tab title matches the CLI.
- README status badge dropped "Phase 1 MVP" (stale since v0.2). README
  Roadmap section re-grouped into Shipped / Next / Later buckets.
  `docs/ROADMAP.md` bumped to v0.6.0 stamp; v0.5.1 reclassified as the
  deprecation-shim release; v0.6.0 reclassified as the rename release;
  Evidence chain of custody content moved to v0.7.0.

### Fixed

- Two pre-existing `mypy --strict` errors in
  `packages/evidentia-ai/src/evidentia_ai/client.py` — added `cast()`
  around `instructor.from_litellm()` so the declared `Instructor` /
  `AsyncInstructor` return types propagate under strict type-checking.

### Added — Enterprise-grade audit + compliance infrastructure (v0.7.0 scope)

Second v0.7.0 batch, targeting the enterprise-grade checklist (Big-4
audit firm, FedRAMP 3PAO adoption bar).

#### Audit module (`evidentia_core.audit`)

Four new modules power the enterprise-grade audit trail:

- `events.py` — curated `EventAction` catalog: 30 action values across
  collect / auth / config / sign / verify / manifest namespaces. Plus
  ECS enums (`EventCategory`, `EventType`, `EventOutcome`).
- `logger.py` — ECS 8.11 JSON logger with NIST SP 800-53 Rev 5 AU-3
  content coverage (what / when / where / source / outcome / identity)
  + OpenTelemetry trace correlation (`trace.id` = run_id). Secret
  scrubber for AWS access keys, GitHub tokens, JWTs, generic
  password/token patterns. Third-party log record fallback. Rich
  console (default) and JSON (opt-in) output modes.
- `retry.py` — `@with_retry` decorator built on tenacity with
  exponential backoff + jitter. Emits `evidentia.collect.retry`
  events on every attempt. Zero-backoff under `EVIDENTIA_TEST_MODE=1`.
- `provenance.py` — `CollectionContext` (per-finding provenance),
  `CollectionManifest` (per-run completeness attestation),
  `PaginationContext`, `CoverageCount`, `new_run_id()` (ULID).

CLI: global `--json-logs` flag switches all logging to ECS JSON for
SIEM ingestion. Works with Splunk / Elastic / Datadog / Sumo Logic /
Microsoft Sentinel without custom parsers.

New deps: `tenacity>=9.0`, `python-ulid>=3.0`. Both small.

#### OLIR (NIST relationship typing) on control mappings

`evidentia_core.models.common.OLIRRelationship` — all six values from
NIST OLIR Derived Relationship Mapping vocabulary (`equivalent-to`,
`equal-to`, `subset-of`, `superset-of`, `intersects-with`, `related-to`).

`ControlMapping` extended with `relationship` (default `RELATED_TO`)
and `justification` (default empty, max 1024 chars). Pre-v0.7.0
callers that construct `ControlMapping(framework, control_id)` continue
to work without changes.

`aws/mapping.py` — 27 Config rules and 25 Security Hub controls
classified with authoritative per-entry OLIR relationships + FSBP/CIS
citations. Security Hub entries use `SUBSET_OF` (per AWS's own
"Related requirements" field as the authoritative subset claim);
Config rules use a mix of `SUBSET_OF` and `INTERSECTS_WITH` per rule
semantics. Added `map_config_rule_to_control_mappings` and
`map_security_hub_control_to_control_mappings` functions.

#### SecurityFinding schema migration

`evidentia_core.models.finding.SecurityFinding`:

- `control_mappings: list[ControlMapping]` replaces
  `control_ids: list[str]`. A `@model_validator` accepts the old
  `control_ids=[...]` kwarg at construction and auto-converts to
  `RELATED_TO`-typed ControlMappings with "Pre-v0.7.0 mapping"
  justification. A `.control_ids` property preserves read compat.
- New `collection_context: CollectionContext` field; defaults to a
  synthetic `"legacy-pre-v0.7.0"` placeholder so pre-v0.7.0 callers
  keep working. Upgraded collectors pass real context.

`models/migrations/v0_6_to_v0_7.py` — read-only JSON migration helper
that detects legacy finding shapes and synthesizes v0.7.0 fields,
emitting a WARN-level log event for audit visibility.

#### Sigstore / Rekor signing

New `evidentia_core.oscal.sigstore` (opt-in via
`pip install 'evidentia-core[sigstore]'`):

- Keyless signing via Fulcio + Rekor — the bundle
  (`<artifact>.sigstore.json`) carries cert, signature, and Rekor
  inclusion proof in one file.
- Four typed error classes: `SigstoreNotAvailableError` (lib missing),
  `SigstoreAirGapError` (offline refusal), `SigstoreSigningError`,
  `SigstoreVerifyError`.
- Air-gap mode refuses Sigstore before any network IO and points
  operators at GPG for offline deployments.
- Additive to GPG, not replacement. Both can coexist on the same AR
  artifact for defence-in-depth.

`export_report()` grows `sign_with_sigstore=True` + optional
`sigstore_identity_token` to thread Sigstore signing through the
OSCAL AR export path.

#### Collector hardening (AWS Config + Security Hub + GitHub branch
protection)

- `aws/collector.py`: bare `except Exception` replaced with typed
  catches emitting discrete ECS events. `@with_retry` wraps the
  STS `GetCallerIdentity` call. New `collect_all_v2()` returns
  `(findings, manifest)`. Every SecurityFinding carries a real
  CollectionContext with the STS caller ARN + account:region.
  `collect_all()` keeps the v0.6 signature; adds `dry_run=True`.
  Security Hub findings with `Compliance.RelatedRequirements`
  referring to NIST 800-53 get promoted to `SUBSET_OF` mappings
  with justification citing AWS's native mapping.
- `github/collector.py`: 9 inline `control_ids=[...]` call sites
  migrated to OLIR-typed `ControlMapping` tables at module scope.
  Every finding carries a CollectionContext. New `collect_v2()`
  returns `(findings, manifest)` with coverage counts. `dry_run=True`
  flag added to `collect()`.

#### New collectors (v0.7.0 greenfield)

- **AWS IAM Access Analyzer**
  (`evidentia_collectors.aws.AccessAnalyzerCollector`) — supports
  ExternalAccess, UnusedIAMRole, UnusedIAMUser\*Credential,
  UnusedPermission, and Policy Validation finding types. Each type
  has a curated OLIR-typed mapping to AC-2 / AC-3 / AC-4 / AC-5 /
  AC-6 / AC-6(1) / IA-2 / IA-5(1) / SC-7 with authoritative
  justifications. **Five blind-spot disclosures** (KMS grant chains,
  S3 ACLs vs Block Public Access, service-linked role exclusion,
  unsupported resource types, finding-generation latency) are
  emitted as manifest warnings — the OSCAL exporter will promote
  them to back-matter `class="blind-spot"` resources in a future
  v0.7.x so auditors see the limits of coverage inline (Q7=Yes).
- **GitHub Dependabot alerts**
  (`evidentia_collectors.github.DependabotCollector`) — full state
  coverage (open / fixed / dismissed / auto_dismissed) with
  policy-driven dismissal handling (Tier 3): `no_bandwidth` and
  `tolerable_risk` default to ACTIVE (auditor-surfaced gaps);
  `fix_started`, `inaccurate`, `not_used` default to RESOLVED.
  Operators override via `DismissalVerdict` policy dict. Seven
  control mappings per alert (SI-2, SI-5, RA-5, SR-3, SR-11, plus
  SSDF PO.3 / PW.4 / RV.2 with GitHub Well-Architected as the
  authoritative citation source).

#### Structured logging schema (`docs/log-schema.md`)

New reference doc describing the ECS 8.11 + NIST AU-3 + OpenTelemetry
field conventions used by the audit logger. Includes the EventAction
catalog and example log records.

#### Enterprise-grade credibility checklist (`docs/enterprise-grade.md`)

30-item checklist synthesized from AWS Audit Manager, AWS Security Hub,
FedRAMP Rev 5, NIST SP 800-53 AU-3, SSAE 18, AICPA TSP, and GitHub
SSDF references. Each item tagged BLOCKER / HIGH / MEDIUM / LOW with
the Evidentia v0.7.0 implementation status.

#### CycloneDX SBOM on release (Q2=A)

Release workflow now generates a CycloneDX 1.6 JSON SBOM via
`cyclonedx-bom` and attaches it to the GitHub Release alongside the
wheel artifacts. Addresses checklist item H2 (SLSA L2+/SBOM).

#### Testing

Total suite: **862 passed, 8 skipped** (up from 657 baseline at
`e6dc94d`, +205 new tests). mypy clean across 96 source files.
ruff clean.

New test modules:

- `tests/unit/test_audit/` — 79 tests (events vocabulary, ECS
  record shape, retry semantics, provenance roundtrip).
- `tests/unit/test_models/test_olir_and_finding_schema.py` — 20
  tests (OLIR enum, ControlMapping backward compat, SecurityFinding
  control_ids kwarg shim, migration shim).
- `tests/unit/test_collectors/test_aws_olir_mappings.py` — 31 tests
  (every Config rule + every Security Hub control classified).
- `tests/unit/test_oscal/test_sigstore.py` — 10 tests (structural +
  CI-gated sign/verify integration per Q5=A).
- `tests/unit/test_collectors/test_access_analyzer.py` — 23 tests.
- `tests/unit/test_collectors/test_dependabot.py` — 34 tests.

## [0.6.0] - 2026-04-22

### Renamed from ControlBridge to Evidentia

This release is a **project rename** with no functional changes. Every
feature, CLI command, API route, and test from v0.5.0 works identically
under the new name. Only naming changes.

#### Why

The ControlBridge name collided with [controlbridge.ai](https://www.controlbridge.ai/),
a live commercial SOX 302/404 compliance platform for internal audit and
finance teams. The markets overlap directly (GRC / compliance automation,
CFO / audit-committee buyers), so continuing to use the identical name
created trademark, SEO, and buyer-confusion risks. v0.5.0 shipped days
ago with ~0 external users, so the remediation window is at its minimum.
See [RENAMED.md](RENAMED.md) for the full background.

#### What changed

- **PyPI package names:**
  - `controlbridge` → `evidentia`
  - `controlbridge-core` → `evidentia-core`
  - `controlbridge-ai` → `evidentia-ai`
  - `controlbridge-api` → `evidentia-api`
  - `controlbridge-collectors` → `evidentia-collectors`
  - `controlbridge-integrations` → `evidentia-integrations`
- **Python module names:** `controlbridge_*` → `evidentia_*` (same pattern).
- **CLI entry point:** `controlbridge` → `evidentia`. The `cb` short alias
  remains unchanged under the new `evidentia` package.
- **Frontend npm scope:** `@controlbridge/ui` → `@evidentia/ui`.
- **GitHub repositories:**
  - `allenfbyrd/controlbridge` → `allenfbyrd/evidentia`
  - `allenfbyrd/controlbridge-action` → `allenfbyrd/evidentia-action`
  - Both redirects are permanent (GitHub's built-in rename mechanism).
  - Old URLs printed on resumes, blog posts, and chat logs continue to work.
- **Config file name:** user-project `controlbridge.yaml` → `evidentia.yaml`.
  The bootstrap wizard + `evidentia init` generate the new name; the
  `.gitignore` keeps `controlbridge.yaml` ignored for migration compatibility.

#### Migration

Install the replacements:

```bash
pip install evidentia                    # CLI + library
pip install "evidentia[gui]"             # + web UI server
```

Rewrite imports:

```python
# before
from controlbridge_core.models.gap import Gap

# after
from evidentia_core.models.gap import Gap
```

If you can't migrate in one shot, the six old PyPI names stay installable
as **v0.5.1 transitional shims**. Each emits a `DeprecationWarning` on
import and forwards every attribute + submodule to the new `evidentia-*`
equivalents via `sys.modules` aliasing:

```bash
pip install controlbridge-core==0.5.1   # works; emits deprecation warning
```

Deep imports like `from controlbridge_core.models.common import EvidentiaModel`
continue to resolve to the same object as `from evidentia_core.models.common
import EvidentiaModel`. The CLI entry `controlbridge` remains available via
the shim and delegates to the new `evidentia` app.

**The shims will be yanked in v0.7.0** (~October 2026). Please migrate
within six months.

#### Added

- `packages/shim-controlbridge{,-core,-ai,-api,-collectors,-integrations}/`
  — six transitional re-export packages.
- `RENAMED.md` at repo root — canonical rename-rationale document indexed
  by Google for users searching "ControlBridge".
- `tests/unit/test_rename_shims.py` — 16 parametrised tests guarding the
  shims' DeprecationWarning + submodule-aliasing + CLI-entry-point
  behaviour until v0.7.0.
- `scripts/_rename_content.py`, `scripts/_bump_version.py`,
  `scripts/_create_shim_packages.py` — one-shot rename tooling, retained
  as historical reference for anyone auditing the rename diff.

#### Changed

- All 7 `pyproject.toml` files version-bumped `0.5.0` → `0.6.0`; inter-package
  dependency pins widened from `>=0.5.0,<0.6.0` to `>=0.6.0,<0.7.0`.
- All 7 workspace package directories renamed via `git mv`
  (history preserved).
- All 6 Python module directories (`src/controlbridge_*` → `src/evidentia_*`)
  renamed via `git mv`.
- 2,094 mechanical string replacements across 203 tracked files (lowercase,
  title-case, and uppercase variants of "controlbridge"/"ControlBridge"/
  "CONTROLBRIDGE").
- `uv.lock` + `packages/evidentia-ui/package-lock.json` regenerated from
  scratch.
- README.md gets a "Renamed from ControlBridge" banner at the very top
  so visitors arriving via GitHub's redirect understand continuity.

#### Shipped as

- 6 × `evidentia-*` wheels @ v0.6.0 (primary)
- 6 × `controlbridge-*` shim wheels @ v0.5.1 (transitional, removed v0.7.0)

## [0.5.0] - 2026-04-20

The **"Phase 2 integrations"** release. Evidentia finally wires the
long-advertised `evidentia-integrations` and `evidentia-collectors`
packages with real implementations: push gaps as Jira issues,
bidirectionally sync status, and auto-collect evidence from AWS +
GitHub. Maps every collected finding to NIST 800-53 control families.

Also extends strict mypy to the two formerly-empty shells and adds
boto3 + moto to dev deps so collector tests run out of the box.

### Added — Jira output integration

New: `pip install "evidentia-integrations"` (no extra needed — the
bundled implementation uses httpx directly rather than the heavyweight
`jira` SDK).

- **`evidentia_integrations.jira.JiraClient`** — httpx-based
  REST v3 client with `test_connection`, `create_issue`, `get_issue`,
  `list_transitions`, `transition_issue`. Secret-safe: API tokens flow
  only through HTTP basic-auth; never logged, never in response bodies.
- **`evidentia_integrations.jira.mapper`** — pure functions mapping
  ControlGap <-> Jira issue body + GapStatus <-> Jira workflow name.
  Forward mapping covers all five `GapStatus` enum values; reverse
  mapping covers the default Jira Cloud workflow plus common custom
  statuses (Blocked, In Review, Reopened, Won't Fix, WontFix, etc.).
- **`push_gap_to_jira`, `sync_gap_from_jira`** — gap-level helpers that
  combine client + mapper. Mutate `gap.jira_issue_key` on create;
  update `gap.status` + `gap.remediated_at` on sync. Return typed
  `JiraSyncOutcome` entries so CLI / API callers can render per-gap
  results without a second pass.
- **`push_open_gaps`, `sync_report`** — batch wrappers over a
  `GapAnalysisReport` with severity-filter + max-issues safety rail.
- **CLI**: `evidentia integrations jira {test,push,sync,status-map}`
- **REST API**:
  - `GET /api/integrations/jira/status` — connection probe (never returns token)
  - `GET /api/integrations/jira/status-map` — current mapping for UI
  - `POST /api/integrations/jira/push/{report_key}` — batch push
  - `POST /api/integrations/jira/sync/{report_key}` — batch sync

Credentials: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`,
`JIRA_PROJECT_KEY`, `JIRA_ISSUE_TYPE` env vars.

### Added — AWS evidence collector

New: `pip install "evidentia-collectors[aws]"` (adds `boto3`).

- **`evidentia_collectors.aws.AwsCollector`** — orchestrator for
  Config + Security Hub with per-subsystem `collect_*` methods +
  `collect_all()`. Sub-collector failures are swallowed + logged so one
  bad service doesn't drop the other's findings.
- **AWS Config collector** — iterates `describe_compliance_by_config_rule`,
  then expands each non-compliant rule via
  `get_compliance_details_by_config_rule`. One SecurityFinding per
  non-compliant resource.
- **Security Hub collector** — batches `get_findings` with workflow/state
  filters. Prefers `Compliance.RelatedRequirements` for NIST 800-53 IDs
  when present (direct AWS attribution); falls back to the curated
  mapping table otherwise.
- **Control mapping** — `map_config_rule_to_controls` + `map_security_hub_control_to_controls`
  with 25+ rule/control entries covering AC/IA/SC/AU/CM/CP/SI families.
  Rule-name normalizer handles hyphenated + camelCase + underscored
  forms consistently.
- Credentials via standard boto3 chain (env / ~/.aws / instance profile).

### Added — GitHub evidence collector

New: ships in the base `evidentia-collectors` package — zero extra
deps needed (uses httpx directly; `[github]` extra remains for users
who want pygithub for custom workflows).

- **`evidentia_collectors.github.GitHubCollector`** — collects from
  a single repo: visibility, default-branch protection state, CODEOWNERS
  presence at any of three canonical paths.
- Emits findings for both compliance (PR review required, status checks
  configured, admins enforced, CODEOWNERS present — all INFORMATIONAL /
  RESOLVED) and non-compliance (unprotected default branch, missing
  CODEOWNERS, public repo — HIGH / MEDIUM / ACTIVE).
- Control mapping: SA-11 (developer security testing), CM-2/CM-3
  (baseline/change), AC-3/AC-6 (access enforcement), SI-2 (flaw
  remediation).
- Credential: `GITHUB_TOKEN` env var (personal access token or Actions
  workflow token). Public repos work unauthenticated.

### Added — collector CLI + REST API

- **CLI**: `evidentia collect {aws,github}` — writes findings as
  JSON to `--output` (default stdout) + prints a Rich summary table
  broken down by severity + source.
- **REST API**:
  - `GET /api/collectors/status` — which collectors are installed +
    whether `GITHUB_TOKEN` is set (never returns token value).
  - `POST /api/collectors/aws/collect` — run AWS collector with
    optional region/profile/subsystem flags.
  - `POST /api/collectors/github/collect` — run GitHub collector;
    request body: `{repo: "owner/repo"}`.

### Added — dev deps

- `boto3>=1.35` + `moto[all]>=5.0` in the workspace dev group so
  collector tests run without any extra install step.

### Changed

- **CI mypy target** extended from 3 packages to all 5 Python packages.
  `evidentia-integrations` and `evidentia-collectors` now
  enforce `--strict-optional` on every commit.
- **Roadmap**: v0.5.0 shipped Jira + AWS + GitHub. Okta / ServiceNow /
  Vanta / Drata shifted to v0.5.1. Evidence chain of custody still
  targets v0.6.0.

### Tests: 501 → **604 passing** (+103)

- +43 Jira mapper / client unit tests (httpx.MockTransport-backed)
- +14 Jira sync helper tests (fake JiraClient via MagicMock)
- +8 Jira REST-endpoint integration tests (TestClient)
- +22 AWS collector tests (MagicMock paginators + curated mapping)
- +12 GitHub collector tests (httpx.MockTransport)
- +4 collector REST-endpoint tests

Frontend test count unchanged (6 Vitest).

### Migration

None — v0.5.0 is a strict feature add. Inter-package pins bump from
`>=0.4.0,<0.5.0` to `>=0.5.0,<0.6.0` across every package; existing
v0.4.x installs need to upgrade all six packages in lockstep (which
`pip install --upgrade evidentia` does automatically).

## [0.4.1] - 2026-04-19

Completes the v0.4.0 "Accessible GRC" release — adds every interactive
page the v0.4.0-alpha.1 backend exposed over REST. Non-technical users
can now run gap analysis, diff reports, generate risks, and edit
configuration entirely in the browser without ever touching the CLI.

Also ships the reusable GitHub Action as a separately-published repo
(`allenfbyrd/evidentia-action@v1`) and fixes three mypy regressions
that slipped into `evidentia-api` routers on the alpha.1 release.

### Added — interactive web UI

- **Three-path onboarding wizard on Home page** (Zustand state machine):
  - "Try sample data" — guides through the Meridian v2 walkthrough
  - "Upload inventory" — drag-drop file picker, auto-detects format
  - "Start from scratch" — 4-question wizard (industry / hosting /
    data types / regulatory) -> POST /api/init/wizard -> previews
    all three generated YAMLs with copy-to-clipboard
- **Gap Analyze page** — framework multi-select (82 catalogs filterable),
  file upload OR server-side path, organization / system_name overrides,
  run button -> TanStack Table with sortable columns + global filter +
  severity/effort/priority badges.
- **Gap Diff page** — two-report picker from gap store, summary cards
  (opened / closed / severity↑ / severity↓ / unchanged), regression
  alert, filterable per-entry table. Matches the CLI's `gap diff`
  output exactly.
- **Risk Generate page** — SSE-streamed per-gap progress. POSTs to
  `/api/risk/generate` and reads the `text/event-stream` response via
  `ReadableStream` + `TextDecoder`, parsing each `data: {...}` frame
  into a progress row. Supports cancel mid-stream; fails cleanly on
  offline-mode violations.
- **Settings edit form** — validated PUT to `/api/config`. Writes
  `evidentia.yaml` server-side; CLI + GUI both pick up changes.
  LLM-provider and air-gap sections stay read-only (env-var sourced).

### Added — separate reusable GitHub Action

- New repo: [`allenfbyrd/evidentia-action`](https://github.com/allenfbyrd/evidentia-action)
  at v1.0.0 + floating `v1` pointer. One-line replacement for the
  80-line drop-in workflow template from v0.3.0:
  `uses: allenfbyrd/evidentia-action@v1`.
- Shipped from `scripts/evidentia-action-skeleton/` which remains
  as the authoritative source for the action's files; future changes
  propagate via `cp -r` + tag.

### Added — shadcn/ui primitives

- `input.tsx`, `label.tsx`, `textarea.tsx`, `switch.tsx`, `tabs.tsx`,
  `alert.tsx`, `progress.tsx` — Radix-based, matching shadcn New York
  preset. WCAG 2.1 AA via underlying Radix primitives.

### Added — Vitest coverage

- `src/lib/utils.test.ts` — `cn()` behavior (Tailwind merge, falsy
  filtering, object syntax)
- `src/lib/severity.test.ts` — severity-rank ordering + badge mapping

Frontend CI now runs 6 passing tests. Deeper component coverage
queued for v0.4.2.

### Fixed

- **Three mypy regressions in evidentia-api routers** (caught by
  the `typecheck` job on CI, not reproduced locally until now):
  - `routers/gaps.py`: `valid` helper missing a type annotation
  - `routers/risks.py`: passed `yaml.safe_load(...)` dict where
    `RiskStatementGenerator.generate_async` expected a typed
    `SystemContext` — now loads via `SystemContext.from_yaml(path)`
    and emits a clear SSE error if no context file is provided.
  - `routers/explain.py`: called non-existent `gen.explain(...)` —
    actual method is `generate(control, framework_id, refresh)`.

### Tests: 501 passing (unchanged)

Frontend: +6 Vitest tests. Backend: unchanged at 501 pytest (mypy
regressions were caught at CI-time, not via tests).

### Migration

None — v0.4.1 is a strict feature add on top of v0.4.0. Inter-package
pins stay at `>=0.4.0,<0.5.0`.

## [0.4.0-alpha.1] - 2026-04-19

The **"Accessible GRC"** release — Evidentia grows beyond the CLI.
Adds a FastAPI REST server, a React + shadcn/ui web UI (localhost-only,
WCAG 2.1 AA via Radix primitives), an air-gapped mode (`--offline`
flag + `doctor --check-air-gap` validator), and a new sixth workspace
package (`evidentia-api`). The web UI is installable via the new
`[gui]` extra: `pip install "evidentia[gui]"` then
`evidentia serve`.

This `alpha.1` ships the backend end-to-end + the read-only web UI
surface (Home / Dashboard / Frameworks / Settings). Interactive pages
(onboarding wizard, Gap Analyze form, Gap Diff picker, Risk Generate
streaming) land in `alpha.2`. The full `v0.4.0` release is gated on
Playwright E2E coverage and a fresh-venv smoke test on
Windows/macOS/Linux.

### Added

- **New workspace package `evidentia-api`** (`packages/evidentia-api/`)
  shipping a FastAPI app with 18 endpoints under `/api/*`. The `[gui]`
  optional extra on the meta-package pulls it in:
  `pip install "evidentia[gui]"`.
- **New CLI subcommand `evidentia serve`** — launches uvicorn serving
  both the REST API and the bundled React SPA from `127.0.0.1:8000`
  (localhost-only by default; `--host 0.0.0.0` emits a security warning).
  Flags: `--port`, `--host`, `--dev` (permissive CORS for Vite HMR),
  `--no-browser`, `--reload`.
- **Global `--offline` flag on every command.** Wires through to the new
  `evidentia_core.network_guard` module; when set, any attempted LLM
  or network call to a non-loopback / non-RFC-1918 host raises
  `OfflineViolationError` before network IO is issued. Works with Ollama
  (localhost:11434), vLLM, and custom OpenAI-compatible endpoints on
  private IPs.
- **`evidentia doctor --check-air-gap`** — per-subsystem posture
  report (LLM client, catalog loader, AI telemetry, gap store, web UI).
  Renders as a Rich table in the CLI and as JSON via
  `POST /api/doctor/check-air-gap`.
- **Web UI pages (v0.4.0-alpha.1 scope):**
  - `/` — Home / quick-nav cards to Frameworks, Dashboard, Settings
  - `/dashboard` — historical gap reports + top-line metrics
  - `/frameworks` — 82-framework browser with tier / category / free-text filters
  - `/frameworks/:id` — framework detail with full control list
  - `/settings` — config view + LLM-provider presence + air-gap posture
- **18 REST endpoints under `/api/*`:** health, version, config (GET/PUT),
  doctor (GET, `/check-air-gap`), llm-status (presence only — never
  returns key values), frameworks (list, detail, single-control), gaps
  (analyze, reports list, single-report, diff), risks (`/generate` SSE),
  explain (`/{framework}/{control_id}` SSE), init-wizard.
- **Shared `evidentia_core.init_wizard` module** — starter YAML
  generators + deterministic framework recommender. The CLI
  `evidentia init` and GUI `/api/init/wizard` endpoint now produce
  identical files from the same code path. Presets:
  `soc2-starter`, `nist-moderate-starter`, `hipaa-starter`,
  `cmmc-starter`, `empty`.
- **`evidentia_core.config`** moved from the CLI meta-package
  (`evidentia.config`) into `evidentia-core` so both the CLI
  and the API backend consume it without a circular dependency. A
  transparent re-export shim at the old location keeps existing
  `from evidentia.config import ...` imports working unchanged.
- **Hatchling build hook** (`packages/evidentia-api/hatch_build.py`)
  that drives `npm run build` in `packages/evidentia-ui/` and copies
  `dist/*` into the Python package's `static/` directory before wheel
  assembly. Set `EVIDENTIA_SKIP_FRONTEND_BUILD=1` to bypass for
  Python-only build matrices.
- **New workspace directory `packages/evidentia-ui/`** — Vite + React
  + TypeScript + shadcn/ui frontend. Not a Python workspace member;
  builds via `npm run build`. Stack: React 18, Vite 5, Tailwind CSS,
  shadcn/ui (Radix primitives), TanStack Query / Table / Virtual,
  React Router 6, Zustand, React Hook Form + Zod, Recharts.

### Changed

- **Roadmap shuffle (`docs/ROADMAP.md`):** GUI pulled forward from v0.6.0
  to v0.4.0; `--offline` flag pulled forward from v0.5.0 to v0.4.0;
  Phase 2 integrations (Jira, AWS, GitHub, Okta, ServiceNow, Vanta,
  Drata) shifted right to v0.5.0; evidence chain of custody (SHA-256 +
  GPG) shifted right to v0.6.0. See roadmap for the full shape.
- **`evidentia_ai.client.get_instructor_client`** now wraps
  `litellm.completion` / `acompletion` with an offline guard. When
  offline mode is on, cloud LLM calls raise
  `OfflineViolationError` before any network IO.
- **Meta-package `evidentia` deps:** removed `fastapi>=0.115`,
  `uvicorn[standard]>=0.30`, `python-multipart>=0.0.9` (moved to
  `evidentia-api` where they're actually used).
- **`evidentia init` defaults:** `--frameworks` now defaults to
  `nist-800-53-rev5-moderate,soc2-tsc` (was
  `nist-800-53-mod,soc2-tsc`); new `--preset` flag accepts the five
  wizard presets above; new `--organization` flag for headless use.
- **CI test workflow** (`.github/workflows/test.yml`): new `frontend-test`
  job runs TypeScript typecheck + Vite build on Node 20; existing mypy
  target list extended to include `evidentia-api`.
- **CI release workflow** (`.github/workflows/release.yml`): adds Node 20
  setup + SPA-bundled-in-wheel verification step before PyPI publish.

### Fixed

- **Windows cp1252 encoding** on `evidentia --help`: the
  pre-existing `--config` help string used `\u2192` (→) which crashed
  legacy Windows consoles. Replaced with ASCII `->`. Same class of fix
  as v0.3.1's `gap diff --format console` normalization.

### Tests: 392 → **501 passing** (+109)

- `+43` from `evidentia_core.network_guard` (host classifier, URL
  guard, LLM-model guard, offline-mode toggle + context manager).
- `+30` from `evidentia_core.init_wizard` (3 YAML generators + the
  framework recommender's decision tree).
- `+36` from `evidentia-api` FastAPI TestClient coverage (basic
  endpoints, frameworks browser, config read/write, init-wizard,
  gap analyze/reports/diff, SSE endpoint validation, OpenAPI schema).

### Migration

- **Library users importing `evidentia.config`**: no change needed
  (shim re-export). For new code, prefer the canonical
  `evidentia_core.config` import.
- **Users of `evidentia init`**: default framework list changed
  from the legacy 16-control NIST sample to the full Rev 5 Moderate
  baseline; supply `--frameworks nist-800-53-mod,soc2-tsc` to keep the
  old behavior.
- **CI consumers building from source**: install Node 20+ in the
  environment (or set `EVIDENTIA_SKIP_FRONTEND_BUILD=1` when Node
  is unavailable; the wheel will serve a dev-placeholder page in lieu
  of the SPA).

## [0.3.1] - 2026-04-19

Comprehensive examples + dogfooded GitHub Action + one latent-bug fix
surfaced by the new integration tests. No new features, no breaking
API changes; scope is "prove every v0.3.0 feature works end-to-end
against realistic data."

### Added — three realistic end-to-end scenarios

- **`examples/meridian-fintech-v2/`** — 48-control inventory against
  `nist-800-53-rev5-moderate` + `soc2-tsc` + `eu-gdpr`. Baseline
  (`my-controls.yaml`) + PR branch (`my-controls-pr.yaml`) engineered
  to produce every `gap diff` classification (opened + closed +
  severity_increased + severity_decreased + unchanged). Ships with
  pre-generated `snapshots/baseline.json` + `snapshots/pr-branch.json`
  + `snapshots/pr-diff.md` for zero-setup demo. Uses the v0.2.1
  `evidentia.yaml` schema (flat `frameworks:`, `llm.model`,
  `organization`, `system_name`). Mixes NIST-pub (`AC-2(1)`) and
  NIST-OSCAL (`ac-2.3`) ID conventions to exercise the normalizer.
  `user-catalog-demo/soc2-tsc-licensed.json` is a fake "licensed
  AICPA copy" fixture for the `catalog import` shadow-precedence
  demo.

- **`examples/acme-healthtech/`** — 34-control HIPAA-covered-entity
  scenario. Frameworks: `hipaa-security` + `hipaa-privacy` +
  `hipaa-breach` + `nist-800-53-rev5-moderate`. Showcases HIPAA's
  `164.308(a)(1)(i)` dotted-section ID style and multi-rule cross-
  framework efficiency where one control satisfies 3–4 frameworks.

- **`examples/dod-contractor/`** — 30-control CMMC Level 2 +
  NIST 800-171 Rev 2 scenario for DoD-contract workflows. Uses
  `CMMC.L2-3.1.1`-style prefixed IDs alongside plain `3.1.1`
  dotted IDs to exercise both conventions in one report. Includes
  a realistic DIBCAC-style gap (SIEM correlation missing).

- **`examples/WALKTHROUGH.md`** — tour document with exact command
  sequences for every v0.3.0 feature, keyed to each scenario.

- **`scripts/demo/generate_snapshot_pair.py`** — regeneration helper
  that rebuilds Meridian v2's `baseline.json` / `pr-branch.json` /
  `pr-diff.md` from the committed inventories. Use it after a
  NIST catalog refresh to keep the README's expected counts in sync.

- **`.github/workflows/evidentia.yml`** — Evidentia dog-
  fooding its own GitHub Action. On every PR touching the Meridian
  v2 inventory or the bundled catalogs, the workflow runs `gap
  analyze` + `gap diff` and posts the result as a PR comment;
  `--fail-on-regression` gates merging. Uses the local `uv sync`
  build so the action runs against whatever's on the PR branch,
  not the last-published PyPI wheel.

### Added — integration tests

- `tests/integration/test_examples/test_examples_smoke.py` — 8 cases
  covering each scenario's `gap analyze` pipeline, the Meridian v2
  `gap diff` every-classification regression guard, CSV inventory
  parse, and config-loader deprecation behavior (legacy meridian
  emits DeprecationWarning on its v0.1.x yaml schema; Meridian v2
  emits no warnings on the v0.2.1 schema).

### Fixed — `_is_open` gap-status filter on in-memory diff path

`evidentia_core.gap_diff._is_open()` used `str(gap.status)` to
compare against `GapStatus.OPEN.value`. On the JSON-roundtrip path
(CLI: `analyze` → save JSON → load JSON → `diff`), Pydantic
coerces the enum to its string value and the comparison works.
On the in-memory path (library users calling `compute_gap_diff()`
directly against freshly-computed `GapAnalysisReport`s with
`use_enum_values=True` active), `gap.status` is still a `GapStatus`
instance and `str(enum)` returns `"GapStatus.OPEN"` rather than
`"open"` — so `_is_open()` returned `False` for every gap and the
diff summary reported all zeros. The v0.3.1 fix normalizes via
`gap.status.value if isinstance(gap.status, GapStatus) else ...`
so both paths work identically. Flagged by the new Meridian v2
every-classification integration test — this bug never surfaced
in v0.3.0 because no test exercised the in-memory path.

### Fixed — Windows console Unicode handling in `gap diff` output

The v0.3.0 Rich console renderer used Unicode glyphs (`✗`, `✓`,
🆕, 📈) that crashed on Windows legacy consoles (cp1252 encoding):
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2717'`.
v0.3.1 uses ASCII-only glyphs in the Rich path (`FAIL` /
`PASS` / section headers without emoji). The markdown and
github-annotation renderers keep their emoji — those target
UTF-8-clean surfaces (PR comments, Actions logs).

### Changed

- **Legacy `examples/meridian-fintech/`** gets a deprecation
  banner at the top of its README pointing at
  `examples/meridian-fintech-v2/`. No files deleted — all existing
  links still work.

### Tests: 384 → **392 passing** (+8)

New integration tests exercise the examples + config-loader
deprecation path end-to-end.

## [0.3.0] - 2026-04-17

The **"compliance-as-code" release.** Two user-facing feature areas plus
deprecation cleanup and a fully-strict mypy CI gate. No breaking API
changes to existing commands; new commands and a removed deprecated
enum.

### Added — PR-level compliance checking: `evidentia gap diff`

Compare two :class:`GapAnalysisReport` snapshots and classify each gap
into one of five states (opened, closed, severity_increased,
severity_decreased, unchanged). Drop-in for CI/CD pipelines: every pull
request can now run `evidentia gap diff --fail-on-regression` to
block merges that make the compliance posture worse.

- New module `evidentia_core.gap_diff` with `compute_gap_diff()`,
  `render_markdown()` (PR-comment-friendly), and
  `render_github_annotations()` (`::error::` / `::warning::` / `::notice::`
  lines that surface inline on the Actions Checks page).
- New models `GapDiff`, `GapDiffEntry`, `GapDiffSummary` (all Pydantic-
  validated and JSON-serializable).
- New CLI: `evidentia gap diff [--base PATH] [--head PATH]
  [--fail-on-regression] [--format console|json|markdown|github]
  [--output PATH]`. When `--base` / `--head` are omitted, auto-picks
  the two most-recent reports from the v0.2.1 gap store.
- **Control-ID normalization in diff**: a gap `AC-2(1)` in base and
  `ac-2.1` in head is correctly recognized as the same gap (uses the
  v0.2.1 normalizer, no false opened+closed pair).
- **Status-aware**: REMEDIATED / ACCEPTED / NOT_APPLICABLE gaps are
  excluded from the diff (they're not "open gaps" to regress on). An
  ACCEPTED gap in base that re-appears OPEN in head counts as a
  regression (acceptance was revoked).
- **GitHub Action scaffolding**: new `docs/github-action/README.md`
  (full setup guide) + `docs/github-action/workflow-example.yml`
  (drop-in `.github/workflows/evidentia.yml` template). The
  companion reusable action `allenfbyrd/evidentia-action` is
  scoped for v0.3.1.

### Added — Plain-English control explanations: `evidentia explain`

Translate authoritative-but-opaque framework control text into
actionable engineer-and-executive language. Every explanation is
cached on disk per (framework, control, model, temperature) tuple —
you pay the LLM cost once per lookup.

- New module `evidentia_ai.explain` with:
  - `PlainEnglishExplanation` Pydantic model (strict schema: plain
    English summary, why-it-matters paragraph, 3-8 what-to-do bullets,
    effort estimate, optional common-misconceptions paragraph).
  - `ExplanationGenerator` — Instructor-backed LLM pipeline on top of
    LiteLLM. Works with any LiteLLM-supported provider
    (OpenAI / Anthropic / Google / Ollama / etc).
  - Disk cache at `<platformdirs-cache>/evidentia/explanations/`
    keyed by SHA-256 of (framework, control, model, temperature).
    Override via `EVIDENTIA_EXPLAIN_CACHE_DIR`.
- New CLI: `evidentia explain control <id> [--framework FW]
  [--model MODEL] [--refresh] [--format panel|markdown|json]
  [--output PATH]`. Pre-flight check warns if no API-key env var
  matches the picked model (e.g., using `claude-*` without
  `ANTHROPIC_API_KEY`).
- Cache management: `evidentia explain cache where` (prints the
  cache directory), `evidentia explain cache clear` (wipes it).
- Reads defaults from `evidentia.yaml` using the v0.2.1 config
  loader (flag > env > yaml > built-in default).

### Changed

- **`FrameworkId` enum removed** from `evidentia_core.models.common`.
  Deprecated in v0.2.0 with a module-level `__getattr__` that emitted
  `DeprecationWarning`; v0.3.0 drops the enum and the getattr hook
  entirely. `ControlMapping.framework` has always been `str`; users
  who were relying on the enum value should use the plain string
  framework ID (e.g., `"nist-800-53-rev5"`) or
  `evidentia_core.catalogs.manifest.load_manifest()` for
  programmatic discovery.
- **mypy CI job flipped from advisory to strict.** v0.2.1 added
  `--strict-optional` as `continue-on-error: true` to avoid blocking
  releases on pre-existing annotation gaps; v0.3.0 fixed those 7
  gaps and dropped the `continue-on-error`. Enabled the
  `pydantic.mypy` plugin in `[tool.mypy]` so every
  `Model.model_validate*()` return type is correctly inferred.
  Added `types-PyYAML` and `pydantic` to the dev dependency group so
  mypy can find them.
- **`evidentia gap analyze`**: no behavior change, but the gap
  store write at the end of each run is now a required dependency
  of `gap diff`'s auto-picker. Unchanged from v0.2.1 users'
  perspective.

### Tests: 352 → **384** passing (+32 new)

- `tests/unit/test_gap_analyzer/test_gap_diff.py` — 16 cases covering
  every diff-status classification, control-ID normalization across
  notation styles, REMEDIATED/ACCEPTED status handling, sort order,
  and both Markdown / GitHub-annotation renderers.
- `tests/unit/test_ai/test_explain.py` — 19 cases covering the
  explanation cache (key determinism, model/temperature sensitivity,
  corruption handling), `ExplanationGenerator` behavior (cache hit
  skips LLM, refresh bypasses cache, echo-field defensive override),
  and the `PlainEnglishExplanation` schema's strict-validation edges.
- `tests/unit/test_models/test_framework_id_deprecation.py` — removed
  (the deprecation path and the enum are both gone).

### Infrastructure / hygiene

- Inter-package dependency pins bumped from `>=0.2.0,<0.3.0` to
  `>=0.3.0,<0.4.0` across all 5 packages.
- `scripts/catalogs/` generator scripts unchanged — v0.2.1 NIST
  bundling is stable.

### Known follow-ups (tracked in `docs/ROADMAP.md`)

- **Reusable `allenfbyrd/evidentia-action`** — the full GitHub
  Action wrapper. v0.3.0 ships the CLI; v0.3.1 will add the one-line
  `uses:` wrapper so users don't need the 80-line workflow in
  `docs/github-action/workflow-example.yml`.
- **PyPI Trusted Publisher (OIDC) migration** — still pending PyPI-
  side UI configuration. v0.3.0 continues using the API token.

## [0.2.1] - 2026-04-16

Correctness and integrity release. Follow-up to the v0.2.0 Phase 1.5
big-bang: fixes bugs an external code audit surfaced, bundles the full
NIST SP 800-53 Rev 5 catalog (1,196 controls + 4 resolved baselines),
adds 221 new tests, and lights up a working `evidentia.yaml`
project-config loader. No breaking API changes — all additions are
either additive (new CLI flags, new config keys) or transparent
(richer data, better defaults).

See `docs/ROADMAP.md` for the v0.3.0+ plan.

### Added

- **Full NIST SP 800-53 Rev 5 catalog** bundled verbatim from the CC0
  `usnistgov/oscal-content` repository at pinned tag `v1.4.0`. Ships as
  `nist-800-53-rev5.json` (1,196 controls across 20 families, including
  all enhancements) plus 4 resolved baseline catalogs:

  | Framework ID                    | Controls (inc. enhancements) | Use case                     |
  |---------------------------------|------------------------------|------------------------------|
  | `nist-800-53-rev5-low`          | 149                          | Low-impact FISMA systems     |
  | `nist-800-53-rev5-moderate`     | 287                          | Most federal / FedRAMP Mod   |
  | `nist-800-53-rev5-high`         | 370                          | High-impact FISMA / FedRAMP High |
  | `nist-800-53-rev5-privacy`      | 102                          | Privacy overlay              |

  Resolution uses the OSCAL profile resolver shipped in v0.2.0 (plus
  the fragment-href back-matter fix described under **Fixed** below).
  New script `scripts/catalogs/fetch_nist_oscal.py` regenerates these
  at release time against a pinned upstream tag.

- **FedRAMP baselines (`fedramp-rev5-low/moderate/high/li-saas`)** now
  carry real NIST 800-53 control text. v0.2.0 shipped these as
  pointer-only catalogs where every description was literally
  "See nist-800-53-rev5 catalog for full control text". v0.2.1 resolves
  each FedRAMP control ID against the bundled NIST catalog and
  substitutes real titles + descriptions (1,008 control descriptions
  replaced; zero unresolved).

- **Hybrid effort estimator** (`GapAnalyzer._estimate_effort`). v0.2.0
  used only a structural complexity score derived from
  `len(enhancements) + len(assessment_objectives)`, which was zero for
  every bundled catalog except the new NIST OSCAL one — meaning every
  gap scored `LOW` and the priority formula silently collapsed to
  `severity × (1 + 0.2 × cross_fw_count)`. The replacement is a
  three-layer cascade: structural score → keyword presence in the
  description → description-length fallback. See
  `docs/architecture/effort-estimation.md` for keyword lists and
  scoring rationale.

- **`evidentia.yaml` project-config loader** (`evidentia/config.py`).
  `evidentia init` has generated this file since v0.1.0 but no
  subcommand read it. v0.2.1 walks CWD → parents looking for the first
  `evidentia.yaml`, validates a strict schema, and applies values
  via precedence: **CLI flag > env var > yaml > built-in default**.
  Honored keys for v0.2.1:

  - `organization` / `system_name` — auto-populates inventory metadata
  - `frameworks:` — default set for `gap analyze`; CLI `--frameworks`
    replaces (does not union)
  - `llm.model` / `llm.temperature` — defaults for `risk generate`;
    overridden by env `EVIDENTIA_LLM_MODEL` / `EVIDENTIA_LLM_TEMPERATURE`

  Legacy v0.2.0 keys (`storage:`, `logging:`, nested `frameworks.default:`)
  are accepted without validation errors; `frameworks.default` triggers
  a deprecation warning pointing at the flattened v0.2.1 shape.
  `${ENV_VAR}` interpolation is supported in any string value.

- **Persistent gap report store** (`evidentia_core/gap_store.py`).
  Every `gap analyze` run writes a canonical snapshot to
  `<platformdirs>/evidentia/gap_store/<hash>.json`. `risk generate
  --gap-id GAP-…` (without `--gaps`) now loads the most-recent report
  from the store automatically. Override location via
  `EVIDENTIA_GAP_STORE_DIR`.

- **`--organization` / `--system-name` CLI flags on `gap analyze`**.
  Override inventory metadata for CSV-sourced runs (which previously
  hardcoded `"Unknown Organization (from CSV)"`) or when the inventory
  file's org name doesn't match the report recipient.

- **Placeholder-catalog warning**. Running `gap analyze` against a
  Tier-C stub catalog (e.g., `soc2-tsc`) now emits a prominent
  `UserWarning` telling users the control text isn't authoritative and
  pointing them at `evidentia catalog import` to load their
  licensed copy.

- **mypy CI job** (`.github/workflows/test.yml`). Runs `mypy --strict-optional`
  against `packages/evidentia-core/src` and
  `packages/evidentia/src`. Advisory-only for v0.2.1 (`continue-on-error`)
  because the existing v0.1.x codebase has some untyped helpers; will be
  tightened in v0.3.0.

- **221 new tests, bringing total from 131 → 352 passing**. New suites:

  - `tests/unit/test_gap_analyzer/test_effort_estimator.py` — 44 cases
    covering structural layer, all keyword substitutions, length fallback,
    regression guard for the v0.2.0 "everything is LOW" bug.
  - `tests/unit/test_gap_analyzer/test_priority_math.py` — 85 cases
    parameterized over every severity × effort × cross-fw-count
    combination, asserting priority matches the documented formula
    exactly.
  - `tests/unit/test_gap_analyzer/test_gap_store.py` — 14 cases for
    the persistent gap-store facility (directory resolution
    precedence, hash-key determinism, roundtrip integrity, latest-by-mtime
    lookup).
  - `tests/unit/test_oscal/test_profile_resolver.py` — 12 cases for
    OSCAL profile resolution edge cases (relative paths, `file://` URIs,
    fragment-href back-matter lookup, JSON-rlink preference,
    include/exclude filters, override IDs, missing-import errors).
  - `tests/unit/test_oscal/test_exporter.py` — 5 cases pinning the
    shape of OSCAL Assessment Results exports.
  - `tests/unit/test_config.py` — 24 cases for the new
    `evidentia.yaml` loader (schema validation, precedence chain,
    legacy-shape warnings, env-var interpolation).
  - `tests/unit/test_models/test_control_id_normalization.py` — 20
    cases covering the NIST-publication style (`AC-2(1)(a)`) vs.
    NIST-OSCAL style (`ac-2.1.a`) normalization added to support the
    bundled NIST catalog.
  - `tests/integration/test_cli/test_catalog_cli.py` — 12 cases for
    the v0.2.0 CLI subcommands (`import`, `where`, `license-info`,
    `remove`, `list --tier`, `list --category`, shadow-resolution,
    duplicate-import behavior, `doctor`, `version`) that previously had
    zero coverage.

- **`docs/ROADMAP.md`** — forward plan for v0.3.0 through v0.6.0+ with
  scope-locked priorities (compliance-as-code diff, plain-English
  explanations, Phase 2 integrations, air-gapped mode, evidence chain
  of custody, etc.).

- **`docs/architecture/effort-estimation.md`** — design doc for the new
  hybrid estimator so future reviewers don't re-derive the keyword
  lists from code.

### Fixed

- **OSCAL profile resolver — back-matter fragment href resolution.**
  v0.2.0's resolver rejected `href: "#<uuid>"` references (raising
  `ProfileResolutionError: Fragment-only hrefs not yet supported`),
  which meant every real-world OSCAL profile (including every NIST
  baseline) couldn't be resolved. v0.2.1 looks up the UUID in the
  profile's `back-matter.resources[].uuid`, walks the first JSON-media
  `rlinks[].href`, and follows it. Falls back to the first non-empty
  rlink when no JSON-flagged entry exists.

- **Dual control-ID convention support.** NIST publications render
  enhancement IDs as `AC-2(1)(a)`; NIST OSCAL renders them as
  `ac-2.1.a`. v0.2.0's `ControlCatalog.get_control()` was strict
  (did a `.upper()`-only lookup), so users typing one style against a
  catalog indexed in the other got `None`. v0.2.1 normalizes both via
  a new `_normalize_control_id()` helper: both
  `catalog.get_control("AC-2(1)(a)")` and
  `catalog.get_control("ac-2.1.a")` resolve to the same control.

- **`evidentia.yaml` is now actually read by subcommands** (see
  **Added** above).

- **`risk generate --gap-id` no longer unconditionally errors.** The
  new gap-store lookup resolves `--gap-id` against the last-saved
  report when `--gaps` is omitted. Provides a clear message
  ("Run `evidentia gap analyze ...` first") when no report exists.

- **CSV organization override.** v0.2.0 hardcoded
  `"Unknown Organization (from CSV)"` in the CSV inventory parser with
  no override path. The new `--organization` / `--system-name` CLI
  flags on `gap analyze` and the corresponding `evidentia.yaml`
  keys resolve this.

### Changed

- **`evidentia init` template** updates the generated
  `evidentia.yaml` to the v0.2.1 schema with commented-out examples
  of every honored key.

- **`litellm` version pin tightened** from `>=1.50` to `>=1.50,<2.0`
  (LiteLLM has historically broken minor-version APIs).

- **`nist-800-53-mod` (the 16-control v0.1.x sample)** kept intact for
  yaml-pin backward compatibility, but renamed in metadata to clearly
  flag it as deprecated and point at `nist-800-53-rev5-moderate` (the
  real 287-control baseline). Will be removed in v0.3.0.

- **Framework count** in `evidentia doctor` grows from 77 → 82 (5
  new NIST catalogs).

### Deferred / known follow-ups

- **PyPI Trusted Publisher (OIDC) migration** — release workflow
  continues to use `PYPI_API_TOKEN` for v0.2.1. Switching without
  configuring a Trusted Publisher on PyPI's admin panel first would
  break the release pipeline. Tracked in `docs/ROADMAP.md`.

- **Full `--strict` mypy** — the advisory-mode `--strict-optional` job
  added in v0.2.1 surfaces existing type-annotation gaps without
  blocking releases. v0.3.0 will clean those up and switch to
  strict-fail.

- **v0.2.0 release-workflow API token rotation** — the v0.2.0 commit
  that removed Claude co-authorship used `git filter-branch`; the
  resulting force-push to `main` has been well-tolerated by PyPI, but
  a future history-rewrite-heavy release should confirm PyPI token
  validity before tagging.

## [0.2.0] - 2026-04-16

**Phase 1.5 big-bang release — exhaustive framework expansion.** Follow-up
to the v0.1.1 legal remediation and v0.1.2 version-reporting truth-up.
Evidentia now ships ~77 bundled frameworks across four redistribution
tiers — a comprehensive GRC catalog library so common GRC workflows work
out of the box without digging.

### Added — Frameworks (77 total; up from 2)

**Tier A — US federal (verbatim public domain, 25 frameworks)**

- NIST family: 800-171 Rev 2 (110 controls), 800-171 Rev 3 (90), 800-172
  enhanced CUI protections (33), Cybersecurity Framework 2.0 (106
  subcategories), AI RMF 1.0 (72), Privacy Framework 1.0 (94), Secure
  Software Development Framework (SSDF) 800-218 (42)
- FedRAMP Rev 5: Low / Moderate / High / LI-SaaS baselines (pointer
  catalogs; full resolution via OSCAL profile resolver)
- CMMC 2.0: Levels 1 / 2 / 3
- HIPAA: Security Rule (45 CFR § 164 Subpart C), Privacy Rule (Subpart E),
  Breach Notification Rule (Subpart D)
- US regulatory: GLBA Safeguards Rule, NY DFS 23 NYCRR 500, NERC CIP v7,
  FDA 21 CFR Part 11, IRS Publication 1075, CMS ARS 5.1, FBI CJIS Security
  Policy v6.0, CISA Cross-Sector Cybersecurity Performance Goals
- Plus the existing 16-control `nist-800-53-mod` sample

**Tier A — International (6 frameworks)**

- UK: NCSC Cyber Assessment Framework 3.2, Cyber Essentials
- Australia: Essential Eight, Information Security Manual (ISM)
- Canada: ITSG-33
- New Zealand: NZISM 3.7

**Tier D — Statutory obligations (21 frameworks; government edicts — not
copyrightable)**

- EU: GDPR, AI Act (Regulation 2024/1689), NIS2 Directive, DORA
- UK: Data Protection Act 2018
- Canada: PIPEDA
- US state privacy laws (15): California CCPA/CPRA, Virginia VCDPA,
  Colorado CPA, Connecticut CTDPA, Utah UCPA, Texas TDPSA, Oregon OCPA,
  Delaware DPDPA, Montana MCDPA, Iowa ICDPA, Florida FDBR, Tennessee TIPA,
  New Hampshire NHPA, Maryland MODPA, Minnesota MNCDPA

**Tier C — Licensed stubs (20 frameworks; copyrighted control text not
bundled — structural numbering + license URLs for user import)**

- ISO/IEC family: 27001:2022 (93 Annex A controls), 27002:2022, 27017:2015,
  27018:2019, 27701:2019, 42001:2023 (AI), 22301:2019 (BC)
- PCI DSS v4.0.1
- HITRUST CSF v11
- COBIT 2019
- SWIFT CSCF v2024
- CIS Controls v8.1 + 5 CIS Benchmarks (AWS, Azure, GCP, Kubernetes, RHEL 9)
- Secure Controls Framework (SCF) 2024
- IEC 62443 (industrial/OT security)
- SOC 2 TSC (retained from v0.1.1)

**Tier B — Threat and vulnerability catalogs (4 frameworks)**

- MITRE ATT&CK Enterprise (41 high-use techniques/sub-techniques across
  all 14 tactics)
- MITRE CWE (Top 25 weaknesses for 2024)
- MITRE CAPEC (10-pattern sample)
- CISA Known Exploited Vulnerabilities (8-CVE sample of notable entries
  including Log4Shell, MOVEit, EternalBlue)

### Added — Architecture foundation

- **Manifest-driven registry**: `data/frameworks.yaml` replaces the three
  v0.1.x parallel sources of truth (`FRAMEWORK_METADATA` dict,
  `framework_files` dict, `FrameworkId` enum). Adding a framework = drop
  JSON + one YAML edit. Regenerate via
  `scripts/catalogs/regenerate_manifest.py`.
- **`ControlCatalog` model expansion**: new optional fields `guidance`,
  `objective`, `examples`, `control_class`, `ordering`, `family_hierarchy`,
  `category`. All additive — existing v0.1.x JSONs continue to parse under
  `extra="forbid"`.
- **Recursive enhancement flattener**: fixes NIST 800-53 Rev 5 3-level ID
  lookup like `AC-2(1)(a)` that v0.1.x silently lost. `catalog.get_control`
  now walks the full enhancement tree.
- **`TechniqueCatalog`, `VulnerabilityCatalog`, `ObligationCatalog` models**
  for non-control catalog types. See `evidentia_core/models/threat.py`
  and `evidentia_core/models/obligation.py`.
- **OSCAL profile resolver** (`evidentia_core/oscal/profile.py`):
  supports `include-controls`, `exclude-controls`, `set-parameter`,
  `alter.add`, `merge`. Enables user-supplied OSCAL profile JSONs via
  `evidentia catalog import --profile profile.json --catalog source.json`.
- **User-import facility**: new CLI commands `catalog import`, `catalog
  where`, `catalog license-info`, `catalog remove`, and `catalog list
  --tier <A|B|C|D> --category <control|technique|vulnerability|obligation>`.
  User-imported catalogs shadow bundled ones of the same ID (via
  `platformdirs`-resolved user directory, overridable by
  `EVIDENTIA_CATALOG_DIR`). A licensed ISO 27001 copy imported by a
  customer replaces the Tier-C stub transparently for all `catalog show` /
  `gap analyze` calls.
- **Tier-partitioned catalog directory layout**: `data/us-federal/`,
  `data/international/`, `data/state-privacy/`, `data/stubs/`,
  `data/threats/`, `data/mappings/`.

### Added — Crosswalks (6 total)

- NIST CSF 2.0 → NIST 800-53 (36 mappings, derived from NIST OLIR)
- FedRAMP Moderate → CMMC Level 2 (32 mappings, from DoD CMMC Assessment
  Guide correlations)
- NIST 800-53 → HIPAA Security Rule (20 mappings, from HHS OCR guidance)
- Virginia VCDPA → California CCPA/CPRA (13 subject-rights mappings)
- ISO/IEC 27001:2022 → NIST 800-53 (23 conceptual parity mappings)
- Existing `nist-800-53-rev5_to_soc2-tsc` crosswalk (17 mappings, retained
  from v0.1.1 with sanitized titles)

### Added — Testing

- 80 new unit tests bringing total from 22 → **131 tests passing**:
  parametric smoke test per bundled framework (77 cases), tier invariants
  (Tier-C must be placeholder, Tier-A must not), OSCAL model validation,
  manifest loader, user-dir resolution, `FrameworkId` deprecation gating,
  recursive enhancement flattener.

### Changed

- `FrameworkId` enum (in `evidentia_core.models.common`) is deprecated
  — emits `DeprecationWarning` on import. Use manifest-driven string IDs
  instead. Will be removed in v0.3.0.
- `evidentia catalog list` now filters by `--tier` / `--category` /
  `--bundled-only` / `--user-only` and shows tier + category columns.
- `evidentia catalog show <fw> <ctrl>` renders
  `[Licensed — see <license_url>]` for Tier-C placeholder controls instead
  of the raw placeholder text.
- `platformdirs>=4.3` added as a `evidentia-core` runtime dependency
  (for user-catalog directory resolution).

### Infrastructure

- `scripts/catalogs/` now hosts compact Python generators (one per
  framework family) plus `regenerate_manifest.py` so `frameworks.yaml` is
  built from what's actually on disk.
- v0.2.1 roadmap: upstream fetch adapters (`scripts/catalogs/upstream/`)
  and GitHub Actions cron workflow (`.github/workflows/catalog-refresh.yml`)
  for auto-detecting upstream drift and opening tracking issues.

## [0.1.2] - 2026-04-16

Version-reporting truth-up patch. Follow-up to v0.1.1. No functional
changes — the installed packages already reported their real versions
to package managers (`pip show`, PyPI metadata); this patch fixes the
version strings that Evidentia itself prints and embeds in
exported artifacts.

### Fixed

- `evidentia version` CLI output reported `"0.1.0"` regardless of
  which version was actually installed, because every package's
  `__version__` was a hardcoded string literal. All five `__init__.py`
  modules now resolve `__version__` from `importlib.metadata` at
  import time — the reported version always matches the installed
  wheel and will never drift again.
- `GapReport.evidentia_version`, `RiskRegister.evidentia_version`,
  and `EvidenceBundle.evidentia_version` all defaulted to `"0.1.0"`.
  They now use a `default_factory` that resolves the live
  `evidentia-core` version, so exported audit artifacts accurately
  record the version that produced them.

### Added

- `evidentia_core.models.common.current_version()` helper that
  returns the installed `evidentia-core` version, used as the
  `default_factory` for all report-stamp fields.

## [0.1.1] - 2026-04-16

Legal remediation + registry truth-up patch. No API breakage — all changes
are additive optional fields on existing models. The **v0.2.0 big-bang
Phase 1.5 release** (exhaustive framework expansion to ~50 frameworks
across four redistribution tiers, plus `evidentia catalog import`
for user-supplied licensed content, plus GitHub Actions refresh CI)
follows this patch.

### Fixed

- **SOC 2 TSC catalog replaced with Tier-C stub.** The v0.1.0 bundled
  `soc2-tsc.json` contained 12 paraphrased AICPA criteria whose titles
  closely mirrored the copyrighted AICPA Trust Services Criteria 2017
  text and embedded references to COSO Internal Control Integrated
  Framework principles. That content is removed. The stub ships 61
  criteria (CC1.1–CC9.2, A1.1–A1.3, C1.1–C1.2, P1.1–P8.1, PI1.1–PI1.5)
  with generic titles ("Common Criteria 6.1" rather than AICPA's full
  phrasing), `placeholder: true` on every entry, and a `license_url`
  pointing to the AICPA download page. `evidentia catalog show
  soc2-tsc CC6.1` now renders `[Licensed content — see license_url for
  authoritative text.]` rather than a paraphrase. v0.2.0 will add
  `evidentia catalog import` so users can load their own licensed
  copy without touching the installed package.
- **Bundled `nist-800-53-rev5_to_soc2-tsc.json` crosswalk** had the same
  AICPA-paraphrase exposure in `target_control_title` fields; those are
  now the generic stub titles matching the stub catalog. The 17
  source↔target mappings themselves are unchanged — the mapping concept
  (e.g., NIST AC-2 relates to SOC 2 CC6.1) is factual and uncopyrightable.
- **Registry no longer advertises 7 framework IDs with no backing data.**
  `FRAMEWORK_METADATA` in v0.1.0 listed 9 frameworks (`nist-800-53-rev5`,
  `nist-800-53-mod`, `nist-800-53-high`, `nist-csf-2.0`, `soc2-tsc`,
  `iso27001-2022`, `cis-controls-v8`, `cmmc-2-level2`, `pci-dss-4`) but
  only 2 had catalog JSON on disk. `evidentia catalog list` produced
  7 "loaded: no" rows — misleading for a GRC tool whose users need to
  trust stated coverage. `FRAMEWORK_METADATA`, the `framework_files`
  dispatch in `loader.py`, and the `FrameworkId` enum are all trimmed
  to the 2 backed frameworks (`nist-800-53-mod`, `soc2-tsc`). `doctor`
  output now reports 2 frameworks, matching reality.
- **README "9 registered frameworks" claim corrected** to "2 bundled"
  with an explicit Tier-A/Tier-C explanation and a pointer to the v0.2.0
  roadmap.

### Added

- Optional fields on `CatalogControl`: `tier` (`"A"` through `"D"`),
  `license_required`, `license_url`, `placeholder`. All default to safe
  values; existing catalog JSONs continue to parse under `extra="forbid"`.
- Optional fields on `ControlCatalog`: same four plus `license_terms`
  (human-readable description of licensing constraints).
- New test `test_load_bundled_soc2_catalog_is_licensed_stub` locks in
  the Tier-C stub shape so a future accidental re-add of paraphrased
  AICPA content trips the test suite.

### Changed

- `FrameworkId` enum in `evidentia_core.models.common` trimmed to
  `NIST_800_53_MOD` and `SOC2_TSC`. Callers using free-form `str`
  framework IDs (via `ControlMapping.framework`) are unaffected. The
  enum itself will be deprecated in v0.2.0 in favor of a
  manifest-driven registry and removed in v0.3.0.

## [0.1.0] - 2026-04-16

Initial release: **Phase 1 MVP** — a working, tested, end-to-end gap analyzer
with AI risk statement generation. Evidentia is an open-source,
Python-first GRC platform that treats compliance as a software problem:
composable libraries, structured data, open standards (OSCAL), and AI only
where language understanding is the bottleneck.

### Added

- **uv workspace monorepo** with 5 packages: `evidentia-core`,
  `evidentia-ai`, `evidentia-collectors`, `evidentia-integrations`,
  and the `evidentia` CLI meta-package
- **Pydantic v2 data models** for controls, catalogs, gaps, risks, evidence,
  and findings
- **OSCAL catalog loader and crosswalk engine** with 9 registered frameworks
  and bundled NIST 800-53 Moderate + SOC 2 TSC catalogs
- **Multi-format inventory parser** supporting YAML, CSV (with fuzzy header
  matching), OSCAL component-definition, and CISO Assistant export formats
- **Gap analyzer** with severity calculation, effort-weighted priority
  scoring, and cross-framework efficiency analysis
- **Four report exporters**: JSON, CSV, Markdown, OSCAL Assessment Results
- **AI Risk Statement Generator** (NIST SP 800-30 Rev 1) using LiteLLM +
  Instructor for provider-agnostic structured LLM output
- **Typer + Rich CLI**: `init`, `catalog` (list/show/crosswalk), `gap analyze`,
  `risk generate`, `doctor`, `version`
- **End-to-end walkthrough sample** (Meridian Financial fintech scenario)
  exercising every feature with 20 controls across two frameworks
- **22 passing pytest tests** covering models, catalogs, crosswalks,
  multi-format parsing, gap scoring, and all four exporters
- **GitHub Actions CI** (pytest matrix on ubuntu/windows/macos + ruff lint)
- **Code of Conduct** (Contributor Covenant v2.1 by reference),
  `CONTRIBUTING.md`, and issue templates

### Known limitations (intentional Phase 1 scope)

- Evidence collectors for AWS, GitHub, Okta, Azure, GCP — planned for Phase 2
- Jira and ServiceNow push integrations — planned for Phase 2
- LLM-based evidence validation — planned for Phase 3
- FastAPI REST server and web UI — planned for Phase 4
- Production-sized OSCAL catalogs: the bundled NIST 800-53 Moderate catalog
  has 16 hand-curated controls for demonstration, not the full ~323 from the
  NIST OSCAL content repo — planned for Phase 1.5

[Unreleased]: https://github.com/allenfbyrd/evidentia/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/allenfbyrd/evidentia/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/allenfbyrd/evidentia/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/allenfbyrd/evidentia/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/allenfbyrd/evidentia/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/allenfbyrd/evidentia/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/allenfbyrd/evidentia/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/allenfbyrd/evidentia/releases/tag/v0.1.0
