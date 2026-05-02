"""ServiceNow output integration — push gaps as records (v0.7.7 C2).

Closes the v0.7.3 P2 carry-forward item. Unlike the Jira integration
(bidirectional sync), the ServiceNow integration is push-only: it
creates records in ServiceNow's Table API for each open Evidentia
gap. Pull-back is intentionally out of scope for v0.7.7 — many
ServiceNow deployments use closed-loop workflows (Catalog Items,
Approvals, Workflow Engine) that the Jira-style sync model doesn't
fit cleanly.

Public surface::

    from evidentia_integrations.servicenow import (
        ServiceNowClient,
        ServiceNowConfig,
        gap_to_record_request,
        push_open_gaps,
    )

The default target table is ``incident`` (universal + always
available). Operators with the GRC plugin should override
``table_name`` to ``sn_grc_issue`` or a custom GRC table in
``ServiceNowConfig``.

Credentials are sourced from env vars per the secret-handling
protocol::

    EVIDENTIA_SERVICENOW_USER
    EVIDENTIA_SERVICENOW_PASSWORD

The base URL is the instance URL like ``https://acme.service-now.com``
— it must be HTTPS (the constructor refuses HTTP).
"""

from evidentia_integrations.servicenow.client import (
    ServiceNowApiError,
    ServiceNowClient,
    ServiceNowRecord,
)
from evidentia_integrations.servicenow.config import ServiceNowConfig
from evidentia_integrations.servicenow.mapper import (
    SEVERITY_TO_SN_PRIORITY,
    ServiceNowMappingError,
    gap_to_record_request,
)
from evidentia_integrations.servicenow.sync import (
    ServiceNowSyncOutcome,
    ServiceNowSyncResult,
    push_gap_to_servicenow,
    push_open_gaps,
)

__all__ = [
    "SEVERITY_TO_SN_PRIORITY",
    "ServiceNowApiError",
    "ServiceNowClient",
    "ServiceNowConfig",
    "ServiceNowMappingError",
    "ServiceNowRecord",
    "ServiceNowSyncOutcome",
    "ServiceNowSyncResult",
    "gap_to_record_request",
    "push_gap_to_servicenow",
    "push_open_gaps",
]
