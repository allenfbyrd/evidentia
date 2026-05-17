# Federal-SI walk-through fixtures (v0.9.4 P3.1)

Synthetic test data backing the federal-SI walk-through scenario
captured in [`docs/walkthrough-federal-si.md`](../../../docs/walkthrough-federal-si.md).

## Contents

| File | Purpose |
|---|---|
| `state.yaml` | CONMON state with 7 cadences in mixed attention buckets (1 overdue, 1 due_soon, 5 current) relative to a 2026-05-18 reference date |
| `ai-systems.yaml` | High-risk AI system descriptor (Annex III employment) → classifies as `EUAIActTier.HIGH` |
| `ai-systems-low-risk.yaml` | Minimal-risk AI system descriptor → classifies as `EUAIActTier.MINIMAL` |

## Provenance

All data is **synthetic** — created for the v0.9.4 walk-through.
NO real customer data, NO real federal-SI procurement records,
NO real PII. Names + organizations are fictional.

## Usage

See the recipe doc + the smoke test at
`tests/integration/test_walkthrough_federal_si.py`.
