# ControlBridge

> **Bridge the gap between your controls and your frameworks.**

**ControlBridge** is an open-source, Python-first Governance, Risk, and Compliance
(GRC) platform that turns compliance from a spreadsheet problem into a software
problem. It provides composable building blocks for control gap analysis,
AI-generated risk statements, automated evidence collection, and compliance
reporting — all usable from a Python library, a CLI, or a REST API.

[![tests](https://github.com/allenfbyrd/controlbridge/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/allenfbyrd/controlbridge/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/controlbridge.svg)](https://pypi.org/project/controlbridge/)
![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)
![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)
![Status: Phase 1 MVP](https://img.shields.io/badge/status-Phase%201%20MVP-yellow.svg)
[![Code of Conduct](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

---

## The problem

Modern GRC is stuck in 2005. The typical compliance program runs on:

- **Spreadsheets** that get copy-pasted between auditors, engineers, and exec staff
- **Vendor GRC suites** that cost $50K-500K per year, lock you in, and still require
  weeks of manual work to map one framework to another
- **Point solutions** that handle one piece (a vulnerability scanner, a policy
  tracker, a questionnaire manager) but can't talk to each other
- **Consultants** who re-learn your environment from scratch every audit cycle

Meanwhile, the compliance workload keeps growing. A single fintech or healthcare
SaaS company today might simultaneously be in scope for **SOC 2, PCI DSS 4.0,
HIPAA, GDPR, CCPA, ISO 27001, and NYDFS Part 500** — seven frameworks with
substantial overlap, each demanding its own evidence, gap analysis, and risk
documentation.

The same control (say, "MFA on all privileged accounts") satisfies requirements
in all seven. But because each framework uses different vocabulary, numbering,
and organization, compliance teams end up documenting the same control seven
different ways — and audit season becomes a months-long exercise in cross-referencing.

**This is a software problem.** It should be solved the way software problems
get solved: with composable libraries, structured data, version control, and
automation.

## Why ControlBridge exists

ControlBridge is built on four principles:

1. **Open standards, not vendor lock-in.** Inputs and outputs use
   [OSCAL](https://pages.nist.gov/OSCAL/) — NIST's open standard for control
   catalogs and assessment results. If you outgrow ControlBridge, your data
   travels with you.

2. **Library-first, CLI-second, API-third.** The Python library is the
   canonical interface. The CLI is a thin wrapper. The REST API is a thin
   wrapper. Everything ControlBridge can do via the CLI, it can do from a
   Python script — which means you can embed it in CI pipelines, compliance
   portals, or custom integrations.

3. **AI where it helps, not where it hurts.** ControlBridge uses LLMs for
   tasks where language understanding is the bottleneck (writing NIST SP 800-30
   risk statements from a gap, validating whether a policy PDF actually
   covers a control). It uses deterministic code for tasks where correctness
   matters (OSCAL parsing, gap arithmetic, cross-framework mapping).

4. **Provider-agnostic LLM access.** All AI features route through
   [LiteLLM](https://docs.litellm.ai/) + [Instructor](https://python.useinstructor.com/),
   giving you structured Pydantic output from any model — OpenAI, Anthropic,
   Google, Azure, Ollama, vLLM, or any OpenAI-compatible endpoint. No vendor
   lock-in on the AI layer either.

## Who it's for

- **Security engineers** at startups and mid-size companies who need to
  hit SOC 2 Type II without hiring a full compliance team
- **GRC consultants** who want to stop rebuilding the same spreadsheets
  for every engagement
- **Platform teams** who want to embed gap analysis into their CI pipelines
  and catch drift before the auditor does
- **CISO offices** that want a real audit trail on risk decisions, backed
  by versioned structured data instead of Slack threads
- **Anyone** who has ever said "I know this NIST control is the same as
  this SOC 2 criterion, but I don't want to re-document it for the fifth time"

---

## Current status: 82 frameworks bundled, 501 tests passing

**v0.4.0-alpha.1 (April 2026)** is the **"Accessible GRC"** release.
ControlBridge grows beyond the CLI with a FastAPI REST server, a
React + shadcn/ui web UI (localhost-only, WCAG 2.1 AA via Radix
primitives), an air-gapped mode (`--offline` flag +
`doctor --check-air-gap` validator), and a new sixth workspace
package (`controlbridge-api`).

Install the UI via the new `[gui]` extra:

```bash
uv tool install "controlbridge[gui]"
# or
pip install "controlbridge[gui]"

controlbridge serve   # web UI at http://127.0.0.1:8000
```

See [`docs/gui/README.md`](docs/gui/README.md) for the full UI guide and
[`docs/air-gapped.md`](docs/air-gapped.md) for air-gapped deployments.
The alpha.1 ships the read-only web UI (Home / Dashboard / Frameworks /
Settings); the interactive onboarding wizard, Gap Analyze form, Gap
Diff picker, and Risk Generate streaming page land in alpha.2.

**v0.3.1 (April 2026)** added three realistic end-to-end example
scenarios — Meridian Financial (fintech), Acme Healthtech (HIPAA),
Northstar Systems (DoD contractor) — with pre-generated gap
snapshots and a full walkthrough that exercises every feature
added through v0.3.0. The repo dog-foods its own GitHub Action
(`.github/workflows/controlbridge.yml`) on every PR against the
Meridian v2 inventory. Start at
[`examples/WALKTHROUGH.md`](examples/WALKTHROUGH.md). Also fixed one
latent bug in `compute_gap_diff` that only affected library-level
(non-CLI) callers — flagged by the new integration-test regression
guard.

**v0.3.0 (April 2026)** is the **compliance-as-code release**:

- **`controlbridge gap diff`** — compare two gap-analysis snapshots,
  classify each gap as opened / closed / severity-changed / unchanged.
  Pair with `--fail-on-regression` in a GitHub Action to block PRs
  that make compliance posture worse. No commercial GRC tool does this
  at the PR level. See [`docs/github-action/README.md`](docs/github-action/README.md)
  for the drop-in workflow.
- **`controlbridge explain <control_id>`** — LLM-generated plain-English
  translation of any framework's control text. Answers the questions
  engineers actually ask ("what does this mean, why should I care,
  what do I do?") instead of quoting the NIST legal prose verbatim.
  Cached to disk per (framework, control, model, temperature) so
  repeat lookups are free.

Also: the `FrameworkId` enum (deprecated in v0.2.0) is removed; mypy
CI is now strict (no more `continue-on-error`); +32 new tests.

**v0.2.1 (April 2026)** was the correctness patch that:

- Bundles the full **NIST SP 800-53 Rev 5** catalog (1,196 controls,
  verbatim from `usnistgov/oscal-content`) plus the four resolved
  **Low / Moderate / High / Privacy baselines** — so `gap analyze
  --framework nist-800-53-rev5-moderate` actually runs against the real
  287-control baseline instead of a 16-control sample.
- Rewrites the FedRAMP baselines with real NIST text (v0.2.0 shipped them
  as pointer-only stubs).
- Replaces the always-LOW gap effort estimator with a keyword-aware
  hybrid heuristic, so the prioritized roadmap actually surfaces
  easy-win controls.
- Wires the `controlbridge.yaml` project config loader that `init` has
  been generating since v0.1.0 but nothing read. Precedence:
  **CLI flag > env var > yaml > built-in default**.
- Persists gap reports to a user-dir store, making `risk generate
  --gap-id GAP-…` work without re-running `gap analyze`.
- +221 new tests (131 → 352 passing); all `controlbridge catalog`
  subcommands now covered; OSCAL profile resolver tested end-to-end.

See [`CHANGELOG.md`](CHANGELOG.md) for the full v0.2.1 entry and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the v0.3.0+ plan.

### What works today

- **Gap analysis against 77 bundled frameworks** across four redistribution
  tiers:

  - **Tier A — US federal (25 frameworks, verbatim public domain):**
    NIST 800-53 Moderate sample, 800-171 Rev 2/Rev 3, 800-172, CSF 2.0,
    AI RMF 1.0, Privacy Framework 1.0, SSDF 800-218; FedRAMP Rev 5
    Low/Moderate/High/LI-SaaS baselines; CMMC 2.0 Levels 1/2/3; HIPAA
    Security/Privacy/Breach Notification Rules; GLBA Safeguards, NY DFS
    500, NERC CIP v7, FDA 21 CFR Part 11, IRS 1075, CMS ARS, FBI CJIS v6,
    CISA Cross-Sector CPGs.

  - **Tier A — International (6 frameworks):** UK NCSC CAF 3.2, UK Cyber
    Essentials, Australian Essential Eight, Australian ISM, Canada
    ITSG-33, New Zealand NZISM.

  - **Tier D — Statutory obligations (21 frameworks, government edicts,
    uncopyrightable):** EU GDPR, EU AI Act, EU NIS2, EU DORA, UK DPA 2018,
    Canada PIPEDA, plus all 15 comprehensive US state privacy laws (CA
    CCPA/CPRA, VA, CO, CT, UT, TX, OR, DE, MT, IA, FL, TN, NH, MD, MN).

  - **Tier C — Licensed stubs (20 frameworks):** ISO/IEC 27001:2022,
    27002:2022, 27017, 27018, 27701, 42001 (AI), 22301 (BC); PCI DSS
    v4.0.1; HITRUST CSF v11; COBIT 2019; SWIFT CSCF 2024; CIS Controls
    v8.1 plus 5 CIS Benchmarks (AWS, Azure, GCP, Kubernetes, RHEL 9);
    Secure Controls Framework 2024; IEC 62443; SOC 2 TSC. Copyrighted
    authoritative text isn't bundled — ships with public clause numbering
    plus a `controlbridge catalog import` hook for your licensed copy.

  - **Tier B — Threat and vulnerability catalogs (4 frameworks):** MITRE
    ATT&CK Enterprise (41 techniques), MITRE CWE Top 25 (2024), MITRE
    CAPEC sample, CISA KEV sample (Log4Shell, MOVEit, EternalBlue, etc).

- **Six bundled crosswalks:** NIST CSF 2.0 → 800-53, FedRAMP Moderate →
  CMMC L2, NIST 800-53 → HIPAA Security, ISO 27001 → NIST 800-53, VCDPA →
  CCPA/CPRA, NIST 800-53 → SOC 2 TSC.

- **Multi-format inventory parsing.** Load your controls from YAML, CSV, JSON
  (including OSCAL component-definition), or any format with fuzzy-matched
  column headers. Status normalization handles "implemented", "partial",
  "planned", "in progress", "missing", etc.

- **Cross-framework crosswalk engine.** Bidirectional mapping index: ask
  "what NIST 800-53 controls satisfy my SOC 2 criterion?" or "what CMMC
  Level 2 controls match my FedRAMP Moderate posture?". v0.2.0 ships six
  bundled crosswalks (118 mappings total). Custom crosswalks are
  drop-in JSON files in `catalogs/data/mappings/`.

- **Prioritized gap reports.** Severity by implementation state, effort-weighted
  priority scores, efficiency opportunities (controls that close gaps in 2+
  frameworks simultaneously), and a prioritized remediation roadmap.

- **Four output formats:** JSON (canonical), CSV (flat), Markdown (human
  review), and OSCAL Assessment Results (for audit handoff and tool interop).

- **AI risk statement generator.** NIST SP 800-30 Rev 1 compliant risk
  statements from gaps + system context. Uses Instructor to enforce the
  `RiskStatement` Pydantic schema on LLM output, with automatic retries on
  validation failure. Works with any LiteLLM-supported model.

- **Typer + Rich CLI** with `init`, `catalog list/show/crosswalk/import/
  where/license-info/remove`, `gap analyze`, `risk generate`, `doctor`,
  and `version` commands. `catalog list` supports `--tier` and `--category`
  filters; `catalog import` accepts direct JSON or an OSCAL profile (via
  `--profile <profile.json> --catalog <source.json>`).

- **392 passing pytest tests** covering models, catalog loading (with a
  parametric smoke test per bundled framework), recursive enhancement
  flattener for NIST Rev 5 3-level IDs, tier invariants, OSCAL profile
  resolution, user-import directory precedence, `FrameworkId` deprecation,
  crosswalk bidirectionality, multi-format inventory parsing, severity
  calculation, and all four report exporters.

### What Phase 1 explicitly does NOT include

Setting expectations matters. Phase 1 does NOT yet include:

- Evidence collectors for AWS, Azure, GCP, GitHub, or Okta (Phase 2)
- LLM-based evidence validation (Phase 3)
- Jira or ServiceNow push integrations (Phase 2)
- The FastAPI REST server (`controlbridge serve`)
- A web UI
- Full-depth NIST 800-53 Rev 5 catalog (~323 controls with 3-level
  enhancements) — v0.2.0 ships the 16-control Moderate sample plus
  pointer-style FedRAMP baselines that the OSCAL profile resolver can
  turn into resolved 149/287/369-control baselines once you supply the
  full upstream NIST OSCAL catalog via `catalog import --profile`.
  Direct bundling of the full NIST Rev 5 catalog is planned for v0.2.1
  via the upstream refresh CI workflow.
- Authoritative control text for copyrighted frameworks (ISO 27001/27002,
  SOC 2 TSC, PCI DSS, HITRUST CSF, etc.). These frameworks will ship as
  **Tier C stubs** in v0.2.0 — public clause numbering only, with a
  `controlbridge catalog import` command to load your own licensed copy.

---

## Quick start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 0.4+ (recommended) or pip

### Install from PyPI

```bash
pip install controlbridge
```

This installs the `controlbridge` and `cb` CLI commands, plus the four workspace
sub-packages as transitive dependencies (`controlbridge-core`, `controlbridge-ai`,
`controlbridge-collectors`, `controlbridge-integrations`).

### Install from source (for contributors)

```bash
git clone https://github.com/allenfbyrd/controlbridge.git
cd controlbridge
uv sync --all-packages
```

This downloads Python 3.12 (if needed), creates a `.venv`, and installs all
five workspace packages in editable mode.

### Run the smoke test

```bash
uv run pytest tests/ -q
# Expected: 22 passed in ~0.3s
```

### End-to-end walkthrough with sample data

ControlBridge ships with a realistic fictional fintech scenario in
[`examples/meridian-fintech/`](examples/meridian-fintech/). Walk through it in five steps:

```bash
# 1. Verify installation
uv run controlbridge doctor

# 2. Explore available frameworks
uv run controlbridge catalog list

# 3. Inspect a specific control
uv run controlbridge catalog show nist-800-53-mod --control SI-4

# 4. See how one framework maps to another
uv run controlbridge catalog crosswalk \
  --source nist-800-53-mod --target soc2-tsc --control AC-2

# 5. Run gap analysis on the Meridian Financial sample inventory
cd examples/meridian-fintech
uv --project ../.. run controlbridge gap analyze \
  --inventory my-controls.yaml \
  --frameworks nist-800-53-mod,soc2-tsc \
  --output report.md --format markdown \
  --min-efficiency-frameworks 2
```

Expected output: a 17-gap report against 28 required controls, 39.3% coverage,
11 critical / 5 high / 1 medium severities, with the top of the priority queue
dominated by monitoring/detection gaps (CC7.1, CC7.2, SI-4, AU-6).

### Generate AI risk statements

Requires an LLM API key. Any LiteLLM-supported provider works:

```bash
export OPENAI_API_KEY=sk-...            # or ANTHROPIC_API_KEY, etc.

uv --project ../.. run controlbridge risk generate \
  --context system-context.yaml \
  --gaps report.json \
  --model gpt-4o \
  --output risks.json \
  --limit 5
```

This produces five validated `RiskStatement` objects (NIST SP 800-30 structure)
for the five highest-priority gaps.

### Starting your own project

```bash
# From an empty directory
uv run controlbridge init

# Creates:
#   controlbridge.yaml       — config with defaults
#   my-controls.yaml         — template control inventory
#   system-context.yaml      — template system context
#   .controlbridge/          — local storage
```

Edit `my-controls.yaml` with your real inventory and run `controlbridge gap analyze`.

---

## Architecture

ControlBridge is a **uv workspace monorepo** of five composable Python packages:

| Package                      | Role                                                                        |
| ---------------------------- | --------------------------------------------------------------------------- |
| `controlbridge-core`         | Pydantic data models, OSCAL catalog loader, crosswalk engine, gap analyzer  |
| `controlbridge-ai`           | LiteLLM + Instructor client, risk statement generator, evidence validator  |
| `controlbridge-collectors`   | Evidence collection agents for cloud and SaaS systems *(Phase 2)*          |
| `controlbridge-integrations` | Jira and ServiceNow push integrations *(Phase 2)*                           |
| `controlbridge`              | Meta-package: Typer/Rich CLI and FastAPI REST server                        |

### Data flow (Phase 1)

```
┌─────────────────┐   ┌─────────────────┐   ┌────────────────────┐
│ my-controls.yaml│   │  OSCAL catalogs │   │ framework mappings │
│       .csv      │   │  (77 bundled;   │   │    (crosswalks)    │
│       .json     │   │  manifest-driven) │   └──────────┬───────┘
└────────┬────────┘   └────────┬────────┘              │
         │                     ▼                       ▼
         │           ┌──────────────────────────────────────┐
         └──────────▶│         GapAnalyzer                  │
                     │  normalize → match → score → rank    │
                     └──────────────────┬───────────────────┘
                                        │
                     ┌──────────────────┴───────────────────┐
                     │                                      │
                     ▼                                      ▼
         ┌──────────────────────┐              ┌──────────────────────┐
         │  GapAnalysisReport   │              │   RiskStatementGen   │
         │  (JSON/CSV/MD/OSCAL) │              │   (NIST SP 800-30)   │
         └──────────────────────┘              └──────────┬───────────┘
                                                          │
                                                          ▼
                                              ┌──────────────────────┐
                                              │  LiteLLM+Instructor  │
                                              │  (any LLM provider)  │
                                              └──────────────────────┘
```

### Key design decisions

- **Pydantic v2 everywhere** with `ConfigDict(use_enum_values=True, extra="forbid", str_strip_whitespace=True)`. Structured data, strict validation, JSON-roundtripping for free.
- **OSCAL as the lingua franca.** Inputs parse OSCAL catalogs and component-definitions. Outputs include OSCAL Assessment Results. Your data is portable.
- **Instructor for AI structured output.** LLMs return raw text; Instructor enforces a Pydantic schema and automatically retries on validation failure. No regex parsing of LLM output.
- **Hatchling build backend** with `[tool.hatch.build.targets.wheel] packages = ["src/..."]` and `[dependency-groups] dev = [...]` (the modern uv spec, not the deprecated `[tool.uv] dev-dependencies`).

---

## Roadmap

### Phase 1 — MVP (this release)
- [x] Core data models
- [x] OSCAL catalog loader + crosswalk engine
- [x] Multi-format inventory parser
- [x] Gap analyzer with priority scoring
- [x] Report exporters (JSON/CSV/Markdown/OSCAL-AR)
- [x] AI risk statement generator
- [x] CLI (init, catalog, gap, risk, doctor)
- [x] Sample data + end-to-end walkthrough
- [x] **Phase 1.5 (v0.2.0 big-bang):** exhaustive framework expansion
      — full upstream NIST 800-53 Rev 5 OSCAL (~1189 controls + Low/Mod/High/Privacy baselines),
      NIST 800-171 r2/r3, 800-172, CSF 2.0, AI RMF, SSDF, Privacy Framework;
      FedRAMP Rev 5 baselines; CMMC 2.0 L1/L2/L3; CJIS, CISA CPGs, HIPAA,
      GLBA, NY DFS 500, NERC CIP, FDA 21 CFR Pt 11, IRS 1075, CMS ARS;
      EU GDPR/AI Act/NIS2/DORA, UK NCSC CAF, Essential Eight, ACSC ISM,
      Canada ITSG-33/PIPEDA, NZISM; 15 US state privacy laws; Tier-C stubs
      for ISO 27001/27002/27017/27018/27701/42001/22301/9001, SOC 2 TSC,
      PCI DSS 4.0, HITRUST, COBIT, SWIFT CSCF, CIS Controls + Benchmarks,
      SCF, IEC 62443; MITRE ATT&CK, CWE, CAPEC, CISA KEV;
      `controlbridge catalog import` for user-licensed Tier-C content;
      GitHub Actions refresh CI for upstream change detection.

### Phase 2 — Evidence Collection (next)
- [ ] Base collector architecture with `check_connection()`, `collect()`, `get_supported_controls()`
- [ ] **AWS collector** — Config rules, Security Hub findings, IAM policies, CloudTrail, Audit Manager
- [ ] **GitHub collector** — branch protection, required reviews, Actions runners, secret scanning status
- [ ] **Okta collector** — MFA enforcement, session policies, user lifecycle evidence
- [ ] **Azure collector** — Policy, Defender for Cloud, Entra ID
- [ ] **GCP collector** — Security Command Center, Cloud Asset Inventory
- [ ] **Evidence bundle storage** — local file, SQLite, git-backed
- [ ] **Scheduled collection** with cron or CI triggers
- [ ] **Jira / ServiceNow integration** — push gaps as tickets with severity and remediation guidance

### Phase 3 — AI Evidence Validation
- [ ] Evidence-to-control relevance scoring (is this screenshot actually proof of MFA?)
- [ ] Freshness / staleness detection per framework (SOC 2 = 90 days, NIST = 365)
- [ ] Multi-modal validation (PDFs, screenshots, log exports, JSON)
- [ ] Coverage heatmaps

### Phase 4 — Platform
- [ ] FastAPI REST server (`controlbridge serve`)
- [ ] Multi-tenant database backend (PostgreSQL)
- [ ] Web UI for non-technical reviewers
- [ ] Audit trail with cryptographic evidence hashes
- [ ] Cost analytics (LLM spend per control / per framework)

### Phase 5 — Ecosystem
- [ ] Plugin system for custom collectors
- [ ] OSCAL catalog marketplace / community contributions
- [ ] Integration with policy-as-code tools (OPA, Cedar)
- [ ] Terraform provider for compliance-as-code

See [`ControlBridge-Architecture-and-Implementation-Plan.md`](ControlBridge-Architecture-and-Implementation-Plan.md)
for the full canonical plan (312 KB, ~8200 lines) including all code sketches, data
flows, and technology rationales.

---

## Development

### Project layout

```
ControlBridge/
├── packages/
│   ├── controlbridge-core/         # Pydantic models, catalogs, gap analyzer
│   ├── controlbridge-ai/           # LiteLLM client, risk generator
│   ├── controlbridge-collectors/   # (Phase 2)
│   ├── controlbridge-integrations/ # (Phase 2)
│   └── controlbridge/              # CLI + API meta-package
├── tests/
│   ├── fixtures/                   # Sample inventories for tests
│   └── unit/                       # Unit + end-to-end tests
├── examples/
│   └── meridian-fintech/           # Realistic walkthrough sample
├── .github/
│   ├── workflows/test.yml          # CI: pytest matrix + ruff
│   └── ISSUE_TEMPLATE/             # Bug report / feature request
└── pyproject.toml                  # uv workspace root
```

### Run tests

```bash
uv run pytest tests/ -q                       # All tests
uv run pytest tests/unit/ -v                  # Unit tests with verbose output
uv run pytest tests/unit/test_gap_analyzer/   # One subpackage
```

### Add a new framework catalog

1. Drop an OSCAL catalog JSON file in `packages/controlbridge-core/src/controlbridge_core/catalogs/data/<framework-id>.json`.
2. Register its metadata in `catalogs/registry.py` under `FRAMEWORK_METADATA`.
3. Optionally add crosswalks in `catalogs/data/mappings/`.
4. Run `controlbridge catalog list` — your framework should appear.

### Code style

- Python 3.12+ syntax: `str | None`, `list[str]`, `from datetime import UTC`
- `from __future__ import annotations` at the top of every module
- Ruff + mypy (configured in `pyproject.toml`)

---

## Contributing

Phase 1 is complete and the architecture is stable. High-value contribution
areas:

- **Production OSCAL catalogs** — drop-in JSON files from upstream sources
- **Additional crosswalks** — especially ISO 27001 ↔ NIST 800-53 and PCI DSS ↔ SOC 2
- **Phase 2 collectors** — AWS, GitHub, and Okta are the highest priority
- **Test coverage** — particularly edge cases in CSV header matching and OSCAL parsing

---

## License

[Apache License 2.0](LICENSE)

---

## Acknowledgments

ControlBridge stands on the shoulders of excellent open-source projects:

- **[NIST OSCAL](https://pages.nist.gov/OSCAL/)** — the structured data standard that makes framework interop possible
- **[Pydantic](https://docs.pydantic.dev/)** — type-safe data models without the boilerplate
- **[LiteLLM](https://docs.litellm.ai/)** — unified LLM access across every provider
- **[Instructor](https://python.useinstructor.com/)** — structured output extraction from LLMs
- **[Typer](https://typer.tiangolo.com/)** and **[Rich](https://rich.readthedocs.io/)** — the CLI is only as good as the framework
- **[uv](https://docs.astral.sh/uv/)** — Python packaging that finally feels modern

## AI assistance

This project was developed alongside AI platforms.

Models used: Claude Opus 4.6, Claude Opus 4.7, Sonar Deep Research
