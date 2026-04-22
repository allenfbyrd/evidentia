"""Jira output integration — push gaps as issues + bidirectional status sync.

Public surface (imports from ``evidentia_integrations.jira``):

- :class:`JiraClient` — httpx-based REST client; one instance per server.
- :class:`JiraConfig` — typed configuration (base URL, project key, etc.).
  Credentials come from environment variables; the config object never
  carries the API token in its serialized form.
- :class:`JiraIssue` — response shape from Jira's REST v3 API, narrowed
  to the fields we actually care about.
- :class:`JiraApiError`, :class:`JiraMappingError` — exception types.
- :func:`gap_to_create_request` / :func:`jira_status_to_gap_status` —
  pure functions exposing the mapping between Evidentia gaps and
  Jira issues. Easy to unit-test without a live server.
- :func:`push_gap_to_jira` / :func:`sync_gap_from_jira` — gap-level
  helpers that combine client + mapper.
- :func:`push_open_gaps` / :func:`sync_report` — batch wrappers over a
  :class:`GapAnalysisReport`. Used by the CLI and REST endpoints.

v0.5.0 uses the Jira Cloud REST API v3 (``/rest/api/3``). Server-hosted
Jira is untested; most of the same endpoints exist but the workflow
configuration + auth story diverge. File an issue if you need Server
support.
"""

from evidentia_integrations.jira.client import (
    JiraApiError,
    JiraClient,
    JiraIssue,
)
from evidentia_integrations.jira.config import JiraConfig
from evidentia_integrations.jira.mapper import (
    GAP_STATUS_TO_JIRA_STATUS,
    JIRA_STATUS_TO_GAP_STATUS,
    JiraMappingError,
    gap_to_create_request,
    jira_status_to_gap_status,
)
from evidentia_integrations.jira.sync import (
    JiraSyncAction,
    JiraSyncOutcome,
    JiraSyncResult,
    push_gap_to_jira,
    push_open_gaps,
    sync_gap_from_jira,
    sync_report,
)

__all__ = [
    "GAP_STATUS_TO_JIRA_STATUS",
    "JIRA_STATUS_TO_GAP_STATUS",
    "JiraApiError",
    "JiraClient",
    "JiraConfig",
    "JiraIssue",
    "JiraMappingError",
    "JiraSyncAction",
    "JiraSyncOutcome",
    "JiraSyncResult",
    "gap_to_create_request",
    "jira_status_to_gap_status",
    "push_gap_to_jira",
    "push_open_gaps",
    "sync_gap_from_jira",
    "sync_report",
]
