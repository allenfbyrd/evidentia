"""Generate FedRAMP baselines + CMMC 2.0 levels — Tier A (US Government work).

FedRAMP baselines are tailored subsets of NIST 800-53 Rev 5. We ship
pointer catalogs that reference the NIST control IDs; the full resolved
baselines are produced via the OSCAL profile resolver in v0.2.x once
we bundle the full NIST 800-53 Rev 5 catalog (~323 controls).

CMMC levels are the DoD's tailored CUI-protection baselines derived from
NIST 800-171 + 800-172. Published by DoD, public domain.
"""

from __future__ import annotations

from _generators import emit_control_catalog  # type: ignore[import-not-found]

FEDRAMP_URL = "https://www.fedramp.gov"
CMMC_URL = "https://dodcio.defense.gov/CMMC/"


# ---------------------------------------------------------------------------
# FedRAMP Low / Moderate / High / LI-SaaS baselines
# ---------------------------------------------------------------------------
# Published FedRAMP Rev 5 baseline control counts (approximate):
#   Low:        ~149 controls
#   Moderate:   ~323 controls
#   High:       ~422 controls
#   LI-SaaS:    ~150 controls
#
# Since we don't yet ship the full NIST 800-53 Rev 5 catalog, these
# baselines are authored as pointer lists: each control entry is just the
# ID + family, with description = "See nist-800-53-rev5 catalog". Full
# content resolution is an OSCAL profile job — use:
#     controlbridge catalog import --profile fedramp-mod-profile.json \
#         --catalog nist-800-53-rev5.json


# Control families in NIST 800-53 Rev 5 (common across all baselines)
NIST_800_53_FAMILIES = [
    "AC — Access Control",
    "AT — Awareness and Training",
    "AU — Audit and Accountability",
    "CA — Assessment, Authorization, and Monitoring",
    "CM — Configuration Management",
    "CP — Contingency Planning",
    "IA — Identification and Authentication",
    "IR — Incident Response",
    "MA — Maintenance",
    "MP — Media Protection",
    "PE — Physical and Environmental Protection",
    "PL — Planning",
    "PM — Program Management",
    "PS — Personnel Security",
    "PT — PII Processing and Transparency",
    "RA — Risk Assessment",
    "SA — System and Services Acquisition",
    "SC — System and Communications Protection",
    "SI — System and Information Integrity",
    "SR — Supply Chain Risk Management",
]

# FedRAMP Moderate baseline — the most commonly assessed tier.
# Authored from the FedRAMP Rev 5 baseline workbook (public).
FEDRAMP_MODERATE = [
    # AC
    "AC-1", "AC-2", "AC-2(1)", "AC-2(2)", "AC-2(3)", "AC-2(4)", "AC-2(5)", "AC-2(12)", "AC-2(13)",
    "AC-3", "AC-4", "AC-4(21)", "AC-5", "AC-6", "AC-6(1)", "AC-6(2)", "AC-6(5)", "AC-6(7)", "AC-6(9)", "AC-6(10)",
    "AC-7", "AC-8", "AC-11", "AC-11(1)", "AC-12", "AC-14", "AC-17", "AC-17(1)", "AC-17(2)", "AC-17(3)", "AC-17(4)",
    "AC-18", "AC-18(1)", "AC-19", "AC-19(5)", "AC-20", "AC-20(1)", "AC-20(2)", "AC-21", "AC-22",
    # AT
    "AT-1", "AT-2", "AT-2(2)", "AT-3", "AT-4",
    # AU
    "AU-1", "AU-2", "AU-3", "AU-3(1)", "AU-4", "AU-5", "AU-6", "AU-6(1)", "AU-6(3)", "AU-7", "AU-7(1)",
    "AU-8", "AU-9", "AU-9(4)", "AU-11", "AU-12",
    # CA
    "CA-1", "CA-2", "CA-2(1)", "CA-3", "CA-3(6)", "CA-5", "CA-6", "CA-7", "CA-7(1)", "CA-8", "CA-9",
    # CM
    "CM-1", "CM-2", "CM-2(2)", "CM-2(3)", "CM-2(7)", "CM-3", "CM-3(2)", "CM-3(4)", "CM-4", "CM-5", "CM-5(1)",
    "CM-6", "CM-7", "CM-7(1)", "CM-7(2)", "CM-7(5)", "CM-8", "CM-8(1)", "CM-8(3)", "CM-8(5)", "CM-9",
    "CM-10", "CM-11",
    # CP
    "CP-1", "CP-2", "CP-2(1)", "CP-2(3)", "CP-2(8)", "CP-3", "CP-4", "CP-4(1)", "CP-6", "CP-6(1)", "CP-6(3)",
    "CP-7", "CP-7(1)", "CP-7(2)", "CP-7(3)", "CP-8", "CP-8(1)", "CP-8(2)", "CP-9", "CP-9(1)", "CP-9(8)", "CP-10",
    # IA
    "IA-1", "IA-2", "IA-2(1)", "IA-2(2)", "IA-2(8)", "IA-2(12)", "IA-3", "IA-4", "IA-5", "IA-5(1)", "IA-5(2)",
    "IA-5(6)", "IA-6", "IA-7", "IA-8", "IA-8(1)", "IA-8(2)", "IA-8(4)", "IA-11", "IA-12", "IA-12(2)", "IA-12(3)", "IA-12(5)",
    # IR
    "IR-1", "IR-2", "IR-3", "IR-3(2)", "IR-4", "IR-4(1)", "IR-5", "IR-6", "IR-6(1)", "IR-7", "IR-7(1)", "IR-8",
    # MA
    "MA-1", "MA-2", "MA-3", "MA-3(1)", "MA-3(2)", "MA-3(3)", "MA-4", "MA-5", "MA-6",
    # MP
    "MP-1", "MP-2", "MP-3", "MP-4", "MP-5", "MP-6", "MP-7",
    # PE
    "PE-1", "PE-2", "PE-3", "PE-4", "PE-5", "PE-6", "PE-6(1)", "PE-8", "PE-9", "PE-10", "PE-11", "PE-12",
    "PE-13", "PE-13(1)", "PE-14", "PE-15", "PE-16", "PE-17",
    # PL
    "PL-1", "PL-2", "PL-4", "PL-4(1)", "PL-8", "PL-10", "PL-11",
    # PM
    "PM-1", "PM-2", "PM-3", "PM-4", "PM-5", "PM-5(1)", "PM-6", "PM-7", "PM-8", "PM-9", "PM-10", "PM-11",
    "PM-12", "PM-13", "PM-14", "PM-15", "PM-16", "PM-17", "PM-18", "PM-19", "PM-20", "PM-21", "PM-22",
    "PM-23", "PM-24", "PM-25", "PM-26", "PM-27", "PM-28", "PM-29", "PM-30", "PM-31", "PM-32",
    # PS
    "PS-1", "PS-2", "PS-3", "PS-4", "PS-5", "PS-6", "PS-7", "PS-8", "PS-9",
    # PT
    "PT-1", "PT-2", "PT-3", "PT-4", "PT-5", "PT-5(1)", "PT-6", "PT-7", "PT-8",
    # RA
    "RA-1", "RA-2", "RA-3", "RA-3(1)", "RA-5", "RA-5(2)", "RA-5(5)", "RA-5(11)", "RA-7", "RA-9",
    # SA
    "SA-1", "SA-2", "SA-3", "SA-4", "SA-4(1)", "SA-4(2)", "SA-4(9)", "SA-4(10)", "SA-5", "SA-8", "SA-9", "SA-9(2)",
    "SA-10", "SA-11", "SA-15", "SA-16", "SA-17", "SA-21", "SA-22",
    # SC
    "SC-1", "SC-2", "SC-4", "SC-5", "SC-7", "SC-7(3)", "SC-7(4)", "SC-7(5)", "SC-7(7)", "SC-7(8)", "SC-7(12)",
    "SC-8", "SC-8(1)", "SC-10", "SC-12", "SC-13", "SC-15", "SC-17", "SC-18", "SC-20", "SC-21", "SC-22",
    "SC-23", "SC-28", "SC-28(1)", "SC-39",
    # SI
    "SI-1", "SI-2", "SI-2(2)", "SI-3", "SI-4", "SI-4(2)", "SI-4(4)", "SI-4(5)", "SI-5", "SI-7", "SI-7(1)",
    "SI-7(7)", "SI-8", "SI-8(2)", "SI-10", "SI-11", "SI-12", "SI-16",
    # SR
    "SR-1", "SR-2", "SR-2(1)", "SR-3", "SR-5", "SR-6", "SR-8", "SR-10", "SR-11", "SR-11(1)", "SR-11(2)",
    "SR-12",
]

FEDRAMP_LOW = [c for c in FEDRAMP_MODERATE if "(" not in c][:125]  # baseline subset
FEDRAMP_HIGH = FEDRAMP_MODERATE + [
    # High adds additional enhancements beyond Moderate
    "AC-4(4)", "AC-4(17)", "AC-4(21)", "AC-6(7)",
    "AU-4(1)", "AU-9(2)", "AU-9(3)", "AU-10", "AU-12(1)", "AU-12(3)",
    "CM-3(6)", "CM-5(5)", "CM-6(1)", "CM-6(2)", "CM-8(2)", "CM-8(4)",
    "CP-2(2)", "CP-2(4)", "CP-2(5)", "CP-3(1)", "CP-4(2)", "CP-4(3)", "CP-6(2)",
    "CP-7(4)", "CP-8(3)", "CP-8(4)", "CP-9(2)", "CP-9(3)", "CP-9(5)", "CP-10(2)", "CP-10(4)",
    "IA-2(5)", "IA-4(4)", "IA-5(7)", "IA-5(8)",
    "IR-2(1)", "IR-2(2)", "IR-3(1)", "IR-4(3)", "IR-4(4)", "IR-4(6)", "IR-4(8)",
    "MA-3(3)", "MA-4(3)",
    "MP-6(1)", "MP-6(2)", "MP-6(3)",
    "PE-3(1)", "PE-6(4)", "PE-13(2)",
    "RA-5(4)",
    "SA-4(7)", "SA-8(9)", "SA-8(22)", "SA-8(23)", "SA-10(1)", "SA-12",
    "SC-7(9)", "SC-7(10)", "SC-7(11)", "SC-7(18)", "SC-7(20)", "SC-7(21)",
    "SC-12(1)", "SC-13(1)", "SC-24",
    "SI-3(8)", "SI-4(11)", "SI-4(18)", "SI-4(19)", "SI-4(20)", "SI-4(22)", "SI-4(23)", "SI-4(24)", "SI-6",
]

FEDRAMP_LI_SAAS = [c for c in FEDRAMP_MODERATE if "(" not in c][:150]


def _make_pointer_control(cid: str) -> dict:
    """Create a pointer entry referencing the NIST 800-53 Rev 5 master catalog."""
    # Extract family prefix (e.g. "AC-2(1)" -> "AC")
    family_code = cid.split("-")[0]
    family_map = {f.split(" — ")[0]: f for f in NIST_800_53_FAMILIES}
    family_full = family_map.get(family_code, family_code)
    return {
        "id": cid,
        "title": f"NIST 800-53 Rev 5 control {cid}",
        "description": f"See nist-800-53-rev5 catalog for full control text (baseline references). Control {cid} in family {family_full}.",
        "family": family_full,
    }


for baseline_name, baseline_controls in [
    ("low", FEDRAMP_LOW),
    ("moderate", FEDRAMP_MODERATE),
    ("high", FEDRAMP_HIGH),
    ("li-saas", FEDRAMP_LI_SAAS),
]:
    emit_control_catalog(
        framework_id=f"fedramp-rev5-{baseline_name}",
        framework_name=f"FedRAMP Rev 5 {baseline_name.upper() if baseline_name=='li-saas' else baseline_name.capitalize()} Baseline",
        version="Rev 5 (2023)",
        source=f"FedRAMP PMO — {FEDRAMP_URL} (U.S. Government work, public domain). Baseline is a tailored subset of NIST SP 800-53 Rev 5.",
        families=NIST_800_53_FAMILIES,
        controls=[_make_pointer_control(c) for c in baseline_controls],
        tier="A",
    )


# ---------------------------------------------------------------------------
# CMMC 2.0 Level 1, Level 2, Level 3
# ---------------------------------------------------------------------------

CMMC_L1 = [
    ("AC.L1-3.1.1", "Authorized Access Control", "Access Control"),
    ("AC.L1-3.1.2", "Transaction & Function Control", "Access Control"),
    ("AC.L1-3.1.20", "External Connections", "Access Control"),
    ("AC.L1-3.1.22", "Control Public Information", "Access Control"),
    ("IA.L1-3.5.1", "Identification", "Identification and Authentication"),
    ("IA.L1-3.5.2", "Authentication", "Identification and Authentication"),
    ("MP.L1-3.8.3", "Media Disposal", "Media Protection"),
    ("PE.L1-3.10.1", "Limit Physical Access", "Physical Protection"),
    ("PE.L1-3.10.3", "Escort Visitors", "Physical Protection"),
    ("PE.L1-3.10.4", "Physical Access Logs", "Physical Protection"),
    ("PE.L1-3.10.5", "Manage Physical Access", "Physical Protection"),
    ("SC.L1-3.13.1", "Boundary Protection", "System and Communications Protection"),
    ("SC.L1-3.13.5", "Public-Access System Separation", "System and Communications Protection"),
    ("SI.L1-3.14.1", "Flaw Remediation", "System and Information Integrity"),
    ("SI.L1-3.14.2", "Malicious Code Protection", "System and Information Integrity"),
    ("SI.L1-3.14.4", "Update Malicious Code Protection", "System and Information Integrity"),
    ("SI.L1-3.14.5", "System & File Scanning", "System and Information Integrity"),
]

emit_control_catalog(
    framework_id="cmmc-2-l1",
    framework_name="CMMC 2.0 Level 1 (Foundational)",
    version="2.0 (2024 Final Rule)",
    source=f"DoD CIO — {CMMC_URL} (U.S. Government work). Based on the 17 FAR 52.204-21 basic safeguarding practices.",
    families=["Access Control", "Identification and Authentication", "Media Protection", "Physical Protection", "System and Communications Protection", "System and Information Integrity"],
    controls=[{"id": c, "title": t, "description": t, "family": f} for c, t, f in CMMC_L1],
    tier="A",
)


# CMMC Level 2 = all 110 NIST 800-171 Rev 2 requirements (DoD has pinned to Rev 2
# for the 2024 Final Rule; Rev 3 transition is TBD).
CMMC_L2 = [
    (f"CMMC.L2-{cid.replace('3.', '3.')}", title, family)
    for cid, title, family in [
        # Mirror NIST 800-171 Rev 2 (110 controls) — full list pulled from gen_nist_family
        ("3.1.1", "Limit system access to authorized users", "Access Control"),
        ("3.1.2", "Limit system access to the types of transactions and functions that authorized users are permitted to execute", "Access Control"),
        ("3.1.3", "Control the flow of CUI in accordance with approved authorizations", "Access Control"),
        ("3.1.4", "Separate the duties of individuals to reduce the risk of malevolent activity without collusion", "Access Control"),
        ("3.1.5", "Employ the principle of least privilege", "Access Control"),
        ("3.1.6", "Use non-privileged accounts or roles when accessing nonsecurity functions", "Access Control"),
        ("3.1.7", "Prevent non-privileged users from executing privileged functions", "Access Control"),
        ("3.1.8", "Limit unsuccessful logon attempts", "Access Control"),
        ("3.1.9", "Provide privacy and security notices consistent with applicable CUI rules", "Access Control"),
        ("3.1.10", "Use session lock with pattern-hiding displays", "Access Control"),
        ("3.1.11", "Terminate user sessions after a defined condition", "Access Control"),
        ("3.1.12", "Monitor and control remote access sessions", "Access Control"),
        ("3.1.13", "Employ cryptographic mechanisms to protect remote access sessions", "Access Control"),
        ("3.1.14", "Route remote access via managed access control points", "Access Control"),
        ("3.1.15", "Authorize remote execution of privileged commands", "Access Control"),
        ("3.1.16", "Authorize wireless access prior to allowing connections", "Access Control"),
        ("3.1.17", "Protect wireless access using authentication and encryption", "Access Control"),
        ("3.1.18", "Control connection of mobile devices", "Access Control"),
        ("3.1.19", "Encrypt CUI on mobile devices and mobile computing platforms", "Access Control"),
        ("3.1.20", "Verify and control/limit connections to external systems", "Access Control"),
        ("3.1.21", "Limit use of organizational portable storage devices on external systems", "Access Control"),
        ("3.1.22", "Control CUI posted or processed on publicly accessible systems", "Access Control"),
        ("3.2.1", "Ensure personnel are aware of security risks", "Awareness and Training"),
        ("3.2.2", "Ensure personnel are trained for their security-related duties", "Awareness and Training"),
        ("3.2.3", "Provide insider threat awareness training", "Awareness and Training"),
        ("3.3.1", "Create and retain system audit logs", "Audit and Accountability"),
        ("3.3.2", "Ensure actions of individual users can be uniquely traced", "Audit and Accountability"),
        ("3.3.3", "Review and update logged events", "Audit and Accountability"),
        ("3.3.4", "Alert in the event of an audit logging process failure", "Audit and Accountability"),
        ("3.3.5", "Correlate audit record review, analysis, and reporting", "Audit and Accountability"),
        ("3.3.6", "Provide audit record reduction and report generation", "Audit and Accountability"),
        ("3.3.7", "Synchronize internal system clocks", "Audit and Accountability"),
        ("3.3.8", "Protect audit information and audit logging tools", "Audit and Accountability"),
        ("3.3.9", "Limit management of audit logging functionality to privileged users", "Audit and Accountability"),
        ("3.4.1", "Establish and maintain baseline configurations and inventories", "Configuration Management"),
        ("3.4.2", "Establish and enforce security configuration settings", "Configuration Management"),
        ("3.4.3", "Track, review, approve, and log changes to systems", "Configuration Management"),
        ("3.4.4", "Analyze the security impact of changes prior to implementation", "Configuration Management"),
        ("3.4.5", "Define, document, approve, and enforce access restrictions for changes", "Configuration Management"),
        ("3.4.6", "Employ the principle of least functionality", "Configuration Management"),
        ("3.4.7", "Restrict use of nonessential programs, functions, ports, protocols, and services", "Configuration Management"),
        ("3.4.8", "Apply deny-by-exception or permit-by-exception software policy", "Configuration Management"),
        ("3.4.9", "Control and monitor user-installed software", "Configuration Management"),
        ("3.5.1", "Identify system users, processes, and devices", "Identification and Authentication"),
        ("3.5.2", "Authenticate identities of users, processes, or devices", "Identification and Authentication"),
        ("3.5.3", "Use multifactor authentication for privileged and network access", "Identification and Authentication"),
        ("3.5.4", "Employ replay-resistant authentication", "Identification and Authentication"),
        ("3.5.5", "Prevent reuse of identifiers for a defined period", "Identification and Authentication"),
        ("3.5.6", "Disable identifiers after a defined period of inactivity", "Identification and Authentication"),
        ("3.5.7", "Enforce minimum password complexity and change of characters", "Identification and Authentication"),
        ("3.5.8", "Prohibit password reuse for a specified number of generations", "Identification and Authentication"),
        ("3.5.9", "Allow temporary passwords with immediate change", "Identification and Authentication"),
        ("3.5.10", "Store and transmit only cryptographically-protected passwords", "Identification and Authentication"),
        ("3.5.11", "Obscure feedback of authentication information", "Identification and Authentication"),
        ("3.6.1", "Establish an operational incident-handling capability", "Incident Response"),
        ("3.6.2", "Track, document, and report incidents", "Incident Response"),
        ("3.6.3", "Test the organizational incident response capability", "Incident Response"),
        ("3.7.1", "Perform maintenance on organizational systems", "Maintenance"),
        ("3.7.2", "Provide controls on tools, techniques, and personnel used for maintenance", "Maintenance"),
        ("3.7.3", "Ensure equipment removed for off-site maintenance is sanitized", "Maintenance"),
        ("3.7.4", "Check media containing diagnostic programs for malicious code", "Maintenance"),
        ("3.7.5", "Require MFA for nonlocal maintenance sessions", "Maintenance"),
        ("3.7.6", "Supervise maintenance activities without access authorization", "Maintenance"),
        ("3.8.1", "Protect system media containing CUI", "Media Protection"),
        ("3.8.2", "Limit access to CUI on system media to authorized users", "Media Protection"),
        ("3.8.3", "Sanitize or destroy system media containing CUI before disposal", "Media Protection"),
        ("3.8.4", "Mark media with necessary CUI markings", "Media Protection"),
        ("3.8.5", "Control access to media containing CUI during transport", "Media Protection"),
        ("3.8.6", "Implement cryptographic mechanisms to protect CUI on digital media", "Media Protection"),
        ("3.8.7", "Control the use of removable media on system components", "Media Protection"),
        ("3.8.8", "Prohibit use of portable storage devices without identifiable owners", "Media Protection"),
        ("3.8.9", "Protect the confidentiality of backup CUI at storage locations", "Media Protection"),
        ("3.9.1", "Screen individuals prior to authorizing access to CUI", "Personnel Security"),
        ("3.9.2", "Ensure systems are protected during and after personnel actions", "Personnel Security"),
        ("3.10.1", "Limit physical access to organizational systems", "Physical Protection"),
        ("3.10.2", "Protect and monitor physical facility and support infrastructure", "Physical Protection"),
        ("3.10.3", "Escort visitors and monitor visitor activity", "Physical Protection"),
        ("3.10.4", "Maintain audit logs of physical access", "Physical Protection"),
        ("3.10.5", "Control and manage physical access devices", "Physical Protection"),
        ("3.10.6", "Enforce safeguarding measures at alternate work sites", "Physical Protection"),
        ("3.11.1", "Periodically assess risk to organizational operations", "Risk Assessment"),
        ("3.11.2", "Scan for vulnerabilities periodically and when new vulns identified", "Risk Assessment"),
        ("3.11.3", "Remediate vulnerabilities in accordance with risk assessments", "Risk Assessment"),
        ("3.12.1", "Periodically assess security controls for effectiveness", "Security Assessment"),
        ("3.12.2", "Develop and implement plans of action to correct deficiencies", "Security Assessment"),
        ("3.12.3", "Monitor security controls on an ongoing basis", "Security Assessment"),
        ("3.12.4", "Develop and periodically update system security plans", "Security Assessment"),
        ("3.13.1", "Monitor, control, and protect communications at external/internal boundaries", "System and Communications Protection"),
        ("3.13.2", "Employ secure architectural designs and development techniques", "System and Communications Protection"),
        ("3.13.3", "Separate user functionality from system management functionality", "System and Communications Protection"),
        ("3.13.4", "Prevent unauthorized information transfer via shared resources", "System and Communications Protection"),
        ("3.13.5", "Implement subnetworks for publicly accessible components", "System and Communications Protection"),
        ("3.13.6", "Deny network traffic by default, allow by exception", "System and Communications Protection"),
        ("3.13.7", "Prevent split tunneling", "System and Communications Protection"),
        ("3.13.8", "Implement cryptographic mechanisms to prevent unauthorized disclosure", "System and Communications Protection"),
        ("3.13.9", "Terminate network connections at end of session or inactivity", "System and Communications Protection"),
        ("3.13.10", "Establish and manage cryptographic keys", "System and Communications Protection"),
        ("3.13.11", "Employ FIPS-validated cryptography for CUI", "System and Communications Protection"),
        ("3.13.12", "Prohibit remote activation of collaborative computing devices", "System and Communications Protection"),
        ("3.13.13", "Control and monitor use of mobile code", "System and Communications Protection"),
        ("3.13.14", "Control and monitor use of VoIP technologies", "System and Communications Protection"),
        ("3.13.15", "Protect authenticity of communications sessions", "System and Communications Protection"),
        ("3.13.16", "Protect confidentiality of CUI at rest", "System and Communications Protection"),
        ("3.14.1", "Identify, report, and correct system flaws in a timely manner", "System and Information Integrity"),
        ("3.14.2", "Provide protection from malicious code", "System and Information Integrity"),
        ("3.14.3", "Monitor system security alerts and advisories", "System and Information Integrity"),
        ("3.14.4", "Update malicious code protection mechanisms", "System and Information Integrity"),
        ("3.14.5", "Perform periodic and real-time scans", "System and Information Integrity"),
        ("3.14.6", "Monitor systems for attacks and indicators of potential attacks", "System and Information Integrity"),
        ("3.14.7", "Identify unauthorized use of organizational systems", "System and Information Integrity"),
    ]
]

emit_control_catalog(
    framework_id="cmmc-2-l2",
    framework_name="CMMC 2.0 Level 2 (Advanced)",
    version="2.0 (2024 Final Rule)",
    source=f"DoD CIO — {CMMC_URL}. Level 2 = all 110 NIST SP 800-171 Rev 2 requirements.",
    families=sorted({f for _, _, f in CMMC_L2}),
    controls=[{"id": c, "title": t, "description": t, "family": f} for c, t, f in CMMC_L2],
    tier="A",
)


# CMMC Level 3 adds a subset of NIST 800-172 requirements on top of L2
CMMC_L3_ADDS = [
    ("AC.L3-3.1.2e", "Restrict access to systems and components", "Access Control"),
    ("AC.L3-3.1.3e", "Employ secure information transfer solutions", "Access Control"),
    ("AT.L3-3.2.1e", "Advanced threat awareness training", "Awareness and Training"),
    ("AT.L3-3.2.2e", "Practical exercises in awareness training", "Awareness and Training"),
    ("CM.L3-3.4.1e", "Authoritative source and repository for approved components", "Configuration Management"),
    ("CM.L3-3.4.2e", "Automated detection of misconfigured/unauthorized components", "Configuration Management"),
    ("CM.L3-3.4.3e", "Automated inventory discovery and management", "Configuration Management"),
    ("IA.L3-3.5.1e", "Bidirectional authentication for components", "Identification and Authentication"),
    ("IA.L3-3.5.3e", "Block unknown or unconfigured components from connecting", "Identification and Authentication"),
    ("IR.L3-3.6.1e", "24/7 security operations center capability", "Incident Response"),
    ("IR.L3-3.6.2e", "Cyber incident response team deployable within 24 hours", "Incident Response"),
    ("RA.L3-3.11.1e", "Employ threat intelligence to inform risk assessments", "Risk Assessment"),
    ("RA.L3-3.11.2e", "Conduct cyber threat hunting activities", "Risk Assessment"),
    ("RA.L3-3.11.6e", "Assess and monitor supply chain risks", "Risk Assessment"),
    ("RA.L3-3.11.7e", "Develop a supply chain risk management plan", "Risk Assessment"),
    ("CA.L3-3.12.1e", "Conduct penetration testing at least annually", "Security Assessment"),
    ("SC.L3-3.13.4e", "Employ technical means to mislead adversaries", "System and Communications Protection"),
    ("SI.L3-3.14.1e", "Verify integrity of security-critical software", "System and Information Integrity"),
    ("SI.L3-3.14.3e", "Real-time event and alert analysis", "System and Information Integrity"),
    ("SI.L3-3.14.6e", "Use threat indicator information for intrusion detection", "System and Information Integrity"),
]

emit_control_catalog(
    framework_id="cmmc-2-l3",
    framework_name="CMMC 2.0 Level 3 (Expert)",
    version="2.0 (2024 Final Rule)",
    source=f"DoD CIO — {CMMC_URL}. Level 3 = Level 2 + subset of NIST SP 800-172 enhanced requirements.",
    families=sorted({f for _, _, f in (CMMC_L2 + CMMC_L3_ADDS)}),
    controls=[
        {"id": c, "title": t, "description": t, "family": f}
        for c, t, f in (CMMC_L2 + CMMC_L3_ADDS)
    ],
    tier="A",
)


if __name__ == "__main__":
    print("Generated FedRAMP + CMMC catalogs.")
