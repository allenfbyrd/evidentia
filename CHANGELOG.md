# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-16

Initial release: **Phase 1 MVP** — a working, tested, end-to-end gap analyzer
with AI risk statement generation. ControlBridge is an open-source,
Python-first GRC platform that treats compliance as a software problem:
composable libraries, structured data, open standards (OSCAL), and AI only
where language understanding is the bottleneck.

### Added

- **uv workspace monorepo** with 5 packages: `controlbridge-core`,
  `controlbridge-ai`, `controlbridge-collectors`, `controlbridge-integrations`,
  and the `controlbridge` CLI meta-package
- **Pydantic v2 data models** for controls, catalogs, gaps, risks, evidence,
  and findings
- **OSCAL catalog loader and crosswalk engine** with 9 registered frameworks
  and bundled NIST 800-53 Moderate + SOC 2 TSC catalogs
- **Multi-format inventory parser** supporting YAML, CSV (with fuzzy header
  matching), OSCAL component-definition, and CISO Assistant export formats
- **Gap analyzer** with severity calculation, effort-weighted priority
  scoring, and cross-framework efficiency analysis
- **Four report exporters**: JSON, CSV, Markdown, OSCAL Assessment Results
- **AI Risk Statement Generator** (NIST SP 800-30 Rev 1) using LiteLLM +
  Instructor for provider-agnostic structured LLM output
- **Typer + Rich CLI**: `init`, `catalog` (list/show/crosswalk), `gap analyze`,
  `risk generate`, `doctor`, `version`
- **End-to-end walkthrough sample** (Meridian Financial fintech scenario)
  exercising every feature with 20 controls across two frameworks
- **22 passing pytest tests** covering models, catalogs, crosswalks,
  multi-format parsing, gap scoring, and all four exporters
- **GitHub Actions CI** (pytest matrix on ubuntu/windows/macos + ruff lint)
- **Code of Conduct** (Contributor Covenant v2.1 by reference),
  `CONTRIBUTING.md`, and issue templates

### Known limitations (intentional Phase 1 scope)

- Evidence collectors for AWS, GitHub, Okta, Azure, GCP — planned for Phase 2
- Jira and ServiceNow push integrations — planned for Phase 2
- LLM-based evidence validation — planned for Phase 3
- FastAPI REST server and web UI — planned for Phase 4
- Production-sized OSCAL catalogs: the bundled NIST 800-53 Moderate catalog
  has 16 hand-curated controls for demonstration, not the full ~323 from the
  NIST OSCAL content repo — planned for Phase 1.5

[Unreleased]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/allenfbyrd/controlbridge/releases/tag/v0.1.0
