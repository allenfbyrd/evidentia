# Evidentia governance

This document describes how Evidentia is governed: who makes decisions,
how decisions are made and recorded, and how the project sustains
itself across time.

It is a living document — when project structure changes (e.g., when a
second maintainer joins, when an LLC is formed, when a steering group
is constituted), this file is updated in the same PR that makes the
change.

## Current model: BDFL with public process

Evidentia is currently a single-maintainer project. The maintainer
(Allen Byrd) holds final authority on:

- **Technical direction** — architecture, public API, breaking
  changes, dependency choices, supply-chain posture.
- **Scope** — what's in / out of the OSS edition; what ships in each
  release.
- **Release authority** — who can cut a tag, sign a release, and
  publish to PyPI / GHCR.
- **Security disclosure handling** — triage, fix coordination, CVE
  assignment, advisory publication (per [`SECURITY.md`](SECURITY.md)).
- **Code of Conduct enforcement** — see [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

This is the BDFL ("benevolent dictator for life") pattern, common for
early-stage open-source projects. It is not a permanent structure;
it's the structure that fits the project's current size.

## How decisions are made

Decisions are made openly, in writing, in places that anyone can read
and search:

- **Technical decisions** — proposed and discussed in
  [GitHub Issues](https://github.com/allenfbyrd/evidentia/issues) and
  [Pull Requests](https://github.com/allenfbyrd/evidentia/pulls).
  Significant design decisions also land in
  [`docs/`](docs/) as version-controlled records (e.g., the per-release
  plan files at `docs/v0.7.x-plan.md`).
- **Roadmap** — proposed and tracked in [`docs/ROADMAP.md`](docs/ROADMAP.md)
  and the per-release plan files. Quarterly and per-release updates
  are committed to the repo so the history of intent is visible.
- **Security decisions** — handled per the disclosure policy in
  [`SECURITY.md`](SECURITY.md) using GitHub Private Vulnerability
  Reporting + the per-release [`docs/release-checklist.md`](docs/release-checklist.md)
  security gate. Per-release security reviews are published as
  `docs/security-review-vX.Y.Z.md`.
- **Release decisions** — gated by the 11-step
  [`docs/release-checklist.md`](docs/release-checklist.md) (pre-release
  scope confirmation through post-release verification).

The maintainer acknowledges proposals on issues / PRs within a few
days under normal load. There is no obligation to accept every
proposal — limited resources mean some get declined or deferred — but
every reasonable proposal gets a response with a rationale.

## Roles

The project currently has one role:

- **Maintainer (Allen Byrd)** — owns all categories above. Granted
  by virtue of being the project originator. Maintains:
  - GitHub repo write + admin access.
  - PyPI Trusted Publisher binding for the 6 `evidentia*` packages.
  - GHCR push access for `ghcr.io/allenfbyrd/evidentia`.
  - Domain ownership for any future `evidentia.*` web surface.

When a second maintainer joins, the following roles will be defined:

- **Triager** — issue triage, label management, first-pass PR review.
- **Catalog Curator** — Tier-A / Tier-B / Tier-C catalog updates,
  crosswalk maintenance.
- **Release Engineer** — secondary release authority (so any single
  maintainer can be unavailable without blocking a release).

## Becoming a contributor

Anyone can contribute. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for
the contribution workflow (PRs, coding standards, test policy).

There are no project-level CLA / DCO requirements at this stage
(single-maintainer project; all commits to date are by the
maintainer). When a second contributor is onboarded, a DCO flow
(`.github/workflows/dco.yml` + sign-off-by trailers) will be enabled
in the same PR that adds them.

## Becoming a maintainer

The project currently has a single maintainer because that's what the
contributor base supports. As external contributors begin shipping
substantive work (collectors, integrations, catalog updates, doc
contributions, security improvements), the path to maintainership is:

1. Sustained contribution over time (months, not weeks) with a track
   record of merged PRs that don't require heavy revision.
2. Demonstrated understanding of the project's scope, architecture,
   and security posture.
3. Public proposal in a GitHub Issue (filed by the candidate or by an
   existing maintainer) with rationale.
4. Acceptance by consensus of existing maintainers (currently: just
   the BDFL — when there are 2+ maintainers, consensus among them).

Maintainers can step down at any time by filing an issue. The
remaining maintainers (or the BDFL, if back to one) update this
document in the same PR.

## Continuity and bus factor

The project's current bus factor is 1 (single maintainer). The
following continuity mitigations exist by design:

- **Keyless signing** — Sigstore + Trusted Publisher OIDC + cosign
  keyless mean there are no offline private keys that can be lost
  with the maintainer. A successor maintainer with repo write access
  can continue releases without any key transfer.
- **Public process** — every operational procedure is documented in
  the repo (release-checklist.md, threat-model.md, security
  policy, per-release plans). A successor doesn't need to interview
  the original maintainer to take over.
- **Standard infrastructure** — GitHub for source + issues, PyPI for
  Python distribution, GHCR for container images. All standard,
  recoverable platforms with documented account-recovery procedures.
- **Apache-2.0 license** — anyone can fork at any time without the
  maintainer's permission.

The remaining single-point-of-failure is GitHub repo ownership +
PyPI project-owner roles. Both platforms have documented support
procedures for ownership transfer in the event of maintainer
incapacity, but the procedure does require external verification.
A formal continuity plan (named successor + organizational entity)
is planned alongside LLC formation.

## Changes to this document

Changes to governance happen via PR like any other change. The
maintainer reviews + approves. When a steering group exists, that
group will review proposed governance changes by a process they
define and add here.
