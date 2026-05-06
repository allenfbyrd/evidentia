# Mutation testing (v0.8.2 G1)

> Status: v0.8.2 baseline establishment. CI workflow:
> `.github/workflows/mutmut.yml`. Paths under test:
> `evidentia_core.gap_analyzer` + `evidentia_ai.risk_statements`.

## What mutation testing measures

Statement coverage (the OpenSSF Silver `test_statement_coverage80`
gate, currently at 82.14% for Evidentia) tells you whether each
line of code is _executed_ by the test suite. Mutation testing
tells you whether each line is _verified_ — does flipping the
line's behavior actually break a test?

`mutmut` introduces small random mutations to the source code:

- `x + 1` → `x - 1`
- `if x > 0:` → `if x < 0:`
- `return None` → `return ""`
- boolean flips, off-by-one tweaks, return-value swaps

For each mutation, mutmut re-runs the test suite. A **killed**
mutant means at least one test failed (the test caught the
mutation). A **survived** mutant means every test passed
despite the mutation — pointing at a coverage gap.

The **mutation score** is `killed / (killed + survived)`. A
score of 100% means every mutation is caught; 0% means none
are. Real-world targets are typically 60-80%.

## Why we mutation-test gap_analyzer + risk_statements

These two modules carry the highest leverage:

- **`evidentia_core.gap_analyzer`** — the canonical control-
  mapping engine. A silent bug here surfaces as a wrong gap
  classification on every gap analysis the operator runs.
- **`evidentia_ai.risk_statements`** — the canonical AI risk-
  statement generator. A silent bug here ships hallucinated
  content into auditor-facing artifacts.

Other modules are well-covered by integration tests (e.g.,
the OSCAL emit roundtrip catches bugs in the OSCAL exporter
without needing per-mutation gating). The gap-analyzer +
risk-statement modules have less integration-level surfacing,
so mutation-testing them is high-ROI.

## How to run locally

```bash
# Install pip-tools-driven dev deps (mutmut included):
uv sync

# Sanity-check: the baseline test suite must pass.
uv run pytest -x -q tests/unit/test_gap_analyzer/ tests/unit/test_ai/

# Run mutmut against the [tool.mutmut] config in pyproject.toml.
# First run takes ~30-60 min depending on machine.
uv run mutmut run

# Inspect results:
uv run mutmut results
uv run mutmut show all   # show every mutant's status
uv run mutmut show <id>  # show a specific surviving mutant's diff
```

## Interpreting results

```
- 1234 ★ killed (test suite caught the mutation)
-    5 ⚰ skipped (mutation was syntactically equivalent — ignored)
-   42 🐛 survived (TEST GAP — investigate)
-    0 ⏰ timeout
```

Survivors mean the corresponding mutation was undetectable by
the current test suite. The fix is usually one of:

1. **Add a test** that would have caught the mutation. This
   is the most common path — find an assertion that ties the
   real behavior to the surviving mutant's altered behavior.
2. **Remove dead code** if the mutation was on a branch the
   tests don't care about because the branch is unreachable.
3. **Document the gap** if the mutation is on a piece of code
   whose behavior is genuinely outside the test scope (e.g.,
   logging-side-effect-only branches; pure rendering layers).

## CI cadence

The `.github/workflows/mutmut.yml` workflow runs:

- **Weekly** (Sunday 03:00 UTC) — captures trend-line drift.
- **On-demand** (`workflow_dispatch`) — operators can re-run
  manually after a major refactor to confirm the mutation
  score didn't regress.

It does **NOT** run on every PR. Full mutmut runs are too slow
for PR-level gating; per-PR test-coverage protection happens
via Codecov instead (≥ 80% statement coverage MUST per
OpenSSF Silver tier).

## v0.8.2 baseline

The first run of `mutmut run` against the gap_analyzer +
risk_statements paths establishes the v0.8.2 baseline. Per
the §25 plan R2 mitigation:

> if baseline lands < 60% after 1 day of tuning, drop the
> threshold to whatever the actual mutation score is +
> document as the new baseline. v0.8.3 then aims to raise it.

The CI gate's value is **regression detection**, not the
absolute number. Once the baseline is published, every
subsequent run that drops materially below it is a signal —
either a test was deleted, or new code landed without
matching tests.

## Future work (v0.8.3+)

- Tune the baseline upward as new tests land.
- Expand `paths_to_mutate` to the OSCAL exporter, plugin
  contracts, and the eval harness once those modules
  stabilize.
- Wire a "mutation-score regression" PR comment via a
  follow-up workflow (compares a PR's mutmut output against
  the main-branch baseline).

## References

- [Mutmut documentation](https://mutmut.readthedocs.io/)
- Plan: §25.2 P2.1 / §25.3 step 4 (v0.8.2 cycle)
- Sister doc: `docs/dockerfile-pinning.md` (v0.8.2 G4 closure
  — the second cycle hardening item)
