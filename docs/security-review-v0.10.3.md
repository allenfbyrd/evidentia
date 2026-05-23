# Security review — v0.10.3

> **Status**: in-cycle artifact for the v0.10.3 ship — the v4
> pre-release-review's 5th canonical deliverable.
>
> **Theme**: YAML-format catalog support (Phase 1, Candidate C from
> `docs/v0.10.3-plan.md`) + OpenSSF Gemara reference-model mapping
> (Phase 2, Candidate D).

## Cycle scope

v0.10.3 is the third patch on the v0.10.x line and the **fourth
ship on 2026-05-23** — same calendar day as v0.10.0 (03:07 UTC)
+ v0.10.1 (~04:54 UTC) + v0.10.2 (~06:30 UTC). The
[`docs/v0.10.3-plan.md`](v0.10.3-plan.md) selected Candidates C +
D under Allen's "C, then D, both under v0.10.3" directive:

1. **Phase 1 — Candidate C (YAML-driven catalog definitions)**:
   `evidentia_core.catalogs.loader._load_catalog_data` helper
   dispatches by file extension (`.json` → `json.loads`, `.yaml`
   / `.yml` → `yaml.safe_load`); rejects unsupported extensions
   + non-mapping YAML roots. All downstream loaders
   (`load_oscal_catalog`, `load_evidentia_catalog`,
   `load_non_control_catalog`, `load_catalog`, `load_any_catalog`)
   refactored to use the helper. `regenerate_manifest.py` extended
   to scan both extensions. Proof: `iso-27017-2015.json` →
   `iso-27017-2015.yaml` (7-control Tier-C stub); 89 bundled
   catalogs unchanged. 7 new tests in `test_yaml_loader.py`.
   New contributor doc `docs/contributing-a-catalog.md`.
2. **Phase 2 — Candidate D (OpenSSF Gemara reference-model
   mapping)**: NEW `docs/gemara-mapping.md` (NORMATIVE positioning)
   with 13-row component-by-component mapping table. Gemara v1.1.0
   (2026-05-12) cited; adopters FINOS CCC + OpenSSF Security
   Baseline. "Mapping, not conformance claim" framing — Evidentia
   does not yet emit Gemara-shape artifacts; CUE-constraint emit
   is a v0.11+ candidate. `docs/positioning-and-value.md` §8.3
   bullet corrected.

## Review structure

v0.10.3 was reviewed under the v4 default pre-tag variant with the
Diff + 1-hop dep closure scope (Step 1.4 option 1, auto-confirmed
per the established v0.10.0–v0.10.2 rhythm). The changeset is on
`main` (local), so `/security-review` and `/code-review` use
direct delta inspection per the v0.9.8 / v0.9.9 / v0.10.0–v0.10.2
precedent.

| Pass | Scope | Verdict |
|---|---|---|
| 3 — commit re-test + 1-hop closure | 3 unpushed commits (Phase 1 + Phase 2 + positioning skip-by-reuse) + 2 review-deliverable commits added in Step 4 + Step 5. `/security-review` direct delta inspection: **0 findings ≥ confidence 8**. `/code-review --effort high` (fired on Trigger #1: new modules): **0 critical, 4 polish-class suggestions** — all deferred to v0.10.4. | PROCEED-CLEAN |
| 4 — capability matrix (REUSE + delta) | v0.10.0 + v0.10.1 + v0.10.2 matrices reused for unchanged subsystems; v0.10.3 PRE-TAG section added with 5 new surfaces + 8-vector adversarial probe table on the YAML loader. | PROCEED-CLEAN |
| 6.C — final pre-tag pass | Full HEAD vs `v0.10.2` direct delta inspection; 16-row pre-push gate (filled below); 0 new findings; no api-stability surface change to validate. | PROCEED-CLEAN |

## Findings ledger

**Zero NEW findings.** All prior v0.10.x findings remain CLOSED
(F-V100-L1 + F-V100-M1 + F-V100-S1 + F-V101-L1).

`/code-review` raised 4 polish-class suggestions, none blocking:

| ID | File | Topic | Severity | Disposition |
|---|---|---|---|---|
| CR-V103-1 | `packages/evidentia-core/src/evidentia_core/catalogs/loader.py` | Module-level docstring choke-point note for `_load_catalog_data` | LOW (maintainability) | DEFERRED → v0.10.4 P1 |
| CR-V103-2 | `packages/evidentia-core/src/evidentia_core/catalogs/loader.py` | Error message polish when `suffix == ''` (no-extension path) | LOW (maintainability) | DEFERRED → v0.10.4 P2 |
| CR-V103-3 | `scripts/catalogs/regenerate_manifest.py` | `framework_id` collision guard in `scan_dir` | LOW (correctness, defensive) | DEFERRED → v0.10.4 P3 |
| CR-V103-4 | `tests/unit/test_catalogs/test_yaml_loader.py` | Multi-line round-trip coverage (`description` / `assessment_objectives` / `parameters`) | LOW (test coverage) | DEFERRED → v0.10.4 P4 |

## Subsystem-by-subsystem coverage

- **`_load_catalog_data` (new helper)** — closed-allowlist extension
  dispatch + non-mapping-root rejection; `yaml.safe_load` (safe
  variant, no arbitrary-object construction). 4 direct unit tests
  cover dispatch + 2 rejection paths.
- **`load_*` refactor** — pure call-site change; downstream Pydantic
  validation unchanged. Bundled catalogs (89) load identically.
- **`regenerate_manifest.py`** — developer-only maintenance script;
  not exposed at runtime. New extension globs preserve the existing
  WARN-and-skip pattern on parse errors.
- **`iso-27017-2015.yaml` (data file)** — 1:1 content conversion
  of the prior JSON Tier-C stub; same 7 controls; same framework
  metadata.
- **`docs/contributing-a-catalog.md` + `docs/gemara-mapping.md` +
  `docs/positioning-and-value.md` §8.3** — docs-only; no
  security surface.

## Step 6 16-row pre-push gate (to be filled at Step 6.E)

To be populated immediately before the irreversible push action —
see the live per-run JSON at
`.local/pre-release-review/runs/2026-05-23T17-24-18Z.json`.

## Disposition

**PROCEED-CLEAN.** Bump shape: **patch** (v0.10.2 → v0.10.3).

This is the **16th consecutive PROCEED-CLEAN** of the v0.7.x →
v0.8.x → v0.9.x → v0.10.x line. Continuous PROCEED-CLEAN tally:
v0.7.0 / v0.7.1 / v0.7.2 / v0.7.3 / v0.7.4 / v0.7.5 / v0.7.6 /
v0.7.7 / v0.7.8 / v0.7.9 / v0.8.0 / v0.8.1 / v0.8.2 / v0.8.3 /
v0.8.4 / v0.8.5 / v0.8.6 / v0.8.7 / v0.9.0 / v0.9.1 / v0.9.2 /
v0.9.3 / v0.9.4 / v0.9.5 / v0.9.6 / v0.9.7 / v0.9.8 / v0.9.9 /
v0.10.0 / v0.10.1 / v0.10.2 / **v0.10.3**.
