"""NIST 800-53 Rev 5 control mappings for Databricks findings.

Each mapping carries an OLIR relationship + per-rule justification so
the audit trail can defend why a particular Databricks observation
maps to a particular control. Spot-checked against NIST SP 800-53
Rev 5 control families and the specific Databricks feature's
security role.

v0.7.8 P0.1 ships PAT-inventory mappings only. Mappings for the
remaining 6 evidence sources (audit logs, lineage, clusters,
network, service principals, secrets) land alongside the
implementation of each sub-check.
"""

from __future__ import annotations

from evidentia_core.models.common import ControlMapping, OLIRRelationship


def _m(
    control_id: str,
    relationship: OLIRRelationship,
    justification: str,
) -> ControlMapping:
    return ControlMapping(
        framework="nist-800-53-rev5",
        control_id=control_id,
        relationship=relationship,
        justification=justification,
    )


# ── PAT (Personal Access Token) — AC-2, IA-5 ────────────────────────


PAT_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2",
        OLIRRelationship.SUBSET_OF,
        "AC-2 Account Management — PAT inventory enumerates "
        "non-interactive credentials issued to users + service "
        "accounts. Inventory is the foundation of account-management "
        "evidence: you can't review accounts you can't list.",
    ),
    _m(
        "IA-5",
        OLIRRelationship.SUBSET_OF,
        "IA-5 Authenticator Management — PATs are bearer-token "
        "authenticators. The inventory contributes to IA-5(1) "
        "lifecycle evidence (issuance + expiry tracking).",
    ),
]

PAT_LONG_LIVED_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2(11)",
        OLIRRelationship.SUBSET_OF,
        "AC-2(11) Usage Conditions — PAT lifetime exceeds the "
        "90-day rotation threshold. Long-lived authenticators "
        "accumulate compromise risk over time and limit the "
        "organization's ability to enforce credential-rotation "
        "policy.",
    ),
    _m(
        "IA-5(1)",
        OLIRRelationship.SUBSET_OF,
        "IA-5(1) Password-Based Authentication — although PATs are "
        "bearer tokens, IA-5(1)(d) Lifetime Restrictions apply by "
        "analogy: authenticators must have a maximum lifetime "
        "appropriate to their risk class.",
    ),
]

PAT_NEVER_EXPIRES_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2(11)",
        OLIRRelationship.SUBSET_OF,
        "AC-2(11) Usage Conditions — PAT was issued without an "
        "expiry date. Permanent credentials are higher-risk than "
        "any rotation-bounded credential and require explicit "
        "compensating controls (vault check-out, monitored "
        "logon, etc.) which the collector cannot verify.",
    ),
    _m(
        "IA-5(1)",
        OLIRRelationship.SUBSET_OF,
        "IA-5(1)(d) Lifetime Restrictions — explicit policy "
        "violation: an authenticator with no maximum lifetime "
        "fails the lifetime-restriction requirement outright.",
    ),
    _m(
        "AC-3",
        OLIRRelationship.RELATED_TO,
        "AC-3 Access Enforcement — secondary impact: a never-"
        "expiring credential bypasses time-bounded access decisions, "
        "weakening AC-3 enforcement guarantees over time.",
    ),
]


# ── Future mappings (placeholders for v0.7.8 P0.1 follow-up commits)


# WORKSPACE_AUDIT_LOG_MAPPINGS = [...]   # AU-2, AU-3
# TABLE_LINEAGE_MAPPINGS       = [...]   # SI-7, SR 11-7 (financial overlay)
# CLUSTER_COMPLIANCE_MAPPINGS  = [...]   # CM-2, CM-3, SI-2
# NETWORK_POLICY_MAPPINGS      = [...]   # SC-7
# SERVICE_PRINCIPAL_MAPPINGS   = [...]   # AC-2, AC-3
# SECRET_SCOPE_MAPPINGS        = [...]   # SC-12
