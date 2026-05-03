# OpenSSF Best Practices Badge — tier roadmap

Authoritative in-repo plan for Evidentia's OpenSSF Best Practices
Badge progression. Companion to [`docs/release-checklist.md`](release-checklist.md):
each release is an opportunity to harden whichever tier is in flight.

BadgeApp project entry: <https://www.bestpractices.dev/projects/12724>.

## Status snapshot (as of this doc's commit)

| Tier | Status | Blockers | Target |
|------|--------|----------|--------|
| **Passing** | In progress (36% form-filled before this doc) | Form completion only — every Met claim is already substantiated in the repo. | This release cycle (v0.7.9). |
| **Silver** | Ready to file after small doc additions | GOVERNANCE.md added in this commit. Coding-standards paragraph added to CONTRIBUTING.md. Stale strings in CONTRIBUTING.md + SECURITY.md fixed. Remaining: (a) embed Passing badge in README once awarded (auto-satisfies `documentation_achievements`); (b) optionally publish coverage % via Codecov to formalize `test_statement_coverage80` Met claim. | v0.7.9 ship. |
| **Gold** | Not reachable today. | Hard MUST blockers requiring ≥2 contributors: `bus_factor ≥2`, `contributors_unassociated ≥2`, `two_person_review 50%+`, meaningful `code_review_standards`. Plus mechanical: per-file copyright + SPDX headers, `good first issue` labels, reproducible-build verification, ≥90% statement / ≥80% branch coverage. | v1.0+ or whenever OSS contributor base develops. |

## Passing-tier embed

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/12724/badge)](https://www.bestpractices.dev/projects/12724)
```

Goes in the README badge cluster near the top. The image auto-updates
as the project advances tiers, so it's a one-time embed. The act of
embedding it also satisfies Silver's `documentation_achievements`
criterion.

## Silver-tier remaining work

After this commit lands:

1. **Embed the Passing badge in README** the moment the Passing form
   hits 100% (ideally same commit as this doc's update once awarded).
2. **Optional: publish coverage %** — add `--cov` invocation to
   `test.yml` + a Codecov upload action + the resulting badge in
   README. Confirms Silver's `test_statement_coverage80` and
   pre-positions for Gold's `test_statement_coverage90` +
   `test_branch_coverage80`.
3. **Optional: docs/assurance-case.md** — a single doc that explicitly
   stitches `docs/threat-model.md` + the latest
   `docs/security-review-vX.Y.Z.md` + `docs/enterprise-grade-accepted-findings.md`
   into the OpenSSF assurance-case structure. Strengthens
   `assurance_case` from "composed across 3 docs" to "single direct
   URL."

## Silver-tier defensible Unmets

These remain Unmet after the work above. All are defensible because
they are SHOULD or SUGGESTED criteria with explicit project-stage
rationale:

- **`dco`** (SHOULD) — single-maintainer; will adopt when 2nd contributor joins.
- **`bus_factor`** (SHOULD) — single-maintainer; mitigated by keyless infrastructure.
- **`version_tags_signed`** (SUGGESTED) — Sigstore PEP 740 + SLSA L3
  provides stronger provenance than tag signing; planned for v0.8.0.
- **`access_continuity`** (MUST, partial) — full closure waits on LLC
  + named successor; current mitigation is keyless infrastructure +
  GitHub/PyPI standard recovery procedures.

## Gold-tier sequencing

Gold cannot be filed until Silver is awarded (BadgeApp auto-disables
Gold criteria until `achieve_silver` flips Met).

Mechanical Gold prep that can ship independently of contributor
recruitment, in priority order:

1. **Coverage to ≥80% branch / ≥90% statement** — incremental work
   per release; tracked via Codecov once enabled.
2. **`good first issue` labels** — label 5-10 catalog-refresh /
   docstring / additional-test issues; refresh quarterly.
3. **Reproducible-build verification** — run release.yml twice
   against the same tag, compare wheel SHA-256 hashes byte-for-byte.
   If `SOURCE_DATE_EPOCH` isn't honored by hatchling, set it
   explicitly in the workflow.
4. **`docs/code-review-standards.md`** — describe what a future
   reviewer would check (security, tests, docs, CHANGELOG entry,
   ruff/mypy clean, CI green). Useful even before a second reviewer
   exists; shows the infrastructure is ready.
5. **Per-file copyright + SPDX headers** — one-shot script across
   ~138 Python files + N TypeScript files:

   ```python
   # Copyright (c) <YEAR> Allen Byrd. Licensed under Apache-2.0.
   # SPDX-License-Identifier: Apache-2.0
   ```

   Plus add `reuse lint` as a pre-commit hook to enforce going
   forward.

Hard Gold blockers that wait on project-shape changes:

- **`bus_factor ≥2` (MUST)** — recruit a second maintainer.
- **`contributors_unassociated ≥2` (MUST)** — recruit ≥1 contributor
  outside Allen's organizational orbit.
- **`two_person_review 50%+` (MUST)** — requires a second reviewer
  for ≥half of all PRs.
- **`code_review_standards` (MUST)** — meaningful only when there's a
  second reviewer to apply them.

## Per-release operational tie-in

Add to [`docs/release-checklist.md`](release-checklist.md) Step 4
(doc refresh) when next updated:

> If the OpenSSF Best Practices badge tier changed in this release
> cycle, update the README badge embed (auto-updates anyway, but
> verify it renders correctly) and add a CHANGELOG entry under "Added"
> or "Changed" referencing the new tier.

## References

- BadgeApp project: <https://www.bestpractices.dev/projects/12724>
- BadgeApp criteria spec: <https://www.bestpractices.dev/en/criteria/0>
- Personal answer-sheet plan files (private, not in repo):
  - `~/.claude/plans/c-users-allen-downloads-badgeapp-edit-f-partitioned-aho.md` — Passing
  - `~/.claude/plans/evidentia-badgeapp-silver-gold-answer-sheet.md` — Silver + Gold
