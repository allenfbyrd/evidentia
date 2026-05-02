"""Power BI output integration (v0.7.8 P1.2).

Pushes Evidentia compliance data — gap inventory + risk register +
collection-run audit trail — to a Power BI workspace as Push
Datasets. Risk officers + audit committees can build refreshable
Power BI reports on the published datasets.

Public surface (imports from ``evidentia_integrations.powerbi``):

- :class:`PowerBIClient` — pure-Python wrapper around the Power BI
  REST API via httpx. Handles Azure AD service-principal auth via
  MSAL.
- :class:`PowerBIConfig` — typed configuration (workspace ID,
  tenant ID, client ID, env-var name for the client secret).
  Credentials never live in the config object.
- :class:`PowerBIApiError`, :class:`PowerBIAuthError`,
  :class:`PowerBIPublishError` — typed exception hierarchy.
- :func:`build_gap_dataset_rows` / :func:`build_risk_dataset_rows`
  / :func:`build_collection_run_dataset_rows` — pure functions
  that produce JSON-serializable row dicts ready for the Push
  Datasets API. Easy to unit-test without a live Power BI
  workspace.
- :func:`publish_report` — high-level orchestration: build the
  datasets, authenticate to Power BI, ensure the datasets exist,
  push rows. Returns a :class:`PowerBIPublishResult`.

Per ``~/.claude/CLAUDE.md`` secret-handling protocol:

- The integration NEVER accepts a client secret in code at the CLI
  surface. The CLI surface (``evidentia integrations powerbi
  publish``) reads the secret from the env var named via
  ``--client-secret-env``.
- The client secret NEVER appears in API request bodies — only
  the env-var name does.

Design choice — Push Datasets API:

- Power BI offers two main programmatic surfaces: REST Push
  Datasets (real-time-ish, no underlying data store, good for
  dashboards) and "Datasets v2 / Fabric" (full Power BI Premium
  storage). v0.7.8 ships Push Datasets because it's:
    1. Available on the standard Power BI Pro license (no
       Premium add-on required)
    2. Doesn't require Power BI Premium / Fabric capacity
    3. Fits the "compliance dashboard" use case
       cleanly (small fact tables refreshed periodically)
- Power BI Embedded + service-side Tabular Model deployments are
  documented as a v0.7.9+ enhancement (different ship; different
  auth scope).

Auth modes supported:

- **Service Principal** — Azure AD service principal with the
  ``Dataset.ReadWrite.All`` workspace permission. Uses MSAL Python
  for the OAuth2 client-credentials flow. Recommended for
  production unattended publishing.
- **Username + password** — supported by MSAL but NOT exposed
  here; password auth is not a documented Power BI service-
  principal posture.
"""

from evidentia_integrations.powerbi.client import (
    PowerBIApiError,
    PowerBIAuthError,
    PowerBIClient,
    PowerBIPublishError,
)
from evidentia_integrations.powerbi.config import PowerBIConfig
from evidentia_integrations.powerbi.extract import (
    build_collection_run_dataset_rows,
    build_gap_dataset_rows,
    build_risk_dataset_rows,
)
from evidentia_integrations.powerbi.publish import (
    PowerBIPublishedDataset,
    PowerBIPublishResult,
    publish_report,
)

__all__ = [
    "PowerBIApiError",
    "PowerBIAuthError",
    "PowerBIClient",
    "PowerBIConfig",
    "PowerBIPublishError",
    "PowerBIPublishResult",
    "PowerBIPublishedDataset",
    "build_collection_run_dataset_rows",
    "build_gap_dataset_rows",
    "build_risk_dataset_rows",
    "publish_report",
]
