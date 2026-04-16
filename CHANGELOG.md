# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2026-04-16

Version-reporting truth-up patch. Follow-up to v0.1.1. No functional
changes — the installed packages already reported their real versions
to package managers (`pip show`, PyPI metadata); this patch fixes the
version strings that ControlBridge itself prints and embeds in
exported artifacts.

### Fixed

- `controlbridge version` CLI output reported `"0.1.0"` regardless of
  which version was actually installed, because every package's
  `__version__` was a hardcoded string literal. All five `__init__.py`
  modules now resolve `__version__` from `importlib.metadata` at
  import time — the reported version always matches the installed
  wheel and will never drift again.
- `GapReport.controlbridge_version`, `RiskRegister.controlbridge_version`,
  and `EvidenceBundle.controlbridge_version` all defaulted to `"0.1.0"`.
  They now use a `default_factory` that resolves the live
  `controlbridge-core` version, so exported audit artifacts accurately
  record the version that produced them.

### Added

- `controlbridge_core.models.common.current_version()` helper that
  returns the installed `controlbridge-core` version, used as the
  `default_factory` for all report-stamp fields.

## [0.1.1] - 2026-04-16

Legal remediation + registry truth-up patch. No API breakage — all changes
are additive optional fields on existing models. The **v0.2.0 big-bang
Phase 1.5 release** (exhaustive framework expansion to ~50 frameworks
across four redistribution tiers, plus `controlbridge catalog import`
for user-supplied licensed content, plus GitHub Actions refresh CI)
follows this patch.

### Fixed

- **SOC 2 TSC catalog replaced with Tier-C stub.** The v0.1.0 bundled
  `soc2-tsc.json` contained 12 paraphrased AICPA criteria whose titles
  closely mirrored the copyrighted AICPA Trust Services Criteria 2017
  text and embedded references to COSO Internal Control Integrated
  Framework principles. That content is removed. The stub ships 61
  criteria (CC1.1–CC9.2, A1.1–A1.3, C1.1–C1.2, P1.1–P8.1, PI1.1–PI1.5)
  with generic titles ("Common Criteria 6.1" rather than AICPA's full
  phrasing), `placeholder: true` on every entry, and a `license_url`
  pointing to the AICPA download page. `controlbridge catalog show
  soc2-tsc CC6.1` now renders `[Licensed content — see license_url for
  authoritative text.]` rather than a paraphrase. v0.2.0 will add
  `controlbridge catalog import` so users can load their own licensed
  copy without touching the installed package.
- **Bundled `nist-800-53-rev5_to_soc2-tsc.json` crosswalk** had the same
  AICPA-paraphrase exposure in `target_control_title` fields; those are
  now the generic stub titles matching the stub catalog. The 17
  source↔target mappings themselves are unchanged — the mapping concept
  (e.g., NIST AC-2 relates to SOC 2 CC6.1) is factual and uncopyrightable.
- **Registry no longer advertises 7 framework IDs with no backing data.**
  `FRAMEWORK_METADATA` in v0.1.0 listed 9 frameworks (`nist-800-53-rev5`,
  `nist-800-53-mod`, `nist-800-53-high`, `nist-csf-2.0`, `soc2-tsc`,
  `iso27001-2022`, `cis-controls-v8`, `cmmc-2-level2`, `pci-dss-4`) but
  only 2 had catalog JSON on disk. `controlbridge catalog list` produced
  7 "loaded: no" rows — misleading for a GRC tool whose users need to
  trust stated coverage. `FRAMEWORK_METADATA`, the `framework_files`
  dispatch in `loader.py`, and the `FrameworkId` enum are all trimmed
  to the 2 backed frameworks (`nist-800-53-mod`, `soc2-tsc`). `doctor`
  output now reports 2 frameworks, matching reality.
- **README "9 registered frameworks" claim corrected** to "2 bundled"
  with an explicit Tier-A/Tier-C explanation and a pointer to the v0.2.0
  roadmap.

### Added

- Optional fields on `CatalogControl`: `tier` (`"A"` through `"D"`),
  `license_required`, `license_url`, `placeholder`. All default to safe
  values; existing catalog JSONs continue to parse under `extra="forbid"`.
- Optional fields on `ControlCatalog`: same four plus `license_terms`
  (human-readable description of licensing constraints).
- New test `test_load_bundled_soc2_catalog_is_licensed_stub` locks in
  the Tier-C stub shape so a future accidental re-add of paraphrased
  AICPA content trips the test suite.

### Changed

- `FrameworkId` enum in `controlbridge_core.models.common` trimmed to
  `NIST_800_53_MOD` and `SOC2_TSC`. Callers using free-form `str`
  framework IDs (via `ControlMapping.framework`) are unaffected. The
  enum itself will be deprecated in v0.2.0 in favor of a
  manifest-driven registry and removed in v0.3.0.

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

[Unreleased]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/allenfbyrd/controlbridge/releases/tag/v0.1.0
