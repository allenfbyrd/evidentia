"""Databricks evidence collector for Evidentia (v0.7.8 P0.1).

Read-only collector that surfaces compliance-relevant evidence from a
Databricks workspace + Unity Catalog: Personal Access Token (PAT)
inventory (AC-2 / IA-5), workspace audit logs via Unity Catalog
system tables (AU-2 / AU-3), table + column lineage (SI-7), cluster
compliance (CM-2 / CM-3 / SI-2), workspace network policies (SC-7),
service-principal usage (AC-2 / AC-3), and secret-scope inventory
(SC-12).

Public surface::

    from evidentia_collectors.databricks import DatabricksCollector

    collector = DatabricksCollector(
        host="https://my-workspace.cloud.databricks.com",
        # Token sourced from DATABRICKS_TOKEN env var by the SDK
        # itself; pass token=os.environ[...] explicitly only when
        # bypassing the SDK's unified-auth layer.
    )
    findings, manifest = collector.collect_v2()

Or via context manager (recommended; releases the SDK client cleanly)::

    with DatabricksCollector(host="...") as c:
        findings, manifest = c.collect_v2()

Credentials per `~/.claude/CLAUDE.md` secret-handling protocol:

- The collector NEVER takes a token in code. The Databricks SDK's
  unified-auth resolver reads from the standard Databricks
  environment variables (``DATABRICKS_TOKEN``, ``DATABRICKS_HOST``,
  Azure AD config, AWS IAM credentials, etc.) — operators configure
  auth in the environment, not in code.
- For PAT auth specifically: set ``DATABRICKS_TOKEN`` to a PAT
  scoped to the principal that the collector runs as.

Required principal privileges:

- Workspace API:
  - ``can_use`` on the workspace itself (any user has this)
  - ``token_management`` permission (or workspace admin) to read
    token inventory; falls back to "current user only" if missing
- Account API (for cross-workspace evidence):
  - ``account admin`` role (only for cluster-policy + network-config
    collection at account level)
- Unity Catalog system tables (for audit-log + lineage evidence):
  - ``USE CATALOG`` on ``system``
  - ``SELECT`` on ``system.access.audit``,
    ``system.access.column_lineage``, ``system.access.table_lineage``
  - These are normally available to UC metastore admins; for
    non-admin principals, request the grant via
    ``GRANT USE CATALOG ON CATALOG system TO <principal>;``

Driver: ``databricks-sdk>=0.30``. Install via the ``[databricks]``
extra::

    pip install evidentia-collectors[databricks]

Auth modes supported (per the Databricks SDK's unified-auth resolver):

- Personal Access Token (``DATABRICKS_TOKEN`` env var)
- Azure Active Directory service principal
- AWS IAM (when the workspace is on AWS)
- OAuth machine-to-machine (``DATABRICKS_CLIENT_ID`` +
  ``DATABRICKS_CLIENT_SECRET`` env vars)
- ``.databrickscfg`` profile file (``~/.databrickscfg``, profile
  selected via ``DATABRICKS_CONFIG_PROFILE``)

The collector forwards to the SDK's resolver — no auth code lives
in this module.
"""

from evidentia_collectors.databricks.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    DatabricksAuthError,
    DatabricksCollector,
    DatabricksCollectorError,
    DatabricksPermissionError,
)

__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "DatabricksAuthError",
    "DatabricksCollector",
    "DatabricksCollectorError",
    "DatabricksPermissionError",
]
