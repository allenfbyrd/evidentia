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


# ── Cluster compliance — CM-2, CM-3, SI-2 ──────────────────────────


CLUSTER_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "CM-8",
        OLIRRelationship.SUBSET_OF,
        "CM-8 System Component Inventory — cluster enumeration is "
        "the foundational evidence for system-component inventory "
        "in a Databricks workspace. Each cluster is a compute node "
        "running user workloads; the inventory is required for "
        "configuration-management visibility.",
    ),
    _m(
        "CM-2",
        OLIRRelationship.RELATED_TO,
        "CM-2 Baseline Configuration — cluster inventory captures "
        "the runtime version + library set + init-script references "
        "that constitute the baseline configuration. Drift from a "
        "documented baseline is detected by diffing successive "
        "inventory snapshots.",
    ),
]

CLUSTER_OUTDATED_RUNTIME_MAPPINGS: list[ControlMapping] = [
    _m(
        "SI-2",
        OLIRRelationship.SUBSET_OF,
        "SI-2 Flaw Remediation — cluster runtime is below the "
        "current LTS. Outdated runtimes accumulate unpatched "
        "vulnerabilities (Spark CVEs, Java CVEs, Databricks "
        "platform CVEs). SI-2(2) Automated Flaw Remediation Status "
        "explicitly requires tracking which components are not on "
        "current patch level.",
    ),
    _m(
        "CM-2",
        OLIRRelationship.RELATED_TO,
        "CM-2(2) Baseline Configuration — Automation Support — an "
        "outdated runtime is a baseline-deviation indicator: the "
        "approved baseline is the current LTS; clusters not on it "
        "are deviations requiring remediation or explicit waiver.",
    ),
]

CLUSTER_INIT_SCRIPT_MAPPINGS: list[ControlMapping] = [
    _m(
        "CM-3",
        OLIRRelationship.RELATED_TO,
        "CM-3 Configuration Change Control — init scripts modify "
        "cluster configuration at startup (install packages, set "
        "env vars, write files). Their presence is a configuration-"
        "change vector that must be inventoried even if content "
        "isn't collectible from this surface (see "
        "EVIDENTIA-DATABRICKS-CLUSTER-INIT-SCRIPT-CONTENT BLIND_SPOT).",
    ),
    _m(
        "SI-2",
        OLIRRelationship.RELATED_TO,
        "SI-2 Flaw Remediation — init scripts often install patches "
        "or pin specific dependency versions for SI-2 compliance. "
        "The reference + path are inventoried for audit; content "
        "review is operator-driven.",
    ),
]


# ── Service Principal usage — AC-2, AC-3 ───────────────────────────


SERVICE_PRINCIPAL_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2",
        OLIRRelationship.SUBSET_OF,
        "AC-2 Account Management — service principals are non-"
        "interactive accounts used by automation. The inventory is "
        "required AC-2(a) (assign account managers) and AC-2(d) "
        "(specify authorized users) evidence for non-human "
        "identities — a frequently-overlooked compliance surface.",
    ),
    _m(
        "AC-3",
        OLIRRelationship.RELATED_TO,
        "AC-3 Access Enforcement — SPs are first-class principals "
        "that AC-3 access decisions apply to identically. The "
        "inventory + active/inactive state is the foundation for "
        "AC-3 evidence regarding non-interactive access.",
    ),
]

SERVICE_PRINCIPAL_INACTIVE_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2(3)",
        OLIRRelationship.SUBSET_OF,
        "AC-2(3) Disable Inactive Accounts — service principal is "
        "marked inactive in the workspace identity graph. Inactive "
        "non-interactive accounts that remain enabled are an attack "
        "surface; the typical remediation is to disable + revoke "
        "associated tokens.",
    ),
]


# ── Secret scopes — SC-12 ──────────────────────────────────────────


SECRET_SCOPE_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "SC-12",
        OLIRRelationship.SUBSET_OF,
        "SC-12 Cryptographic Key Establishment and Management — "
        "secret scopes are the workspace's secret-management surface; "
        "scope inventory is the foundation of SC-12(2) Symmetric "
        "Keys + SC-12(3) Asymmetric Keys evidence within Databricks.",
    ),
    _m(
        "IA-5",
        OLIRRelationship.RELATED_TO,
        "IA-5 Authenticator Management — secrets stored in scopes "
        "are typically authenticators for downstream systems "
        "(database passwords, API keys, OAuth refresh tokens). Scope "
        "enumeration is part of authenticator-management evidence.",
    ),
]

SECRET_SCOPE_DATABRICKS_BACKED_MAPPINGS: list[ControlMapping] = [
    _m(
        "SC-12",
        OLIRRelationship.RELATED_TO,
        "SC-12 — Databricks-backed scopes encrypt secrets with a "
        "workspace-controlled key. For higher-assurance "
        "deployments (FedRAMP / financial), Azure Key Vault-backed "
        "or AWS Secrets Manager-backed scopes are preferred — they "
        "delegate key management to the cloud provider's hardened "
        "KMS.",
    ),
]

SECRET_SCOPE_KEY_VAULT_BACKED_MAPPINGS: list[ControlMapping] = [
    _m(
        "SC-12",
        OLIRRelationship.SUBSET_OF,
        "SC-12 Cryptographic Key Establishment and Management — "
        "Azure Key Vault-backed scope delegates secret encryption "
        "to a cloud-provider KMS with HSM-backed keys. This is the "
        "preferred posture for SC-12 in regulated environments + "
        "satisfies SC-12(1) Availability + SC-12(3) Asymmetric "
        "Keys when the KMS is configured with HSM-backed keys.",
    ),
]


# ── Future mappings (placeholders for follow-up commits) ───────────


# WORKSPACE_AUDIT_LOG_MAPPINGS = [...]   # AU-2, AU-3 (needs SQL Warehouse)
# TABLE_LINEAGE_MAPPINGS       = [...]   # SI-7, SR 11-7 (needs SQL Warehouse)
# NETWORK_POLICY_MAPPINGS      = [...]   # SC-7 (needs Account API auth)
