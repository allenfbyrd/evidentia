# Security review — v0.9.8

> **Status**: in-cycle artifact for the v0.9.8 ship. The v4
> pre-release-review's 5th canonical deliverable (see
> `pre-release-review/references/deliverables.md`). v0.9.8 was
> reviewed in two passes across two sessions; this doc consolidates
> both.
>
> **Theme**: v0.9.7 deferral closure + v1.0-prep integration wiring.

## Cycle scope

v0.9.8 wires v0.9.7's data/decision-only primitives into live CLI,
REST, MCP-dispatch, and storage surfaces — multi-tenant RBAC
enforced end-to-end, MCP tool outputs signed at the FastMCP
dispatch layer, an in-tree Sigstore-keyless reference signer — then
closes the CR-V97 review polish and clears a class of supply-chain
and type-safety gaps surfaced during the pre-tag review.

## Review structure

| Pass | Commits | Scope | Verdict |
|---|---|---|---|
| 1 — feature work | `71eb5e6..176eb51` (5) | Full pre-release-review of the integration features (prior session) | PROCEED-CLEAN |
| 2 — supply-chain + type-safety delta | `7b55c6d..7374635` (5) | Focused delta pass over the commits added after Pass 1 | PROCEED-CLEAN |

## Findings ledger

### Pass 1 — feature-work review

Findings as reported by the Pass 1 session's pre-release-review;
granular CVSS / CWE / EPSS scoring is held in that session's
per-run log.

| Finding | Severity | Status |
|---|---|---|
| F-V98-01 — the FastMCP dispatch-signing wrapper mishandled FastMCP 1.27's `(unstructured, structured)` tuple return, breaking every MCP tool call when signing was enabled; the unit tests stubbed `call_tool` with bare values and never exercised the real contract | CRITICAL | FIXED in-cycle — the signature now rides in `CallToolResult._meta` as additive provenance, leaving tool output untouched; 2 real-FastMCP integration tests added to close the coverage gap |
| F-V98-02 — the FastAPI RBAC layer never constructed a multi-tenant policy from the resolved tenant claim | HIGH | FIXED in-cycle via a shared `load_rbac_policy_auto` so CLI and REST classify a policy file identically |
| 3× MEDIUM / LOW batch | MEDIUM / LOW | all FIXED in-cycle |

### Pass 2 — supply-chain + type-safety delta review

Zero findings across all four buckets. Pass 2 reviewed all 5 delta
commits per-commit + 1-hop dependency closure (scope: diff +
dependency closure). The delta is a CVE-removing dependency bump,
two identical sigstore-4.2.0 API-rename migrations, a
type-narrowing assert, a CI-gate strengthening, and the
`chore(release)` commit — no new attack surface, no logic change to
any security-relevant path.

| Finding | Severity | Status |
|---|---|---|
| (none) | — | Zero CRITICAL / HIGH / MEDIUM / LOW |

### Carry-over disposition

| Finding | Severity | Disposition |
|---|---|---|
| F-V97-mcp-signer-trust | INFO | **CLOSED** — v0.9.8 P1.2 ships the in-tree Sigstore-keyless reference signer, removing operator-managed key material from the trust path |
| F-V97-multi-tenant-claim-spoofing | INFO | **CLOSED** — v0.9.8 P1.4 derives the tenant claim from the authenticated principal, not operator-asserted env input |
| idna CVE-2026-45409 | MEDIUM | **CLOSED** — idna 3.11 → 3.15 (Pass 2 commit `7b55c6d`) |
| paramiko CVE-2026-44405 | LOW | **CARRY-FORWARD → v0.9.9** — a fix now exists upstream (paramiko 5.0.0, unblocked by compliance-trestle 4.0.3); deferred as its own focused major-version SSH-library bump rather than a release-day insert |

**Zero unfixed CRITICAL / HIGH / MEDIUM at v0.9.8 ship.** Both
v0.9.7 INFO findings are closed by v0.9.8 integration work.

## `/security-review` + `/code-review`

- **Pass 1** ran the v4-mandated `/security-review` invocations
  against the feature commits; `/code-review` auto-fired on the new
  RBAC / MCP-signing source files.
- **Pass 2** — the `/security-review` and `/code-review` builtins
  auto-scope to current-branch-vs-main; the v0.9.8 work was already
  merged to `origin/main`, so per
  `security-review-integration.md` the delta was reviewed by direct
  file inspection. `/code-review` trigger 4 fired (commit `adfcbf3`
  touched `oscal/sigstore.py`); triggers 1–3 did not (no new public
  API, no new source files, 332 LOC < 500).

## 16-row pre-push gate

Completed at Step 6.C — see the table appended at gate execution.

## Cross-references

- `CHANGELOG.md` `[0.9.8]` block
- `docs/v0.9.8-plan.md` — phase-by-phase cycle plan
- `docs/threat-model.md` — v0.9.8 attack-surface delta
- `docs/capability-matrix.md` — v0.9.8 SHIPPED snapshot
- `docs/ROADMAP.md` — v0.9.8 SHIPPED transition
- `docs/security-review-v0.9.7.md` — prior-cycle artifact (carried the F-V97 INFO findings now closed)

## PROCEED-CLEAN gate verdict

Finalized at Step 6.C after the 16-row pre-push gate. Provisional:
both review passes returned PROCEED-CLEAN with zero unfixed
CRITICAL / HIGH / MEDIUM findings.
