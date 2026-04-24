# Evidentia structured log schema (v0.7.0)

Evidentia emits machine-readable audit logs conforming to three
authorities:

- **Elastic Common Schema (ECS) 8.11** — the de-facto SIEM interchange
  format. Splunk, Elastic, Datadog, Sumo Logic, and Microsoft Sentinel
  ingest ECS without custom parsers.
- **NIST SP 800-53 Rev 5 AU-3** (Content of Audit Records) — the
  federal audit-content requirement: *what, when, where, source,
  outcome, identity*.
- **OpenTelemetry Logs Data Model v1.31** — correlation fields
  (`trace.id`, `span.id`) for cross-referencing logs, metrics, and
  traces.

## Two output modes

| Mode | Trigger | Use case |
|---|---|---|
| **Rich console** (default) | No flag | Interactive CLI runs |
| **ECS JSON** | `--json-logs` CLI flag or `evidentia_core.audit.enable_json_logs()` | SIEM ingestion, CI, long-term log storage |

Both modes emit the same events; only the encoding differs.

## Example record

```json
{
  "@timestamp": "2026-04-24T14:28:36.123Z",
  "ecs": {"version": "8.11"},
  "log": {
    "level": "info",
    "logger": "evidentia.collectors.aws.access_analyzer"
  },
  "message": "Retrieved 42 Access Analyzer findings from us-east-1",

  "event": {
    "kind": "event",
    "category": ["configuration", "iam"],
    "type": ["info"],
    "action": "evidentia.collect.finding_retrieved",
    "outcome": "success",
    "id": "01HXYZ7K8N2M3P4Q5R6S7T8U9V",
    "start": "2026-04-24T14:28:36.123Z",
    "end": "2026-04-24T14:28:36.265Z",
    "duration": 142000000,
    "dataset": "evidentia.audit"
  },

  "service": {
    "name": "evidentia",
    "version": "0.7.0",
    "type": "grc"
  },

  "host": {
    "hostname": "collector-01.example.com"
  },

  "trace": {"id": "01KPXRYJVQ0BNNHTC8TC3GXC2V"},
  "span": {"id": "5f6e7d8c9b0a1b2c"},

  "user": {
    "id": "arn:aws:iam::123456789012:role/grc-read-only-collector",
    "domain": "aws"
  },

  "cloud": {
    "provider": "aws",
    "account": {"id": "123456789012"},
    "region": "us-east-1"
  },

  "evidentia": {
    "run_id": "01KPXRYJVQ0BNNHTC8TC3GXC2V",
    "collector": {"id": "aws-access-analyzer", "version": "0.7.0"},
    "analyzer_arn": "arn:aws:access-analyzer:us-east-1:…:analyzer/grc",
    "findings_count": 42
  }
}
```

## NIST AU-3 field mapping

| AU-3 requirement | Evidentia fields |
|---|---|
| **What** | `event.action` + `event.category` |
| **When** | `@timestamp` + `event.start` + `event.end` |
| **Where** | `host.*` + `cloud.*` |
| **Source** | `service.name` + `log.logger` |
| **Outcome** | `event.outcome` (success / failure / unknown) |
| **Identity** | `user.id` + `user.domain` |

## Event catalog

Every `event.action` value is drawn from a curated enum
(`evidentia_core.audit.events.EventAction`). Unknown actions are
accepted but tagged with a warning, so the vocabulary can grow
without breaking consumers.

### `evidentia.collect.*` — collection lifecycle

| Action | When emitted |
|---|---|
| `evidentia.collect.started` | Collector begins a run |
| `evidentia.collect.finding_retrieved` | Each finding pulled from source |
| `evidentia.collect.finding_skipped` | Finding filtered out |
| `evidentia.collect.page_fetched` | Pagination page loaded |
| `evidentia.collect.retry` | Retry attempt after transient failure |
| `evidentia.collect.completed` | Run finished cleanly |
| `evidentia.collect.failed` | Run finished with unrecoverable error |
| `evidentia.collect.aborted` | Operator or safety-cap terminated run |

### `evidentia.auth.*` — credential events

| Action | When emitted |
|---|---|
| `evidentia.auth.credential_resolved` | Principal identified from SDK chain |
| `evidentia.auth.credential_refresh` | Token renewed mid-run |
| `evidentia.auth.credential_failed` | Auth lookup failed (falls back to placeholder) |

### `evidentia.config.*` — configuration events

| Action | When emitted |
|---|---|
| `evidentia.config.loaded` | `evidentia.yaml` parsed |
| `evidentia.config.resolved` | Precedence chain applied (CLI > env > yaml > default) |
| `evidentia.config.override_applied` | Operator-supplied override took effect |
| `evidentia.config.invalid` | Config validation failed |

### `evidentia.sign.*` / `evidentia.verify.*` — signing lifecycle

| Action | When emitted |
|---|---|
| `evidentia.sign.gpg_signed` | GPG signature produced |
| `evidentia.sign.sigstore_signed` | Sigstore bundle produced |
| `evidentia.sign.sigstore_skipped_airgap` | Sigstore refused in air-gap mode |
| `evidentia.sign.signing_failed` | Signing raised an error |
| `evidentia.verify.started` | Verification run begins |
| `evidentia.verify.digest_passed` / `digest_failed` | Per-resource digest check |
| `evidentia.verify.signature_passed` / `signature_failed` | Signature check |
| `evidentia.verify.completed` | Verification done |

### `evidentia.manifest.*` — completeness attestation

| Action | When emitted |
|---|---|
| `evidentia.manifest.generated` | CollectionManifest written |
| `evidentia.manifest.empty_set_attested` | Scanned category returned zero findings (explicit empty-set claim per B5) |
| `evidentia.manifest.incomplete` | Run marked `is_complete=False` |

## Secret scrubbing

Before emission, `message` strings pass through a regex-based scrubber
that redacts:

- AWS access key IDs (`AKIA*`, `ASIA*`, 20 chars total)
- GitHub tokens (`ghp_*`, `gho_*`, `ghu_*`, `ghs_*`, `ghr_*` + 36 chars)
- Generic `password=`, `token=`, `api_key=`, `secret=`, `credential=` shapes ≥8 chars
- JWTs (three base64url segments separated by dots)

Matched strings are replaced with `[REDACTED]`. The scrubber is a
safety net — collectors are responsible for keeping secrets out of
structured field values (not logged as strings).

## Trace correlation

A collection run begins with `new_run_id()` (26-char ULID). That
run_id flows into every emitted event's `trace.id` via
`log.scope(trace_id=run_id)`. Operators querying SIEM by `trace.id`
retrieve every event from that run, across retries and sub-collectors,
in chronological order (ULID's 48-bit timestamp prefix makes them
sortable even when `@timestamp` resolution collides).

## Configuration

```bash
# CLI flag (one-shot)
evidentia --json-logs collect aws

# Python API
from evidentia_core.audit import enable_json_logs
enable_json_logs(stream=sys.stderr)
```

JSON logs emit to `stderr` by default so they don't contaminate stdout
(which CLI commands use for primary output).

## Test mode

Set `EVIDENTIA_TEST_MODE=1` to zero out retry backoff — used by the
test suite to keep `@with_retry` tests fast. Production should never
set this.
