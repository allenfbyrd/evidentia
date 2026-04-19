# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-04-19

Comprehensive examples + dogfooded GitHub Action + one latent-bug fix
surfaced by the new integration tests. No new features, no breaking
API changes; scope is "prove every v0.3.0 feature works end-to-end
against realistic data."

### Added — three realistic end-to-end scenarios

- **`examples/meridian-fintech-v2/`** — 48-control inventory against
  `nist-800-53-rev5-moderate` + `soc2-tsc` + `eu-gdpr`. Baseline
  (`my-controls.yaml`) + PR branch (`my-controls-pr.yaml`) engineered
  to produce every `gap diff` classification (opened + closed +
  severity_increased + severity_decreased + unchanged). Ships with
  pre-generated `snapshots/baseline.json` + `snapshots/pr-branch.json`
  + `snapshots/pr-diff.md` for zero-setup demo. Uses the v0.2.1
  `controlbridge.yaml` schema (flat `frameworks:`, `llm.model`,
  `organization`, `system_name`). Mixes NIST-pub (`AC-2(1)`) and
  NIST-OSCAL (`ac-2.3`) ID conventions to exercise the normalizer.
  `user-catalog-demo/soc2-tsc-licensed.json` is a fake "licensed
  AICPA copy" fixture for the `catalog import` shadow-precedence
  demo.

- **`examples/acme-healthtech/`** — 34-control HIPAA-covered-entity
  scenario. Frameworks: `hipaa-security` + `hipaa-privacy` +
  `hipaa-breach` + `nist-800-53-rev5-moderate`. Showcases HIPAA's
  `164.308(a)(1)(i)` dotted-section ID style and multi-rule cross-
  framework efficiency where one control satisfies 3–4 frameworks.

- **`examples/dod-contractor/`** — 30-control CMMC Level 2 +
  NIST 800-171 Rev 2 scenario for DoD-contract workflows. Uses
  `CMMC.L2-3.1.1`-style prefixed IDs alongside plain `3.1.1`
  dotted IDs to exercise both conventions in one report. Includes
  a realistic DIBCAC-style gap (SIEM correlation missing).

- **`examples/WALKTHROUGH.md`** — tour document with exact command
  sequences for every v0.3.0 feature, keyed to each scenario.

- **`scripts/demo/generate_snapshot_pair.py`** — regeneration helper
  that rebuilds Meridian v2's `baseline.json` / `pr-branch.json` /
  `pr-diff.md` from the committed inventories. Use it after a
  NIST catalog refresh to keep the README's expected counts in sync.

- **`.github/workflows/controlbridge.yml`** — ControlBridge dog-
  fooding its own GitHub Action. On every PR touching the Meridian
  v2 inventory or the bundled catalogs, the workflow runs `gap
  analyze` + `gap diff` and posts the result as a PR comment;
  `--fail-on-regression` gates merging. Uses the local `uv sync`
  build so the action runs against whatever's on the PR branch,
  not the last-published PyPI wheel.

### Added — integration tests

- `tests/integration/test_examples/test_examples_smoke.py` — 8 cases
  covering each scenario's `gap analyze` pipeline, the Meridian v2
  `gap diff` every-classification regression guard, CSV inventory
  parse, and config-loader deprecation behavior (legacy meridian
  emits DeprecationWarning on its v0.1.x yaml schema; Meridian v2
  emits no warnings on the v0.2.1 schema).

### Fixed — `_is_open` gap-status filter on in-memory diff path

`controlbridge_core.gap_diff._is_open()` used `str(gap.status)` to
compare against `GapStatus.OPEN.value`. On the JSON-roundtrip path
(CLI: `analyze` → save JSON → load JSON → `diff`), Pydantic
coerces the enum to its string value and the comparison works.
On the in-memory path (library users calling `compute_gap_diff()`
directly against freshly-computed `GapAnalysisReport`s with
`use_enum_values=True` active), `gap.status` is still a `GapStatus`
instance and `str(enum)` returns `"GapStatus.OPEN"` rather than
`"open"` — so `_is_open()` returned `False` for every gap and the
diff summary reported all zeros. The v0.3.1 fix normalizes via
`gap.status.value if isinstance(gap.status, GapStatus) else ...`
so both paths work identically. Flagged by the new Meridian v2
every-classification integration test — this bug never surfaced
in v0.3.0 because no test exercised the in-memory path.

### Fixed — Windows console Unicode handling in `gap diff` output

The v0.3.0 Rich console renderer used Unicode glyphs (`✗`, `✓`,
🆕, 📈) that crashed on Windows legacy consoles (cp1252 encoding):
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2717'`.
v0.3.1 uses ASCII-only glyphs in the Rich path (`FAIL` /
`PASS` / section headers without emoji). The markdown and
github-annotation renderers keep their emoji — those target
UTF-8-clean surfaces (PR comments, Actions logs).

### Changed

- **Legacy `examples/meridian-fintech/`** gets a deprecation
  banner at the top of its README pointing at
  `examples/meridian-fintech-v2/`. No files deleted — all existing
  links still work.

### Tests: 384 → **392 passing** (+8)

New integration tests exercise the examples + config-loader
deprecation path end-to-end.

## [0.3.0] - 2026-04-17

The **"compliance-as-code" release.** Two user-facing feature areas plus
deprecation cleanup and a fully-strict mypy CI gate. No breaking API
changes to existing commands; new commands and a removed deprecated
enum.

### Added — PR-level compliance checking: `controlbridge gap diff`

Compare two :class:`GapAnalysisReport` snapshots and classify each gap
into one of five states (opened, closed, severity_increased,
severity_decreased, unchanged). Drop-in for CI/CD pipelines: every pull
request can now run `controlbridge gap diff --fail-on-regression` to
block merges that make the compliance posture worse.

- New module `controlbridge_core.gap_diff` with `compute_gap_diff()`,
  `render_markdown()` (PR-comment-friendly), and
  `render_github_annotations()` (`::error::` / `::warning::` / `::notice::`
  lines that surface inline on the Actions Checks page).
- New models `GapDiff`, `GapDiffEntry`, `GapDiffSummary` (all Pydantic-
  validated and JSON-serializable).
- New CLI: `controlbridge gap diff [--base PATH] [--head PATH]
  [--fail-on-regression] [--format console|json|markdown|github]
  [--output PATH]`. When `--base` / `--head` are omitted, auto-picks
  the two most-recent reports from the v0.2.1 gap store.
- **Control-ID normalization in diff**: a gap `AC-2(1)` in base and
  `ac-2.1` in head is correctly recognized as the same gap (uses the
  v0.2.1 normalizer, no false opened+closed pair).
- **Status-aware**: REMEDIATED / ACCEPTED / NOT_APPLICABLE gaps are
  excluded from the diff (they're not "open gaps" to regress on). An
  ACCEPTED gap in base that re-appears OPEN in head counts as a
  regression (acceptance was revoked).
- **GitHub Action scaffolding**: new `docs/github-action/README.md`
  (full setup guide) + `docs/github-action/workflow-example.yml`
  (drop-in `.github/workflows/controlbridge.yml` template). The
  companion reusable action `allenfbyrd/controlbridge-action` is
  scoped for v0.3.1.

### Added — Plain-English control explanations: `controlbridge explain`

Translate authoritative-but-opaque framework control text into
actionable engineer-and-executive language. Every explanation is
cached on disk per (framework, control, model, temperature) tuple —
you pay the LLM cost once per lookup.

- New module `controlbridge_ai.explain` with:
  - `PlainEnglishExplanation` Pydantic model (strict schema: plain
    English summary, why-it-matters paragraph, 3-8 what-to-do bullets,
    effort estimate, optional common-misconceptions paragraph).
  - `ExplanationGenerator` — Instructor-backed LLM pipeline on top of
    LiteLLM. Works with any LiteLLM-supported provider
    (OpenAI / Anthropic / Google / Ollama / etc).
  - Disk cache at `<platformdirs-cache>/controlbridge/explanations/`
    keyed by SHA-256 of (framework, control, model, temperature).
    Override via `CONTROLBRIDGE_EXPLAIN_CACHE_DIR`.
- New CLI: `controlbridge explain control <id> [--framework FW]
  [--model MODEL] [--refresh] [--format panel|markdown|json]
  [--output PATH]`. Pre-flight check warns if no API-key env var
  matches the picked model (e.g., using `claude-*` without
  `ANTHROPIC_API_KEY`).
- Cache management: `controlbridge explain cache where` (prints the
  cache directory), `controlbridge explain cache clear` (wipes it).
- Reads defaults from `controlbridge.yaml` using the v0.2.1 config
  loader (flag > env > yaml > built-in default).

### Changed

- **`FrameworkId` enum removed** from `controlbridge_core.models.common`.
  Deprecated in v0.2.0 with a module-level `__getattr__` that emitted
  `DeprecationWarning`; v0.3.0 drops the enum and the getattr hook
  entirely. `ControlMapping.framework` has always been `str`; users
  who were relying on the enum value should use the plain string
  framework ID (e.g., `"nist-800-53-rev5"`) or
  `controlbridge_core.catalogs.manifest.load_manifest()` for
  programmatic discovery.
- **mypy CI job flipped from advisory to strict.** v0.2.1 added
  `--strict-optional` as `continue-on-error: true` to avoid blocking
  releases on pre-existing annotation gaps; v0.3.0 fixed those 7
  gaps and dropped the `continue-on-error`. Enabled the
  `pydantic.mypy` plugin in `[tool.mypy]` so every
  `Model.model_validate*()` return type is correctly inferred.
  Added `types-PyYAML` and `pydantic` to the dev dependency group so
  mypy can find them.
- **`controlbridge gap analyze`**: no behavior change, but the gap
  store write at the end of each run is now a required dependency
  of `gap diff`'s auto-picker. Unchanged from v0.2.1 users'
  perspective.

### Tests: 352 → **384** passing (+32 new)

- `tests/unit/test_gap_analyzer/test_gap_diff.py` — 16 cases covering
  every diff-status classification, control-ID normalization across
  notation styles, REMEDIATED/ACCEPTED status handling, sort order,
  and both Markdown / GitHub-annotation renderers.
- `tests/unit/test_ai/test_explain.py` — 19 cases covering the
  explanation cache (key determinism, model/temperature sensitivity,
  corruption handling), `ExplanationGenerator` behavior (cache hit
  skips LLM, refresh bypasses cache, echo-field defensive override),
  and the `PlainEnglishExplanation` schema's strict-validation edges.
- `tests/unit/test_models/test_framework_id_deprecation.py` — removed
  (the deprecation path and the enum are both gone).

### Infrastructure / hygiene

- Inter-package dependency pins bumped from `>=0.2.0,<0.3.0` to
  `>=0.3.0,<0.4.0` across all 5 packages.
- `scripts/catalogs/` generator scripts unchanged — v0.2.1 NIST
  bundling is stable.

### Known follow-ups (tracked in `docs/ROADMAP.md`)

- **Reusable `allenfbyrd/controlbridge-action`** — the full GitHub
  Action wrapper. v0.3.0 ships the CLI; v0.3.1 will add the one-line
  `uses:` wrapper so users don't need the 80-line workflow in
  `docs/github-action/workflow-example.yml`.
- **PyPI Trusted Publisher (OIDC) migration** — still pending PyPI-
  side UI configuration. v0.3.0 continues using the API token.

## [0.2.1] - 2026-04-16

Correctness and integrity release. Follow-up to the v0.2.0 Phase 1.5
big-bang: fixes bugs an external code audit surfaced, bundles the full
NIST SP 800-53 Rev 5 catalog (1,196 controls + 4 resolved baselines),
adds 221 new tests, and lights up a working `controlbridge.yaml`
project-config loader. No breaking API changes — all additions are
either additive (new CLI flags, new config keys) or transparent
(richer data, better defaults).

See `docs/ROADMAP.md` for the v0.3.0+ plan.

### Added

- **Full NIST SP 800-53 Rev 5 catalog** bundled verbatim from the CC0
  `usnistgov/oscal-content` repository at pinned tag `v1.4.0`. Ships as
  `nist-800-53-rev5.json` (1,196 controls across 20 families, including
  all enhancements) plus 4 resolved baseline catalogs:

  | Framework ID                    | Controls (inc. enhancements) | Use case                     |
  |---------------------------------|------------------------------|------------------------------|
  | `nist-800-53-rev5-low`          | 149                          | Low-impact FISMA systems     |
  | `nist-800-53-rev5-moderate`     | 287                          | Most federal / FedRAMP Mod   |
  | `nist-800-53-rev5-high`         | 370                          | High-impact FISMA / FedRAMP High |
  | `nist-800-53-rev5-privacy`      | 102                          | Privacy overlay              |

  Resolution uses the OSCAL profile resolver shipped in v0.2.0 (plus
  the fragment-href back-matter fix described under **Fixed** below).
  New script `scripts/catalogs/fetch_nist_oscal.py` regenerates these
  at release time against a pinned upstream tag.

- **FedRAMP baselines (`fedramp-rev5-low/moderate/high/li-saas`)** now
  carry real NIST 800-53 control text. v0.2.0 shipped these as
  pointer-only catalogs where every description was literally
  "See nist-800-53-rev5 catalog for full control text". v0.2.1 resolves
  each FedRAMP control ID against the bundled NIST catalog and
  substitutes real titles + descriptions (1,008 control descriptions
  replaced; zero unresolved).

- **Hybrid effort estimator** (`GapAnalyzer._estimate_effort`). v0.2.0
  used only a structural complexity score derived from
  `len(enhancements) + len(assessment_objectives)`, which was zero for
  every bundled catalog except the new NIST OSCAL one — meaning every
  gap scored `LOW` and the priority formula silently collapsed to
  `severity × (1 + 0.2 × cross_fw_count)`. The replacement is a
  three-layer cascade: structural score → keyword presence in the
  description → description-length fallback. See
  `docs/architecture/effort-estimation.md` for keyword lists and
  scoring rationale.

- **`controlbridge.yaml` project-config loader** (`controlbridge/config.py`).
  `controlbridge init` has generated this file since v0.1.0 but no
  subcommand read it. v0.2.1 walks CWD → parents looking for the first
  `controlbridge.yaml`, validates a strict schema, and applies values
  via precedence: **CLI flag > env var > yaml > built-in default**.
  Honored keys for v0.2.1:

  - `organization` / `system_name` — auto-populates inventory metadata
  - `frameworks:` — default set for `gap analyze`; CLI `--frameworks`
    replaces (does not union)
  - `llm.model` / `llm.temperature` — defaults for `risk generate`;
    overridden by env `CONTROLBRIDGE_LLM_MODEL` / `CONTROLBRIDGE_LLM_TEMPERATURE`

  Legacy v0.2.0 keys (`storage:`, `logging:`, nested `frameworks.default:`)
  are accepted without validation errors; `frameworks.default` triggers
  a deprecation warning pointing at the flattened v0.2.1 shape.
  `${ENV_VAR}` interpolation is supported in any string value.

- **Persistent gap report store** (`controlbridge_core/gap_store.py`).
  Every `gap analyze` run writes a canonical snapshot to
  `<platformdirs>/controlbridge/gap_store/<hash>.json`. `risk generate
  --gap-id GAP-…` (without `--gaps`) now loads the most-recent report
  from the store automatically. Override location via
  `CONTROLBRIDGE_GAP_STORE_DIR`.

- **`--organization` / `--system-name` CLI flags on `gap analyze`**.
  Override inventory metadata for CSV-sourced runs (which previously
  hardcoded `"Unknown Organization (from CSV)"`) or when the inventory
  file's org name doesn't match the report recipient.

- **Placeholder-catalog warning**. Running `gap analyze` against a
  Tier-C stub catalog (e.g., `soc2-tsc`) now emits a prominent
  `UserWarning` telling users the control text isn't authoritative and
  pointing them at `controlbridge catalog import` to load their
  licensed copy.

- **mypy CI job** (`.github/workflows/test.yml`). Runs `mypy --strict-optional`
  against `packages/controlbridge-core/src` and
  `packages/controlbridge/src`. Advisory-only for v0.2.1 (`continue-on-error`)
  because the existing v0.1.x codebase has some untyped helpers; will be
  tightened in v0.3.0.

- **221 new tests, bringing total from 131 → 352 passing**. New suites:

  - `tests/unit/test_gap_analyzer/test_effort_estimator.py` — 44 cases
    covering structural layer, all keyword substitutions, length fallback,
    regression guard for the v0.2.0 "everything is LOW" bug.
  - `tests/unit/test_gap_analyzer/test_priority_math.py` — 85 cases
    parameterized over every severity × effort × cross-fw-count
    combination, asserting priority matches the documented formula
    exactly.
  - `tests/unit/test_gap_analyzer/test_gap_store.py` — 14 cases for
    the persistent gap-store facility (directory resolution
    precedence, hash-key determinism, roundtrip integrity, latest-by-mtime
    lookup).
  - `tests/unit/test_oscal/test_profile_resolver.py` — 12 cases for
    OSCAL profile resolution edge cases (relative paths, `file://` URIs,
    fragment-href back-matter lookup, JSON-rlink preference,
    include/exclude filters, override IDs, missing-import errors).
  - `tests/unit/test_oscal/test_exporter.py` — 5 cases pinning the
    shape of OSCAL Assessment Results exports.
  - `tests/unit/test_config.py` — 24 cases for the new
    `controlbridge.yaml` loader (schema validation, precedence chain,
    legacy-shape warnings, env-var interpolation).
  - `tests/unit/test_models/test_control_id_normalization.py` — 20
    cases covering the NIST-publication style (`AC-2(1)(a)`) vs.
    NIST-OSCAL style (`ac-2.1.a`) normalization added to support the
    bundled NIST catalog.
  - `tests/integration/test_cli/test_catalog_cli.py` — 12 cases for
    the v0.2.0 CLI subcommands (`import`, `where`, `license-info`,
    `remove`, `list --tier`, `list --category`, shadow-resolution,
    duplicate-import behavior, `doctor`, `version`) that previously had
    zero coverage.

- **`docs/ROADMAP.md`** — forward plan for v0.3.0 through v0.6.0+ with
  scope-locked priorities (compliance-as-code diff, plain-English
  explanations, Phase 2 integrations, air-gapped mode, evidence chain
  of custody, etc.).

- **`docs/architecture/effort-estimation.md`** — design doc for the new
  hybrid estimator so future reviewers don't re-derive the keyword
  lists from code.

### Fixed

- **OSCAL profile resolver — back-matter fragment href resolution.**
  v0.2.0's resolver rejected `href: "#<uuid>"` references (raising
  `ProfileResolutionError: Fragment-only hrefs not yet supported`),
  which meant every real-world OSCAL profile (including every NIST
  baseline) couldn't be resolved. v0.2.1 looks up the UUID in the
  profile's `back-matter.resources[].uuid`, walks the first JSON-media
  `rlinks[].href`, and follows it. Falls back to the first non-empty
  rlink when no JSON-flagged entry exists.

- **Dual control-ID convention support.** NIST publications render
  enhancement IDs as `AC-2(1)(a)`; NIST OSCAL renders them as
  `ac-2.1.a`. v0.2.0's `ControlCatalog.get_control()` was strict
  (did a `.upper()`-only lookup), so users typing one style against a
  catalog indexed in the other got `None`. v0.2.1 normalizes both via
  a new `_normalize_control_id()` helper: both
  `catalog.get_control("AC-2(1)(a)")` and
  `catalog.get_control("ac-2.1.a")` resolve to the same control.

- **`controlbridge.yaml` is now actually read by subcommands** (see
  **Added** above).

- **`risk generate --gap-id` no longer unconditionally errors.** The
  new gap-store lookup resolves `--gap-id` against the last-saved
  report when `--gaps` is omitted. Provides a clear message
  ("Run `controlbridge gap analyze ...` first") when no report exists.

- **CSV organization override.** v0.2.0 hardcoded
  `"Unknown Organization (from CSV)"` in the CSV inventory parser with
  no override path. The new `--organization` / `--system-name` CLI
  flags on `gap analyze` and the corresponding `controlbridge.yaml`
  keys resolve this.

### Changed

- **`controlbridge init` template** updates the generated
  `controlbridge.yaml` to the v0.2.1 schema with commented-out examples
  of every honored key.

- **`litellm` version pin tightened** from `>=1.50` to `>=1.50,<2.0`
  (LiteLLM has historically broken minor-version APIs).

- **`nist-800-53-mod` (the 16-control v0.1.x sample)** kept intact for
  yaml-pin backward compatibility, but renamed in metadata to clearly
  flag it as deprecated and point at `nist-800-53-rev5-moderate` (the
  real 287-control baseline). Will be removed in v0.3.0.

- **Framework count** in `controlbridge doctor` grows from 77 → 82 (5
  new NIST catalogs).

### Deferred / known follow-ups

- **PyPI Trusted Publisher (OIDC) migration** — release workflow
  continues to use `PYPI_API_TOKEN` for v0.2.1. Switching without
  configuring a Trusted Publisher on PyPI's admin panel first would
  break the release pipeline. Tracked in `docs/ROADMAP.md`.

- **Full `--strict` mypy** — the advisory-mode `--strict-optional` job
  added in v0.2.1 surfaces existing type-annotation gaps without
  blocking releases. v0.3.0 will clean those up and switch to
  strict-fail.

- **v0.2.0 release-workflow API token rotation** — the v0.2.0 commit
  that removed Claude co-authorship used `git filter-branch`; the
  resulting force-push to `main` has been well-tolerated by PyPI, but
  a future history-rewrite-heavy release should confirm PyPI token
  validity before tagging.

## [0.2.0] - 2026-04-16

**Phase 1.5 big-bang release — exhaustive framework expansion.** Follow-up
to the v0.1.1 legal remediation and v0.1.2 version-reporting truth-up.
ControlBridge now ships ~77 bundled frameworks across four redistribution
tiers — a comprehensive GRC catalog library so common GRC workflows work
out of the box without digging.

### Added — Frameworks (77 total; up from 2)

**Tier A — US federal (verbatim public domain, 25 frameworks)**

- NIST family: 800-171 Rev 2 (110 controls), 800-171 Rev 3 (90), 800-172
  enhanced CUI protections (33), Cybersecurity Framework 2.0 (106
  subcategories), AI RMF 1.0 (72), Privacy Framework 1.0 (94), Secure
  Software Development Framework (SSDF) 800-218 (42)
- FedRAMP Rev 5: Low / Moderate / High / LI-SaaS baselines (pointer
  catalogs; full resolution via OSCAL profile resolver)
- CMMC 2.0: Levels 1 / 2 / 3
- HIPAA: Security Rule (45 CFR § 164 Subpart C), Privacy Rule (Subpart E),
  Breach Notification Rule (Subpart D)
- US regulatory: GLBA Safeguards Rule, NY DFS 23 NYCRR 500, NERC CIP v7,
  FDA 21 CFR Part 11, IRS Publication 1075, CMS ARS 5.1, FBI CJIS Security
  Policy v6.0, CISA Cross-Sector Cybersecurity Performance Goals
- Plus the existing 16-control `nist-800-53-mod` sample

**Tier A — International (6 frameworks)**

- UK: NCSC Cyber Assessment Framework 3.2, Cyber Essentials
- Australia: Essential Eight, Information Security Manual (ISM)
- Canada: ITSG-33
- New Zealand: NZISM 3.7

**Tier D — Statutory obligations (21 frameworks; government edicts — not
copyrightable)**

- EU: GDPR, AI Act (Regulation 2024/1689), NIS2 Directive, DORA
- UK: Data Protection Act 2018
- Canada: PIPEDA
- US state privacy laws (15): California CCPA/CPRA, Virginia VCDPA,
  Colorado CPA, Connecticut CTDPA, Utah UCPA, Texas TDPSA, Oregon OCPA,
  Delaware DPDPA, Montana MCDPA, Iowa ICDPA, Florida FDBR, Tennessee TIPA,
  New Hampshire NHPA, Maryland MODPA, Minnesota MNCDPA

**Tier C — Licensed stubs (20 frameworks; copyrighted control text not
bundled — structural numbering + license URLs for user import)**

- ISO/IEC family: 27001:2022 (93 Annex A controls), 27002:2022, 27017:2015,
  27018:2019, 27701:2019, 42001:2023 (AI), 22301:2019 (BC)
- PCI DSS v4.0.1
- HITRUST CSF v11
- COBIT 2019
- SWIFT CSCF v2024
- CIS Controls v8.1 + 5 CIS Benchmarks (AWS, Azure, GCP, Kubernetes, RHEL 9)
- Secure Controls Framework (SCF) 2024
- IEC 62443 (industrial/OT security)
- SOC 2 TSC (retained from v0.1.1)

**Tier B — Threat and vulnerability catalogs (4 frameworks)**

- MITRE ATT&CK Enterprise (41 high-use techniques/sub-techniques across
  all 14 tactics)
- MITRE CWE (Top 25 weaknesses for 2024)
- MITRE CAPEC (10-pattern sample)
- CISA Known Exploited Vulnerabilities (8-CVE sample of notable entries
  including Log4Shell, MOVEit, EternalBlue)

### Added — Architecture foundation

- **Manifest-driven registry**: `data/frameworks.yaml` replaces the three
  v0.1.x parallel sources of truth (`FRAMEWORK_METADATA` dict,
  `framework_files` dict, `FrameworkId` enum). Adding a framework = drop
  JSON + one YAML edit. Regenerate via
  `scripts/catalogs/regenerate_manifest.py`.
- **`ControlCatalog` model expansion**: new optional fields `guidance`,
  `objective`, `examples`, `control_class`, `ordering`, `family_hierarchy`,
  `category`. All additive — existing v0.1.x JSONs continue to parse under
  `extra="forbid"`.
- **Recursive enhancement flattener**: fixes NIST 800-53 Rev 5 3-level ID
  lookup like `AC-2(1)(a)` that v0.1.x silently lost. `catalog.get_control`
  now walks the full enhancement tree.
- **`TechniqueCatalog`, `VulnerabilityCatalog`, `ObligationCatalog` models**
  for non-control catalog types. See `controlbridge_core/models/threat.py`
  and `controlbridge_core/models/obligation.py`.
- **OSCAL profile resolver** (`controlbridge_core/oscal/profile.py`):
  supports `include-controls`, `exclude-controls`, `set-parameter`,
  `alter.add`, `merge`. Enables user-supplied OSCAL profile JSONs via
  `controlbridge catalog import --profile profile.json --catalog source.json`.
- **User-import facility**: new CLI commands `catalog import`, `catalog
  where`, `catalog license-info`, `catalog remove`, and `catalog list
  --tier <A|B|C|D> --category <control|technique|vulnerability|obligation>`.
  User-imported catalogs shadow bundled ones of the same ID (via
  `platformdirs`-resolved user directory, overridable by
  `CONTROLBRIDGE_CATALOG_DIR`). A licensed ISO 27001 copy imported by a
  customer replaces the Tier-C stub transparently for all `catalog show` /
  `gap analyze` calls.
- **Tier-partitioned catalog directory layout**: `data/us-federal/`,
  `data/international/`, `data/state-privacy/`, `data/stubs/`,
  `data/threats/`, `data/mappings/`.

### Added — Crosswalks (6 total)

- NIST CSF 2.0 → NIST 800-53 (36 mappings, derived from NIST OLIR)
- FedRAMP Moderate → CMMC Level 2 (32 mappings, from DoD CMMC Assessment
  Guide correlations)
- NIST 800-53 → HIPAA Security Rule (20 mappings, from HHS OCR guidance)
- Virginia VCDPA → California CCPA/CPRA (13 subject-rights mappings)
- ISO/IEC 27001:2022 → NIST 800-53 (23 conceptual parity mappings)
- Existing `nist-800-53-rev5_to_soc2-tsc` crosswalk (17 mappings, retained
  from v0.1.1 with sanitized titles)

### Added — Testing

- 80 new unit tests bringing total from 22 → **131 tests passing**:
  parametric smoke test per bundled framework (77 cases), tier invariants
  (Tier-C must be placeholder, Tier-A must not), OSCAL model validation,
  manifest loader, user-dir resolution, `FrameworkId` deprecation gating,
  recursive enhancement flattener.

### Changed

- `FrameworkId` enum (in `controlbridge_core.models.common`) is deprecated
  — emits `DeprecationWarning` on import. Use manifest-driven string IDs
  instead. Will be removed in v0.3.0.
- `controlbridge catalog list` now filters by `--tier` / `--category` /
  `--bundled-only` / `--user-only` and shows tier + category columns.
- `controlbridge catalog show <fw> <ctrl>` renders
  `[Licensed — see <license_url>]` for Tier-C placeholder controls instead
  of the raw placeholder text.
- `platformdirs>=4.3` added as a `controlbridge-core` runtime dependency
  (for user-catalog directory resolution).

### Infrastructure

- `scripts/catalogs/` now hosts compact Python generators (one per
  framework family) plus `regenerate_manifest.py` so `frameworks.yaml` is
  built from what's actually on disk.
- v0.2.1 roadmap: upstream fetch adapters (`scripts/catalogs/upstream/`)
  and GitHub Actions cron workflow (`.github/workflows/catalog-refresh.yml`)
  for auto-detecting upstream drift and opening tracking issues.

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

[Unreleased]: https://github.com/allenfbyrd/controlbridge/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/allenfbyrd/controlbridge/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/allenfbyrd/controlbridge/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/allenfbyrd/controlbridge/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/allenfbyrd/controlbridge/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/allenfbyrd/controlbridge/releases/tag/v0.1.0
