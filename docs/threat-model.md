# Evidentia threat model

> Public threat model for Evidentia, capturing the external input
> surfaces, the sanitization layers that protect them, and the
> currently-acknowledged gaps. Reviewed each release per
> [`docs/release-checklist.md`](release-checklist.md) Step 5;
> tracked alongside [`docs/enterprise-grade-accepted-findings.md`](enterprise-grade-accepted-findings.md)
> (the per-finding rationale appendix for static-analysis accepts).

**Last full deep-pass**: 2026-05-01 (v0.7.6 P1 Q2). 54 surfaces
walked across 5 tiers. **0 HIGH, 0 MEDIUM, 3 LOW** — all
design-choice or pre-existing intentional patterns. v0.7.5
sanitization patterns confirmed at every callsite.

---

## Why this doc exists

- Auditors + integrators get a single canonical place to map
  "what does Evidentia do with my data?" to "what stops it from
  doing the wrong thing?"
- Pre-release-review v4's G5 gate (CISA Secure by Design Pledge
  alignment) refuses to advance past Step 1 on a minor release
  if `docs/threat-model.md` is missing or > 180 days stale. This
  doc satisfies G5 ahead of the v0.8.0 minor.
- Future deep-pass reviews diff against this doc rather than
  starting from scratch — coverage decay shows up as new
  un-sanitized surfaces vs. the prior version.

---

## Trust boundaries

Evidentia runs on the operator's machine + their controlled
infrastructure. Trust boundaries cross at:

1. **CLI flags + arguments** (operator-controlled; trusted)
2. **Environment variables** (operator-controlled; trusted for
   config, gated for secrets — see "Secret handling" below)
3. **File system reads** (operator-controlled paths; resolved
   through `validate_within` for any user-controlled path)
4. **REST API request bodies** (browser / consumer / CI;
   semi-trusted — Pydantic-validated with `extra="forbid"`)
5. **OSCAL / YAML / JSON deserialization** (semi-trusted — safe
   parsers + strict Pydantic models; never `pickle`, never
   `yaml.unsafe_load`, never `eval`)
6. **Network egress** (LLM providers, Sigstore/Rekor, GitHub,
   PyPI; HTTPS-only with cert validation; air-gap mode refuses
   non-loopback)
7. **Subprocess execution** (only `gpg` for AR signature
   verification; always `shell=False`)

Trust ranks: CLI flags + env > file system > REST body > OSCAL
input > LLM response (treated as untrusted by contract — see
v0.8.0-plan §DFAH for the determinism harness).

---

## Surface coverage by tier

54 external input surfaces grouped into 5 tiers.

### Tier A — REST API request handlers (16 surfaces)

**Status**: clean. All Pydantic-protected with `extra="forbid"`.

- 16 REST endpoints under `/api/*` (POST `/api/gap/analyze`,
  POST `/api/risk/generate`, GET `/api/gap/diff`, etc.)
- Pydantic validation on every request body
- Path validation via `validate_within` for any file path or
  gap-store key flowing through the request
- Network guards on LLM `model` + `api_base` request fields via
  `evidentia_core.network_guard.check_llm_model()`
- CORS origin allowlist on the FastAPI app
- v0.7.5 R2 / `oscal verify` UX fix lives here — `/api/oscal/verify`
  now returns `PASS (no verification surface)` for metadata-only
  ARs instead of misleading FAIL

### Tier B — CLI + file deserialization (18 surfaces)

**Status**: clean. All using `safe_load` + Pydantic models.

- `evidentia gap analyze` (inventory path, findings, output,
  frameworks, organization, system_name, optional GPG signing)
- `evidentia risk generate` (gap report path, gap-id filter, model)
- `evidentia catalog` (load, upload, list, show)
- `evidentia config` (get, set, validate)
- `evidentia.yaml` parsing — `yaml.safe_load` + `EvidentiaConfig.model_validate`
- Bundled + user-imported catalogs via `resolve_catalog_path` with
  allowlist
- OSCAL Assessment Result deserialization via Pydantic models

### Tier C — Network egress + collector integration (10 surfaces)

**Status**: clean except for 1 LOW finding (informational; see
"Accepted findings" below).

- Collector credential env vars (`COLLECTOR_*`) — trusted import
  paths; per-variable character-set allowlist optional for v0.8.0
- LLM provider requests — fixed HTTPS endpoint per provider;
  model + api_base validated against network_guard
- Sigstore / Rekor verification — hardcoded HTTPS; offline-mode
  blocks
- GitHub releases API — hardcoded endpoint; offline-mode blocks
- Config `llm_api_base` validation via `network_guard.check_llm_model()`
- HTTP proxy configuration via standard Python env vars
- TLS certificate validation: `verify=True` default everywhere
- DNS resolution pre-flight via `is_loopback_or_private()` —
  enforces RFC-1918 / loopback-only when `--offline` is set

### Tier D — OSCAL deserialization + verification (7 surfaces)

**Status**: clean except for 1 LOW finding (legacy compatibility;
see "Accepted findings" below).

- OSCAL Catalog parsing (groups → controls → enhancements)
- OSCAL control prose extraction (recursive parts concatenation)
- OSCAL component-definition import
- CISO Assistant JSON export parsing
- Gap report (Assessment Result) loading + verification
- Per-resource SHA-256 digest verification
- GPG signature verification — `shell=False` subprocess to `gpg`

### Tier E — Internal data flow + context injection (3 surfaces)

**Status**: clean except for 1 LOW finding (deferred; see
"Accepted findings" below).

- Risk-context file path (`context_path` parameter)
- LLM prompt generation — structured data only; no free-text
  user prompts that could template-inject
- Evidence reference resolution — metadata annotations only; no
  external URL dereferencing

---

## v0.7.5 sanitization checklist (validated at every release)

- [x] Path-traversal protection via `validate_within()` at 14+
      callsites (added v0.7.5 S1; landed in
      `evidentia_core.security.paths`)
- [x] Request validation: Pydantic `extra="forbid"` on all REST
      schemas
- [x] Safe deserialization: `yaml.safe_load`, `json.load` +
      `model_validate` (never `pickle`, `eval`, `yaml.unsafe_load`)
- [x] Subprocess safety: `shell=False` on all calls (only `gpg`
      for AR signature verification)
- [x] LLM provider gating: `check_llm_model()` whitelist +
      `api_base` validation
- [x] Environment-variable interpolation: ReDoS-safe regex
      (bounded character class, not polynomial alternation; v0.7.5
      S2 fix in `evidentia_core/models/catalog.py`)
- [x] Gap-store key validation: 16-hex-character format enforced
      (no path injection)
- [x] Offline-mode enforcement: `network_guard.set_offline(True)`
      flips a process-wide flag that refuses non-loopback targets
- [x] Stack-trace redaction: API errors logged internally via
      `evidentia_core.audit.logger`, returned externally as generic
      500s correlated by `request_id` (v0.7.5 S3 fix in
      `routers/integrations.py`)

---

## Accepted findings

### LOW — informational / design-choice

The 3 LOW findings from the v0.7.6 deep-pass don't block release.
Each is documented for transparency:

#### C1 — Collector credential env scope (LOW)

- **Issue**: `COLLECTOR_*` environment variables lack a
  per-variable character-set allowlist. A malformed env value
  could pass through to the collector untouched.
- **Mitigation in place**: Collectors are trusted code paths.
  Users only run collectors against systems they own.
- **Action**: Document expected character set in collector docs;
  defer regex enforcement to v0.8.0 once the collector framework
  stabilizes around the v0.7.7 SQL-family additions.

#### D1 — Legacy gap-report `inventory_source` optional (LOW)

- **Issue**: Pre-v0.7.0 gap reports may lack the
  `inventory_source` field; the loader falls back to
  `organization`.
- **Mitigation in place**: Acceptable legacy support boundary.
  New reports (v0.7.0+) always populate `inventory_source`.
- **Action**: Continue accepting legacy reports through the
  v0.7.x line; v0.8.0 may deprecate the fallback path with a
  one-release migration window.

#### E1 — `context_path` validation deferred (LOW)

- **Issue**: The `context_path` parameter passed to
  `RiskStatementGenerator` is validated by Typer at the CLI
  boundary but not by `validate_within` at the REST API
  boundary.
- **Mitigation in place**: The REST `/api/risk/generate` handler
  has Pydantic schema validation; the path itself goes to a
  read-only generator. CLI usage is fully validated.
- **Action**: Add `validate_within(STATIC_DIR)` to the REST
  handler in v0.8.0 alongside the AI-moat hardening work
  ([`v0.8.0-plan.md`](v0.8.0-plan.md) §P0).

### Static-analysis accepts (Scorecard + CodeQL)

See [`docs/enterprise-grade-accepted-findings.md`](enterprise-grade-accepted-findings.md)
for the per-alert rationale on:
- 3 CodeQL `py/path-injection` false positives on the
  `validate_within` sanitizer (#71/#72/#73). Long-term fix
  in v0.7.7 CF3: contribute a custom CodeQL pack declaring
  `validate_within` as a `BarrierGuard`.
- 2 OpenSSF Scorecard accepts: `contents: write` for release-
  notes append (#75 + pre-existing #29/#30) +
  `Pinned-Dependencies` `==X.Y.Z` PyPI pin (#74).

---

## Out of scope

These categories are **not** addressed by this threat model:

- **Supply-chain attacks**: covered separately by the SLSA L3 +
  PEP 740 + cosign + CycloneDX SBOM chain documented in
  [`enterprise-grade.md`](enterprise-grade.md) §HIGH and the
  [`sigstore-quickstart.md`](sigstore-quickstart.md) walkthrough.
- **LLM injection / AI-moat threats**: AI features are designed
  by-contract to treat LLM output as untrusted. Determinism +
  policy-reasoning-trace work for v0.8.0 (DFAH + PRT per
  [`v0.8.0-plan.md`](v0.8.0-plan.md)) hardens this surface.
- **Social engineering** on individual operators
- **Physical security** of operator workstations
- **Denial of service** under sustained load — covered separately
  by [`benchmarks.md`](benchmarks.md) (perf budget) + future
  rate-limiting work in v0.8.0
- **Side-channel attacks** on cryptographic primitives — relies
  on the standard-library + `cryptography` package guarantees
- **Cryptographic key rotation cadence** — covered by the
  release-checklist secret-rotation row + Sigstore short-lived
  cert model

---

## v0.7.9 attack-surface delta (SHIPPED 2026-05-04 at tag `v0.7.9`)

The v0.7.9 ship adds **12 new public surfaces** across the TPRM
module + the vendor-risk-collector quartet + OSCAL TPRM emit.
All inherit the established defense baseline (Pydantic
`extra="forbid"`; `validate_within` for path inputs; UUID-shape
validation for IDs; manual `HTTPException(400, ...)` for runtime
body errors per the v0.7.8 F-V08-DAST-3 invariant; never accept
secrets via CLI args or REST request bodies; env-var-only
credential sourcing per CLAUDE.md secret-handling protocol).
Specific new surfaces + their hardening:

### P0.1 — TPRM vendor inventory (CLI + REST + storage)

5 new CLI verbs (`evidentia tprm vendor add/list/show/edit/
delete`), 5 new REST endpoints (`/api/tprm/vendors` CRUD + cadence
preview), and JSON-file persistence under platformdirs-backed
user-dir. Surfaces inherit `validate_within` + UUID-shape
validation; manual `HTTPException` preserves F-V08-DAST-3 invariant.
REST `create_vendor`/`replace_vendor` operate on
`model_copy(update=...)` of the request DTO rather than mutating
it directly (closes Continuous-review H-3). `save_vendor` writes
atomically via tmp-file + `os.replace` (M-1 fix). `EvidenceRef`
enforces its two-mode contract (artifact_id OR file_path+sha256)
via `@model_validator` (H-1 fix).

### P0.2 — Due-diligence questionnaire generator + ingest

`evidentia tprm dd-questionnaire generate/ingest` CLI + 1 REST
endpoint. 5 input formats (evidentia-generic / caiq-lite /
caiq-full all packaged + sig / sig-lite via `--from-template`
BYO XLSX). 3 output formats (JSON / CSV / XLSX behind new
`[xlsx]` extra). Hardening:

- **CSV-injection defense** (CWE-1236) on every operator-supplied
  user-content cell (vendor name, fourth-party names, region,
  relationship_owner, regulatory_classification, question_text,
  notes) via `_csv_safe()` OWASP single-quote prefix. Same
  defense applied to XLSX render path as defense-in-depth even
  though XLSX doesn't auto-evaluate formulas the way CSV
  spreadsheet importers do.
- **Format-string foot-gun** closed: `title_template.replace(
  "{vendor_name}", vendor.name)` instead of
  `title_template.format(vendor_name=...)` so a vendor name
  containing `{}` / `{0}` / `{secret}` cannot raise KeyError or
  walk format args (P0.3+P0.2-first Continuous H-3 fix).
- **Ingest deserialization safety**: `json.loads` (CWE-502-safe;
  never `pickle.loads` / `yaml.unsafe_load`); `csv.reader` (safe);
  `openpyxl.load_workbook(data_only=True)` (no formula evaluation;
  no VBA macro execution per openpyxl's documented behavior).
- **SIG BYO XLSX template path**: CLI-only (no REST exposure).
  Operator-supplied path validated via Typer's `exists=True`;
  uses `Path` typing; openpyxl's read does not auto-execute
  macros.

### P0.3 — Concentration-risk reporting

`evidentia tprm concentration-report` CLI + 1 REST endpoint;
6 dimensions; HTML/JSON/CSV outputs. Hardening:

- **HTML XSS-safe** via `html.escape` on every operator-supplied
  vendor + value name (Continuous H-1 fix). Single-file output
  (no JS deps; sortable tables via inline click-to-sort JS that
  doesn't execute user content).
- **CSV-injection defense** (`_csv_safe`) on user-content cells.
- **Cloud-provider direct-vs-4P collision** resolved with
  `(direct)`/`(4th-party)` source suffix so two vendors with the
  same name (one `vendor.type==cloud_provider` + one disclosed
  as a 4th-party of another vendor) don't silently overwrite each
  other in the aggregate (Continuous H-2 fix).

### P0.4 — Vendor-risk SaaS collectors (Vanta + Drata + BitSight + SecurityScorecard)

4 new CLI commands (`evidentia collect {vanta,drata,bitsight,
securityscorecard}`) + 4 new REST endpoints + 4 status-endpoint
extensions. All read-only against the upstream vendor APIs.
Hardening:

- **Token sourcing**: env-var only (`VANTA_API_TOKEN` /
  `DRATA_API_TOKEN` / `BITSIGHT_API_TOKEN` /
  `SECURITYSCORECARD_API_TOKEN`); never accepted via CLI args or
  REST request bodies; never echoed in log messages or error
  responses.
- **Auth header diversity**: Vanta + Drata use `Authorization:
  Bearer <token>`; BitSight uses HTTP Basic with token-as-username
  + empty password (wrapped internally; never in URLs); SSC uses
  `Authorization: Token <value>`. Each collector's `_ensure_client`
  builds the header in code, not via URL params.
- **Cross-host pagination guards** (Vanta + Drata + BitSight + SSC):
  `_paginate` refuses to follow `next` URLs pointing off-host
  (CWE-319 cross-host info-leak defense). BitSight additionally
  refuses scheme-downgrade (HTTPS→HTTP) `next` URLs to prevent a
  malicious upstream from leaking the HTTP Basic auth header
  over cleartext HTTP (Continuous F-V09-S1 fix per CWE-319
  cleartext transmission).
- **Stuck-cursor guards** (Vanta + Drata + SSC): if upstream API
  returns the same `endCursor` / `nextPageToken` twice or fails
  the monotonic-output-grew check, loop terminates instead of
  running to the `max_vendors`/`max_companies` cap (Continuous
  H-1 / H-3 fixes).
- **Explicit-key payload-priority** (Drata + SSC): rejects
  fall-through `data.get("data") or data.get("results") or []`
  patterns that mishandle legitimate `{"data": []}` empty pages
  (Continuous H-2 fix per CWE-697).
- **Defensive field-shape detection**: each collector's
  `_is_high_risk` / low-rating detector covers 4-6 documented +
  de-facto API field-shape variants. `BLIND_SPOTS` documents
  the field-shape uncertainty for auditor-grade transparency.

### P0.5 — OSCAL TPRM emit

Extends `evidentia_core.oscal.exporter.gap_report_to_oscal_ar()`
+ adds `--vendor-inventory` flag on `evidentia gap analyze`.
Hardening:

- **Tamper-evident vendor records**: each Vendor lands in
  `back-matter.resources[]` with canonical-JSON `base64.value` +
  SHA-256 `rlinks[].hashes[]`. Same integrity model as the v0.7.0
  finding-resource embedding — tampering with vendor record
  changes hash + fails `evidentia oscal verify`.
- **Deterministic canonical JSON**: `json.dumps(sort_keys=True,
  separators=(",", ":"))` so verifier-side recompute is
  bit-for-bit reproducible.
- **Cross-reference resolution**: vendor's party UUID +
  back-matter resource UUID both equal `Vendor.id` so
  `href: "#<vendor-id>"` references resolve intra-document.

### Defense-in-depth: security-headers middleware

A response-headers middleware
(`evidentia_api.security_headers.SecurityHeadersMiddleware`)
landed in this cycle, closing the v0.7.8 Step 5.A deferred
F-V08-DAST-2 LOW finding (CWE-693). When enabled, every response
carries Content-Security-Policy (locks loads to same-origin;
`frame-ancestors 'none'`), X-Frame-Options DENY, X-Content-Type-
Options nosniff, Referrer-Policy strict-origin-when-cross-origin,
Strict-Transport-Security one year + subdomains, and Permissions-
Policy denying camera/microphone/geolocation/payment/USB/FLoC.
The new `--security-headers / --no-security-headers` flag on
`evidentia serve` defaults to auto — ON for non-loopback binds,
OFF for localhost (dev-loop parity). Operators behind a TLS-
terminating reverse proxy that already injects these headers can
suppress duplicates via `--no-security-headers`.

### v0.7.8 carry-over hardening

- **Snowflake quoted-identifier escape** via `_quote_snowflake_
  identifier()` static helper (Snowflake's documented double-up
  convention; defensive against operator-controlled inputs in
  third-party-managed Snowflake accounts).
- **Snowflake masking-policy + row-access-policy count separation**:
  manifest reflects distinct CoverageCount per evidence source.
- **Databricks PermissionDenied typed catch** replaces v0.7.8
  message-string heuristic with `databricks.sdk.errors.
  PermissionDenied` + `Unauthenticated`. ImportError-safe
  fallback to v0.7.8 heuristic on older SDK.
- **Power BI 1MB byte-cap guard**: `push_rows()` bisects batches
  exceeding 950 KB headroom (Power BI's documented 1 MB body
  limit). Single-row exceedance raises clear `PowerBIPublishError`.

## Hardening backlog

### v0.7.7 (shipped)

- **CF3** — CodeQL custom sanitizer pack: contribute a `.qll`
  declaring `validate_within` as a `BarrierGuard` to close the
  3 path-injection false positives (#71/#72/#73) at the analysis
  layer rather than dismissing each instance.
- **CF4** (this doc) — public threat model elevation. ✅
- **C1 partial** — character-set regex allowlist for `COLLECTOR_*`
  env vars (optional; depends on cycle headroom alongside the
  5 SQL adapters).

### v0.7.9 (in motion)

- **F-V08-DAST-2** — defense-in-depth response headers via
  `SecurityHeadersMiddleware`. ✅ (this doc + CHANGELOG entry).
- **TPRM data-layer hardening** — atomic write semantics in
  `vendor_store.save_vendor`; UUID-shape ID validation +
  `validate_within` belt-and-suspenders; FastAPI `model_copy`
  semantic in REST handlers; `@model_validator` enforcement on
  `EvidenceRef` two-mode reference contract. ✅ (P0.1 first
  slice + Continuous-review fixes).
- **F-V08-CR-MEDIUM Snowflake quoted-identifier hardening** —
  carry-over from v0.7.8 deferred list; theoretical
  (Snowflake doesn't allow `"` in db names by convention) but
  defensive. Lands alongside any P1 Snowflake catalog work.
- **F-V08-CR-MEDIUM Power BI 1MB-per-batch byte guard** —
  carry-over from v0.7.8 deferred list. Lands during P3 docs.

### v0.8.0 (queued)

- **E1** — `validate_within(STATIC_DIR)` on REST
  `/api/risk/generate` handler.
- Rate-limit enforcement on REST endpoints.
- Telemetry opt-out mechanism.
- AI-moat hardening: DFAH determinism harness + PRT policy
  reasoning traces + plugin contract for out-of-tree extensions.

### v0.9.0+ (open)

- WORM evidence retention backends (S3 Object Lock / Azure
  Immutable Blob / GCS Bucket Lock) per
  [`v0.7.9-plan.md`](v0.7.9-plan.md) P2.
- Continuous Monitoring (CONMON) capability surface for federal
  compliance per the domain-expert input log.

---

## Review cadence

This doc is reviewed at every release per
[`release-checklist.md`](release-checklist.md) Step 5. A full
deep-pass walk (re-walk of every external input surface, not just
diff scope) runs at every minor release per pre-release-review
v4 §G5 + on a quarterly cadence regardless of release activity
per Step 11.

---

*First published v0.7.7 (2026-05). Origin: promoted from a
project-internal deep-pass note to a public-surface doc to
satisfy pre-release-review v4 G5 (threat-model existence gate)
ahead of the v0.8.0 minor release. The internal note remains in
`.local/` for cycle-by-cycle drafting; the public doc here is the
canonical reference for auditors + integrators.*
