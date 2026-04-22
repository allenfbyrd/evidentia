# Evidentia end-to-end walkthrough

**Every v0.3.0 feature, exercised against three realistic scenarios.**

This document is the "take the tour" doc — run the commands in order
and every piece of Evidentia (gap analysis, cross-framework
efficiency, `gap diff`, LLM-powered `explain`, user-catalog import,
persistent gap store, config-driven defaults) is touched at least
once.

Budget: ~10 minutes (most of which is reading output).

---

## Prerequisites

```bash
pip install evidentia==0.3.0        # or later
evidentia doctor                    # should report 82 frameworks
```

For the `explain` and `risk generate` steps you'll also need an LLM
API key in env (one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GOOGLE_API_KEY`) — match the `llm.model` set in each scenario's
`evidentia.yaml` or override with `--model`.

---

## Scenario 1 — Meridian Financial (fintech)

**What it proves**: core gap analysis + PR-level compliance diff +
user-catalog shadow + config-driven defaults, against a 48-control
fintech inventory covering 3 frameworks (`nist-800-53-rev5-moderate`,
`soc2-tsc`, `eu-gdpr`).

```bash
cd examples/meridian-fintech-v2

# 1. Baseline analysis — note that --frameworks is NOT passed;
#    it's read from evidentia.yaml via the v0.2.1 config loader
evidentia gap analyze \
  --inventory my-controls.yaml \
  --output snapshots/baseline.json

# 2. Re-run on the "PR branch" inventory
evidentia gap analyze \
  --inventory my-controls-pr.yaml \
  --output snapshots/pr-branch.json

# 3. Diff the two — exercises the v0.3.0 headline feature
evidentia gap diff \
  --base snapshots/baseline.json \
  --head snapshots/pr-branch.json

# Expect: +1 opened, -3 closed, +1 severity_increased, -2 severity_decreased.
# The "opened" gap is AU-12 (net-new control). The regression is AC-17
# (Cloudflare Access config drift) + CP-10 (DR test failed).

# 4. PR-comment-ready Markdown
evidentia gap diff \
  --base snapshots/baseline.json --head snapshots/pr-branch.json \
  --format markdown --output snapshots/pr-diff.md
cat snapshots/pr-diff.md

# 5. GitHub-Actions inline annotations
evidentia gap diff \
  --base snapshots/baseline.json --head snapshots/pr-branch.json \
  --format github

# 6. CI gate — this exits 1 (regression detected)
evidentia gap diff \
  --base snapshots/baseline.json --head snapshots/pr-branch.json \
  --fail-on-regression || echo "[demo] Exit code $? confirms regression gating works"

# 7. CSV inventory + --organization override
evidentia gap analyze \
  --inventory my-controls.csv \
  --frameworks nist-800-53-rev5-moderate \
  --organization "Meridian Financial" \
  --system-name "Meridian Customer Banking Platform" \
  --output report-csv.json

# 8. User-catalog shadowing — override the SOC2-TSC stub
evidentia catalog import \
  ./user-catalog-demo/soc2-tsc-licensed.json --force
evidentia catalog where soc2-tsc            # reports "user" source
evidentia catalog show soc2-tsc --control CC6.1
evidentia catalog remove soc2-tsc --yes     # undo

# 9. LLM-powered explain (requires API key)
evidentia explain control AC-2 --framework nist-800-53-rev5-moderate
evidentia explain cache where               # shows cache dir
# evidentia explain cache clear --yes       # if you want to wipe

# 10. Risk statement on a single gap (from persistent gap store)
# Look at the "priority_score" field in snapshots/baseline.json — pick
# a gap ID, then:
# evidentia risk generate \
#   --context system-context.yaml \
#   --gap-id <GAP-UUID>
```

---

## Scenario 2 — Acme Healthtech (HIPAA-covered entity)

**What it proves**: multi-HIPAA-rule cross-framework efficiency,
dotted-section control-ID normalization, obligation-catalog-aware gap
analysis.

```bash
cd examples/acme-healthtech

# Analyze against all 4 frameworks (HIPAA Security + Privacy + Breach
# + NIST 800-53 Moderate overlay) — reads from evidentia.yaml
evidentia gap analyze --inventory my-controls.yaml --output report.json

# Watch for efficiency_opportunities where IA-2(1) (MFA) satisfies
# 164.312(d) (HIPAA Security), AC-2 (NIST), AND implicitly supports
# 164.404 safe-harbor for breach notification.
python -c "
import json
r = json.load(open('report.json'))
for e in r['efficiency_opportunities'][:5]:
    print(f\"{e['control_id']}: satisfies {e['framework_count']} frameworks\")
"

# Plain-English explanation of a HIPAA-specific control
evidentia explain control 164.312(d) --framework hipaa-security
```

---

## Scenario 3 — Northstar Systems (DoD contractor)

**What it proves**: CMMC + NIST 800-171 parallel coverage, cross-
framework efficiency between near-identical frameworks, CMMC-style
control IDs.

```bash
cd examples/dod-contractor

evidentia gap analyze --inventory my-controls.yaml --output report.json

# Expect very high cross-framework efficiency — CMMC L2 and NIST
# 800-171 Rev 2 are essentially the same control set.

# Explain the flagship known-gap
evidentia explain control CMMC.L2-3.3.5 --framework cmmc-2-l2
```

---

## What each scenario covers

| Feature                          | Meridian v2 | Acme Healthtech | DoD Northstar |
|----------------------------------|:-----------:|:---------------:|:-------------:|
| Full NIST 800-53 Rev 5 bundled   |      ✓      |        ✓        |               |
| HIPAA family (Security+Privacy+Breach) |       |        ✓        |               |
| CMMC 2.0 L2                      |             |                 |       ✓       |
| NIST 800-171 Rev 2 parallel      |             |                 |       ✓       |
| GDPR obligation catalog          |      ✓      |                 |               |
| NIST-pub vs NIST-OSCAL ID conventions |   ✓   |                 |               |
| HIPAA dotted-section IDs         |             |        ✓        |               |
| CMMC prefixed IDs                |             |                 |       ✓       |
| v0.2.1 `evidentia.yaml`      |      ✓      |        ✓        |       ✓       |
| `--organization` / `--system-name` overrides |  ✓  |             |               |
| CSV inventory + override         |      ✓      |                 |               |
| `gap diff` (all 5 classifications) |    ✓      |                 |               |
| Markdown + github-annotation renderers |  ✓    |                 |               |
| `catalog import` + shadow precedence |  ✓      |                 |               |
| `explain` LLM pipeline           |      ✓      |        ✓        |       ✓       |
| Cross-framework efficiency opportunities | ✓  |        ✓        |       ✓       |
| Persistent gap store             |      ✓      |                 |               |

---

## Regenerating snapshots

The `snapshots/baseline.json` and `snapshots/pr-branch.json` files in
Meridian v2 are pre-generated so users who just want to see the
`gap diff` output can skip the generation step. To regenerate (e.g.,
after a catalog refresh):

```bash
cd examples/meridian-fintech-v2
python ../../scripts/demo/generate_snapshot_pair.py
```

See [`scripts/demo/generate_snapshot_pair.py`](../scripts/demo/generate_snapshot_pair.py)
for the one-liner that produces both.

---

## If something goes wrong

- **`evidentia: command not found`** — `pip install evidentia`
  (or `uv tool install evidentia`).
- **`LLM call failed: APIError`** — you need an API key env var for
  the model in `evidentia.yaml`. The pre-flight warning points
  at which one.
- **`Framework 'soc2-tsc' is a Tier-C placeholder catalog — ...`** —
  this is an informational warning, not an error. The analyzer runs;
  the control descriptions in the report are placeholders. Use the
  `catalog import` flow in Scenario 1 step 8 to load your licensed
  copy.
- **`Error: no frameworks specified`** — either pass `--frameworks`
  on the command line OR ensure `evidentia.yaml` has a
  top-level `frameworks:` list (this scenario's yaml does; check the
  walkthrough's CWD).
