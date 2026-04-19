# ControlBridge roadmap

**Last updated: v0.4.0-alpha.1 (April 2026).**

This roadmap synthesizes community feedback with the architecture plan
at the project root. It is scope-locked for v0.4.0 through v0.6.0.
Beyond v0.6.0 is aspirational — the exact shape will depend on real-world
usage patterns.

## v0.3.0 — Compliance-as-code — SHIPPED

- `controlbridge gap diff` — compare two gap snapshots, classify every
  gap as opened / closed / severity-changed / unchanged. Supports
  console / json / markdown / github output formats.
  `--fail-on-regression` blocks PRs that make compliance posture worse.
- `controlbridge explain <control_id>` — LLM-generated plain-English
  control translation, cached on disk.
- Documentation: `docs/github-action/README.md` + example workflow YAML
  so anyone can drop a `.github/workflows/controlbridge.yml` into their
  repo and get PR-level compliance checking without waiting for the
  reusable-action wrapper.

## v0.3.1 — Examples + latent-bug fix — SHIPPED

- Three realistic end-to-end scenarios in `examples/` (Meridian fintech
  v2, Acme Healthtech, Northstar DoD contractor).
- Dogfooded GitHub Action workflow (`.github/workflows/controlbridge.yml`).
- Fixed `_is_open` bug on the in-memory gap-diff path.
- 392 passing tests.

## v0.4.0 — Accessible GRC — IN FLIGHT (alpha.1 shipped)

The audience shift from security engineers (CLI) to compliance officers
and auditors (web UI). Three coordinated deliverables:

### 1. Web UI — `controlbridge serve`

FastAPI backend + React/Vite/shadcn/ui frontend, served together from
`127.0.0.1:8000`. Non-technical users install via
`uv tool install "controlbridge[gui]"` or
`pip install "controlbridge[gui]"`, then run `controlbridge serve` and
get a polished localhost-only dashboard.

**Shipped in alpha.1:**
- `controlbridge serve` CLI command
- New workspace package `controlbridge-api` with 18 REST endpoints
  under `/api/*`
- New workspace directory `controlbridge-ui` (Vite + React + shadcn/ui)
- Read-only web UI pages: Home, Dashboard, Frameworks (list + detail),
  Settings
- Hatchling build hook that bundles the SPA into the Python wheel
- 36 TestClient integration tests for the API surface

**Planned for alpha.2:**
- Interactive onboarding wizard (3 paths: sample data / upload / wizard)
- Gap Analyze page (form → run analysis → sortable/filterable TanStack
  Table)
- Gap Diff page (pick two reports → diff summary + per-entry table)
- Risk Generate page (SSE-streamed per-gap progress)
- Config edit form (PUT `/api/config` with validated Pydantic payload)
- Vitest component tests + Playwright E2E smoke test against
  `controlbridge serve`

**Stack:** React 18 + TypeScript strict + Vite 5 + shadcn/ui (Radix
primitives -> WCAG 2.1 AA) + TanStack Query / Table / Virtual +
React Router 6 + Zustand + React Hook Form + Zod + Recharts.

### 2. Air-gapped mode — `--offline` flag

Global CLI flag plus `controlbridge doctor --check-air-gap` validator.
Every LLM / network call consults the `controlbridge_core.network_guard`
module; non-loopback / non-RFC-1918 targets raise
`OfflineViolationError` before any network IO fires.

**Positioning:** *"The only open-source GRC tool that runs entirely on
your infrastructure. Use with Ollama for fully air-gapped FedRAMP,
CMMC, and healthcare deployments."*

**Shipped in alpha.1:** flag, guard module, doctor validator, LLM
client integration, 43 unit tests covering the host classifier and
guard functions.

**Planned for alpha.2:** GUI Settings-page air-gap toggle wired to
`/api/*` requests; graceful LLM-feature degradation when no
offline-compatible endpoint is configured.

### 3. Reusable GitHub Action — `allenfbyrd/controlbridge-action`

Separate repo at `github.com/allenfbyrd/controlbridge-action`. One-line
`uses:` wrapper that replaces the 80-line drop-in workflow template
from `docs/github-action/workflow-example.yml`.

**Planned for alpha.2 / rc:** repo creation, `action.yml` composite
action, README with screenshots, v1.0.0 tag, submission to the GitHub
Actions Marketplace.

## v0.5.0 — Phase 2 integrations

First real collectors and integrations. These have been advertised
in the workspace layout since v0.1.0 but shipped as empty shells.
v0.5.0 wires them up. Priority order by community demand (highest
first):

### `controlbridge-integrations[jira]`

Push gaps as Jira issues. Bidirectional status sync: when a Jira
issue is closed, update the corresponding control to IMPLEMENTED in
the inventory.

### `controlbridge-collectors[aws]`

Auto-evidence from AWS Config + Security Hub + IAM Access Analyzer.
Covers NIST 800-53 AC/IA/SC/AU/CM families for cloud-native
deployments. Highest-ROI collector — a single command auto-collects
most of a cloud org's NIST evidence.

### `controlbridge-collectors[github]`

Branch protection rules, Dependabot alerts, CODEOWNERS presence ->
maps to SA-11, CM-2, SI-2.

### `controlbridge-collectors[okta]`

MFA enforcement, inactive users, privileged account counts -> AC-2,
IA-2, IA-5.

### `controlbridge-integrations[servicenow]`

Push to `sn_compliance_task` via REST with OAuth 2.0.

### `controlbridge-integrations[vanta]` and `[drata]`

Custom test results push into Vanta and Drata via their public APIs.

## v0.6.0 — Evidence chain of custody

### Evidence integrity

Every OSCAL Assessment Results export carries a SHA-256 digest of each
evidence item. Optionally GPG-sign the whole AR document with the
operator's key. Creates a tamper-evident audit trail that survives
external-auditor scrutiny.

## v0.7.0+ — Quality signals and UI polish

### Risk-statement quality validator

Every AI-generated risk statement gets scored against NIST SP 800-30 /
IR 8286 criteria. Statements that fail validation are automatically
regenerated with corrective instructions. Produces audit-survivable
output that no other open-source tool guarantees.

### Compliance ROI scoring

Reframes the cross-framework efficiency feature as "close N gaps
across M frameworks with one remediation." CFOs and CISOs respond to
ROI framing in ways they don't respond to "coverage %".

### UI polish

- Auto-generated TypeScript types from FastAPI's OpenAPI schema
  (hand-authored in v0.4.0; auto-gen removes the drift class entirely)
- Tauri desktop packaging option for offline-first users who prefer
  an installable app over `controlbridge serve`
- Optional multi-user auth / RBAC for network deployments
  (localhost-only in v0.4.0 — v0.7.0+ adds token auth)

## Deferred / rejected items

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

v0.4.0 continues using `PYPI_API_TOKEN` for release authentication.
Before v0.5.0, the project should:

1. Configure a Trusted Publisher on PyPI's admin panel pointing at
   `allenfbyrd/controlbridge` / `.github/workflows/release.yml` for
   each of the 6 packages.
2. Update `release.yml` to add `permissions: id-token: write` and
   drop the `password: ${{ secrets.PYPI_API_TOKEN }}` input.
3. Delete the PyPI API token from GitHub repo secrets.

Why deferred: switching without step 1 first breaks the release
pipeline. Step 1 requires PyPI UI clicks that the release workflow
can't do from code.
