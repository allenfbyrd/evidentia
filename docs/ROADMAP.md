# ControlBridge roadmap

**Last updated: v0.2.1 release (April 2026).**

This roadmap synthesizes community feedback (including the April 2026
external code-audit report at `Downloads/ControlBridge-Comprehensive-Analysis-and-Recommendations.md`)
with the existing architecture plan at the project root. It is scope-locked
for v0.3.0 through v0.6.0. Beyond v0.6.0 is "aspirational" territory —
the shape will depend on real-world usage patterns.

## v0.3.0 — "Compliance-as-code" (next up)

The novel-differentiator bet: no open-source GRC tool does PR-level
compliance checking today. Two commands and one GitHub Action land here.

### `controlbridge gap diff`

Compare two gap-analysis snapshots — typically
before/after a code change — and report which gaps closed vs. opened.

```bash
controlbridge gap diff \
  --base .controlbridge/main-snapshot.json \
  --head .controlbridge/pr-snapshot.json
```

Wraps the v0.2.1 gap-store infrastructure. Output: JSON + Markdown-formatted
summary suitable for PR comments. Supports `--fail-on-regression` for
use in CI.

### `allenfbyrd/controlbridge-action` GitHub Action

A reusable action that:

1. Runs `controlbridge gap analyze` against a designated inventory file
2. Loads a baseline snapshot from the target branch (if present)
3. Runs `controlbridge gap diff` and comments on the PR with the result
4. Fails the check if `--fail-on-regression` is set

```yaml
- name: ControlBridge compliance check
  uses: allenfbyrd/controlbridge-action@v0.3
  with:
    inventory: inventory.yaml
    frameworks: nist-800-53-rev5-moderate,soc2-tsc
    fail-on-regression: true
```

### `controlbridge explain <control_id>`

LLM-generated plain-English control description for engineers and
executives. Translates NIST/HIPAA compliance-speak into actionable
engineer-speak.

```bash
$ controlbridge explain AC-2 --framework nist-800-53-rev5

Gap: AC-2 — Account Management
Plain English: You need a formal process for creating, modifying, and
  deleting user accounts. That means documented procedures for
  on/offboarding, at least quarterly access reviews, and someone
  accountable for approving access requests.
Why it matters: Unmanaged accounts are one of the top attack vectors —
  attackers frequently exploit former employees' credentials.
Effort: Medium — requires policy documentation + quarterly review
  calendar + possibly IAM tooling if you have >50 users.
```

Leverages the existing LiteLLM + Instructor stack. Caches responses at
`~/.cache/controlbridge/explanations/<framework>/<control>.json` keyed
on framework + control + model + temperature. Users who already paid
for one explanation get it back free next time.

## v0.4.0 — Phase 2 integrations

First real collectors and integrations. These have been advertised in
the workspace layout since v0.1.0 but shipped as empty shells. v0.4.0
wires them up. Priority order by community demand (highest first):

### `controlbridge-integrations[jira]`

Push gaps as Jira issues. Bidirectional status sync: when a Jira issue
is closed, update the corresponding control to IMPLEMENTED in the
inventory.

### `controlbridge-collectors[aws]`

Auto-evidence from AWS Config + Security Hub + IAM Access Analyzer.
Covers NIST 800-53 AC/IA/SC/AU/CM families for cloud-native deployments.
Highest-ROI collector — a single command auto-collects most of a cloud
org's NIST evidence.

### `controlbridge-collectors[github]`

Branch protection rules, Dependabot alerts, CODEOWNERS presence → maps
to SA-11, CM-2, SI-2.

### `controlbridge-collectors[okta]`

MFA enforcement, inactive users, privileged account counts → AC-2, IA-2,
IA-5.

### `controlbridge-integrations[servicenow]`

Push to `sn_compliance_task` via REST with OAuth 2.0.

### `controlbridge-integrations[vanta]` and `[drata]`

Custom test results push into Vanta and Drata via their public APIs.

## v0.5.0 — Air-gapped + evidence integrity

### `--offline` flag

All commands support `--offline` which refuses any outbound network
call. `controlbridge doctor --check-air-gap` validates that no
configured LLM endpoint points outside `localhost` or explicitly-allowed
internal hostnames.

Positioning: "The only open-source GRC tool that runs entirely on your
infrastructure. Use with Ollama for fully air-gapped FedRAMP, CMMC, and
healthcare deployments."

### Evidence chain of custody

Every OSCAL Assessment Results export carries a SHA-256 digest of each
evidence item. Optionally GPG-sign the whole AR document with the
operator's key. Creates a tamper-evident audit trail that survives
external-auditor scrutiny.

## v0.6.0+ — UI and quality signals

### Streamlit prototype

Two-to-three day spike. Validates the UX approach before committing to
a full React + FastAPI build. Python-only, no new dependencies.

### FastAPI REST server (`controlbridge serve`)

Prerequisite for any web UI. Reuses the existing data models — each
Pydantic model becomes a serializer, CLI commands become handlers.
Enables external tooling to consume ControlBridge without re-launching
the Python process.

### React + Vite + shadcn/ui frontend

If and only if product-market fit is proven by the Streamlit prototype
and REST server. Cross-platform, non-technical-user friendly, served
locally by `controlbridge serve` or packaged as a Tauri desktop app.

### Risk-statement quality validator

Every AI-generated risk statement gets scored against NIST SP 800-30 /
IR 8286 criteria. Statements that fail validation are automatically
regenerated with corrective instructions. Produces audit-survivable
output that no other open-source tool guarantees.

### Compliance ROI scoring

Reframes the cross-framework efficiency feature as "close N gaps across
M frameworks with one remediation." CFOs and CISOs respond to ROI
framing in ways they don't respond to "coverage %".

## Deferred / rejected items

- **Full React GUI in v0.3.0** — deferred to v0.6.0+. The next-user
  migration effort is in compliance-as-code CLI, not in a GUI.
- **RSA Archer integration** — deferred indefinitely. Enterprise-only,
  requires an Archer instance to develop against, and the market has
  been moving to REST-native alternatives for years.
- **COSO framework content** — legally non-starter (AICPA copyright,
  same basis as the SOC 2 Tier-C stub treatment).
- **Per-framework crosswalk auto-generation via LLM** — rejected on
  correctness grounds. Crosswalks are audit-critical and need
  human-in-the-loop review. An LLM-authored crosswalk should be
  reviewed and committed, not generated at runtime.

## Release-runbook follow-ups (not a feature, operational debt)

### PyPI Trusted Publisher (OIDC) migration

v0.2.1 continues using `PYPI_API_TOKEN` for release authentication.
Before v0.3.0, the project should:

1. Configure a Trusted Publisher on PyPI's admin panel pointing at
   `allenfbyrd/controlbridge` / `.github/workflows/release.yml` for each
   of the 5 packages.
2. Update `release.yml` to add `permissions: id-token: write` and drop
   the `password: ${{ secrets.PYPI_API_TOKEN }}` input.
3. Delete the PyPI API token from GitHub repo secrets.

Why deferred: switching without step 1 first breaks the release
pipeline. Step 1 requires PyPI UI clicks that the release workflow
can't do from code.
