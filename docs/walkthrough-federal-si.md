# Federal-SI walk-through (v0.9.4 P3.1)

> Operator persona: federal Systems Integrator (SI) procurement
> officer at a CSP candidate. Walks the operator through a realistic
> compliance + AI-governance workflow against synthetic fixtures in
> `tests/data/walkthrough-federal-si/`.
>
> Deferred since v0.9.0 §31.A. v0.9.4 P3.1 ships the synthetic data
> + this recipe doc; smoke-tested by
> `tests/integration/test_walkthrough_federal_si.py`.

## Why this walk-through exists

The federal SI buyer persona is a compliance-engineer adjacent
role responsible for both:

1. **Continuous compliance** for the SI's own SaaS / cloud
   infrastructure (FedRAMP ConMon, NIST 800-53 CA-7, DoD RMF
   annual review)
2. **AI-governance attestation** for AI/ML systems the SI
   deploys to support federal contracts (EU AI Act tier
   classification + ISO 42001 readiness + NIST AI RMF mapping)

Both surfaces have hard deadlines (FedRAMP ConMon monthly
attestation, EU AI Act Article 50 high-risk obligations Aug 2026)
and overlap heavily for an SI shipping AI-powered systems into
regulated environments.

The walk-through demonstrates Evidentia's end-to-end coverage of
the SI's typical day-to-day in 7 steps. Each step has expected
output documented so an operator can spot a regression without
needing to know the internal data model.

## Pre-requisites

```bash
pip install evidentia
# Optional: containerized for FedRAMP-High air-gap compatibility
docker pull ghcr.io/polycentric-labs/evidentia:v0.9.4
```

## Step 1 — Confirm catalogs

```bash
evidentia catalog list | grep -E "(nist|fedramp|nist-ai-rmf|eu-ai-act)"
```

**Expected**: at minimum the bundled NIST 800-53 Rev 5, FedRAMP
overlay, NIST AI RMF 1.0, EU AI Act statutory excerpts. Evidentia
ships 89 framework catalogs by default; this filter narrows to the
ones the SI workflow exercises.

## Step 2 — Run CONMON cycle check

```bash
evidentia conmon check \
  --state-file tests/data/walkthrough-federal-si/state.yaml \
  --today 2026-05-18
```

**Expected**: 1 OVERDUE cadence (`nist-800-53-rev5-ca7` last
completed 2026-03-15, monthly cadence → ~33 days past due),
1 DUE_SOON cadence (`fedramp-conmon-poam` due ~end-of-May),
5 CURRENT cadences.

If you have a daemon running, run instead:

```bash
evidentia conmon watch --poll \
  --state-file tests/data/walkthrough-federal-si/state.yaml \
  --poll-interval 60 \
  --window-days 14 \
  --status-file /tmp/conmon-daemon.status.json \
  --state-lock
```

— with the v0.9.4 `--state-lock` flag for safe concurrent
`mark-completed` invocations, and `--status-file` for the
companion `GET /api/conmon/daemon-status` health-check endpoint.

## Step 3 — Compute framework health

```bash
evidentia conmon health \
  --state-file tests/data/walkthrough-federal-si/state.yaml \
  --today 2026-05-18 \
  --window-days 14 \
  --json
```

**Expected JSON shape**: per-framework attention-bucket counts +
overall health score. With the fixture, expect ~`0.857` overall
(6 of 7 not-overdue / 7 total).

## Step 4 — Classify AI systems against EU AI Act

```bash
# High-risk system (employment domain, Annex III)
evidentia ai-gov classify \
  --descriptor tests/data/walkthrough-federal-si/ai-systems.yaml \
  --json

# Compare against minimal-risk system
evidentia ai-gov classify \
  --descriptor tests/data/walkthrough-federal-si/ai-systems-low-risk.yaml \
  --json
```

**Expected**: first call returns `eu_ai_act_tier: "high"` (Annex
III employment domain + advisory decision role); second returns
`eu_ai_act_tier: "minimal"` (no Annex III; no natural-person
impact).

This is the classification call SIs make at procurement-evaluation
time when deciding which AI components a candidate vendor can
deploy into a federal environment.

## Step 5 — Register AI systems

```bash
EVIDENTIA_AI_REGISTRY_DIR=/tmp/walkthrough-federal-si-registry \
evidentia ai-gov register \
  --descriptor tests/data/walkthrough-federal-si/ai-systems.yaml \
  --provider acme-ai \
  --owner federal-si-hr-team \
  --deployment-status pilot
```

**Expected**: `Registered AI system: federal-si-resume-screener`
+ a UUID `system_id`. The registry-store sidecar `_idempotency.json`
also tracks any `X-Idempotency-Key` headers if the same call is
re-issued via the REST surface (v0.9.4 P1.3).

## Step 6 — List registered AI systems

```bash
EVIDENTIA_AI_REGISTRY_DIR=/tmp/walkthrough-federal-si-registry \
evidentia ai-gov list --tier high --json
```

**Expected**: array with one entry (the high-risk system just
registered) — confirms the tier filter works and the registry
persisted correctly.

## Step 7 — Lifecycle transitions

```bash
# Promote pilot → production after stakeholder review
EVIDENTIA_AI_REGISTRY_DIR=/tmp/walkthrough-federal-si-registry \
evidentia ai-gov update <system_id> --deployment-status production

# Retire after contract end (preserves history)
EVIDENTIA_AI_REGISTRY_DIR=/tmp/walkthrough-federal-si-registry \
evidentia ai-gov retire <system_id>
```

**Expected**: `Updated` then `Retired` messages. The entry stays in
the registry — `evidentia ai-gov show <system_id>` still resolves
with `deployment_status: "retired"`. Auditors investigating a
historical AI deployment can still trace ownership + classification.

## What this walk-through validates

| Phase | Capability tested |
|---|---|
| 1 | Catalog discovery — 89 bundled frameworks load |
| 2 | CONMON cycle classification — overdue/due_soon bucketing |
| 3 | Framework health scoring — JSON output for SIEM ingest |
| 4 | EU AI Act tier classification — Annex III + risk attributes |
| 5 | AI registry persistence — file-backed atomic write |
| 6 | Registry query with tier filter — list_all + classification round-trip |
| 7 | Lifecycle CLI verbs (v0.9.4 P2.3) — update + retire firing audit events |

If any step diverges from "expected", file a v0.9.5 bug ticket with
the actual output. The integration test
`tests/integration/test_walkthrough_federal_si.py` runs steps 2-4
+ 6 in CI to catch regressions in the smoke surface; the full
end-to-end (including REST endpoints + daemon) is operator-driven.

## Future enhancements (v0.9.5+)

- POA&M generation from gap report against the walked-through
  inventory (v0.9.0 capability; not exercised here to keep the
  walk-through focused on v0.9.x deltas)
- OSCAL plan-of-action-and-milestones emit (v0.9.0 export path)
- Real federal-SI domain-expert review (the walk-through was
  designed without operator feedback; cycle-close for v0.9.5
  should solicit that)

## See also

- `tests/data/walkthrough-federal-si/README.md` — fixture provenance
- `docs/conmon-runbook.md` — CONMON operator workflows
- `docs/poam-runbook.md` — POA&M operator workflows
- `docs/conmon-daemon-deployment.md` — daemon deployment guide
