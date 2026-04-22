"""GitHub evidence collector for ControlBridge.

Pulls branch protection + CODEOWNERS presence from a GitHub repository
and maps each finding to NIST 800-53 controls in the SA / CM / IA
families.

Zero extra-dep install: the collector uses ``httpx`` (already required
by ``controlbridge-collectors``) rather than the optional ``pygithub``
SDK. Users who want ``pygithub`` for custom workflows can still install
it via the ``[github]`` extra.

Public surface::

    from controlbridge_collectors.github import GitHubCollector

    collector = GitHubCollector(
        owner="allenfbyrd",
        repo="controlbridge",
        token=os.environ["GITHUB_TOKEN"],
    )
    findings = collector.collect()
    # -> list[SecurityFinding]

Credentials:
- ``GITHUB_TOKEN`` env var (personal access token or GITHUB_TOKEN from
  an Actions workflow).
- Required scopes: ``repo`` for private repos, nothing for public
  repos (unauthenticated rate-limited calls still work).
"""

from controlbridge_collectors.github.client import GitHubApiError, GitHubClient
from controlbridge_collectors.github.collector import (
    GitHubCollector,
    GitHubCollectorError,
)

__all__ = [
    "GitHubApiError",
    "GitHubClient",
    "GitHubCollector",
    "GitHubCollectorError",
]
