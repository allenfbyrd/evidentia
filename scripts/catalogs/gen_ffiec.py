"""Generate FFIEC IT Examination Handbook bundled catalogs (v0.7.10 P1).

Authoritative source: <https://ithandbook.ffiec.gov/>. The FFIEC IT
Examination Handbook is published by the Federal Financial
Institutions Examination Council (a US federal interagency body
encompassing OCC + FRB + FDIC + NCUA + CFPB + State Liaison
Committee) and is **public domain** — works of the US federal
government are not eligible for copyright per 17 USC §105, and
inter-agency examination handbooks are explicitly classed as such.

This generator emits Tier A control catalogs for one of the 5
booklets in the FFIEC IT Handbook stack. The other 4 booklets
(Information Security / Audit / Management / Operations / plus
this one — Outsourcing Technology Services) follow the same
pattern; the v0.7.10 P1 first slice ships only the Outsourcing
booklet to establish the shape, with the remaining 4 + the FFIEC
Cybersecurity Assessment Tool + the OCC/SR 26-02 model-risk
catalog deferred to follow-up P1 sub-batches.

Cadence: each booklet is published ~once per several years; the
v0.7.10 manifest pins the 2004-published Outsourcing booklet which
remains the active examination guidance (last revised June 2004
plus 2008 + 2010 supplements; FFIEC has not retired it).
"""

from __future__ import annotations

from _generators import emit_control_catalog  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# FFIEC IT Examination Handbook — Outsourcing Technology Services booklet
# ---------------------------------------------------------------------------
#
# Structure: 7 examination categories (Roles + Responsibilities, Risk
# Management, Outsourcing Decision, Vendor Selection, Contract Issues,
# Ongoing Monitoring, Related Topics) × ~5 sub-elements each = ~30
# control items.
#
# Each control's ``id`` is structured as ``<chapter>.<section>``
# matching the booklet's numbered subsections so operators can
# trace from the bundled catalog back to the source PDF.
FFIEC_OUTSOURCING_URL = (
    "https://ithandbook.ffiec.gov/it-booklets/"
    "outsourcing-technology-services.aspx"
)


def _ctl(
    id_: str,
    title: str,
    description: str,
    family: str,
) -> dict[str, str]:
    return {
        "id": id_,
        "title": title,
        "description": description,
        "family": family,
    }


# Control catalog. Per the FFIEC public-domain stance, full
# authoritative paraphrases are bundled. Operators consuming this
# catalog should refer to the source URL for the full booklet
# narrative; the bundled descriptions are scoped to the
# control-objective level.
FFIEC_OUTSOURCING_CONTROLS: list[dict[str, str]] = [
    # --- 1. Roles + Responsibilities ---
    _ctl(
        "1.1",
        "Board and Senior Management Responsibility",
        "The board of directors and senior management are "
        "responsible for understanding the risks associated with "
        "outsourcing arrangements and ensuring effective risk "
        "management throughout the relationship lifecycle.",
        "1. Roles + Responsibilities",
    ),
    _ctl(
        "1.2",
        "Outsourcing Risk Management Function",
        "The institution establishes a clearly-defined outsourcing "
        "risk management function with documented authority + "
        "reporting lines to the board.",
        "1. Roles + Responsibilities",
    ),
    _ctl(
        "1.3",
        "Information Security Officer Involvement",
        "The Information Security Officer is involved in vendor "
        "selection + ongoing-monitoring decisions for arrangements "
        "involving sensitive customer data or operational impact.",
        "1. Roles + Responsibilities",
    ),
    # --- 2. Risk Management ---
    _ctl(
        "2.1",
        "Risk Assessment Methodology",
        "Outsourcing risk assessments cover: strategic / reputational "
        "/ operational / transaction / credit / compliance / country "
        "risks, prioritized by criticality of the outsourced "
        "function.",
        "2. Risk Management",
    ),
    _ctl(
        "2.2",
        "Critical Function Identification",
        "The institution identifies its critical business functions "
        "and applies enhanced due diligence + monitoring to vendors "
        "supporting them.",
        "2. Risk Management",
    ),
    _ctl(
        "2.3",
        "Concentration Risk Analysis",
        "The institution assesses concentration risk arising from "
        "reliance on a small number of vendors, geographic "
        "concentrations, or shared-service-provider relationships.",
        "2. Risk Management",
    ),
    _ctl(
        "2.4",
        "Subcontractor (4th Party) Risk",
        "The institution maintains visibility into critical "
        "subcontractor relationships used by primary vendors and "
        "extends ongoing-monitoring expectations to those parties.",
        "2. Risk Management",
    ),
    # --- 3. Outsourcing Decision ---
    _ctl(
        "3.1",
        "Strategic Alignment Review",
        "The decision to outsource is documented and reviewed for "
        "alignment with the institution's strategic objectives, "
        "regulatory obligations, and risk appetite.",
        "3. Outsourcing Decision",
    ),
    _ctl(
        "3.2",
        "Cost-Benefit + Risk-Adjusted Analysis",
        "The outsourcing business case includes risk-adjusted "
        "analysis of in-house vs vendor cost, capability, and "
        "quality dimensions.",
        "3. Outsourcing Decision",
    ),
    _ctl(
        "3.3",
        "Regulatory Notification (where required)",
        "The institution notifies the appropriate federal regulator "
        "of material outsourcing arrangements per 12 USC §1867 "
        "(BSCA) when applicable.",
        "3. Outsourcing Decision",
    ),
    # --- 4. Vendor Selection ---
    _ctl(
        "4.1",
        "Due Diligence Scope",
        "Vendor due diligence covers: financial condition, "
        "experience + reputation, business continuity capability, "
        "information security posture, regulatory compliance "
        "history, insurance coverage, and reference checks.",
        "4. Vendor Selection",
    ),
    _ctl(
        "4.2",
        "Information Security Posture Review",
        "Vendor security posture review covers: encryption + key "
        "management, access controls, audit logging, incident "
        "response, vulnerability + patch management, third-party "
        "audit reports (SOC 2, ISO 27001).",
        "4. Vendor Selection",
    ),
    _ctl(
        "4.3",
        "Business Continuity + Disaster Recovery Capability",
        "Vendor BC/DR capability is evaluated, including documented "
        "RTO + RPO targets, tested recovery procedures, and "
        "geographic resilience.",
        "4. Vendor Selection",
    ),
    _ctl(
        "4.4",
        "Pre-Contract Site Visit + Audit",
        "For critical relationships, the institution performs an "
        "on-site or virtual review of vendor facilities + controls "
        "before contract execution.",
        "4. Vendor Selection",
    ),
    # --- 5. Contract Issues ---
    _ctl(
        "5.1",
        "Contract Scope and Performance Standards",
        "The contract clearly defines the services in scope, "
        "performance standards (SLAs), and remedies for "
        "non-performance.",
        "5. Contract Issues",
    ),
    _ctl(
        "5.2",
        "Right-to-Audit Clause",
        "The contract grants the institution + its regulators the "
        "right to audit vendor controls + access vendor records "
        "relating to services provided.",
        "5. Contract Issues",
    ),
    _ctl(
        "5.3",
        "Confidentiality + Data Protection",
        "The contract addresses customer-data protection, "
        "confidentiality, breach notification timelines, and data "
        "return / destruction at contract end.",
        "5. Contract Issues",
    ),
    _ctl(
        "5.4",
        "Subcontracting Restrictions",
        "The contract restricts vendor subcontracting (assignment) "
        "to require prior institution approval for material "
        "transfers; flow-down clauses bind subcontractors to the "
        "same protections.",
        "5. Contract Issues",
    ),
    _ctl(
        "5.5",
        "Termination + Exit Provisions",
        "The contract includes clear termination triggers, notice "
        "periods, transition assistance obligations, and data "
        "return / portability requirements.",
        "5. Contract Issues",
    ),
    _ctl(
        "5.6",
        "Foreign-Based Vendor Considerations",
        "Contracts with foreign-based vendors address governing "
        "law, jurisdiction, regulatory access, and country-risk "
        "factors per FFIEC offshore-outsourcing guidance.",
        "5. Contract Issues",
    ),
    # --- 6. Ongoing Monitoring ---
    _ctl(
        "6.1",
        "Performance Monitoring",
        "Ongoing monitoring covers: SLA performance, financial "
        "condition, control effectiveness (via SOC 2 / ISO 27001 / "
        "right-to-audit), security incidents, regulatory matters.",
        "6. Ongoing Monitoring",
    ),
    _ctl(
        "6.2",
        "Periodic Risk Reassessment",
        "Vendor risk assessments are refreshed on a documented "
        "cadence (typically annual for critical vendors; biennial "
        "for moderate; triennial for low-impact).",
        "6. Ongoing Monitoring",
    ),
    _ctl(
        "6.3",
        "Incident + Issue Tracking",
        "Vendor-side security incidents, control deficiencies, and "
        "SLA misses are tracked + remediated via documented "
        "issue-management processes.",
        "6. Ongoing Monitoring",
    ),
    _ctl(
        "6.4",
        "Change Notification",
        "Vendors are required to notify the institution of material "
        "changes: ownership, key personnel, subcontracting, "
        "service-delivery model, or geographic location.",
        "6. Ongoing Monitoring",
    ),
    _ctl(
        "6.5",
        "Annual Senior-Management + Board Review",
        "Senior management + the board receive at-least-annual "
        "reports on the outsourcing portfolio: vendor list, risk "
        "ratings, performance, incidents, concentration analysis.",
        "6. Ongoing Monitoring",
    ),
    # --- 7. Related Topics ---
    _ctl(
        "7.1",
        "Cloud Computing Considerations",
        "Cloud arrangements receive enhanced scrutiny for shared-"
        "responsibility model clarity, multi-tenancy controls, "
        "data residency, and cross-border data flows.",
        "7. Related Topics",
    ),
    _ctl(
        "7.2",
        "Software-as-a-Service (SaaS) Arrangements",
        "SaaS arrangements are evaluated for vendor lock-in risk, "
        "data portability provisions, and service-availability "
        "track records.",
        "7. Related Topics",
    ),
    _ctl(
        "7.3",
        "Resilience + Concentration Across Critical Functions",
        "The institution's overall outsourcing posture is reviewed "
        "for resilience: avoiding single-point-of-failure vendor "
        "dependencies for critical operations.",
        "7. Related Topics",
    ),
    _ctl(
        "7.4",
        "Affiliate + Group-Level Outsourcing",
        "Intra-group outsourcing is documented + governed under the "
        "same standards as third-party outsourcing, including "
        "affiliate transactions per Regulation W.",
        "7. Related Topics",
    ),
    _ctl(
        "7.5",
        "Records Retention + Examination Access",
        "Vendor-held records are retained per the institution's "
        "retention policy + applicable regulatory requirements; "
        "regulators have access via the right-to-audit clause.",
        "7. Related Topics",
    ),
]


def main() -> None:
    """Emit the FFIEC IT Handbook Outsourcing booklet catalog."""
    emit_control_catalog(
        framework_id="ffiec-outsourcing",
        framework_name=(
            "FFIEC IT Examination Handbook — Outsourcing "
            "Technology Services booklet"
        ),
        version="June 2004 + 2008/2010 supplements",
        source=FFIEC_OUTSOURCING_URL,
        families=[
            "1. Roles + Responsibilities",
            "2. Risk Management",
            "3. Outsourcing Decision",
            "4. Vendor Selection",
            "5. Contract Issues",
            "6. Ongoing Monitoring",
            "7. Related Topics",
        ],
        controls=FFIEC_OUTSOURCING_CONTROLS,
        tier="A",
    )


if __name__ == "__main__":
    main()
