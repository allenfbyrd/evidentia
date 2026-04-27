# Security policy

Thanks for taking the time to report a security concern. Evidentia
takes its supply-chain posture seriously — see the per-release
hardening in [`docs/enterprise-grade.md`](docs/enterprise-grade.md)
and the supply-chain provenance section of every release on
[GitHub Releases](https://github.com/allenfbyrd/evidentia/releases).

## Reporting a vulnerability

**Please do not open a public GitHub issue for security concerns.**

Two private channels:

1. **Preferred — GitHub Private Vulnerability Reporting**:
   <https://github.com/allenfbyrd/evidentia/security/advisories/new>.
   This routes through GitHub's coordinated-disclosure flow (private
   discussion thread, advisory drafting, optional CVE assignment).
2. **Backup — email**: `allen@allenfbyrd.com` with subject
   `[SECURITY] Evidentia <one-line summary>`. Please use this only
   if GitHub Private Vulnerability Reporting is unavailable.

Please include:

- Affected version(s) (`pip show evidentia` output is fine).
- Reproduction steps or a proof-of-concept (minimal is fine —
  willingness to engage matters more than polish).
- Your assessment of impact (data exposed, code execution,
  authentication bypass, etc.).
- Any suggested mitigation if you have one.
- Whether you'd like credit in the advisory (default: yes, with
  the name/handle you specify; no, if you prefer anonymous).

Initial acknowledgment within **3 business days**. Triage assessment
within **10 business days**. See **Disclosure timeline** below for
the full coordination window.

## Supported versions

Evidentia is pre-1.0 and ships from a single supported release line.
Security patches land on the latest minor; older minors do not
receive backports.

| Version | Status | Security patches |
|---------|--------|------------------|
| `0.7.x` | **Supported** | ✅ landed in next patch |
| `0.6.x` | Deprecated | ❌ — upgrade to `0.7.x` |
| `0.5.x` and earlier | Unsupported | ❌ — upgrade to `0.7.x` |
| Legacy `controlbridge*` packages | Yanked from PyPI | ❌ — every version yanked; upgrade path documented in [`RENAMED.md`](RENAMED.md) |

When v0.8.0 ships, v0.7.x moves to maintenance mode (security-only
patches for one minor cycle, then deprecation). The exact deprecation
timeline will be documented in the v0.8.0 release notes and in
[`docs/release-checklist.md`](docs/release-checklist.md).

Once v1.0 ships, the supported-version policy will tighten to
explicit semver guarantees (latest minor of each supported major).

## Disclosure timeline

Standard coordinated-disclosure window: **90 days from initial report
to public disclosure**. The window can shorten or lengthen by mutual
agreement — for example:

- **Shorter**: if the upstream library has already published a fix
  and we just need to bump our pin, we can ship + disclose within
  days. The v0.7.2 supply-chain follow-up
  ([commit 8baa93d](https://github.com/allenfbyrd/evidentia/commit/8baa93d))
  is the canonical pattern: 4 disclosed advisories in upstream
  packages → bumped pins → shipped + documented within hours of
  internal alerts firing.
- **Longer**: if the fix requires architectural changes, we'll
  request a window extension in the private discussion thread and
  agree on a target date.

After fix lands and is published to PyPI, the GitHub Security
Advisory is published and (if applicable) a CVE is requested.
Reporters are credited unless they opt out.

## Scope

In scope:

- Code in this repository (`packages/evidentia*/src/...`,
  `packages/evidentia-ui/src/...`, `scripts/...`).
- Build + release infrastructure (`.github/workflows/*.yml`).
- Distribution surface (PyPI packages `evidentia`, `evidentia-core`,
  `evidentia-collectors`, `evidentia-ai`, `evidentia-api`,
  `evidentia-integrations`).
- The composite GitHub Action
  (`.github/actions/gap-analysis/action.yml`).
- The bundled framework catalogs and crosswalk mappings
  (`packages/evidentia-core/src/evidentia_core/catalogs/data/`)
  insofar as a maliciously-crafted catalog could cause harm at
  load time.

Out of scope:

- **Vulnerabilities in third-party dependencies**. Report those to
  the upstream maintainer. Once a fix is published upstream, our
  Dependabot configuration
  ([`.github/dependabot.yml`](.github/dependabot.yml)) opens an
  auto-PR within the next weekly cycle, or sooner for critical
  advisories. Recent example:
  [PR #8](https://github.com/allenfbyrd/evidentia/pull/8) closed
  4 upstream advisories within hours of disclosure.
- **AWS canonical-example placeholders** in test files
  (`AKIAIOSFODNN7EXAMPLE`, `ASIAIOSFODNN7EXAMPLE` —
  [AWS-published](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html)
  literals that are never valid credentials). These are
  intentional test fixtures for the secret-scrubber's own unit
  tests.
- **Tier-C placeholder catalog text** (catalogs with the
  `placeholder: true` flag). Authoritative control text for these
  frameworks is copyrighted and not bundled; the placeholder text
  is intentionally non-authoritative. Use
  `evidentia catalog import` to load your licensed copy.
- **Findings against unsupported versions** (see Supported versions
  table above). If a vulnerability exists in `0.6.x` but not in
  `0.7.x`, the remediation is to upgrade.
- **Self-XSS, social engineering, or attacks requiring physical
  access to the user's machine.**
- **Theoretical issues without a reproducible exploit path**
  (e.g., "function X uses crypto algorithm Y which has theoretical
  weaknesses").

If you're unsure whether something is in scope, report it anyway.
We'd rather triage and decline than miss a real issue.

## Supply-chain provenance

Every Evidentia release ships with cryptographic provenance:

- **PEP 740 attestations** on every wheel + sdist, signed via the
  GitHub Actions OIDC identity (Sigstore + Rekor public
  transparency log).
- **CycloneDX 1.6 SBOM** generated from `uv.lock`, attached to
  every GitHub Release.
- **Sigstore/Rekor signing** of every OSCAL Assessment Results
  document (or GPG `.asc` signatures in air-gap mode).

Verify a release wheel:

```bash
pip install pypi-attestations
pypi-attestations verify pypi \
  --repository https://github.com/allenfbyrd/evidentia \
  "pypi:evidentia-0.7.2-py3-none-any.whl"
```

If verification fails, **stop and report immediately** via the
private channels above — a verification failure on a published
artifact is itself a security incident.

## Acknowledgments

Coordinated security reports — once disclosed and fixed — are
credited in the corresponding release notes and in the GitHub
Security Advisory. If you'd like a place on a future
`SECURITY-HALL-OF-FAME.md`-style page, that's planned for v0.8.x;
for now, recognition is in-release-only.

Thank you in advance for helping keep Evidentia and its users safe.
