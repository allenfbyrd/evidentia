# Evidentia roadmap

**Last updated: v0.6.0 (April 2026).**

This roadmap synthesizes community feedback with the architecture plan
at the project root. Versions v0.3.0 through v0.6.0 have shipped; v0.7.0
is the next active scope. Anything beyond v0.7.0 is aspirational — the
exact shape will depend on real-world usage patterns.

## v0.3.0 — Compliance-as-code — SHIPPED

- `evidentia gap diff` — compare two gap snapshots, classify every
  gap as opened / closed / severity-changed / unchanged. Supports
  console / json / markdown / github output formats.
  `--fail-on-regression` blocks PRs that make compliance posture worse.
- `evidentia explain <control_id>` — LLM-generated plain-English
  control translation, cached on disk.
- Documentation: `docs/github-action/README.md` + example workflow YAML
  so anyone can drop a `.github/workflows/evidentia.yml` into their
  repo and get PR-level compliance checking without waiting for the
  reusable-action wrapper.

## v0.3.1 — Examples + latent-bug fix — SHIPPED

- Three realistic end-to-end scenarios in `examples/` (Meridian fintech
  v2, Acme Healthtech, Northstar DoD contractor).
- Dogfooded GitHub Action workflow (`.github/workflows/evidentia.yml`).
- Fixed `_is_open` bug on the in-memory gap-diff path.
- 392 passing tests.

## v0.4.0 / v0.4.1 — Accessible GRC — SHIPPED

The audience shift from security engineers (CLI) to compliance officers
and auditors (web UI). Three coordinated deliverables:

### 1. Web UI — `evidentia serve` — SHIPPED (v0.4.1)

FastAPI backend + React/Vite/shadcn/ui frontend, served together from
`127.0.0.1:8000`. Non-technical users install via
`uv tool install "evidentia[gui]"` or
`pip install "evidentia[gui]"`, then run `evidentia serve` and
get a polished localhost-only dashboard.

**Shipped:**
- `evidentia serve` CLI command
- New workspace package `evidentia-api` with 18 REST endpoints
  under `/api/*`
- New workspace directory `evidentia-ui` (Vite + React + shadcn/ui)
- Every user-facing page:
  - **Home** with three-path onboarding wizard (sample data / upload /
    wizard)
  - **Dashboard** — saved-report listing with top-line metrics
  - **Frameworks** (list + detail) — 82-catalog browser with tier /
    category / search filters
  - **Gap Analyze** — interactive form → TanStack Table results
  - **Gap Diff** — two-report picker → summary + per-entry table
  - **Risk Generate** — SSE-streamed per-gap progress
  - **Settings** — editable `evidentia.yaml` + LLM provider /
    air-gap posture
- Hatchling build hook that bundles the SPA into the Python wheel
- 36 FastAPI TestClient + 6 Vitest tests

### Planned for v0.4.2 polish:

- Playwright E2E smoke test against `evidentia serve`
- "Commit to disk" button on the wizard preview (auto-write the three
  YAMLs to the CWD after confirmation)
- Deeper component test coverage (AppLayout, PathChooser, GapTable)
- Auto-generated TypeScript types from FastAPI's OpenAPI schema

**Stack:** React 18 + TypeScript strict + Vite 5 + shadcn/ui (Radix
primitives -> WCAG 2.1 AA) + TanStack Query / Table / Virtual +
React Router 6 + Zustand + React Hook Form + Zod + Recharts.

### 2. Air-gapped mode — `--offline` flag — SHIPPED (v0.4.0)

Global CLI flag plus `evidentia doctor --check-air-gap` validator.
Every LLM / network call consults the `evidentia_core.network_guard`
module; non-loopback / non-RFC-1918 targets raise
`OfflineViolationError` before any network IO fires.

**Positioning:** *"The only open-source GRC tool that runs entirely on
your infrastructure. Use with Ollama for fully air-gapped FedRAMP,
CMMC, and healthcare deployments."*

Shipped: flag, guard module, doctor validator, LLM client integration,
43 unit tests covering the host classifier and guard functions. The UI
Settings page surfaces the posture live. GUI-triggered offline-toggle
is planned for v0.4.2.

### 3. Reusable GitHub Action — SHIPPED (v0.4.1)

`allenfbyrd/evidentia-action` is live at v1.0.0 + floating `v1`
pointer. Consumers replace the 80-line drop-in workflow template with:

```yaml
- uses: allenfbyrd/evidentia-action@v1
  with:
    inventory: my-controls.yaml
    frameworks: nist-800-53-rev5-moderate,soc2-tsc
    fail-on-regression: true
```

Submission to the GitHub Actions Marketplace is a manual UI step in
the repo settings; the listing is pending final screenshots before
publication.

## v0.5.0 — Phase 2 integrations — SHIPPED

First three real integrations. These shipped as empty shells all the
way back to v0.1.0; v0.5.0 wires them up. What landed:

### `evidentia-integrations` (Jira) — SHIPPED

Push gaps as Jira issues + bidirectional status sync. When a Jira
issue transitions to Done, the linked gap's status becomes REMEDIATED
on the next `sync`. Full workflow-name mapping (To Do, In Progress,
Done, Won't Do, + common customizations). Credentials via env vars
only; no secrets ever flow through Evidentia REST responses.

CLI: `evidentia integrations jira {test,push,sync,status-map}`.
REST: `/api/integrations/jira/{status,push/{key},sync/{key},status-map}`.

### `evidentia-collectors[aws]` — SHIPPED

Auto-evidence from AWS Config + Security Hub. Covers NIST 800-53
AC / IA / SC / AU / CM / CP / SI families for cloud-native
deployments. Curated mapping of 25+ Config rules + FSBP / CIS
standards controls; unknown sources fall back to empty `control_ids`
rather than speculative attribution.

Credentials via standard boto3 chain. Unit tests use MagicMock
paginators (Config) + controlled responses (Security Hub);
integration-test-level moto coverage lands in v0.5.1.

CLI: `evidentia collect aws [--region] [--profile]`.
REST: `POST /api/collectors/aws/collect`.

### `evidentia-collectors` (GitHub) — SHIPPED

Branch protection + CODEOWNERS + repo visibility findings mapped to
SA-11 (developer security testing), CM-2/CM-3 (baseline + change
control), AC-3/AC-6 (access enforcement), SI-2 (flaw remediation).
Zero extra deps — uses httpx directly rather than pulling in PyGithub.

CLI: `evidentia collect github --repo owner/repo`.
REST: `POST /api/collectors/github/collect`.

## v0.5.1 — deprecation shims — SHIPPED

The six old PyPI names (`controlbridge`, `controlbridge-core`,
`controlbridge-ai`, `controlbridge-api`, `controlbridge-collectors`,
`controlbridge-integrations`) released at v0.5.1 as transitional shims
that emit a `DeprecationWarning` on import and forward every attribute
and submodule to their `evidentia-*` replacements via `sys.modules`
aliasing. Scheduled for PyPI yank at v0.7.0 (~October 2026).

## v0.6.0 — Project rename (ControlBridge → Evidentia) — SHIPPED

The v0.5.0 name collided with `controlbridge.ai` — a live commercial
SOX 302/404 compliance platform. v0.6.0 renamed the project end-to-end:
PyPI packages (6 names), GitHub repo, CLI entry point, config file
(`controlbridge.yaml` → `evidentia.yaml`), frontend npm scope, and
all docs. No functional changes. See `RENAMED.md` at the repo root for
the full rationale, `CHANGELOG.md § 0.6.0` for the mechanical details,
and the `standing_rule_github_repo_names.md` memory note for the absolute
rule protecting the GitHub URL redirect.

## v0.7.0 — Evidence chain of custody (NEXT)

### Evidence integrity

Every OSCAL Assessment Results export carries a SHA-256 digest of each
evidence item. Optionally GPG-sign the whole AR document with the
operator's key. Creates a tamper-evident audit trail that survives
external-auditor scrutiny.

Originally planned for v0.6.0; displaced by the rename release and
pushed forward one minor.

### Shim yank

Yank the six `controlbridge-*` v0.5.1 shim wheels from PyPI as part
of the v0.7.0 cut (coordinated with a `CHANGELOG.md § Yanked` note).

## v0.7.0+ — Quality signals, more integrations, UI polish

### Risk-statement quality validator

Every AI-generated risk statement gets scored against NIST SP 800-30 /
IR 8286 criteria. Statements that fail validation are automatically
regenerated with corrective instructions. Produces audit-survivable
output that no other open-source tool guarantees.

### Additional collectors + integrations

Same infrastructure as the shipped AWS / GitHub / Jira implementations,
more sources:

- `evidentia-collectors[aws]` — IAM Access Analyzer (AC-3, AC-6, IA-2)
- `evidentia-collectors[github]` — Dependabot alerts (SI-2; requires
  `security-events` scope)
- `evidentia-collectors[okta]` — MFA enforcement, inactive users,
  privileged account counts (AC-2, IA-2, IA-5)
- `evidentia-integrations[servicenow]` — push to `sn_compliance_task`
  via REST with OAuth 2.0
- `evidentia-integrations[vanta]` and `[drata]` — custom test results
  push via their public APIs

### Compliance ROI scoring

Reframes the cross-framework efficiency feature as "close N gaps
across M frameworks with one remediation." CFOs and CISOs respond to
ROI framing in ways they don't respond to "coverage %".

### UI polish

- Auto-generated TypeScript types from FastAPI's OpenAPI schema
  (hand-authored in v0.4.0; auto-gen removes the drift class entirely)
- Tauri desktop packaging option for offline-first users who prefer
  an installable app over `evidentia serve`
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

v0.4.0 – v0.6.0 continue using `PYPI_API_TOKEN` for release authentication.
Target: migrate before v0.7.0 ships.

1. Configure a Trusted Publisher on PyPI's admin panel pointing at
   `allenfbyrd/evidentia` / `.github/workflows/release.yml` for each of
   the **12 packages** (6 primary `evidentia-*` + 6 shim `controlbridge-*`
   names until yank). Forgetting one breaks its release silently while
   the other 11 succeed — each is a per-package config.
2. Update `release.yml` to add `permissions: id-token: write` and
   drop the `password: ${{ secrets.PYPI_API_TOKEN }}` input.
3. Verify with a test patch release, then delete the `PYPI_API_TOKEN`
   GitHub repo secret.

Why deferred: switching without step 1 first breaks the release
pipeline. Step 1 requires ~2 hours of PyPI UI clicks that the release
workflow can't do from code.
