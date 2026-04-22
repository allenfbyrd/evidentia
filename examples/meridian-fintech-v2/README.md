# Meridian Financial v2 — Evidentia comprehensive example

**Fictional B2C fintech SaaS** — 1.2M US + 80K EU customers, FDIC-insured
savings/debit/bill-pay on AWS EKS.

This is the canonical end-to-end demo for **every Evidentia v0.3.0
feature**. The older `examples/meridian-fintech/` (20-control v0.1.x
sample) is kept for backward reference but is no longer the recommended
starting point.

## What's in here

| File / dir                           | Purpose |
|--------------------------------------|---------|
| `evidentia.yaml`                 | Project config using the v0.2.1 schema (flat `frameworks:`, `llm.model`/`temperature`, `organization`, `system_name`) |
| `my-controls.yaml`                   | Baseline control inventory — 48 controls across 15 NIST 800-53 families, mixed implementation states, mixed NIST-pub (`AC-2(1)`) and NIST-OSCAL (`ac-2.3`) ID conventions to exercise the v0.2.1 normalizer |
| `my-controls.csv`                    | Same 48 controls in CSV form so the CSV parser + `--organization` override flow is demonstrated |
| `my-controls-pr.yaml`                | "PR branch" inventory — same org but with intentional regressions (AC-17, CP-10) and improvements (AU-2, AU-6, SI-2, SI-4, SR-3) plus one net-new control (AU-12) |
| `system-context.yaml`                | Realistic system context for `evidentia risk generate` — covers threat actors, data classifications, sub-processors, regulatory scope |
| `snapshots/baseline.json`            | Pre-generated gap report from `my-controls.yaml` — ready for `gap diff` |
| `snapshots/pr-branch.json`           | Pre-generated gap report from `my-controls-pr.yaml` |
| `snapshots/pr-diff.md`               | Pre-rendered markdown diff ready to paste into a PR |
| `user-catalog-demo/soc2-tsc-licensed.json` | Fake "licensed AICPA copy" for `catalog import` shadow-precedence demo |

## Framework coverage

- **`nist-800-53-rev5-moderate`** — the 287-control authoritative NIST
  baseline bundled in v0.2.1 (not the v0.1.x 16-control sample).
- **`soc2-tsc`** — the Tier-C placeholder stub; demonstrates the
  copyright-aware warning and the `catalog import` override flow.
- **`eu-gdpr`** — the 30-obligation privacy catalog; demonstrates that
  `gap analyze` runs against obligation-type catalogs too (not just
  control-type).

## Quick start — every v0.3.0 feature

### 1. Inspect the config-driven project

```bash
cd examples/meridian-fintech-v2
evidentia doctor                  # 82 frameworks registered
evidentia catalog list --tier A | head -20
```

### 2. Gap-analyze the baseline inventory

Notice that `--frameworks` isn't passed — it comes from `evidentia.yaml`.

```bash
evidentia gap analyze \
  --inventory my-controls.yaml \
  --output snapshots/baseline.json \
  --format json
```

Also exported in the four other formats for comparison:

```bash
evidentia gap analyze --inventory my-controls.yaml --output report.md      --format markdown
evidentia gap analyze --inventory my-controls.yaml --output report.csv     --format csv
evidentia gap analyze --inventory my-controls.yaml --output report.oscal.json --format oscal-ar
```

### 3. Gap-analyze the PR-branch inventory

```bash
evidentia gap analyze \
  --inventory my-controls-pr.yaml \
  --output snapshots/pr-branch.json \
  --format json
```

### 4. Diff the two snapshots

Exercises the headline v0.3.0 feature:

```bash
# Terminal output (Rich tables)
evidentia gap diff --base snapshots/baseline.json --head snapshots/pr-branch.json

# PR-comment-style markdown
evidentia gap diff \
  --base snapshots/baseline.json --head snapshots/pr-branch.json \
  --format markdown --output snapshots/pr-diff.md

# GitHub Actions inline annotations (::error::/::warning::/::notice::)
evidentia gap diff \
  --base snapshots/baseline.json --head snapshots/pr-branch.json \
  --format github

# CI gate — exits 1 because the PR opens AU-12 and regresses AC-17 / CP-10
evidentia gap diff \
  --base snapshots/baseline.json --head snapshots/pr-branch.json \
  --fail-on-regression
```

Expected diff output: **+1 opened / -3 closed / ▲1 severity_increased / ▼2 severity_decreased / 305 unchanged**.

### 5. CSV inventory with `--organization` override

```bash
evidentia gap analyze \
  --inventory my-controls.csv \
  --frameworks nist-800-53-rev5-moderate \
  --organization "Meridian Financial" \
  --system-name "Meridian Customer Banking Platform" \
  --output report-csv.json
```

Without `--organization`, the CSV parser would record the inventory as
`"Unknown Organization"` (there's no org field in CSV format).

### 6. User-catalog import — shadow a bundled Tier-C stub

```bash
evidentia catalog import ./user-catalog-demo/soc2-tsc-licensed.json --force
evidentia catalog where soc2-tsc
evidentia catalog show soc2-tsc --control CC6.1

# The gap analyzer now sees your licensed copy instead of the stub:
evidentia gap analyze --inventory my-controls.yaml \
  --frameworks soc2-tsc --output report-soc2-licensed.json

# Undo:
evidentia catalog remove soc2-tsc --yes
```

### 7. Persistent gap store + `risk generate --gap-id`

Every `gap analyze` run writes a canonical snapshot to the user-dir
store. Then you can generate a risk statement for a single gap without
re-running analysis or re-specifying `--gaps`:

```bash
# After running gap analyze above, pick a gap ID from the console output:
evidentia risk generate \
  --context system-context.yaml \
  --gap-id GAP-0001
```

If `$ANTHROPIC_API_KEY` / `$OPENAI_API_KEY` / etc. isn't set, the
pre-flight check emits a clear pointer rather than a cryptic LiteLLM
auth error. Uses the `llm.model` from `evidentia.yaml` by default.

### 8. Plain-English control explanations

```bash
# Requires an LLM API key matching the model in evidentia.yaml
evidentia explain control AC-2 --framework nist-800-53-rev5-moderate

# Format options
evidentia explain control AC-2 --framework nist-800-53-rev5-moderate --format markdown
evidentia explain control AC-2 --framework nist-800-53-rev5-moderate --format json

# Cache management
evidentia explain cache where          # show cache dir
evidentia explain cache clear --yes    # wipe cache

# Force re-generation even if cached
evidentia explain control AC-2 --framework nist-800-53-rev5-moderate --refresh
```

### 9. GitHub-Action-style workflow

See `docs/github-action/README.md` at the repo root for the full
workflow. The `snapshots/` dir in this example is what the cached
action would carry between PR runs.

## How the PR-branch diff was engineered

The `my-controls-pr.yaml` file was designed to produce every diff
classification:

| Control | Base state | PR state | Diff classification |
|---------|-----------|----------|---------------------|
| `AC-17` | implemented | partially_implemented | **severity_increased** (regression) |
| `CP-10` | partially_implemented | not_implemented | **severity_increased** (regression) |
| `AU-12` | (absent) | not_implemented | **opened** (new gap) |
| `AU-2` | planned | implemented | **closed** |
| `AU-6` | not_implemented | partially_implemented | **severity_decreased** |
| `SI-2` | partially_implemented | implemented | **closed** |
| `SI-4` | not_implemented | partially_implemented | **severity_decreased** |
| `SR-3` | partially_implemented | implemented | **closed** |
| everything else | unchanged | unchanged | **unchanged** |

The `snapshots/pr-diff.md` file is the exact markdown that would land
as a PR comment in a real CI workflow.

## Related examples

- [`examples/acme-healthtech/`](../acme-healthtech/) — HIPAA-covered-entity
  scenario (different cross-framework dynamics, same schema)
- [`examples/dod-contractor/`](../dod-contractor/) — CMMC L2 + NIST 800-171
  scenario for DoD-contract workflows
- [`examples/WALKTHROUGH.md`](../WALKTHROUGH.md) — end-to-end narrative
  tying all three scenarios together
