"""Generate bundled crosswalks — cross-framework control mappings.

Ships authoritative or authoritative-adjacent crosswalks for the most
commonly-referenced framework pairs. All mappings are informational and
uncopyrightable (the mapping concept is factual — "NIST AC-2 relates to
SOC 2 CC6.1" — not expressive authorship).

v0.2.x will extend this via live NIST OLIR harvesting in the refresh CI.
"""

from __future__ import annotations

import json
from pathlib import Path

from _generators import DATA_ROOT  # type: ignore[import-not-found]

MAPPINGS_DIR = DATA_ROOT / "mappings"


def emit_crosswalk(
    *,
    source_framework: str,
    target_framework: str,
    version: str,
    source: str,
    mappings: list[dict],
) -> Path:
    payload = {
        "source_framework": source_framework,
        "target_framework": target_framework,
        "version": version,
        "generated_at": "2026-04-16",
        "source": source,
        "mappings": mappings,
    }
    MAPPINGS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = MAPPINGS_DIR / f"{source_framework}_to_{target_framework}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


# ---------------------------------------------------------------------------
# NIST CSF 2.0 → NIST 800-53 (informative references from NIST OLIR)
# ---------------------------------------------------------------------------

CSF_TO_800_53 = [
    ("GV.OC-01", "AC-1", "related", "Policy linking mission to security"),
    ("GV.OC-03", "PL-2", "related", "System security plans document legal/regulatory requirements"),
    ("GV.RM-01", "PM-1", "equivalent", "Program management policy establishes risk objectives"),
    ("GV.RM-02", "PM-9", "equivalent", "Risk management strategy with appetite and tolerance"),
    ("GV.RR-02", "PS-7", "related", "Roles and responsibilities for security"),
    ("GV.SC-01", "SR-1", "equivalent", "Supply chain risk management policy"),
    ("GV.SC-05", "SR-3", "equivalent", "Supply chain controls and processes"),
    ("ID.AM-01", "CM-8", "equivalent", "Hardware inventory"),
    ("ID.AM-02", "CM-8", "equivalent", "Software inventory"),
    ("ID.AM-03", "AC-4", "related", "Network data flow mapping"),
    ("ID.RA-01", "RA-5", "equivalent", "Vulnerability identification"),
    ("ID.RA-05", "RA-3", "equivalent", "Risk determination"),
    ("PR.AA-01", "IA-2", "related", "Identity and credential management"),
    ("PR.AA-03", "IA-2", "equivalent", "User/device authentication"),
    ("PR.AA-05", "AC-3", "equivalent", "Access enforcement"),
    ("PR.AA-06", "PE-2", "related", "Physical access authorization"),
    ("PR.AT-01", "AT-2", "equivalent", "General security awareness training"),
    ("PR.AT-02", "AT-3", "equivalent", "Role-based training"),
    ("PR.DS-01", "SC-28", "equivalent", "Data-at-rest protection"),
    ("PR.DS-02", "SC-8", "equivalent", "Data-in-transit protection"),
    ("PR.DS-11", "CP-9", "equivalent", "Backup protection and testing"),
    ("PR.PS-01", "CM-2", "equivalent", "Baseline configuration management"),
    ("PR.PS-04", "AU-2", "equivalent", "Log record generation"),
    ("PR.PS-05", "CM-7", "related", "Prevent unauthorized software"),
    ("PR.IR-01", "AC-3", "related", "Network access control"),
    ("DE.CM-01", "SI-4", "equivalent", "Network monitoring"),
    ("DE.CM-03", "AU-12", "related", "Personnel activity logging"),
    ("DE.AE-02", "IR-4", "related", "Event analysis"),
    ("DE.AE-08", "IR-8", "related", "Incident declaration criteria"),
    ("RS.MA-01", "IR-4", "equivalent", "Incident response execution"),
    ("RS.MA-03", "IR-4", "equivalent", "Incident categorization and prioritization"),
    ("RS.CO-02", "IR-6", "equivalent", "Incident notification to stakeholders"),
    ("RS.MI-01", "IR-4", "equivalent", "Incident containment"),
    ("RS.MI-02", "IR-4", "equivalent", "Incident eradication"),
    ("RC.RP-01", "CP-10", "equivalent", "System recovery and reconstitution"),
    ("RC.RP-03", "CP-9", "equivalent", "Verify backup integrity before restore"),
]

emit_crosswalk(
    source_framework="nist-csf-2.0",
    target_framework="nist-800-53-mod",
    version="CSF 2.0 / 800-53 Rev 5",
    source="Derived from NIST OLIR informative references",
    mappings=[
        {
            "source_control_id": src,
            "source_control_title": "",
            "target_control_id": tgt,
            "target_control_title": "",
            "relationship": rel,
            "notes": notes,
        }
        for src, tgt, rel, notes in CSF_TO_800_53
    ],
)


# ---------------------------------------------------------------------------
# FedRAMP Moderate → CMMC Level 2 (both derive from NIST 800-53 / 800-171)
# ---------------------------------------------------------------------------

FEDRAMP_MOD_TO_CMMC_L2 = [
    ("AC-2", "CMMC.L2-3.1.1", "related", "Authorized user access"),
    ("AC-3", "CMMC.L2-3.1.2", "equivalent", "Transaction/function control"),
    ("AC-6", "CMMC.L2-3.1.5", "equivalent", "Least privilege"),
    ("AC-7", "CMMC.L2-3.1.8", "equivalent", "Unsuccessful logon attempts"),
    ("AC-11", "CMMC.L2-3.1.10", "equivalent", "Session lock"),
    ("AC-17", "CMMC.L2-3.1.12", "equivalent", "Remote access control"),
    ("AT-2", "CMMC.L2-3.2.1", "equivalent", "Security awareness"),
    ("AT-3", "CMMC.L2-3.2.2", "equivalent", "Role-based training"),
    ("AU-2", "CMMC.L2-3.3.1", "equivalent", "Event logging"),
    ("AU-3", "CMMC.L2-3.3.1", "related", "Audit record content"),
    ("AU-6", "CMMC.L2-3.3.5", "equivalent", "Audit record review"),
    ("AU-8", "CMMC.L2-3.3.7", "equivalent", "Time stamps"),
    ("CM-2", "CMMC.L2-3.4.1", "equivalent", "Baseline configuration"),
    ("CM-6", "CMMC.L2-3.4.2", "equivalent", "Configuration settings"),
    ("CM-7", "CMMC.L2-3.4.7", "equivalent", "Least functionality"),
    ("CM-8", "CMMC.L2-3.4.1", "related", "System component inventory"),
    ("IA-2", "CMMC.L2-3.5.3", "equivalent", "Multi-factor authentication"),
    ("IA-5", "CMMC.L2-3.5.7", "equivalent", "Authenticator management"),
    ("IR-4", "CMMC.L2-3.6.1", "equivalent", "Incident handling"),
    ("IR-6", "CMMC.L2-3.6.2", "equivalent", "Incident reporting"),
    ("MP-6", "CMMC.L2-3.8.3", "equivalent", "Media sanitization"),
    ("PE-2", "CMMC.L2-3.10.1", "equivalent", "Physical access authorization"),
    ("PE-3", "CMMC.L2-3.10.1", "related", "Physical access control"),
    ("RA-3", "CMMC.L2-3.11.1", "equivalent", "Risk assessment"),
    ("RA-5", "CMMC.L2-3.11.2", "equivalent", "Vulnerability scanning"),
    ("SC-7", "CMMC.L2-3.13.1", "equivalent", "Boundary protection"),
    ("SC-8", "CMMC.L2-3.13.8", "equivalent", "Transmission confidentiality"),
    ("SC-13", "CMMC.L2-3.13.11", "equivalent", "Cryptographic protection (FIPS)"),
    ("SC-28", "CMMC.L2-3.13.16", "equivalent", "Data at rest protection"),
    ("SI-2", "CMMC.L2-3.14.1", "equivalent", "Flaw remediation"),
    ("SI-3", "CMMC.L2-3.14.2", "equivalent", "Malicious code protection"),
    ("SI-4", "CMMC.L2-3.14.6", "equivalent", "System monitoring"),
]

emit_crosswalk(
    source_framework="fedramp-rev5-moderate",
    target_framework="cmmc-2-l2",
    version="FedRAMP Rev 5 / CMMC 2.0 Level 2 (2024 Final Rule)",
    source="Evidentia-authored based on DoD CMMC Assessment Guide correlations to NIST 800-171/800-53",
    mappings=[
        {
            "source_control_id": src,
            "source_control_title": "",
            "target_control_id": tgt,
            "target_control_title": "",
            "relationship": rel,
            "notes": notes,
        }
        for src, tgt, rel, notes in FEDRAMP_MOD_TO_CMMC_L2
    ],
)


# ---------------------------------------------------------------------------
# NIST 800-53 → HIPAA Security Rule
# ---------------------------------------------------------------------------

NIST_TO_HIPAA = [
    ("AC-2", "164.308(a)(4)(ii)(B)", "equivalent", "Access authorization"),
    ("AC-2", "164.308(a)(4)(ii)(C)", "related", "Access establishment and modification"),
    ("AC-3", "164.312(a)(1)", "equivalent", "Access control"),
    ("AU-2", "164.312(b)", "equivalent", "Audit controls"),
    ("CP-2", "164.308(a)(7)(i)", "equivalent", "Contingency plan"),
    ("CP-9", "164.308(a)(7)(ii)(A)", "equivalent", "Data backup plan"),
    ("CP-10", "164.308(a)(7)(ii)(B)", "equivalent", "Disaster recovery plan"),
    ("IA-2", "164.312(d)", "equivalent", "Person or entity authentication"),
    ("IA-5", "164.308(a)(5)(ii)(D)", "related", "Password management"),
    ("IR-4", "164.308(a)(6)(ii)", "equivalent", "Response and reporting"),
    ("MP-6", "164.310(d)(2)(i)", "equivalent", "Disposal"),
    ("PE-3", "164.310(a)(1)", "equivalent", "Facility access controls"),
    ("PS-3", "164.308(a)(3)(ii)(B)", "equivalent", "Workforce clearance"),
    ("PS-4", "164.308(a)(3)(ii)(C)", "equivalent", "Termination procedures"),
    ("RA-3", "164.308(a)(1)(ii)(A)", "equivalent", "Risk analysis"),
    ("SC-8", "164.312(e)(1)", "equivalent", "Transmission security"),
    ("SC-13", "164.312(e)(2)(ii)", "equivalent", "Encryption"),
    ("SC-28", "164.312(a)(2)(iv)", "equivalent", "Encryption at rest"),
    ("SI-2", "164.308(a)(5)(ii)(B)", "related", "Protection from malicious software"),
    ("AT-2", "164.308(a)(5)(i)", "equivalent", "Security awareness training"),
]

emit_crosswalk(
    source_framework="nist-800-53-mod",
    target_framework="hipaa-security",
    version="NIST 800-53 Rev 5 / HIPAA 2013 Omnibus",
    source="HHS OCR HIPAA Security Rule Crosswalk Guidance + NIST OLIR",
    mappings=[
        {
            "source_control_id": src,
            "source_control_title": "",
            "target_control_id": tgt,
            "target_control_title": "",
            "relationship": rel,
            "notes": notes,
        }
        for src, tgt, rel, notes in NIST_TO_HIPAA
    ],
)


# ---------------------------------------------------------------------------
# State privacy laws (VCDPA) → CCPA/CPRA canonical
# ---------------------------------------------------------------------------

VCDPA_TO_CCPA = [
    ("VCDPA.ACCESS", "CCPA.ACCESS", "equivalent", "Right to access"),
    ("VCDPA.DELETE", "CCPA.DELETE", "equivalent", "Right to delete"),
    ("VCDPA.CORRECT", "CCPA.CORRECT", "equivalent", "Right to correct"),
    ("VCDPA.PORTABILITY", "CCPA.PORTABILITY", "equivalent", "Right to portability"),
    ("VCDPA.OPT-OUT-SALE", "CCPA.OPT-OUT-SALE", "equivalent", "Opt out of sale"),
    ("VCDPA.OPT-OUT-PROFILING", "CCPA.OPT-OUT-PROFILING", "equivalent", "Opt out of profiling"),
    ("VCDPA.NOTICE", "CCPA.NOTICE", "equivalent", "Privacy notice"),
    ("VCDPA.CONSENT-SENSITIVE", "CCPA.CONSENT-SENSITIVE", "related", "Sensitive data — CCPA uses 'limit' rather than consent"),
    ("VCDPA.MINIMIZATION", "CCPA.MINIMIZATION", "equivalent", "Data minimization"),
    ("VCDPA.SECURITY", "CCPA.SECURITY", "equivalent", "Reasonable security"),
    ("VCDPA.DPA-CONTRACT", "CCPA.DPA-CONTRACT", "equivalent", "Processor contracts"),
    ("VCDPA.DPA-ASSESSMENT", "CCPA.DPA-ASSESSMENT", "equivalent", "DPIA / risk assessment"),
    ("VCDPA.NON-DISCRIMINATION", "CCPA.NON-DISCRIMINATION", "equivalent", "Non-discrimination"),
]

emit_crosswalk(
    source_framework="us-va-vcdpa",
    target_framework="us-ca-ccpa-cpra",
    version="VCDPA / CCPA-CPRA 2023",
    source="Evidentia-authored based on IAPP multi-state privacy matrix",
    mappings=[
        {
            "source_control_id": src,
            "source_control_title": "",
            "target_control_id": tgt,
            "target_control_title": "",
            "relationship": rel,
            "notes": notes,
        }
        for src, tgt, rel, notes in VCDPA_TO_CCPA
    ],
)


# ---------------------------------------------------------------------------
# ISO 27001 (stub) → NIST 800-53 (conceptual parity mapping)
# ---------------------------------------------------------------------------

ISO_TO_NIST = [
    ("A.5.1", "PM-1", "equivalent", "Information security policy"),
    ("A.5.2", "PS-7", "related", "Roles and responsibilities"),
    ("A.5.3", "AC-5", "equivalent", "Separation of duties"),
    ("A.5.15", "AC-3", "equivalent", "Access control"),
    ("A.5.16", "IA-2", "equivalent", "Identity management"),
    ("A.5.19", "SR-3", "equivalent", "Supplier relationships (supply chain)"),
    ("A.5.24", "IR-8", "equivalent", "Incident management planning"),
    ("A.5.29", "CP-2", "equivalent", "Business continuity"),
    ("A.6.3", "AT-2", "equivalent", "Awareness training"),
    ("A.7.2", "PE-3", "equivalent", "Physical entry"),
    ("A.7.14", "MP-6", "equivalent", "Secure disposal"),
    ("A.8.2", "AC-6", "equivalent", "Privileged access"),
    ("A.8.3", "AC-3", "related", "Information access restriction"),
    ("A.8.5", "IA-2", "equivalent", "Secure authentication"),
    ("A.8.7", "SI-3", "equivalent", "Malware protection"),
    ("A.8.8", "RA-5", "equivalent", "Vulnerability management"),
    ("A.8.9", "CM-2", "equivalent", "Configuration management"),
    ("A.8.13", "CP-9", "equivalent", "Information backup"),
    ("A.8.15", "AU-2", "equivalent", "Logging"),
    ("A.8.16", "SI-4", "equivalent", "Monitoring"),
    ("A.8.24", "SC-13", "equivalent", "Cryptography"),
    ("A.8.28", "SA-11", "equivalent", "Secure coding"),
    ("A.8.32", "CM-3", "equivalent", "Change management"),
]

emit_crosswalk(
    source_framework="iso-27001-2022",
    target_framework="nist-800-53-mod",
    version="ISO 27001:2022 / NIST 800-53 Rev 5",
    source="Evidentia-authored based on ISO/IEC 27001:2022 Annex A concordance with NIST 800-53 families",
    mappings=[
        {
            "source_control_id": src,
            "source_control_title": "",
            "target_control_id": tgt,
            "target_control_title": "",
            "relationship": rel,
            "notes": notes,
        }
        for src, tgt, rel, notes in ISO_TO_NIST
    ],
)


if __name__ == "__main__":
    print("Generated crosswalks.")
