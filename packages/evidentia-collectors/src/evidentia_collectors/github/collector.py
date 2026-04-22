"""GitHub evidence collector.

Assembles :class:`SecurityFinding` instances from three observations:

1. **Default branch protection** — is the protection object present, and
   does it require PR review + status checks + signed commits?
   Maps to SA-11 (developer security testing), CM-2 (baseline config),
   CM-3 (change control), and AC-3 (access enforcement).
2. **CODEOWNERS presence** — a CODEOWNERS file at one of the three
   canonical locations. Maps to SA-11 + AC-3 (code review is the
   enforcement mechanism).
3. **Repository visibility** — private repos = expected;  unintentionally
   public repos are a finding (AC-3, AC-6).

Output is always a list of findings whose ``control_ids`` reflect the
rule's Evidentia attribution. A compliant observation still emits
a finding (severity=INFORMATIONAL, status=RESOLVED) so evidence
bundles have a record — auditors want to see both what's failing AND
what's passing.
"""

from __future__ import annotations

from typing import Any

from evidentia_core.models.common import Severity
from evidentia_core.models.finding import FindingStatus, SecurityFinding

from evidentia_collectors.github.client import (
    GitHubApiError,
    GitHubClient,
)


class GitHubCollectorError(Exception):
    """Raised for collector-level failures — missing token, missing repo, etc."""


class GitHubCollector:
    """Collect evidence findings from a single GitHub repository."""

    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        token: str | None = None,
        client: GitHubClient | None = None,
    ) -> None:
        if not owner or not repo:
            raise GitHubCollectorError(
                "GitHubCollector requires non-empty owner + repo."
            )
        self.owner = owner
        self.repo = repo
        self._client = client or GitHubClient(token=token)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GitHubCollector:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    # ── High-level orchestration ────────────────────────────────────

    def collect(self) -> list[SecurityFinding]:
        """Run every sub-check and return the merged findings list."""
        try:
            repo_meta = self._client.get_repo(self.owner, self.repo)
        except GitHubApiError as e:
            raise GitHubCollectorError(
                f"Could not read repo {self.slug}: {e}"
            ) from e

        findings: list[SecurityFinding] = []
        findings.extend(self._visibility_finding(repo_meta))
        findings.extend(self._branch_protection_findings(repo_meta))
        findings.extend(self._codeowners_finding())
        return findings

    # ── Sub-checks ──────────────────────────────────────────────────

    def _visibility_finding(
        self, repo_meta: dict[str, Any]
    ) -> list[SecurityFinding]:
        """Emit a finding describing the repo's public/private posture."""
        is_private = bool(repo_meta.get("private", False))
        visibility = str(repo_meta.get("visibility", "unknown"))

        if is_private:
            return [
                SecurityFinding(
                    title=f"GitHub repo {self.slug} is private",
                    description=(
                        f"Repository {self.slug} visibility is {visibility!r}. "
                        "Source code is not publicly accessible."
                    ),
                    severity=Severity.INFORMATIONAL,
                    status=FindingStatus.RESOLVED,
                    source_system="github",
                    source_finding_id=f"{self.slug}:visibility",
                    resource_type="GitHub::Repository",
                    resource_id=self.slug,
                    control_ids=["AC-3", "AC-6"],
                    raw_data={"visibility": visibility, "private": is_private},
                )
            ]
        return [
            SecurityFinding(
                title=f"GitHub repo {self.slug} is public",
                description=(
                    f"Repository {self.slug} is publicly visible. "
                    "Verify this matches the organization's open-source "
                    "policy. If unintentional, flip visibility to private "
                    "in the repo settings."
                ),
                severity=Severity.MEDIUM,
                status=FindingStatus.ACTIVE,
                source_system="github",
                source_finding_id=f"{self.slug}:visibility",
                resource_type="GitHub::Repository",
                resource_id=self.slug,
                control_ids=["AC-3", "AC-6"],
                raw_data={"visibility": visibility, "private": is_private},
            )
        ]

    def _branch_protection_findings(
        self, repo_meta: dict[str, Any]
    ) -> list[SecurityFinding]:
        """Emit findings for the default branch's protection state."""
        default_branch = str(repo_meta.get("default_branch") or "main")
        try:
            protection = self._client.get_branch_protection(
                self.owner, self.repo, default_branch
            )
        except GitHubApiError as e:
            return [
                SecurityFinding(
                    title=f"Could not read branch protection for {self.slug}@{default_branch}",
                    description=str(e),
                    severity=Severity.LOW,
                    status=FindingStatus.ACTIVE,
                    source_system="github",
                    source_finding_id=f"{self.slug}:{default_branch}:protection-error",
                    resource_type="GitHub::Branch",
                    resource_id=f"{self.slug}:{default_branch}",
                    control_ids=["SA-11", "CM-3"],
                )
            ]

        if protection is None:
            return [
                SecurityFinding(
                    title=(
                        f"Default branch {default_branch!r} in {self.slug} "
                        "has no branch protection"
                    ),
                    description=(
                        "Branch protection is not enabled on the default "
                        "branch. Anyone with write access can push directly "
                        "bypassing PR review. Map to SA-11 (dev security "
                        "testing), CM-3 (change control), and AC-3."
                    ),
                    severity=Severity.HIGH,
                    status=FindingStatus.ACTIVE,
                    source_system="github",
                    source_finding_id=f"{self.slug}:{default_branch}:unprotected",
                    resource_type="GitHub::Branch",
                    resource_id=f"{self.slug}:{default_branch}",
                    control_ids=["SA-11", "CM-2", "CM-3", "AC-3"],
                )
            ]

        # Protection IS enabled — emit individual findings per rule so
        # auditors can see exactly what's configured.
        findings: list[SecurityFinding] = []

        pr_review = (protection.get("required_pull_request_reviews") or {})
        reviewers = int(pr_review.get("required_approving_review_count", 0))
        findings.append(
            _finding(
                slug=self.slug,
                branch=default_branch,
                rule="pr_review",
                title=f"PR review required on {default_branch!r}"
                if reviewers > 0
                else f"PR review NOT required on {default_branch!r}",
                description=(
                    f"{reviewers} approving review(s) required before merge."
                    if reviewers > 0
                    else "No approving reviews required. Code lands without a second pair of eyes."
                ),
                severity=Severity.INFORMATIONAL if reviewers > 0 else Severity.HIGH,
                status=FindingStatus.RESOLVED if reviewers > 0 else FindingStatus.ACTIVE,
                control_ids=["SA-11", "AC-3"],
                raw=pr_review,
            )
        )

        status_checks = (protection.get("required_status_checks") or {})
        contexts = status_checks.get("contexts") or []
        findings.append(
            _finding(
                slug=self.slug,
                branch=default_branch,
                rule="status_checks",
                title=f"Status checks required on {default_branch!r}"
                if contexts
                else f"No required status checks on {default_branch!r}",
                description=(
                    f"{len(contexts)} required check(s): {', '.join(contexts[:5])}"
                    f"{'...' if len(contexts) > 5 else ''}"
                    if contexts
                    else "No required status checks. CI can be bypassed."
                ),
                severity=Severity.INFORMATIONAL if contexts else Severity.MEDIUM,
                status=FindingStatus.RESOLVED if contexts else FindingStatus.ACTIVE,
                control_ids=["SA-11", "SI-2"],
                raw=status_checks,
            )
        )

        enforce_admins = bool(
            (protection.get("enforce_admins") or {}).get("enabled", False)
        )
        findings.append(
            _finding(
                slug=self.slug,
                branch=default_branch,
                rule="enforce_admins",
                title="Admin bypass "
                + ("disabled" if enforce_admins else "allowed")
                + f" on {default_branch!r}",
                description=(
                    "Admins cannot bypass branch protection. Rules apply universally."
                    if enforce_admins
                    else "Admins can bypass branch protection rules. Anomaly detection should flag admin pushes."
                ),
                severity=Severity.INFORMATIONAL if enforce_admins else Severity.MEDIUM,
                status=FindingStatus.RESOLVED if enforce_admins else FindingStatus.ACTIVE,
                control_ids=["AC-6", "CM-3"],
                raw={"enforce_admins": enforce_admins},
            )
        )

        return findings

    def _codeowners_finding(self) -> list[SecurityFinding]:
        """Emit a finding describing CODEOWNERS presence.

        CODEOWNERS lives at ``.github/CODEOWNERS``, ``docs/CODEOWNERS``,
        or ``CODEOWNERS`` (root). Check all three.
        """
        for path in (".github/CODEOWNERS", "docs/CODEOWNERS", "CODEOWNERS"):
            try:
                content = self._client.get_contents(self.owner, self.repo, path)
            except GitHubApiError:
                continue
            if content is not None:
                return [
                    SecurityFinding(
                        title=f"CODEOWNERS present in {self.slug}",
                        description=(
                            f"Code review ownership defined at {path!r}. "
                            "Supports SA-11 (dev security testing) + AC-3 "
                            "(access enforcement via required reviewers)."
                        ),
                        severity=Severity.INFORMATIONAL,
                        status=FindingStatus.RESOLVED,
                        source_system="github",
                        source_finding_id=f"{self.slug}:codeowners",
                        resource_type="GitHub::Repository",
                        resource_id=self.slug,
                        control_ids=["SA-11", "AC-3"],
                        raw_data={"path": path},
                    )
                ]
        return [
            SecurityFinding(
                title=f"CODEOWNERS missing in {self.slug}",
                description=(
                    "No CODEOWNERS file found at .github/CODEOWNERS, "
                    "docs/CODEOWNERS, or the repo root. Code review "
                    "ownership is implicit rather than enforced."
                ),
                severity=Severity.MEDIUM,
                status=FindingStatus.ACTIVE,
                source_system="github",
                source_finding_id=f"{self.slug}:codeowners-missing",
                resource_type="GitHub::Repository",
                resource_id=self.slug,
                control_ids=["SA-11", "AC-3"],
            )
        ]


def _finding(
    *,
    slug: str,
    branch: str,
    rule: str,
    title: str,
    description: str,
    severity: Severity,
    status: FindingStatus,
    control_ids: list[str],
    raw: Any,
) -> SecurityFinding:
    return SecurityFinding(
        title=title[:200],
        description=description[:2000],
        severity=severity,
        status=status,
        source_system="github",
        source_finding_id=f"{slug}:{branch}:{rule}",
        resource_type="GitHub::Branch",
        resource_id=f"{slug}:{branch}",
        control_ids=control_ids,
        raw_data=raw,
    )
