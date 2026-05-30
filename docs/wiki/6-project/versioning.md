# Versioning

Evidentia follows [Semantic Versioning 2.0.0](https://semver.org/). This
page explains how that maps onto Evidentia's pre-1.0 development, what
the bump heuristic is today, and what the transition to v1.0 requires.

For the binding, NORMATIVE definition of which surfaces carry
semantic-versioning guarantees (Pydantic models, the `EventAction` enum,
CLI flags, REST URIs, plugin contracts, MCP tool names, env vars), see
[API stability](api-stability.md) — that document is the contract; this
page is the orientation.

## SemVer interpretation

| Bump | Meaning | Example |
|---|---|---|
| **Major** (X.0.0) | Breaking change to a frozen surface | Remove a Pydantic field, rename a CLI flag |
| **Minor** (0.X.0 / 1.X.0) | New functionality; additive-only changes to frozen surfaces | New EventAction, new CLI command, new optional model field |
| **Patch** (0.0.X / 1.0.X) | Bug fixes, security patches, doc updates, catalog content refreshes | CVE fix, threshold-default adjustment, typo |

## Pre-1.0 reality (Evidentia is at 0.10.x)

Evidentia is currently in the **0.10.x** line. Two pre-1.0 nuances
matter:

**1. The minor-vs-patch heuristic.** Within the 0.x series, the choice
between a minor and a patch bump is made per release, not formulaically:

- **Minor bump** (`0.X.Y → 0.(X+1).0`) — reserved for a release bringing
  **meaningful new feature surface**. The 0.10.0 line, for instance,
  opened with the OCSF normalized-findings schema + SARIF emit; that was
  a minor because it added a substantial new capability surface, not a
  continuation of 0.9.x patches.
- **Patch bump** (`0.X.Y → 0.X.(Y+1)`) — hardening, bug fixes, doc work,
  and supply-chain polish *on the same feature surface*. Most 0.10.x
  releases are patches: they consolidate, harden, and document the
  0.10.0 feature surface.

**2. The API-stability contract binds from 0.9.7 onward.** Although
Evidentia is pre-1.0, the
[API stability](api-stability.md) document has been **NORMATIVE since
v0.9.7**. Evidentia will not knowingly break a frozen surface in any
0.9.x / 0.10.x release without a deprecation cycle. Earlier (0.9.0 –
0.9.6) was the "stabilization window" where the public contract was
identified and documented in DRAFT form; before that (≤0.8.x), minor
bumps could contain breaking changes to any surface.

The v1.0.0 release **ratifies** the contract already in force — it does
not add new constraints.

## Deprecation cycle

When a frozen surface must change, the policy (see
[Deprecation policy](deprecation-policy.md) for the full calendar) is:

1. **Announce** — add a `DeprecationWarning` (Python) or deprecation
   header (REST) in release N; document under "Deprecated" in the
   CHANGELOG.
2. **Maintain** — the deprecated surface keeps working unchanged for at
   least one full minor-release cycle (N through N+1).
3. **Remove** — earliest removal is release N+2, and that constitutes a
   major-version bump.

A worked example currently on the calendar: the `SecurityFinding` →
`Finding` class alias (introduced v0.10.1) is retained through the 0.10.x
line with removal of the old alias targeted no earlier than v1.0.0. The
`evidentia_ai.eval.*` import path is a deprecation shim through v0.11.x
with removal scheduled for v0.12.0.

## The transition to v1.0

v1.0 is **RESERVED**, not scheduled — there is no committed date. Per
[`v1.0-transition.md`](https://github.com/Polycentric-Labs/evidentia/blob/main/docs/v1.0-transition.md),
v1.0 combines two themes:

- **Candidate A — "federal compliance shipped"**: the federal-compliance
  feature surface (CONMON + POA&M, shipped across the 0.9.x / 0.10.x
  lines) tested against real federal-SI workflows and accepted by an
  external domain expert.
- **Candidate B — "API stability commitment"**: the public API contract
  is frozen with full semver guarantees (the contract is already
  NORMATIVE; v1.0 ratifies it).

### Working acceptance gates

The transition document lists these working gates (subject to revision):

- Federal-compliance theme shipped + accepted by a domain expert.
- A domain-expert walk-through completed, with the capability matrix
  expanded with real-world scenario rows.
- 1+ external operator has run a 0.9.x / 0.10.x release in production.
- All public API surfaces documented in `api-stability.md` *(met —
  NORMATIVE since v0.9.7)*.
- A deprecation calendar published *(met)*.
- A pre-release-review PROCEED-CLEAN + Step 7 post-tag verification all
  pass.
- The single procurement-ready acceptance paragraph in
  `positioning-and-value.md` §10.4 (supply-chain attestations + OpenSSF
  Silver + OSPS Baseline Maturity 2, with the OpenSSF-Gold structural
  ceiling acknowledged honestly).

> The roadmap's own working estimate is **v1.0 ≈ Q3–Q4 2026**, explicitly
> labelled a *working assumption, not a commitment*. The publishing of a
> release tag is always a deliberate, human-gated action — there is no
> auto-tagging.

## See also

- [API stability](api-stability.md) — NORMATIVE; the frozen-surface
  contract this page orients you to.
- [Deprecation policy](deprecation-policy.md) — the formal deprecation
  calendar.
- [Roadmap](roadmap.md) — release-by-release theme history + the v1.0
  RESERVED section.
- [Changelog](changelog.md) — the per-release mechanical record.
