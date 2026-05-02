"""NIST 800-53 Rev 5 control mappings for Snowflake findings.

Each mapping carries an OLIR relationship + per-rule justification so
the audit trail can defend why a particular Snowflake observation
maps to a particular control. Spot-checked against NIST SP 800-53
Rev 5 control families and the specific Snowflake feature's
security role.

v0.7.8 P0.2 ships LOGIN_HISTORY + USERS + GRANTS + masking +
network-policy + MFA mappings. ACCESS_HISTORY (lineage) +
failed-login-spike heuristic land in a follow-up commit per the
plan's DEFER candidates.
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


# ── LOGIN_HISTORY — AC-7, AU-2 ─────────────────────────────────────


LOGIN_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AU-2",
        OLIRRelationship.SUBSET_OF,
        "AU-2 Audit Events — LOGIN_HISTORY captures every "
        "authentication attempt against the Snowflake account, "
        "including IP, client app, role chosen, success/failure, "
        "and reported MFA status. This is the canonical AU-2 "
        "evidence stream for Snowflake.",
    ),
    _m(
        "AU-3",
        OLIRRelationship.SUBSET_OF,
        "AU-3 Content of Audit Records — LOGIN_HISTORY rows include "
        "the required AU-3 fields (event-time, user identity, "
        "result, source IP, client agent). The collector inventories "
        "the rows; downstream OSCAL emit reformats them into AU-3-"
        "compliant audit-record shapes.",
    ),
]

LOGIN_FAILED_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-7",
        OLIRRelationship.SUBSET_OF,
        "AC-7 Unsuccessful Logon Attempts — failed-login rows in "
        "LOGIN_HISTORY are the substrate AC-7 enforcement is "
        "evaluated against. The collector surfaces the raw inventory; "
        "spike-detection heuristics (sliding-window thresholds) are a "
        "separate sub-check that runs over the same data.",
    ),
    _m(
        "IR-4",
        OLIRRelationship.RELATED_TO,
        "IR-4 Incident Handling — clusters of failed-login attempts "
        "from the same source IP or against the same user are an "
        "incident-handling trigger. Inventory of failures is the "
        "minimum evidence; IR-4(8) Correlation with External "
        "Organizations + IR-4(11) Insider Threats benefit from this "
        "data being available for SIEM ingestion.",
    ),
]


# ── USERS + GRANTS — AC-2, AC-3, AC-6 ──────────────────────────────


USER_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2",
        OLIRRelationship.SUBSET_OF,
        "AC-2 Account Management — `account_usage.USERS` enumerates "
        "every account in the Snowflake account (human users + "
        "service users + legacy accounts). The inventory is required "
        "AC-2(a) (assign account managers) + AC-2(d) (specify "
        "authorized users) evidence.",
    ),
    _m(
        "AC-2(3)",
        OLIRRelationship.RELATED_TO,
        "AC-2(3) Disable Inactive Accounts — `LAST_SUCCESS_LOGIN` + "
        "`DISABLED` columns in USERS support inactivity-based "
        "disablement reviews. The inventory is the input to that "
        "control; enforcement is operator-driven.",
    ),
]

USER_DISABLED_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2(3)",
        OLIRRelationship.SUBSET_OF,
        "AC-2(3) Disable Inactive Accounts — user is marked "
        "`DISABLED = TRUE` in `account_usage.USERS`. Disabled "
        "accounts that retain grants are an attack surface if the "
        "disable flag can be flipped without the original "
        "authorization workflow being re-run. The inventory + "
        "disabled-state pairing is the evidence trail.",
    ),
]

USER_NEVER_LOGGED_IN_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-2",
        OLIRRelationship.RELATED_TO,
        "AC-2 Account Management — user has no recorded login "
        "history. May indicate an unused account that should be "
        "either documented as a service-only account or disabled "
        "per AC-2(3) Disable Inactive Accounts. The collector "
        "surfaces the observation; operator decides the disposition.",
    ),
]

GRANT_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-3",
        OLIRRelationship.SUBSET_OF,
        "AC-3 Access Enforcement — `account_usage.GRANTS_TO_USERS` "
        "+ `GRANTS_TO_ROLES` enumerate the access-control assignments "
        "Snowflake uses to enforce access decisions. Inventory of "
        "grants is the foundational AC-3 evidence + the input to "
        "AC-3(7) Role-based Access Control reviews.",
    ),
    _m(
        "AC-6",
        OLIRRelationship.SUBSET_OF,
        "AC-6 Least Privilege — grant inventory enables least-"
        "privilege review (AC-6(1) Authorize Access to Security "
        "Functions, AC-6(7) Review of User Privileges). The collector "
        "produces the inventory; the review is a periodic operator "
        "activity (often quarterly per FedRAMP).",
    ),
]

GRANT_ACCOUNTADMIN_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-6(7)",
        OLIRRelationship.SUBSET_OF,
        "AC-6(7) Review of User Privileges — ACCOUNTADMIN grants "
        "carry the highest privilege in a Snowflake account. Each "
        "ACCOUNTADMIN grant should appear on the periodic least-"
        "privilege review. The collector surfaces every active "
        "ACCOUNTADMIN grant for explicit attestation.",
    ),
    _m(
        "AC-2",
        OLIRRelationship.RELATED_TO,
        "AC-2 Account Management — privileged-role grants are "
        "categorized as 'privileged accounts' per AC-2(7) Privileged "
        "User Accounts; their inventory is required evidence.",
    ),
]


# ── MFA — IA-2 ─────────────────────────────────────────────────────


MFA_DISABLED_MAPPINGS: list[ControlMapping] = [
    _m(
        "IA-2(1)",
        OLIRRelationship.SUBSET_OF,
        "IA-2(1) Multi-Factor Authentication to Privileged Accounts "
        "— user has `HAS_MFA = FALSE` in `account_usage.USERS`. For "
        "FedRAMP Moderate + higher, every user (or at minimum every "
        "privileged user) MUST have MFA enabled. The collector "
        "surfaces the gap; remediation is an operator action via "
        "`ALTER USER ... SET MUST_CHANGE_PASSWORD = TRUE` + MFA "
        "enrollment workflow.",
    ),
    _m(
        "IA-2(2)",
        OLIRRelationship.RELATED_TO,
        "IA-2(2) Multi-Factor Authentication to Non-Privileged "
        "Accounts — MFA-disabled non-privileged users are still a "
        "compliance gap for FedRAMP High + DoD environments.",
    ),
]


# ── Masking + row-access policies — AC-3, SC-28 ────────────────────


MASKING_POLICY_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-3",
        OLIRRelationship.SUBSET_OF,
        "AC-3 Access Enforcement — masking policies enforce column-"
        "level access decisions (mask, hash, redact, or show in "
        "cleartext) based on the requesting role. Inventory is the "
        "AC-3 enforcement-control attestation: a column without a "
        "policy reveals raw data to anyone with table-level access.",
    ),
    _m(
        "SC-28",
        OLIRRelationship.SUBSET_OF,
        "SC-28 Protection of Information at Rest — for sensitive "
        "data classes (PII, PCI cardholder data, PHI, financial "
        "MNPI), masking policies are the in-database enforcement "
        "of confidentiality at rest. Policy inventory is the "
        "minimum evidence; operator confirms the policy logic "
        "matches the data-classification regime.",
    ),
]

ROW_ACCESS_POLICY_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "AC-3",
        OLIRRelationship.SUBSET_OF,
        "AC-3 Access Enforcement — row-access policies enforce "
        "row-level access decisions based on the requesting role + "
        "session context. Inventory is required AC-3 evidence; a "
        "table without a row-access policy means every role with "
        "table access sees every row.",
    ),
    _m(
        "AC-3(7)",
        OLIRRelationship.RELATED_TO,
        "AC-3(7) Role-based Access Control — row-access policies "
        "are the typical mechanism for tenant-scoped + region-scoped "
        "+ classification-scoped row filtering. Inventory + per-"
        "policy logic review is the standard AC-3(7) attestation.",
    ),
]


# ── Network policies — SC-7 ────────────────────────────────────────


NETWORK_POLICY_INVENTORY_MAPPINGS: list[ControlMapping] = [
    _m(
        "SC-7",
        OLIRRelationship.SUBSET_OF,
        "SC-7 Boundary Protection — Snowflake network policies are "
        "the account-level + user-level IP allowlist / blocklist "
        "controlling which network addresses can authenticate. "
        "Inventory of policies + their assignment to users is the "
        "primary SC-7(11) Restrict Incoming Communications evidence.",
    ),
    _m(
        "SC-7(5)",
        OLIRRelationship.RELATED_TO,
        "SC-7(5) Deny by Default + Allow by Exception — the "
        "preferred Snowflake configuration is account-level deny + "
        "explicit user-level allowlists. The inventory enables "
        "auditing for that configuration pattern.",
    ),
]

NETWORK_POLICY_NONE_ASSIGNED_MAPPINGS: list[ControlMapping] = [
    _m(
        "SC-7",
        OLIRRelationship.SUBSET_OF,
        "SC-7 Boundary Protection — no network policy is in effect "
        "at the account level. Authentication attempts can originate "
        "from any IP that can reach Snowflake's public endpoints. "
        "For FedRAMP + financial-services environments, an account-"
        "level policy is the baseline expectation. This finding is "
        "an explicit gap callout.",
    ),
]


# ── Encryption + key-rotation — SC-12 ──────────────────────────────


KEY_ROTATION_OPERATOR_FACT_MAPPINGS: list[ControlMapping] = [
    _m(
        "SC-12",
        OLIRRelationship.RELATED_TO,
        "SC-12 Cryptographic Key Establishment and Management — "
        "Snowflake's account-level encryption keys are managed by "
        "Snowflake itself; key-rotation cadence is a platform "
        "property + (for Tri-Secret Secure / customer-managed keys) "
        "an operator-controlled property. The collector ingests the "
        "operator-attested rotation cadence as a manifest-level "
        "attribute rather than a per-finding observation, since "
        "there's no API surface for the platform-managed cadence.",
    ),
]
